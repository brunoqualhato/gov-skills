"""CLI query tool for IBGE municipalities and territories."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Query IBGE municipalities in DuckDB")
console = Console()


@app.command()
def search(
    nome: str = typer.Option(None, "--nome", "-n", help="Nome do município"),
    uf: str = typer.Option(None, "--uf", help="Sigla da UF (ex: SP, MG, BA)"),
    codigo: str = typer.Option(None, "--codigo", "-c", help="Código IBGE (6 ou 7 dígitos)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Quantidade máxima de resultados"),
):
    """Pesquisa municípios brasileiros por nome, UF ou código IBGE."""
    db = get_db()
    if "ibge_municipios" not in db.list_tables():
        console.print("[yellow]A tabela 'ibge_municipios' ainda não existe. Execute 'fetch_ibge.py' primeiro.[/yellow]")
        return

    where_clauses = []
    params = []

    if nome:
        where_clauses.append("LOWER(nome_municipio) LIKE ?")
        params.append(f"%{nome.lower()}%")

    if uf:
        where_clauses.append("uf_sigla = ?")
        params.append(uf.upper())

    if codigo:
        where_clauses.append("codigo_ibge LIKE ?")
        params.append(f"{codigo}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            codigo_ibge,
            nome_municipio,
            uf_sigla AS uf,
            regiao_nome AS regiao,
            microrregiao_nome AS microrregiao,
            regiao_imediata
        FROM ibge_municipios
        {where_sql}
        ORDER BY uf_sigla, nome_municipio
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


@app.command()
def resumo_uf():
    """Exibe o total de municípios por Unidade Federativa e Região."""
    db = get_db()
    if "ibge_municipios" not in db.list_tables():
        console.print("[yellow]A tabela 'ibge_municipios' ainda não existe.[/yellow]")
        return

    sql = """
        SELECT 
            regiao_nome AS regiao,
            uf_sigla AS uf,
            uf_nome AS estado,
            COUNT(*) AS total_municipios
        FROM ibge_municipios
        GROUP BY regiao_nome, uf_sigla, uf_nome
        ORDER BY regiao_nome, total_municipios DESC
    """
    db.display_results(sql, limit=50)


if __name__ == "__main__":
    app()
