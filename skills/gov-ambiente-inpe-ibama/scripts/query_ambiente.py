"""Query IBAMA environmental infractions, embargoed areas, and INPE alerts."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query IBAMA & INPE environmental database")
console = Console()


@app.command()
def infratores(
    termo: str = typer.Option("", "--termo", "-t", help="Nome ou CNPJ/CPF do infrator"),
    uf: str = typer.Option("", "--uf", "-u", help="Filtrar por UF"),
):
    """Busca autos de infração ambiental do IBAMA."""
    db = get_db()
    sql = """
        SELECT 
            numero_auto,
            cpf_cnpj_infrator,
            nome_infrator,
            tipo_infracao,
            printf('R$ %,.2f', valor_multa) AS valor_multa,
            municipio,
            uf,
            bioma,
            data_auto,
            situacao_debito
        FROM ibama_autos_infracao
        WHERE (nome_infrator ILIKE ? OR cpf_cnpj_infrator LIKE ?)
          AND (uf = ? OR ? = '')
        ORDER BY valor_multa DESC
    """
    param_term = f"%{termo}%"
    db.display_results(sql, [param_term, param_term, uf, uf])


@app.command()
def embargos(
    uf: str = typer.Option("", "--uf", "-u", help="Filtrar por UF"),
):
    """Lista fazendas e propriedades rurais sob embargo do IBAMA."""
    db = get_db()
    sql = """
        SELECT 
            numero_termo,
            cpf_cnpj_infrator,
            nome_infrator,
            area_embargada_ha,
            municipio,
            uf,
            motivo_embargo,
            data_embargo
        FROM ibama_areas_embargadas
        WHERE (uf = ? OR ? = '')
        ORDER BY area_embargada_ha DESC
    """
    db.display_results(sql, [uf, uf])


if __name__ == "__main__":
    app()
