"""CLI query tool for macroeconomic data from Banco Central do Brasil."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Query BCB macroeconomic data in DuckDB")
console = Console()


@app.command()
def series(
    codigo: int = typer.Option(None, "--codigo", "-c", help="Filtrar por código de série SGS (ex: 432=Selic)"),
    nome: str = typer.Option(None, "--nome", "-n", help="Filtrar por nome da série"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade de registros"),
):
    """Consulta séries temporais econômicas armazenadas."""
    db = get_db()
    if "bcb_series_temporais" not in db.list_tables():
        console.print("[yellow]A tabela 'bcb_series_temporais' ainda não existe. Execute fetch_bcb.py primeiro.[/yellow]")
        return

    where_clauses = []
    params = []

    if codigo:
        where_clauses.append("codigo_serie = ?")
        params.append(codigo)

    if nome:
        where_clauses.append("LOWER(nome_serie) LIKE ?")
        params.append(f"%{nome.lower()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            codigo_serie,
            nome_serie,
            data_referencia,
            printf('%.4f', valor) AS valor,
            unidade
        FROM bcb_series_temporais
        {where_sql}
        ORDER BY data_referencia DESC
        LIMIT {limit}
    """
    db.display_results(sql, limit=limit)


@app.command()
def focus(
    indicador: str = typer.Option(None, "--indicador", "-i", help="Nome do indicador (ex: IPCA, PIB Total, Selic, Câmbio)"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade de projeções"),
):
    """Consulta projeções de mercado do Relatório Focus."""
    db = get_db()
    if "bcb_expectativas_focus" not in db.list_tables():
        console.print("[yellow]A tabela 'bcb_expectativas_focus' ainda não existe.[/yellow]")
        return

    where_sql = f"WHERE LOWER(indicador) LIKE '%{indicador.lower()}%'" if indicador else ""
    sql = f"""
        SELECT 
            indicador,
            data_pesquisa,
            data_referencia AS mes_referencia,
            printf('%.2f', mediana) AS mediana,
            printf('%.2f', media) AS media,
            printf('%.2f', minimo) AS min,
            printf('%.2f', maximo) AS max,
            numero_respondentes AS respondentes
        FROM bcb_expectativas_focus
        {where_sql}
        ORDER BY data_pesquisa DESC, data_referencia ASC
        LIMIT {limit}
    """
    db.display_results(sql, limit=limit)


if __name__ == "__main__":
    app()
