"""Forensic tracker of abandoned/stalled public works contractors winning new PNCP contracts."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Audit stalled public works contractors against active procurement")
console = Console()


@app.command()
def scan():
    """Identifica empreiteiras com obras paralisadas no Obrasgov que continuam faturando no PNCP."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel("[bold red]AUDITORIA FORENSE: OBRAS PARALISADAS vs NOVOS CONTRATOS NO PNCP[/bold red]\n"
                        "[dim]Rastreia empresas que abandonaram creches, hospitais ou pontes e continuam vencendo licitações.[/dim]",
                        border_style="red"))

    if "obrasgov_obras_publicas" not in tables or "pncp_contratos" not in tables:
        console.print("[yellow]Tabelas 'obrasgov_obras_publicas' e 'pncp_contratos' necessárias.[/yellow]")
        return

    rows = db.query("""
        SELECT 
            o.id_obra,
            o.nome_obra,
            o.municipio AS municipio_obra,
            o.uf AS uf_obra,
            o.situacao_obra,
            o.motivo_paralisacao,
            o.razao_social_executor,
            o.cnpj_executor,
            printf('R$ %,.2f', o.valor_investimento) AS investimento_obra,
            o.percentual_execucao,
            p.numero_contrato,
            p.orgao_nome,
            printf('R$ %,.2f', p.valor_global) AS novo_contrato_pncp,
            p.data_assinatura
        FROM obrasgov_obras_publicas o
        JOIN pncp_contratos p ON o.cnpj_raiz_executor = p.cnpj_raiz_fornecedor
        WHERE o.situacao_obra IN ('PARALISADA', 'ATRASADA')
        ORDER BY p.valor_global DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA FORENSE: Empreiteiras com Obras Paralisadas Vencendo Contratos Públicos", border_style="red")
        t.add_column("Obra Abandonada", style="yellow")
        t.add_column("Local", style="magenta")
        t.add_column("Exec (%)", style="cyan", justify="right")
        t.add_column("Empreiteira", style="bold white")
        t.add_column("CNPJ", style="dim")
        t.add_column("Novo Contrato PNCP", style="bold red", justify="right")
        t.add_column("Novo Órgão Contratante", style="white")

        for r in rows:
            t.add_row(
                r[1][:30],
                f"{r[2]}/{r[3]}",
                f"{r[9]:.1f}%",
                r[6][:28],
                r[7],
                r[12],
                str(r[11])[:30]
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhuma sobreposição de obras paralisadas identificada com os contratos atuais.[/dim green]")


@app.command()
def info():
    """Exibe informações sobre obras no Lakehouse."""
    db = get_db()
    c = db.count("obrasgov_obras_publicas")
    console.print(f"[cyan]Obrasgov no Lakehouse:[/cyan] {c} obras registradas.")


if __name__ == "__main__":
    app()
