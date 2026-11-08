"""Query INEP schools and IDEB educational indicators."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query INEP / MEC database")
console = Console()


@app.command()
def escolas(
    termo: str = typer.Option("", "--termo", "-t", help="Nome da escola ou município"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta escolas cadastradas no Censo Escolar."""
    db = get_db()
    sql = """
        SELECT 
            codigo_escola,
            nome_escola,
            dependencia_administrativa AS rede,
            municipio,
            uf,
            total_matriculas,
            tem_internet,
            tem_agua_potavel
        FROM inep_escolas_censo
        WHERE (nome_escola ILIKE ? OR municipio ILIKE ?)
          AND (uf = ? OR ? = '')
        ORDER BY total_matriculas DESC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, uf, uf])


@app.command()
def ideb(
    uf: str = typer.Option("", "--uf", "-u", help="Filtrar por UF"),
    etapa: str = typer.Option("", "--etapa", "-e", help="Etapa (INICIAIS, FINAIS)"),
):
    """Consulta nota do IDEB por município e etapa de ensino."""
    db = get_db()
    sql = """
        SELECT 
            m.nome_municipio,
            m.uf_sigla,
            i.ano,
            i.etapa_ensino,
            i.rede,
            i.nota_ideb
        FROM inep_ideb_municipios i
        JOIN ibge_municipios m ON i.codigo_ibge = m.codigo_ibge
        WHERE (m.uf_sigla = ? OR ? = '')
          AND (i.etapa_ensino ILIKE ? OR ? = '')
        ORDER BY i.nota_ideb DESC
    """
    db.display_results(sql, [uf, uf, f"%{etapa}%", etapa])


if __name__ == "__main__":
    app()
