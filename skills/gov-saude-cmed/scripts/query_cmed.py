"""CLI query tool for CMED/Anvisa medicine price regulations in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Query CMED/Anvisa medicine price regulation limits")
console = Console()


@app.command()
def search(
    substancia: str = typer.Option(None, "--substancia", "-s", help="Nome do princípio ativo (ex: DIPIRONA, INSULINA)"),
    laboratorio: str = typer.Option(None, "--laboratorio", "-l", help="Nome do fabricante ou laboratório"),
    limit: int = typer.Option(15, "--limit", help="Quantidade máxima de medicamentos"),
):
    """Consulta preços máximos autorizados pela CMED/Anvisa."""
    db = get_db()
    if "cmed_precos_medicamentos" not in db.list_tables():
        console.print("[yellow]A tabela 'cmed_precos_medicamentos' ainda não existe.[/yellow]")
        return

    where_clauses = []
    params = []

    if substancia:
        where_clauses.append("LOWER(substancia) LIKE ?")
        params.append(f"%{substancia.lower()}%")

    if laboratorio:
        where_clauses.append("LOWER(laboratorio) LIKE ?")
        params.append(f"%{laboratorio.lower()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            substancia,
            LEFT(laboratorio, 20) AS laboratorio,
            LEFT(apresentacao, 35) AS apresentacao,
            printf('R$ %,.2f', preco_fabricante_pf) AS preco_fabricante,
            printf('R$ %,.2f', preco_teto_governo_cap) AS teto_governo_cap,
            printf('%.2f%%', percentual_cap) AS cap
        FROM cmed_precos_medicamentos
        {where_sql}
        ORDER BY substancia
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


if __name__ == "__main__":
    app()
