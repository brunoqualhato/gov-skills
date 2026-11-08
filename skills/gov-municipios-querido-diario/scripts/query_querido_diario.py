"""CLI query tool for municipal gazettes in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Query municipal gazettes stored in DuckDB")
console = Console()


@app.command()
def list_gazettes(
    termo: str = typer.Option(None, "--termo", "-t", help="Termo pesquisado"),
    municipio: str = typer.Option(None, "--municipio", "-m", help="Nome do município"),
    uf: str = typer.Option(None, "--uf", help="Sigla da UF"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade máxima"),
):
    """Exibe publicações de diários municipais armazenadas."""
    db = get_db()
    if "querido_diario_publicacoes" not in db.list_tables():
        console.print("[yellow]A tabela 'querido_diario_publicacoes' ainda não existe.[/yellow]")
        return

    where_clauses = []
    params = []

    if termo:
        where_clauses.append("LOWER(termo_pesquisado) LIKE ?")
        params.append(f"%{termo.lower()}%")

    if municipio:
        where_clauses.append("LOWER(nome_municipio) LIKE ?")
        params.append(f"%{municipio.lower()}%")

    if uf:
        where_clauses.append("UPPER(uf_sigla) = ?")
        params.append(uf.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            nome_municipio AS municipio,
            uf_sigla AS uf,
            data_publicacao AS data,
            LEFT(trecho_destaque, 50) AS trecho,
            LEFT(url_pdf, 40) AS url
        FROM querido_diario_publicacoes
        {where_sql}
        ORDER BY data_publicacao DESC
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


if __name__ == "__main__":
    app()
