"""Query MTE Novo CAGED employment statistics and corporate headcount."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query MTE / Novo CAGED database")
console = Console()


@app.command()
def saldos(
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
    setor: str = typer.Option("", "--setor", "-s", help="Setor econômico"),
):
    """Consulta saldo de contratações/demissões CLT por município."""
    db = get_db()
    sql = """
        SELECT 
            m.nome_municipio,
            c.uf,
            c.ano,
            c.mes,
            c.setor_economico,
            c.total_admissoes,
            c.total_desligamentos,
            c.saldo_liquido,
            printf('R$ %,.2f', c.salario_medio_admissao) AS salario_medio
        FROM mte_caged_saldos_municipais c
        LEFT JOIN ibge_municipios m ON c.codigo_ibge = m.codigo_ibge
        WHERE (c.uf = ? OR ? = '')
          AND (c.setor_economico ILIKE ? OR ? = '')
        ORDER BY c.saldo_liquido DESC
    """
    db.display_results(sql, [uf, uf, f"%{setor}%", setor])


@app.command()
def quadro_empresa(
    cnpj: str = typer.Option("", "--cnpj", "-c", help="CNPJ ou termo de busca"),
):
    """Consulta número de empregados ativos declarados pela empresa no CAGED/RAIS."""
    db = get_db()
    sql = """
        SELECT 
            c.cnpj,
            e.razao_social,
            c.total_empregados_ativos,
            c.admissoes_ultimos_12m,
            c.desligamentos_ultimos_12m,
            c.ano_mes_referencia
        FROM mte_caged_empresas_quadro c
        LEFT JOIN rfb_empresas e ON c.cnpj = e.cnpj
        WHERE (c.cnpj LIKE ? OR e.razao_social ILIKE ?)
        ORDER BY c.total_empregados_ativos DESC
    """
    param = f"%{cnpj}%"
    db.display_results(sql, [param, param])


if __name__ == "__main__":
    app()
