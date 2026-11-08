"""Query DataSUS CNES healthcare facilities and hospital beds."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query DataSUS / CNES database")
console = Console()


@app.command()
def estabelecimentos(
    termo: str = typer.Option("", "--termo", "-t", help="Nome do hospital ou CNPJ"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta hospitais e unidades de saúde do CNES."""
    db = get_db()
    sql = """
        SELECT 
            codigo_cnes,
            nome_fantasia,
            tipo_unidade,
            municipio,
            uf,
            qtd_leitos_uti,
            qtd_leitos_internacao,
            possui_atendimento_urgencia AS urgencia
        FROM datasus_estabelecimentos_cnes
        WHERE (nome_fantasia ILIKE ? OR codigo_cnes LIKE ? OR cnpj_mantenedora LIKE ?)
          AND (uf = ? OR ? = '')
        ORDER BY qtd_leitos_internacao DESC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, param, uf, uf])


@app.command()
def leitos_uf(
    uf: str = typer.Option("SP", "--uf", "-u", help="UF"),
):
    """Totaliza leitos de UTI e internação por UF."""
    db = get_db()
    sql = """
        SELECT 
            uf,
            COUNT(codigo_cnes) AS total_hospitais,
            SUM(qtd_leitos_uti) AS total_leitos_uti,
            SUM(qtd_leitos_internacao) AS total_leitos_internacao
        FROM datasus_estabelecimentos_cnes
        WHERE uf = ?
        GROUP BY uf
    """
    db.display_results(sql, [uf])


if __name__ == "__main__":
    app()
