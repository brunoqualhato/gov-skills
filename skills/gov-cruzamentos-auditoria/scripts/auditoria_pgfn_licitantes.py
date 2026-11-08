"""Forensic detector of procurement winners with active debts in PGFN."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect government contractors with active debts inscribed in PGFN")
console = Console()


@app.command()
def scan():
    """Identifica empresas vencedoras de contratos públicos que possuem débitos inscritos na Dívida Ativa da União."""
    db = get_db()
    tables = db.list_tables()

    if "pgfn_divida_ativa" not in tables or "pncp_contratos" not in tables:
        console.print("[yellow]As tabelas 'pgfn_divida_ativa' e 'pncp_contratos' precisam estar populadas.[/yellow]")
        return

    console.print(Panel("[bold red]🚨 DETECÇÃO DE FORNECEDORES PÚBLICOS INSCRITOS NA DÍVIDA ATIVA DA UNIÃO (PGFN)[/bold red]", border_style="red"))

    rows = db.query("""
        SELECT 
            p.nome_fornecedor,
            p.ni_fornecedor,
            p.orgao_nome,
            printf('R$ %,.2f', p.valor_global) AS valor_contrato_governo,
            d.tipo_divida,
            d.situacao_inscricao,
            printf('R$ %,.2f', d.valor_consolidado) AS valor_divida_ativa,
            d.data_inscricao
        FROM pncp_contratos p
        JOIN pgfn_divida_ativa d ON p.cnpj_raiz_fornecedor = d.cnpj_raiz
        ORDER BY d.valor_consolidado DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA: Fornecedor Recebendo Dinheiro Público com Dívida Ativa Não Paga", border_style="bold red")
        t.add_column("Fornecedor Contratado", style="bold yellow")
        t.add_column("CNPJ", style="dim")
        t.add_column("Órgão Contratante", style="white")
        t.add_column("Contrato", style="green", justify="right")
        t.add_column("Tipo de Dívida", style="magenta")
        t.add_column("Situação", style="dim")
        t.add_column("Dívida Ativa PGFN", style="bold red", justify="right")
        for r in rows:
            t.add_row(r[0][:30], r[1], r[2][:25], r[3], r[4], r[5], r[6])
        console.print(t)
        console.print(Panel(
            "[bold yellow]IRREGULARIDADE FISCAL:[/bold yellow] Pelo Art. 68 da Lei nº 14.133/2021, a regularidade fiscal perante a Fazenda Nacional e a Seguridade Social é [bold red]requisito obrigatório de habilitação e manutenção contratual[/bold red]. A realização de pagamentos a empresas em dívida ativa sem retenção cautelar gera responsabilidade solidária do gestor público.",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhum fornecedor do PNCP com débito ativo na PGFN identificado.[/green]")


if __name__ == "__main__":
    app()
