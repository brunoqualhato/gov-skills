"""Fetch and ingest CGU sanctions (CEIS, CNEP, CEPIM) into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.config import settings
from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_cpf, parse_date

app = typer.Typer(help="Fetch CGU Transparency Portal sanctions and public data")
console = Console()

CGU_BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"


def init_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS cgu_sancoes (
        id_sancao VARCHAR PRIMARY KEY,
        tipo_cadastro VARCHAR,
        cnpj_sancionado VARCHAR,
        cnpj_raiz VARCHAR,
        cpf_sancionado VARCHAR,
        nome_sancionado VARCHAR,
        orgao_sancionador VARCHAR,
        uf_orgao VARCHAR,
        data_inicio_sancao DATE,
        data_fim_sancao DATE,
        motivo VARCHAR,
        fundamentacao_legal VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def sancoes(
    tipo: str = typer.Option("ceis", "--tipo", "-t", help="Tipo de cadastro: ceis ou cnep"),
    max_paginas: int = typer.Option(5, "--max-paginas", "-p", help="Máximo de páginas a coletar"),
):
    """Coleta sanções ativas do CEIS ou CNEP via API oficial."""
    init_table()
    db = get_db()

    api_key = settings.CGU_API_KEY
    if not api_key:
        console.print("[yellow]Aviso: 'CGU_API_KEY' não configurada no arquivo .env.[/yellow]")
        console.print("[dim]Para obter uma chave gratuita, cadastre-se em: https://portaldatransparencia.gov.br/api-de-dados/cadastrar[/dim]")
        return

    headers = {"chave-api-dados": api_key}
    endpoint = f"{CGU_BASE_URL}/{tipo.lower()}"
    records = []

    console.print(f"[bold cyan]🔍 Coletando sanções do cadastro {tipo.upper()} via API CGU...[/bold cyan]")
    with GovHttpClient(headers=headers) as client:
        for pag in range(1, max_paginas + 1):
            params = {"pagina": pag}
            try:
                data = client.get_json(endpoint, params=params)
            except Exception as e:
                console.print(f"[red]Erro ao consultar página {pag}: {e}[/red]")
                break

            if not data or not isinstance(data, list):
                console.print(f"[dim]Sem mais registros na página {pag}.[/dim]")
                break

            for item in data:
                sancionado = item.get("sancionado", {})
                orgao = item.get("orgaoSancionador", {})
                
                cpf_cnpj = str(sancionado.get("codigoFormatado") or "")
                cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cpf_cnpj)
                cpf_limpo, _ = normalize_cpf(cpf_cnpj)

                id_sancao = f"{tipo.upper()}_{item.get('id') or len(records)}"

                records.append({
                    "id_sancao": id_sancao,
                    "tipo_cadastro": tipo.upper(),
                    "cnpj_sancionado": cnpj_limpo if (cnpj_limpo and len(cnpj_limpo) == 14) else None,
                    "cnpj_raiz": cnpj_raiz if (cnpj_limpo and len(cnpj_limpo) == 14) else None,
                    "cpf_sancionado": cpf_limpo if (cpf_limpo and len(cpf_limpo) <= 11) else None,
                    "nome_sancionado": sancionado.get("nome", ""),
                    "orgao_sancionador": orgao.get("nome", ""),
                    "uf_orgao": orgao.get("siglaUf", ""),
                    "data_inicio_sancao": parse_date(item.get("dataInicioSancao")),
                    "data_fim_sancao": parse_date(item.get("dataFimSancao")),
                    "motivo": item.get("motivo", "") or item.get("textoPublicacao", ""),
                    "fundamentacao_legal": item.get("fundamentacaoLegal", ""),
                })

            console.print(f"[green]✓ Página {pag}/{max_paginas} processada: {len(data)} sanções.[/green]")

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_cgu_sancoes", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO cgu_sancoes 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_cgu_sancoes
        """)
        total = db.count("cgu_sancoes")
        console.print(f"[bold green]✨ Sucesso! {len(records)} sanções ingeridas no DuckDB. Total: {total}[/bold green]")


@app.command()
def importar_csv(
    arquivo: Path = typer.Option(..., "--arquivo", "-f", help="Caminho do CSV baixado do Portal da Transparência"),
    tipo: str = typer.Option("CEIS", "--tipo", "-t", help="Tipo de sanção: CEIS, CNEP ou CEPIM"),
):
    """Importa arquivo CSV baixado manualmente da seção 'Download de Dados' do Portal da Transparência."""
    if not arquivo.exists():
        console.print(f"[red]Arquivo não encontrado: {arquivo}[/red]")
        return

    init_table()
    db = get_db()

    console.print(f"[bold cyan]🔍 Lendo CSV {arquivo.name}...[/bold cyan]")
    # CSV da CGU costuma ter codificação latin-1 e separador ';'
    try:
        df_raw = pl.read_csv(str(arquivo), separator=";", encoding="latin1", ignore_errors=True)
    except Exception:
        df_raw = pl.read_csv(str(arquivo), separator=";", ignore_errors=True)

    console.print(f"[cyan]Processando {len(df_raw)} registros do arquivo...[/cyan]")
    records = []
    for row in df_raw.iter_rows(named=True):
        cnpj_cpf = str(row.get("CPF ou CNPJ do Sancionado") or row.get("CNPJ Sancionado") or "")
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj_cpf)

        id_sancao = f"{tipo.upper()}_{row.get('Número do Processo', '')}_{len(records)}"

        records.append({
            "id_sancao": id_sancao,
            "tipo_cadastro": tipo.upper(),
            "cnpj_sancionado": cnpj_limpo if (cnpj_limpo and len(cnpj_limpo) == 14) else None,
            "cnpj_raiz": cnpj_raiz if (cnpj_limpo and len(cnpj_limpo) == 14) else None,
            "cpf_sancionado": cnpj_cpf if (len(cnpj_cpf) <= 11) else None,
            "nome_sancionado": str(row.get("Nome do Sancionado") or row.get("Razão Social") or ""),
            "orgao_sancionador": str(row.get("Órgão Sancionador") or ""),
            "uf_orgao": str(row.get("UF Órgão Sancionador") or ""),
            "data_inicio_sancao": parse_date(str(row.get("Data Início Sanção") or "")),
            "data_fim_sancao": parse_date(str(row.get("Data Fim Sanção") or "")),
            "motivo": str(row.get("Motivo") or row.get("Texto da Publicação") or ""),
            "fundamentacao_legal": str(row.get("Fundamentação Legal") or ""),
        })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_cgu_csv", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO cgu_sancoes 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_cgu_csv
        """)
        total = db.count("cgu_sancoes")
        console.print(f"[bold green]✨ Sucesso! {len(records)} sanções importadas do CSV para o DuckDB. Total: {total}[/bold green]")


if __name__ == "__main__":
    app()
