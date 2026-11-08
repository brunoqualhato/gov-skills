"""Query Federal Senate senators and CEAPS expenses."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query Senado Federal database")
console = Console()


@app.command()
def senadores(
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
    partido: str = typer.Option("", "--partido", "-p", help="Partido"),
):
    """Lista senadores em exercício."""
    db = get_db()
    sql = """
        SELECT 
            codigo_parlamentar,
            nome_parlamentar,
            sigla_partido,
            sigla_uf,
            email
        FROM senado_senadores
        WHERE (sigla_uf = ? OR ? = '')
          AND (sigla_partido ILIKE ? OR ? = '')
        ORDER BY nome_parlamentar ASC
    """
    db.display_results(sql, [uf, uf, f"%{partido}%", partido])


@app.command()
def despesas_ceaps(
    termo: str = typer.Option("", "--termo", "-t", help="Nome do senador ou fornecedor"),
):
    """Consulta reembolsos da cota CEAPS do Senado."""
    db = get_db()
    sql = """
        SELECT 
            s.nome_parlamentar,
            s.sigla_uf,
            d.tipo_despesa,
            d.fornecedor_nome,
            d.cnpj_cpf_fornecedor,
            printf('R$ %,.2f', d.valor_reembolsado) AS valor,
            d.data_despesa
        FROM senado_ceaps_despesas d
        JOIN senado_senadores s ON d.codigo_parlamentar = s.codigo_parlamentar
        WHERE (s.nome_parlamentar ILIKE ? OR d.fornecedor_nome ILIKE ? OR d.cnpj_cpf_fornecedor LIKE ?)
        ORDER BY d.valor_reembolsado DESC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, param])


if __name__ == "__main__":
    app()
