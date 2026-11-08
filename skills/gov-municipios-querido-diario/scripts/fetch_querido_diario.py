"""Fetch and index municipal official gazette excerpts via Querido Diário API into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import parse_date

app = typer.Typer(help="Fetch municipal gazettes from Querido Diário")
console = Console()

QD_API_URL = "https://queridodiario.ok.org.br/api/gazettes"


def init_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS querido_diario_publicacoes (
        id_publicacao VARCHAR PRIMARY KEY,
        codigo_ibge VARCHAR,
        nome_municipio VARCHAR,
        uf_sigla VARCHAR,
        data_publicacao DATE,
        termo_pesquisado VARCHAR,
        trecho_destaque VARCHAR,
        url_pdf VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def search(
    termo: str = typer.Option(..., "--termo", "-t", help="Termo ou CNPJ para buscar nos diários municipais"),
    ibge: str = typer.Option(None, "--ibge", help="Filtrar por código IBGE do município"),
    limit: int = typer.Option(20, "--limit", "-l", help="Quantidade máxima de publicações a trazer"),
):
    """Busca publicações oficiais municipais e armazena trechos relevantes no DuckDB."""
    init_table()
    db = get_db()

    params = {
        "querystring": termo,
        "size": min(limit, 50),
    }
    if ibge:
        params["territory_ids"] = ibge

    console.print(f"[bold cyan]🔍 Pesquisando '{termo}' nos Diários Oficiais Municipais (Querido Diário)...[/bold cyan]")
    with GovHttpClient() as client:
        try:
            res = client.get_json(QD_API_URL, params=params)
        except Exception as e:
            console.print(f"[red]Erro ao consultar Querido Diário: {e}[/red]")
            return

    gazettes = res.get("gazettes", []) if isinstance(res, dict) else []
    total_found = res.get("total_gazettes", len(gazettes))

    console.print(f"[green]✓ Encontradas {total_found} ocorrências em todo o país. Processando amostra...[/green]")

    records = []
    for g in gazettes:
        excerpts = g.get("excerpts", [])
        snippet = " [...] ".join(excerpts)[:400] if excerpts else ""
        url_doc = g.get("url") or ""
        doc_id = f"{g.get('territory_id')}_{g.get('date')}_{abs(hash(url_doc)) % 1000000}"

        records.append({
            "id_publicacao": doc_id,
            "codigo_ibge": str(g.get("territory_id") or ""),
            "nome_municipio": str(g.get("territory_name") or ""),
            "uf_sigla": str(g.get("state_code") or ""),
            "data_publicacao": parse_date(g.get("date")),
            "termo_pesquisado": termo,
            "trecho_destaque": snippet,
            "url_pdf": url_doc,
        })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_qd_batch", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO querido_diario_publicacoes 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_qd_batch
        """)
        total = db.count("querido_diario_publicacoes")
        console.print(f"[bold green]✨ {len(records)} publicações municipais salvas no DuckDB. Total: {total}[/bold green]")
    else:
        console.print("[yellow]Nenhuma publicação encontrada para o termo.[/yellow]")


if __name__ == "__main__":
    app()
