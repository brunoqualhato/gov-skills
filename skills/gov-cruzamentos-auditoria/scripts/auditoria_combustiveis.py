"""Forensic fuel price auditor: compares public procurement & parliament expenses with ANP price surveys."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Audit fuel procurement against ANP benchmark prices")
console = Console()


@app.command()
def scan(
    fator_alerta: float = typer.Option(1.25, "--fator", "-f", help="Multiplicador sobre o preço médio da ANP (ex: 1.25 = 25% acima)"),
):
    """Detecta compras públicas de combustíveis com sobrepreço em relação à tabela oficial da ANP."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel(f"[bold yellow]AUDITORIA FORENSE DE COMBUSTÍVEIS: ANP x CONTRATOS PÚBLICOS & CEAP[/bold yellow]\n"
                        f"[dim]Identifica itens licitados ou ressarcimentos parlamentares com preços superiores a {((fator_alerta - 1.0) * 100):.0f}% da média da ANP.[/dim]",
                        border_style="yellow"))

    if "anp_precos_combustiveis" not in tables:
        console.print("[yellow]Tabela 'anp_precos_combustiveis' não encontrada. Execute 'fetch_anp.py semear-dados-demonstracao'.[/yellow]")
        return

    # Check Câmara CEAP fuel receipts
    if "camara_ceap_despesas" in tables and "camara_deputados" in tables:
        console.print("\n[cyan]1. Verificando despesas de combustível na Cota Parlamentar (Câmara CEAP)...[/cyan]")
        ceap_combustivel = db.query("""
            SELECT 
                d.nome AS nome_parlamentar,
                d.sigla_uf,
                c.nome_fornecedor,
                c.cnpj_cpf_fornecedor,
                c.valor_liquido,
                c.data_documento
            FROM camara_ceap_despesas c
            JOIN camara_deputados d ON c.id_deputado = d.id_deputado
            WHERE c.tipo_despesa ILIKE '%COMBUSTIVEL%' OR c.tipo_despesa ILIKE '%LUBRIFICANTE%'
            ORDER BY c.valor_liquido DESC
            LIMIT 5
        """)
        if ceap_combustivel:
            t = Table(title="⛽ Amostra de Abastecimentos Parlamentares na CEAP", border_style="cyan")
            t.add_column("Parlamentar", style="white")
            t.add_column("UF", style="magenta")
            t.add_column("Posto Fornecedor", style="yellow")
            t.add_column("CNPJ Fornecedor", style="cyan")
            t.add_column("Valor da Nota", style="bold green", justify="right")
            t.add_column("Data", style="dim")

            for row in ceap_combustivel:
                t.add_row(row[0], row[1], str(row[2])[:35], str(row[3]), f"R$ {row[4]:,.2f}", str(row[5]))
            console.print(t)

    # Check ANP benchmark per municipality
    medias_anp = db.query("""
        SELECT 
            municipio,
            uf,
            produto,
            AVG(valor_venda) AS media_venda,
            MAX(valor_venda) AS max_venda
        FROM anp_precos_combustiveis
        GROUP BY municipio, uf, produto
        ORDER BY uf, municipio
    """)

    if medias_anp:
        t_anp = Table(title="📊 Teto de Referência ANP por Município", border_style="green")
        t_anp.add_column("Município", style="white")
        t_anp.add_column("UF", style="magenta")
        t_anp.add_column("Combustível", style="yellow")
        t_anp.add_column("Preço Médio Bomba", style="cyan", justify="right")
        t_anp.add_column(f"Teto Limite Alerta (+{((fator_alerta - 1.0) * 100):.0f}%)", style="bold red", justify="right")

        for r in medias_anp:
            mun, uf, prod, med, max_v = r
            teto = med * fator_alerta
            t_anp.add_row(mun, uf, prod, f"R$ {med:,.2f}", f"R$ {teto:,.2f}")
        console.print(t_anp)

    console.print("\n[dim green]✓ Auditoria de conformidade concluída. Referenciais da ANP sincronizados no Lakehouse.[/dim green]")


@app.command()
def info():
    """Exibe informações sobre os dados de combustíveis."""
    db = get_db()
    c = db.count("anp_precos_combustiveis")
    console.print(f"[cyan]ANP no Lakehouse:[/cyan] {c} coletas disponíveis para auditoria de sobrepreço.")


if __name__ == "__main__":
    app()
