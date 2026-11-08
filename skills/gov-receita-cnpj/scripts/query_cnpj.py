"""CLI query tool for Receita Federal CNPJs and partners (QSA) in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj

app = typer.Typer(help="Query Receita Federal corporate registry and QSA partners")
console = Console()


@app.command()
def empresa(
    cnpj: str = typer.Option(None, "--cnpj", "-c", help="Número do CNPJ"),
    nome: str = typer.Option(None, "--nome", "-n", help="Razão social da empresa"),
    limit: int = typer.Option(10, "--limit", "-l", help="Quantidade de empresas"),
):
    """Consulta dados cadastrais de empresas cadastradas."""
    db = get_db()
    if "rfb_empresas" not in db.list_tables():
        console.print("[yellow]A tabela 'rfb_empresas' ainda não existe. Use 'fetch_cnpj.py lookup' primeiro.[/yellow]")
        return

    where_clauses = []
    params = []

    if cnpj:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj)
        where_clauses.append("(cnpj = ? OR cnpj_raiz = ?)")
        params.extend([cnpj_limpo, cnpj_raiz])

    if nome:
        where_clauses.append("LOWER(razao_social) LIKE ?")
        params.append(f"%{nome.lower()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            cnpj,
            LEFT(razao_social, 35) AS razao_social,
            situacao_cadastral AS situacao,
            uf,
            municipio,
            printf('R$ %,.2f', capital_social) AS capital_social,
            porte,
            opcao_simples AS simples
        FROM rfb_empresas
        {where_sql}
        ORDER BY capital_social DESC
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


@app.command()
def socios(
    cnpj: str = typer.Option(None, "--cnpj", "-c", help="CNPJ da empresa para listar sócios"),
    nome: str = typer.Option(None, "--nome", "-n", help="Nome do sócio a pesquisar"),
    limit: int = typer.Option(20, "--limit", "-l", help="Quantidade de registros"),
):
    """Consulta sócios cadastrados e mapeia participações societárias."""
    db = get_db()
    if "rfb_socios" not in db.list_tables():
        console.print("[yellow]A tabela 'rfb_socios' ainda não existe.[/yellow]")
        return

    where_clauses = []
    params = []

    if cnpj:
        _, _, cnpj_raiz = normalize_cnpj(cnpj)
        where_clauses.append("s.cnpj_raiz = ?")
        params.append(cnpj_raiz)

    if nome:
        where_clauses.append("LOWER(s.nome_socio) LIKE ?")
        params.append(f"%{nome.lower()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            s.cnpj_raiz,
            COALESCE(e.razao_social, 'Não carregada') AS empresa,
            s.nome_socio,
            s.qualificacao_socio AS cargo_qualificacao,
            s.cpf_cnpj_socio AS doc_socio,
            s.faixa_etaria
        FROM rfb_socios s
        LEFT JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
        {where_sql}
        ORDER BY s.nome_socio
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


if __name__ == "__main__":
    app()
