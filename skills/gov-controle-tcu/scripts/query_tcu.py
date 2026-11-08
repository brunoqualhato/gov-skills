"""CLI query tool for TCU sanctions and irregular accounts in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj

app = typer.Typer(help="Query TCU inidoneous companies and irregular accounts")
console = Console()


@app.command()
def inidoneas(
    cnpj: str = typer.Option(None, "--cnpj", "-c", help="CNPJ da empresa inidônea"),
    nome: str = typer.Option(None, "--nome", "-n", help="Nome ou razão social"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade máxima"),
):
    """Consulta empresas declaradas inidôneas pelo TCU."""
    db = get_db()
    if "tcu_empresas_inidoneas" not in db.list_tables():
        console.print("[yellow]A tabela 'tcu_empresas_inidoneas' ainda não existe.[/yellow]")
        return

    where_clauses = []
    params = []

    if cnpj:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj)
        where_clauses.append("(cnpj_inidonio = ? OR cnpj_raiz = ?)")
        params.extend([cnpj_limpo, cnpj_raiz])

    if nome:
        where_clauses.append("LOWER(razao_social) LIKE ?")
        params.append(f"%{nome.lower()}%")

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    sql = f"""
        SELECT 
            cnpj_inidonio AS cnpj,
            LEFT(razao_social, 35) AS empresa,
            numero_acordao AS acordao,
            data_inicio_sancao AS inicio,
            data_fim_sancao AS fim,
            LEFT(motivo, 40) AS motivo
        FROM tcu_empresas_inidoneas
        {where_sql}
        ORDER BY data_inicio_sancao DESC
        LIMIT {limit}
    """
    db.display_results(sql, params=params, limit=limit)


@app.command()
def irregulares(
    nome: str = typer.Option(None, "--nome", "-n", help="Nome do gestor público"),
    limit: int = typer.Option(15, "--limit", "-l", help="Quantidade máxima"),
):
    """Consulta pessoas com contas julgadas irregulares pelo TCU (Ficha Limpa)."""
    db = get_db()
    if "tcu_contas_irregulares" not in db.list_tables():
        console.print("[yellow]A tabela 'tcu_contas_irregulares' ainda não existe.[/yellow]")
        return

    where_sql = f"WHERE LOWER(nome_responsavel) LIKE '%{nome.lower()}%'" if nome else ""
    sql = f"""
        SELECT 
            nome_responsavel AS gestor,
            cpf_cnpj AS cpf,
            cargo_funcao AS cargo,
            orgao_origem AS orgao,
            numero_acordao AS acordao,
            data_transito_julgado AS transito,
            data_fim_inelegibilidade AS inelegivel_ate
        FROM tcu_contas_irregulares
        {where_sql}
        ORDER BY data_transito_julgado DESC
        LIMIT {limit}
    """
    db.display_results(sql, limit=limit)


if __name__ == "__main__":
    app()
