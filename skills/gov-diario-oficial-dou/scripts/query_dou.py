"""Query Official Gazette (DOU) publications and contracts."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query DOU database")
console = Console()


@app.command()
def busca(
    termo: str = typer.Option(..., "--termo", "-t", help="Termo de busca textual no Diário Oficial"),
    secao: str = typer.Option("", "--secao", "-s", help="Filtrar por seção (Seção 1, Seção 2, Seção 3)"),
):
    """Realiza busca textual completa em atos oficiais e contratos do DOU."""
    db = get_db()
    sql = """
        SELECT 
            data_publicacao,
            secao,
            orgao_emissor,
            tipo_ato,
            titulo,
            texto_resumo
        FROM dou_publicacoes_atos
        WHERE (titulo ILIKE ? OR texto_resumo ILIKE ? OR texto_completo ILIKE ?)
          AND (secao ILIKE ? OR ? = '')
        ORDER BY data_publicacao DESC
    """
    param = f"%{termo}%"
    db.display_results(sql, [param, param, param, f"%{secao}%", secao])


@app.command()
def contratos():
    """Lista extratos de contratos publicados na Seção 3 do DOU."""
    db = get_db()
    sql = """
        SELECT 
            data_publicacao,
            orgao_emissor,
            titulo,
            texto_resumo,
            url_publicacao
        FROM dou_publicacoes_atos
        WHERE secao ILIKE '%Seção 3%' OR tipo_ato ILIKE '%CONTRATO%'
        ORDER BY data_publicacao DESC
    """
    db.display_results(sql)


if __name__ == "__main__":
    app()
