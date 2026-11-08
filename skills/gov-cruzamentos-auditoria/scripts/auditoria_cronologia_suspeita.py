"""Forensic detector of suspicious timelines: companies created shortly before winning public contracts."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect suspicious timelines: companies created shortly before contract awards")
console = Console()


@app.command()
def scan(
    dias_maximos: int = typer.Option(180, "--dias", "-d", help="Diferença máxima de dias entre a fundação da empresa e o contrato"),
    min_valor: float = typer.Option(100000.0, "--min-valor", help="Valor mínimo de contrato para alerta"),
):
    """Identifica empresas 'recém-nascidas' que ganharam contratos de alto valor logo após a sua fundação na Receita Federal."""
    db = get_db()
    console.print(Panel("[bold red]🚨 DETECÇÃO DE CRONOLOGIA SUSPEITA: 'EMPRESAS CRIADAS SOB MEDIDA'[/bold red]", border_style="red"))

    rows = db.query(f"""
        SELECT 
            p.nome_fornecedor,
            p.ni_fornecedor,
            e.data_inicio_atividade AS data_abertura_empresa,
            p.data_assinatura AS data_contrato,
            DATEDIFF('day', e.data_inicio_atividade, p.data_assinatura) AS dias_de_vida,
            printf('R$ %,.2f', p.valor_global) AS valor_contrato,
            p.orgao_nome,
            LEFT(p.objeto, 40) AS objeto
        FROM pncp_contratos p
        JOIN rfb_empresas e ON p.cnpj_raiz_fornecedor = e.cnpj_raiz
        WHERE e.data_inicio_atividade IS NOT NULL 
          AND p.data_assinatura IS NOT NULL
          AND DATEDIFF('day', e.data_inicio_atividade, p.data_assinatura) BETWEEN 0 AND {dias_maximos}
          AND p.valor_global >= {min_valor}
        ORDER BY dias_de_vida ASC, p.valor_global DESC
    """)

    if rows:
        t = Table(title=f"⚠️ ALERTA: Empresas Criadas Há Menos de {dias_maximos} Dias Vencendo Contratos Relevantes", border_style="bold red")
        t.add_column("Fornecedor", style="bold yellow")
        t.add_column("CNPJ", style="dim")
        t.add_column("Data Abertura", style="cyan")
        t.add_column("Data Contrato", style="yellow")
        t.add_column("Dias de Vida", style="bold red", justify="center")
        t.add_column("Valor do Contrato", style="bold red", justify="right")
        t.add_column("Órgão", style="white")
        for r in rows:
            t.add_row(r[0][:25], r[1], str(r[2]), str(r[3]), f"{r[4]} dias", r[5], r[6][:25])
        console.print(t)
        console.print(Panel(
            "[bold yellow]TIPOLOGIA DE FRAUDE:[/bold yellow] Empresas constituídas poucos meses ou semanas antes de vencerem certames milionários constituem fortíssimo indício de [bold red]'licitação direcionada / empresa sob encomenda'[/bold red], criada especificamente para participar de certame previamente ajustado.",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhuma empresa recém-criada identificada nos contratos da amostra.[/green]")


if __name__ == "__main__":
    app()
