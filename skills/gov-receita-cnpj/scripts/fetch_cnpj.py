"""Fetch corporate registration data and partners (QSA) from Receita Federal open mirrors into DuckDB."""

import sys
import time
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_cnpj, parse_currency, parse_date

app = typer.Typer(help="Fetch Receita Federal CNPJ and QSA (Quadro de Sócios) data")
console = Console()

API_ENDPOINTS = [
    "https://minhareceita.org/{cnpj}",
    "https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
]


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS rfb_empresas (
        cnpj VARCHAR PRIMARY KEY,
        cnpj_raiz VARCHAR,
        razao_social VARCHAR,
        nome_fantasia VARCHAR,
        situacao_cadastral VARCHAR,
        data_inicio_atividade DATE,
        cnae_principal VARCHAR,
        cnae_descricao VARCHAR,
        natureza_juridica VARCHAR,
        capital_social DOUBLE,
        porte VARCHAR,
        uf VARCHAR,
        municipio VARCHAR,
        codigo_ibge VARCHAR,
        opcao_simples BOOLEAN,
        opcao_mei BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS rfb_socios (
        id_socio VARCHAR PRIMARY KEY,
        cnpj_raiz VARCHAR,
        identificador_socio VARCHAR,
        nome_socio VARCHAR,
        cpf_cnpj_socio VARCHAR,
        qualificacao_socio VARCHAR,
        data_entrada_sociedade DATE,
        faixa_etaria VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


def fetch_cnpj_data(cnpj_raw: str) -> dict:
    cnpj_limpo, _, _ = normalize_cnpj(cnpj_raw)
    if not cnpj_limpo or len(cnpj_limpo) != 14:
        raise ValueError(f"CNPJ inválido: {cnpj_raw}")

    with GovHttpClient() as client:
        for template in API_ENDPOINTS:
            url = template.format(cnpj=cnpj_limpo)
            try:
                data = client.get_json(url)
                if data and isinstance(data, dict) and "razao_social" in data:
                    return data
            except Exception:
                continue

    raise RuntimeError(f"Não foi possível obter dados para o CNPJ {cnpj_limpo}")


@app.command()
def lookup(
    cnpj: str = typer.Argument(..., help="Número do CNPJ a consultar"),
):
    """Consulta um CNPJ individual e armazena empresa e sócios no DuckDB."""
    init_tables()
    db = get_db()

    cnpj_limpo, cnpj_fmt, cnpj_raiz = normalize_cnpj(cnpj)
    console.print(f"[bold cyan]🔍 Consultando CNPJ {cnpj_fmt} na base da Receita Federal...[/bold cyan]")

    try:
        data = fetch_cnpj_data(cnpj_limpo)
    except Exception as e:
        console.print(f"[red]Erro na consulta: {e}[/red]")
        return

    # Ingest Empresa
    empresa_record = [{
        "cnpj": cnpj_limpo,
        "cnpj_raiz": cnpj_raiz,
        "razao_social": data.get("razao_social", ""),
        "nome_fantasia": data.get("nome_fantasia", ""),
        "situacao_cadastral": str(data.get("descricao_situacao_cadastral") or data.get("situacao_cadastral") or ""),
        "data_inicio_atividade": parse_date(data.get("data_inicio_atividade")),
        "cnae_principal": str(data.get("cnae_fiscal") or ""),
        "cnae_descricao": str(data.get("cnae_fiscal_descricao") or ""),
        "natureza_juridica": str(data.get("natureza_juridica") or ""),
        "capital_social": parse_currency(data.get("capital_social")),
        "porte": str(data.get("porte") or data.get("descricao_porte") or ""),
        "uf": data.get("uf", ""),
        "municipio": data.get("municipio", ""),
        "codigo_ibge": str(data.get("codigo_municipio_ibge") or ""),
        "opcao_simples": bool(data.get("opcao_pelo_simples")),
        "opcao_mei": bool(data.get("opcao_pelo_mei")),
    }]

    df_empresa = pl.DataFrame(empresa_record)
    db.conn.register("tmp_rfb_empresa", df_empresa.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO rfb_empresas 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_rfb_empresa
    """)

    # Ingest Sócios
    qsa = data.get("qsa", []) or []
    socios_records = []
    for s in qsa:
        nome_socio = s.get("nome_socio") or s.get("nome") or ""
        cpf_cnpj_socio = s.get("cnpj_cpf_do_socio") or s.get("cpf_representante_legal") or ""
        id_socio = f"{cnpj_raiz}_{nome_socio[:20]}_{cpf_cnpj_socio}"

        socios_records.append({
            "id_socio": id_socio,
            "cnpj_raiz": cnpj_raiz,
            "identificador_socio": str(s.get("identificador_de_socio") or s.get("tipo") or ""),
            "nome_socio": nome_socio,
            "cpf_cnpj_socio": cpf_cnpj_socio,
            "qualificacao_socio": str(s.get("qualificacao_socio") or s.get("qualificacao_do_socio") or ""),
            "data_entrada_sociedade": parse_date(s.get("data_entrada_sociedade")),
            "faixa_etaria": str(s.get("faixa_etaria") or ""),
        })

    if socios_records:
        df_socios = pl.DataFrame(socios_records)
        db.conn.register("tmp_rfb_socios", df_socios.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO rfb_socios 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_rfb_socios
        """)

    console.print(f"[bold green]✓ Empresa gravada: {data.get('razao_social')}[/bold green]")
    console.print(f"[green]✓ {len(socios_records)} sócios vinculados no DuckDB.[/green]")


@app.command()
def enriquecer_fornecedores(
    limit: int = typer.Option(5, "--limit", "-l", help="Quantidade de fornecedores a enriquecer"),
):
    """Busca automaticamente na Receita Federal empresas do PNCP e da CEAP que ainda não estão no banco."""
    init_tables()
    db = get_db()

    tables = db.list_tables()
    cnpjs_para_buscar = set()

    # 1. Pega do PNCP
    if "pncp_contratos" in tables:
        rows = db.query("""
            SELECT DISTINCT ni_fornecedor 
            FROM pncp_contratos 
            WHERE LENGTH(ni_fornecedor) = 14
              AND ni_fornecedor NOT IN (SELECT cnpj FROM rfb_empresas)
            LIMIT ?
        """, [limit])
        for r in rows:
            cnpjs_para_buscar.add(r[0])

    # 2. Pega da CEAP
    if "camara_ceap_despesas" in tables and len(cnpjs_para_buscar) < limit:
        remaining = limit - len(cnpjs_para_buscar)
        rows = db.query("""
            SELECT DISTINCT cnpj_cpf_fornecedor 
            FROM camara_ceap_despesas 
            WHERE LENGTH(cnpj_cpf_fornecedor) = 14
              AND cnpj_cpf_fornecedor NOT IN (SELECT cnpj FROM rfb_empresas)
            LIMIT ?
        """, [remaining])
        for r in rows:
            cnpjs_para_buscar.add(r[0])

    if not cnpjs_para_buscar:
        console.print("[green]Todos os principais fornecedores já estão enriquecidos no banco![/green]")
        return

    console.print(f"[bold cyan]🔍 Enriquecendo {len(cnpjs_para_buscar)} fornecedores com dados da Receita Federal...[/bold cyan]")
    for c in cnpjs_para_buscar:
        try:
            lookup(c)
            time.sleep(0.5)  # Respeito ao rate limit das APIs públicas
        except Exception as e:
            console.print(f"[yellow]Não foi possível enriquecer {c}: {e}[/yellow]")


if __name__ == "__main__":
    app()
