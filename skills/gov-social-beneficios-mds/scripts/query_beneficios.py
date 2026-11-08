"""Query MDS & CGU social benefits database."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query MDS social benefits database")
console = Console()


@app.command()
def beneficiarios(
    nome: str = typer.Option("", "--nome", "-n", help="Nome do beneficiário ou CPF mascarado"),
    tipo: str = typer.Option("", "--tipo", "-t", help="Tipo (BOLSA FAMILIA, BPC, etc)"),
):
    """Consulta beneficiários de programas sociais."""
    db = get_db()
    sql = """
        SELECT 
            nome_beneficiario,
            cpf_beneficiario,
            tipo_beneficio,
            municipio,
            uf,
            mes_competencia,
            printf('R$ %,.2f', valor_parcela) AS valor
        FROM cgu_beneficios_cidadao
        WHERE (nome_beneficiario ILIKE ? OR cpf_beneficiario LIKE ?)
          AND (tipo_beneficio ILIKE ? OR ? = '')
        ORDER BY valor_parcela DESC
    """
    param = f"%{nome}%"
    db.display_results(sql, [param, param, f"%{tipo}%", tipo])


@app.command()
def total_municipio(
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Totaliza pagamentos de benefícios por município."""
    db = get_db()
    sql = """
        SELECT 
            municipio,
            uf,
            tipo_beneficio,
            COUNT(id_beneficio) AS qtd_beneficiarios,
            printf('R$ %,.2f', SUM(valor_parcela)) AS total_pago
        FROM cgu_beneficios_cidadao
        WHERE (uf = ? OR ? = '')
        GROUP BY municipio, uf, tipo_beneficio
        ORDER BY SUM(valor_parcela) DESC
    """
    db.display_results(sql, [uf, uf])


if __name__ == "__main__":
    app()
