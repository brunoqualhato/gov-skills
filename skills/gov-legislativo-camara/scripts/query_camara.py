"""CLI query tool for Chamber of Deputies and CEAP expenses in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Query Chamber of Deputies and CEAP expenses")
console = Console()


@app.command()
def deputados(
    nome: str = typer.Option(None, "--nome", "-n", help="Nome do parlamentar"),
    partido: str = typer.Option(None, "--partido", "-p", help="Sigla do partido (ex: PL, PT, MDB)"),
    uf: str = typer.Option(None, "--uf", help="Sigla da UF (ex: SP, RJ, RS)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Quantidade máxima de resultados"),
):
    """Consulta deputados federais cadastrados."""
    db = get_db()
    if "camara_deputados" not in db.list_tables():
        console.print("[yellow]A tabela 'camara_deputados' ainda não existe. Execute 'fetch_camara.py deputados' primeiro.[/yellow]")
        return

    where_clauses = []
    params = []

    if nome:
        where_clauses.append("LOWER(nome) LIKE ?")
        params.append(f"%{nome.lower()}%")

    if partido:
        where_clauses.append("UPPER(sigla_partido) = ?")
        params.append(partido.upper())

    if uf:
        where_clauses.append("UPPER(sigla_uf) = ?")
        params.append(uf.upper())

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            id_deputado,
            nome,
            sigla_partido AS partido,
            sigla_uf AS uf,
            email
        FROM camara_deputados
        {where_sql}
        ORDER BY nome
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


@app.command()
def top_fornecedores(
    limit: int = typer.Option(10, "--limit", "-l", help="Quantidade de fornecedores"),
):
    """Lista as empresas e fornecedores que mais receberam verba de cota parlamentar."""
    db = get_db()
    if "camara_ceap_despesas" not in db.list_tables():
        console.print("[yellow]A tabela 'camara_ceap_despesas' ainda não existe.[/yellow]")
        return

    sql = f"""
        SELECT 
            nome_fornecedor AS fornecedor,
            cnpj_cpf_fornecedor AS cnpj_cpf,
            COUNT(*) AS total_despesas,
            printf('R$ %,.2f', SUM(valor_liquido)) AS montante_total
        FROM camara_ceap_despesas
        WHERE valor_liquido > 0
        GROUP BY nome_fornecedor, cnpj_cpf_fornecedor
        ORDER BY SUM(valor_liquido) DESC
        LIMIT {limit}
    """
    db.display_results(sql, limit=limit)


@app.command()
def gastos_tipo():
    """Exibe a distribuição de gastos por tipo de cota parlamentar."""
    db = get_db()
    if "camara_ceap_despesas" not in db.list_tables():
        console.print("[yellow]A tabela 'camara_ceap_despesas' ainda não existe.[/yellow]")
        return

    sql = """
        SELECT 
            tipo_despesa,
            COUNT(*) AS qtd_notas,
            printf('R$ %,.2f', SUM(valor_liquido)) AS valor_total
        FROM camara_ceap_despesas
        WHERE valor_liquido > 0
        GROUP BY tipo_despesa
        ORDER BY SUM(valor_liquido) DESC
    """
    db.display_results(sql, limit=20)


if __name__ == "__main__":
    app()
