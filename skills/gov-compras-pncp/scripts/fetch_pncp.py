"""Script to fetch public contracts from PNCP (Portal Nacional de Contratações Públicas) and store in DuckDB."""

import sys
from datetime import datetime, timedelta
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_cnpj, parse_currency, parse_date

app = typer.Typer(help="Fetch and ingest PNCP contracts into DuckDB")
console = Console()

PNCP_BASE_URL = "https://pncp.gov.br/api/consulta/v1"


def init_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS pncp_contratos (
        id_contrato VARCHAR PRIMARY KEY,
        numero_contrato VARCHAR,
        ano_contrato INTEGER,
        tipo_contrato VARCHAR,
        orgao_cnpj VARCHAR,
        orgao_nome VARCHAR,
        orgao_esfera VARCHAR,
        orgao_uf VARCHAR,
        municipio_ibge VARCHAR,
        ni_fornecedor VARCHAR,
        cnpj_raiz_fornecedor VARCHAR,
        nome_fornecedor VARCHAR,
        tipo_fornecedor VARCHAR,
        objeto VARCHAR,
        valor_inicial DOUBLE,
        valor_global DOUBLE,
        data_assinatura DATE,
        data_inicio_vigencia DATE,
        data_fim_vigencia DATE,
        categoria_processo VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def fetch(
    dias: int = typer.Option(7, "--dias", "-d", help="Número de dias retroativos para coletar"),
    max_paginas: int = typer.Option(3, "--max-paginas", "-p", help="Quantidade máxima de páginas a coletar"),
    uf: str = typer.Option(None, "--uf", help="Filtrar por UF (ex: DF, SP, RJ)"),
    tamanho_pagina: int = typer.Option(50, "--tamanho-pagina", help="Itens por página (máx 50)"),
):
    """Coleta contratos públicos do PNCP e grava no DuckDB."""
    init_table()
    db = get_db()

    data_fim = datetime.now()
    data_ini = data_fim - timedelta(days=dias)
    data_ini_str = data_ini.strftime("%Y%m%d")
    data_fim_str = data_fim.strftime("%Y%m%d")

    console.print(f"[bold cyan]🔍 Buscando contratos do PNCP de {data_ini.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}...[/bold cyan]")

    records = []
    with GovHttpClient() as client:
        for pag in range(1, max_paginas + 1):
            params = {
                "dataInicial": data_ini_str,
                "dataFinal": data_fim_str,
                "pagina": pag,
                "tamanhoPagina": tamanho_pagina,
            }
            if uf:
                params["uf"] = uf.upper()

            url = f"{PNCP_BASE_URL}/contratos"
            try:
                res = client.get_json(url, params=params)
            except Exception as e:
                console.print(f"[yellow]Aviso ao buscar página {pag}: {e}[/yellow]")
                break

            data = res.get("data", []) if isinstance(res, dict) else res
            if not data:
                console.print(f"[dim]Página {pag} retornou sem mais resultados.[/dim]")
                break

            for item in data:
                orgao = item.get("orgaoEntidade", {})
                fornecedor = item.get("fornecedor", {}) or {}
                
                ni_raw = item.get("niFornecedor") or fornecedor.get("niFornecedor") or ""
                cnpj_limpo, _, cnpj_raiz = normalize_cnpj(ni_raw)

                orgao_cnpj_raw = orgao.get("cnpj", "")
                orgao_cnpj, _, _ = normalize_cnpj(orgao_cnpj_raw)

                id_contrato = f"{orgao_cnpj_raw}_{item.get('anoContrato', '')}_{item.get('numeroContratoEmpenho', '')}_{item.get('sequencialContrato', pag)}"

                records.append({
                    "id_contrato": id_contrato,
                    "numero_contrato": str(item.get("numeroContratoEmpenho") or item.get("sequencialContrato") or ""),
                    "ano_contrato": int(item.get("anoContrato") or 0),
                    "tipo_contrato": str(item.get("tipoContrato", {}).get("nome") if isinstance(item.get("tipoContrato"), dict) else item.get("tipoContrato") or ""),
                    "orgao_cnpj": orgao_cnpj or orgao_cnpj_raw,
                    "orgao_nome": orgao.get("razaoSocial", ""),
                    "orgao_esfera": orgao.get("esferaId", ""),
                    "orgao_uf": orgao.get("ufSigla", ""),
                    "municipio_ibge": str(orgao.get("codigoIbge") or ""),
                    "ni_fornecedor": cnpj_limpo or ni_raw,
                    "cnpj_raiz_fornecedor": cnpj_raiz,
                    "nome_fornecedor": item.get("nomeRazaoSocialFornecedor") or fornecedor.get("razaoSocial") or "",
                    "tipo_fornecedor": item.get("tipoPessoa", ""),
                    "objeto": item.get("objetoContrato", ""),
                    "valor_inicial": parse_currency(item.get("valorInicial")),
                    "valor_global": parse_currency(item.get("valorGlobal")),
                    "data_assinatura": parse_date(item.get("dataAssinatura")),
                    "data_inicio_vigencia": parse_date(item.get("dataVigenciaInicio")),
                    "data_fim_vigencia": parse_date(item.get("dataVigenciaFim")),
                    "categoria_processo": item.get("categoriaProcesso", {}).get("nome", "") if isinstance(item.get("categoriaProcesso"), dict) else "",
                })

            console.print(f"[green]✓ Página {pag}/{max_paginas} processada: {len(data)} contratos encontrados.[/green]")

    if records:
        df = pl.DataFrame(records)
        # Upsert into DuckDB
        db.conn.register("tmp_pncp_batch", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO pncp_contratos 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_pncp_batch
        """)
        total = db.count("pncp_contratos")
        console.print(f"[bold green]✨ Sucesso! Total de contratos armazenados no DuckDB: {total}[/bold green]")
    else:
        console.print("[yellow]Nenhum registro encontrado no período.[/yellow]")


if __name__ == "__main__":
    app()
