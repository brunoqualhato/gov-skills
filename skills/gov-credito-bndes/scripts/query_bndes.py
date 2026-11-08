"""Query BNDES financing and corporate credit database."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query BNDES database")
console = Console()


@app.command()
def contratos(
    termo: str = typer.Option("", "--termo", "-t", help="CNPJ ou Razão Social do tomador"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta contratos de financiamento do BNDES."""
    db = get_db()
    sql = """
        SELECT 
            numero_contrato,
            razao_social_cliente,
            cnpj_cliente,
            linha_financiamento,
            forma_apoio,
            printf('R$ %,.2f', valor_contratado) AS valor_contratado,
            printf('R$ %,.2f', valor_desembolsado) AS valor_desembolsado,
            data_contrato
        FROM bndes_operacoes_financiamento
        WHERE (razao_social_cliente ILIKE ? OR cnpj_cliente LIKE ?)
          AND (uf = ? OR ? = '')
        ORDER BY valor_contratado DESC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, uf, uf])


@app.command()
def total_setor():
    """Totaliza valores contratados por setor econômico."""
    db = get_db()
    sql = """
        SELECT 
            setor_cnae,
            COUNT(numero_contrato) AS total_operacoes,
            printf('R$ %,.2f', SUM(valor_contratado)) AS total_contratado,
            printf('R$ %,.2f', SUM(valor_desembolsado)) AS total_desembolsado
        FROM bndes_operacoes_financiamento
        GROUP BY setor_cnae
        ORDER BY SUM(valor_contratado) DESC
    """
    db.display_results(sql)


if __name__ == "__main__":
    app()
