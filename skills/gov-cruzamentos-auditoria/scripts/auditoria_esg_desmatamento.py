"""ESG & Environmental Compliance Auditor: correlates IBAMA infractions with procurement & BNDES credit."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Audit environmental infractions against public contracts and BNDES credit")
console = Console()


@app.command()
def scan():
    """Identifica empresas autuadas ou embargadas pelo IBAMA recebendo contratos públicos ou crédito do BNDES."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel("[bold green]AUDITORIA FORENSE ESG: MEIO AMBIENTE (IBAMA) x CONTRATOS PNCP & BNDES[/bold green]\n"
                        "[dim]Rastreia empresas com multas por desmatamento ou poluição faturando verbas públicas federais.[/dim]",
                        border_style="green"))

    if "ibama_autos_infracao" not in tables:
        console.print("[yellow]Tabela 'ibama_autos_infracao' não encontrada.[/yellow]")
        return

    # 1. IBAMA x PNCP Contratos
    if "pncp_contratos" in tables:
        console.print("\n[cyan]1. Cruzando Fornecedores do PNCP com Autos de Infração do IBAMA...[/cyan]")
        rows_pncp = db.query("""
            SELECT 
                p.numero_contrato,
                p.orgao_nome,
                p.nome_fornecedor,
                p.ni_fornecedor,
                printf('R$ %,.2f', p.valor_global) AS valor_contrato,
                i.numero_auto,
                i.tipo_infracao,
                printf('R$ %,.2f', i.valor_multa) AS valor_multa,
                i.situacao_debito
            FROM pncp_contratos p
            JOIN ibama_autos_infracao i ON p.cnpj_raiz_fornecedor = i.cnpj_raiz
            ORDER BY p.valor_global DESC
        """)
        if rows_pncp:
            t = Table(title="⚠️ ALERTA ESG: Fornecedores do Governo Federal com Autuação Ambiental no IBAMA", border_style="red")
            t.add_column("Fornecedor", style="white")
            t.add_column("CNPJ", style="cyan")
            t.add_column("Valor Contrato PNCP", style="bold red", justify="right")
            t.add_column("Infração IBAMA", style="yellow")
            t.add_column("Multa IBAMA", style="magenta", justify="right")
            t.add_column("Situação Débito", style="dim")

            for r in rows_pncp:
                t.add_row(r[2][:30], r[3], r[4], r[6][:35], r[7], r[8])
            console.print(t)
        else:
            console.print("[dim green]✓ Nenhum fornecedor do PNCP com autuação no IBAMA até o momento.[/dim green]")

    # 2. IBAMA x BNDES Financiamentos
    if "bndes_operacoes_financiamento" in tables:
        console.print("\n[cyan]2. Cruzando Financiamentos do BNDES com Áreas Embargadas e Autos do IBAMA...[/cyan]")
        rows_bndes = db.query("""
            SELECT 
                b.numero_contrato,
                b.razao_social_cliente,
                b.cnpj_cliente,
                b.linha_financiamento,
                printf('R$ %,.2f', b.valor_contratado) AS valor_bndes,
                i.numero_auto,
                i.tipo_infracao,
                printf('R$ %,.2f', i.valor_multa) AS valor_multa,
                i.bioma
            FROM bndes_operacoes_financiamento b
            JOIN ibama_autos_infracao i ON b.cnpj_raiz_cliente = i.cnpj_raiz
            ORDER BY b.valor_contratado DESC
        """)
        if rows_bndes:
            t = Table(title="🚨 ALERTA ESG: Empresas com Multas Ambientais Financiadas com Recursos do BNDES", border_style="red")
            t.add_column("Empresa Financiada", style="white")
            t.add_column("CNPJ", style="cyan")
            t.add_column("Crédito BNDES", style="bold green", justify="right")
            t.add_column("Linha de Financiamento", style="dim")
            t.add_column("Infração Ambiental", style="bold red")
            t.add_column("Multa IBAMA", style="yellow", justify="right")
            t.add_column("Bioma", style="magenta")

            for r in rows_bndes:
                t.add_row(r[1][:30], r[2], r[4], r[3], r[6][:35], r[7], r[8])
            console.print(t)
        else:
            console.print("[dim green]✓ Nenhuma sobreposição de crédito BNDES com autuações ambientais.[/dim green]")


@app.command()
def info():
    """Exibe informações sobre os dados de fiscalização ambiental."""
    db = get_db()
    c = db.count("ibama_autos_infracao")
    console.print(f"[cyan]IBAMA no Lakehouse:[/cyan] {c} autos de infração cadastrados.")


if __name__ == "__main__":
    app()
