"""CLI query tool for CGU sanctions (CEIS, CNEP) in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj

app = typer.Typer(help="Query CGU sanctions stored in DuckDB")
console = Console()


@app.command()
def search(
    cnpj: str = typer.Option(None, "--cnpj", "-c", help="CNPJ da empresa punida"),
    nome: str = typer.Option(None, "--nome", "-n", help="Nome ou razão social do sancionado"),
    tipo: str = typer.Option(None, "--tipo", "-t", help="Tipo de cadastro (CEIS ou CNEP)"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade de resultados"),
):
    """Pesquisa sanções ativas aplicadas a empresas e pessoas."""
    db = get_db()
    if "cgu_sancoes" not in db.list_tables():
        console.print("[yellow]A tabela 'cgu_sancoes' ainda não existe.[/yellow]")
        return

    where_clauses = []
    params = []

    if cnpj:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj)
        where_clauses.append("(cnpj_sancionado = ? OR cnpj_raiz = ?)")
        params.extend([cnpj_limpo, cnpj_raiz])

    if nome:
        where_clauses.append("LOWER(nome_sancionado) LIKE ?")
        params.append(f"%{nome.lower()}%")

    if tipo:
        where_clauses.append("tipo_cadastro = ?")
        params.append(tipo.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            tipo_cadastro AS tipo,
            LEFT(nome_sancionado, 35) AS sancionado,
            COALESCE(cnpj_sancionado, cpf_sancionado) AS cnpj_cpf,
            LEFT(orgao_sancionador, 25) AS orgao,
            data_inicio_sancao AS inicio,
            data_fim_sancao AS fim,
            LEFT(motivo, 30) AS motivo
        FROM cgu_sancoes
        {where_sql}
        ORDER BY data_inicio_sancao DESC NULLS LAST
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


if __name__ == "__main__":
    app()
