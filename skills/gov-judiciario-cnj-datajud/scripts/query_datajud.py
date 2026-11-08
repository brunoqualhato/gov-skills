"""Query CNJ DataJud legal proceedings, bankruptcy, and public improbity."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query DataJud / CNJ database")
console = Console()


@app.command()
def processos(
    termo: str = typer.Option("", "--termo", "-t", help="CNPJ, CPF ou nome da parte"),
    classe: str = typer.Option("", "--classe", "-c", help="Filtrar por classe processual"),
):
    """Consulta processos judiciais no DataJud."""
    db = get_db()
    sql = """
        SELECT 
            numero_processo,
            classe_processual,
            tribunal,
            nome_parte,
            polo_processual,
            printf('R$ %,.2f', valor_causa) AS valor,
            situacao_processo,
            orgao_julgador
        FROM cnj_processos_judiciais
        WHERE (nome_parte ILIKE ? OR cpf_cnpj_parte LIKE ? OR numero_processo LIKE ?)
          AND (classe_processual ILIKE ? OR ? = '')
        ORDER BY valor_causa DESC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, param, f"%{classe}%", classe])


@app.command()
def falencias():
    """Lista empresas com processos de Falência ou Recuperação Judicial."""
    db = get_db()
    sql = """
        SELECT 
            numero_processo,
            tribunal,
            nome_parte,
            cpf_cnpj_parte,
            situacao_processo,
            printf('R$ %,.2f', valor_causa) AS valor
        FROM cnj_processos_judiciais
        WHERE classe_processual ILIKE '%FALENCIA%' OR classe_processual ILIKE '%RECUPERACAO%'
        ORDER BY valor_causa DESC
    """
    db.display_results(sql)


if __name__ == "__main__":
    app()
