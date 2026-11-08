"""Query federal public works and Transferegov agreements."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query Transferegov & Obrasgov database")
console = Console()


@app.command()
def obras(
    situacao: str = typer.Option("", "--situacao", "-s", help="Situação da obra (PARALISADA, EM EXECUCAO, CONCLUIDA)"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta obras públicas federais cadastradas no Obrasgov."""
    db = get_db()
    sql = """
        SELECT 
            id_obra,
            nome_obra,
            municipio,
            uf,
            situacao_obra,
            percentual_execucao,
            printf('R$ %,.2f', valor_investimento) AS investimento,
            razao_social_executor,
            motivo_paralisacao
        FROM obrasgov_obras_publicas
        WHERE (situacao_obra ILIKE ? OR ? = '')
          AND (uf = ? OR ? = '')
        ORDER BY valor_investimento DESC
    """
    db.display_results(sql, [f"%{situacao}%", situacao, uf, uf])


@app.command()
def convenios(
    uf: str = typer.Option("", "--uf", "-u", help="UF do proponente"),
):
    """Consulta convênios e transferências voluntárias do Transferegov."""
    db = get_db()
    sql = """
        SELECT 
            numero_convenio,
            ano_convenio,
            orgao_concedente,
            municipio_proponente,
            uf_proponente,
            objeto,
            situacao_convenio,
            printf('R$ %,.2f', valor_global) AS valor_global,
            printf('R$ %,.2f', valor_pago) AS valor_pago
        FROM transferegov_convenios
        WHERE (uf_proponente = ? OR ? = '')
        ORDER BY valor_global DESC
    """
    db.display_results(sql, [uf, uf])


if __name__ == "__main__":
    app()
