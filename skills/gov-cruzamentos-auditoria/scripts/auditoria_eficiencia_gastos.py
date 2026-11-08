"""Municipal spending efficiency benchmark: correlates Siconfi budgets with INEP IDEB performance."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Audit municipal public spending efficiency against social outcomes")
console = Console()


@app.command()
def scan():
    """Calcula benchmark de eficiência de gastos públicos: Gastos em Educação x Nota do IDEB."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel("[bold cyan]BENCHMARK DE EFICIÊNCIA PÚBLICA: GASTOS EM EDUCAÇÃO x NOTA DO IDEB[/bold cyan]\n"
                        "[dim]Mede o retorno social de cada real investido na rede municipal de ensino (Siconfi + INEP).[/dim]",
                        border_style="cyan"))

    if "siconfi_gastos_funcao" not in tables or "inep_ideb_municipios" not in tables:
        console.print("[yellow]Tabelas 'siconfi_gastos_funcao' e 'inep_ideb_municipios' necessárias.[/yellow]")
        return

    rows = db.query("""
        SELECT 
            m.nome_municipio,
            m.uf_sigla,
            i.ano,
            i.etapa_ensino,
            i.nota_ideb,
            printf('R$ %,.2f', g.valor_liquidado) AS gasto_educacao,
            printf('R$ %,.2f', g.valor_liquidado / NULLIF(i.nota_ideb, 0)) AS custo_por_ponto_ideb
        FROM siconfi_gastos_funcao g
        JOIN inep_ideb_municipios i ON g.codigo_ibge = i.codigo_ibge
        JOIN ibge_municipios m ON g.codigo_ibge = m.codigo_ibge
        WHERE g.funcao_governo = 'EDUCACAO'
          AND i.rede = 'MUNICIPAL'
        ORDER BY (g.valor_liquidado / NULLIF(i.nota_ideb, 0)) ASC
    """)

    if rows:
        t = Table(title="📈 Ranking de Eficiência dos Gastos Municipais em Educação", border_style="green")
        t.add_column("Município", style="white")
        t.add_column("UF", style="magenta")
        t.add_column("Etapa Ensino", style="yellow")
        t.add_column("Nota IDEB", style="bold green", justify="center")
        t.add_column("Gasto Liquidado (Educação)", style="cyan", justify="right")
        t.add_column("Custo / Ponto IDEB", style="bold yellow", justify="right")

        for r in rows:
            t.add_row(r[0], r[1], r[3], str(r[4]), r[5], r[6])
        console.print(t)
    else:
        console.print("[dim yellow]Nenhum dado consolidado de educação para cruzamento.[/dim yellow]")


@app.command()
def info():
    """Exibe informações sobre os dados de educação e finanças."""
    db = get_db()
    c1 = db.count("siconfi_gastos_funcao")
    c2 = db.count("inep_ideb_municipios")
    console.print(f"[cyan]Lakehouse:[/cyan] {c1} gastos por função, {c2} notas de IDEB.")


if __name__ == "__main__":
    app()
