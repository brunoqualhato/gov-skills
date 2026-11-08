"""Query federal open data catalog (dados.gov.br)."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query dados.gov.br catalog database")
console = Console()


@app.command()
def datasets(
    termo: str = typer.Option("", "--termo", "-t", help="Termo de pesquisa"),
    orgao: str = typer.Option("", "--orgao", "-o", help="Filtrar por órgão responsável"),
):
    """Pesquisa conjuntos de dados abertos no catálogo local."""
    db = get_db()
    sql = """
        SELECT 
            id_dataset,
            titulo,
            orgao_responsavel,
            frequencia_atualizacao,
            qtd_recursos,
            url_portal
        FROM catalogo_conjuntos_dados
        WHERE (titulo ILIKE ? OR descricao ILIKE ?)
          AND (orgao_responsavel ILIKE ? OR ? = '')
        ORDER BY titulo ASC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, f"%{orgao}%", orgao])


@app.command()
def orgaos():
    """Lista órgãos públicos com conjuntos de dados catalogados."""
    db = get_db()
    sql = """
        SELECT 
            orgao_responsavel,
            COUNT(id_dataset) AS total_datasets
        FROM catalogo_conjuntos_dados
        GROUP BY orgao_responsavel
        ORDER BY total_datasets DESC
    """
    db.display_results(sql)


if __name__ == "__main__":
    app()
