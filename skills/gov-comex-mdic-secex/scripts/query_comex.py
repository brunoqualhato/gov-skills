"""Query MDIC Comex Stat trade operations and municipal balances."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query Comex Stat database")
console = Console()


@app.command()
def operacoes(
    tipo: str = typer.Option("", "--tipo", "-t", help="Tipo (EXPORTACAO ou IMPORTACAO)"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta operações de exportação e importação registradas."""
    db = get_db()
    sql = """
        SELECT 
            ano,
            mes,
            tipo_operacao,
            municipio,
            uf,
            descricao_ncm,
            pais_parceiro,
            printf('US$ %,.2f', valor_fob_usd) AS valor_fob
        FROM comex_balanca_comercial
        WHERE (tipo_operacao ILIKE ? OR ? = '')
          AND (uf = ? OR ? = '')
        ORDER BY valor_fob_usd DESC
    """
    db.display_results(sql, [f"%{tipo}%", tipo, uf, uf])


@app.command()
def saldo_municipio():
    """Calcula saldo comercial consolidado (Exportações - Importações) por município."""
    db = get_db()
    sql = """
        SELECT 
            municipio,
            uf,
            printf('US$ %,.2f', SUM(CASE WHEN tipo_operacao = 'EXPORTACAO' THEN valor_fob_usd ELSE 0 END)) AS exportacoes,
            printf('US$ %,.2f', SUM(CASE WHEN tipo_operacao = 'IMPORTACAO' THEN valor_fob_usd ELSE 0 END)) AS importacoes,
            printf('US$ %,.2f', SUM(CASE WHEN tipo_operacao = 'EXPORTACAO' THEN valor_fob_usd ELSE -valor_fob_usd END)) AS saldo_comercial
        FROM comex_balanca_comercial
        GROUP BY municipio, uf
        ORDER BY SUM(CASE WHEN tipo_operacao = 'EXPORTACAO' THEN valor_fob_usd ELSE -valor_fob_usd END) DESC
    """
    db.display_results(sql)


if __name__ == "__main__":
    app()
