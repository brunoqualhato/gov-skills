"""Query TSE candidates, campaign donations and declared assets."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query TSE database")
console = Console()


@app.command()
def doadores(
    termo: str = typer.Option("", "--termo", "-t", help="Nome ou CNPJ/CPF do doador"),
    min_valor: float = typer.Option(0.0, "--min", "-m", help="Valor mínimo doado"),
):
    """Busca doadores de campanha política."""
    db = get_db()
    sql = """
        SELECT 
            d.ano_eleicao,
            d.nm_doador,
            d.nr_cpf_cnpj_doador,
            printf('R$ %,.2f', d.vr_receita) AS valor,
            c.nm_urna AS candidato_beneficiado,
            c.sg_partido,
            c.ds_cargo,
            d.dt_receita
        FROM tse_doacoes d
        LEFT JOIN tse_candidatos c ON d.sq_candidato = c.sq_candidato
        WHERE (d.nm_doador ILIKE ? OR d.nr_cpf_cnpj_doador LIKE ?)
          AND d.vr_receita >= ?
        ORDER BY d.vr_receita DESC
    """
    param_pattern = f"%{termo}%"
    db.display_results(sql, [param_pattern, param_pattern, min_valor])


@app.command()
def candidatos(
    cargo: str = typer.Option("", "--cargo", "-c", help="Filtrar por cargo (PREFEITO, DEPUTADO, etc)"),
    uf: str = typer.Option("", "--uf", "-u", help="Filtrar por UF"),
):
    """Lista candidatos armazenados no Lakehouse."""
    db = get_db()
    sql = """
        SELECT 
            ano_eleicao,
            nm_urna,
            sg_partido,
            ds_cargo,
            sg_uf,
            ds_situacao_candidatura,
            ds_resultado_eleicao
        FROM tse_candidatos
        WHERE (ds_cargo ILIKE ? OR ? = '')
          AND (sg_uf = ? OR ? = '')
        ORDER BY ano_eleicao DESC, nm_urna ASC
    """
    db.display_results(sql, [f"%{cargo}%", cargo, uf, uf])


if __name__ == "__main__":
    app()
