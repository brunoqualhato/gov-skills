"""Query ANP fuel prices by city, state and product."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query ANP fuel prices database")
console = Console()


@app.command()
def precos(
    produto: str = typer.Option("GASOLINA", "--produto", "-p", help="Produto (GASOLINA, ETANOL, DIESEL S10, GNV)"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta preços de combustíveis coletados nos postos."""
    db = get_db()
    sql = """
        SELECT 
            municipio,
            uf,
            produto,
            data_coleta,
            printf('R$ %,.2f', valor_venda) AS preco_venda,
            bandeira,
            nome_posto
        FROM anp_precos_combustiveis
        WHERE produto ILIKE ?
          AND (uf = ? OR ? = '')
        ORDER BY valor_venda ASC
    """
    db.display_results(sql, [f"%{produto}%", uf, uf])


@app.command()
def medias(
    produto: str = typer.Option("GASOLINA", "--produto", "-p", help="Produto"),
):
    """Exibe preço médio, mínimo e máximo por município."""
    db = get_db()
    sql = """
        SELECT 
            municipio,
            uf,
            produto,
            printf('R$ %,.2f', AVG(valor_venda)) AS media,
            printf('R$ %,.2f', MIN(valor_venda)) AS minimo,
            printf('R$ %,.2f', MAX(valor_venda)) AS maximo,
            COUNT(id_coleta) AS qtd_postos
        FROM anp_precos_combustiveis
        WHERE produto ILIKE ?
        GROUP BY municipio, uf, produto
        ORDER BY media ASC
    """
    db.display_results(sql, [f"%{produto}%"])


if __name__ == "__main__":
    app()
