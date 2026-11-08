"""Query Siconfi fiscal transfers and municipal expenses by function."""

import sys
from pathlib import Path
import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from core.db import get_db

app = typer.Typer(help="Query Siconfi / Tesouro Nacional database")
console = Console()


@app.command()
def transferencias(
    tipo: str = typer.Option("", "--tipo", "-t", help="Tipo (FPM, FUNDEB, etc)"),
    uf: str = typer.Option("", "--uf", "-u", help="UF"),
):
    """Consulta transferências constitucionais e legais da União aos municípios."""
    db = get_db()
    sql = """
        SELECT 
            m.nome_municipio,
            t.uf,
            t.tipo_transferencia,
            t.ano_exercicio,
            printf('R$ %,.2f', t.valor_bruto) AS valor_bruto,
            printf('R$ %,.2f', t.valor_liquido) AS valor_liquido,
            t.data_repasse
        FROM siconfi_transferencias t
        LEFT JOIN ibge_municipios m ON t.codigo_ibge = m.codigo_ibge
        WHERE (t.tipo_transferencia ILIKE ? OR ? = '')
          AND (t.uf = ? OR ? = '')
        ORDER BY t.valor_liquido DESC
    """
    db.display_results(sql, [f"%{tipo}%", tipo, uf, uf])


@app.command()
def gastos_funcao(
    funcao: str = typer.Option("", "--funcao", "-f", help="Função de governo (EDUCACAO, SAUDE, etc)"),
):
    """Consulta despesas liquidadas e pagas por função de governo municipal."""
    db = get_db()
    sql = """
        SELECT 
            m.nome_municipio,
            g.uf,
            g.funcao_governo,
            g.ano_exercicio,
            printf('R$ %,.2f', g.valor_liquidado) AS liquidado,
            printf('R$ %,.2f', g.valor_pago) AS pago
        FROM siconfi_gastos_funcao g
        LEFT JOIN ibge_municipios m ON g.codigo_ibge = m.codigo_ibge
        WHERE (g.funcao_governo ILIKE ? OR ? = '')
        ORDER BY g.valor_pago DESC
    """
    db.display_results(sql, [f"%{funcao}%", funcao])


if __name__ == "__main__":
    app()
