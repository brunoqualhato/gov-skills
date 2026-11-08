"""Forensic corporate network graph analyzer: uncovers hidden economic groups and interlocking directorates."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Analyze corporate networks, partner graphs, and hidden groups")
console = Console()


@app.command()
def scan(
    min_empresas: int = typer.Option(2, "--min-empresas", "-m", help="Mínimo de empresas compartilhadas por um sócio"),
):
    """Identifica sócios presentes em múltiplos CNPJs (Interlocking Directorates / Grupos Ocultos)."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel("[bold magenta]AUDITORIA FORENSE: TEIA SOCIETÁRIA & GRUPOS ECONÔMICOS OCULTOS[/bold magenta]\n"
                        "[dim]Mapeia administradores e sócios comuns que conectam empresas formalmente distintas.[/dim]",
                        border_style="magenta"))

    if "rfb_socios" not in tables:
        console.print("[yellow]Tabela 'rfb_socios' não encontrada.[/yellow]")
        return

    rows = db.query(f"""
        SELECT 
            s.nome_socio,
            s.cpf_cnpj_socio,
            COUNT(DISTINCT s.cnpj_raiz) AS total_empresas_vinculadas,
            STRING_AGG(DISTINCT COALESCE(e.razao_social, s.cnpj_raiz), ' | ') AS empresas_conectadas
        FROM rfb_socios s
        LEFT JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
        WHERE s.nome_socio IS NOT NULL AND s.nome_socio != ''
        GROUP BY s.nome_socio, s.cpf_cnpj_socio
        HAVING COUNT(DISTINCT s.cnpj_raiz) >= {min_empresas}
        ORDER BY total_empresas_vinculadas DESC
    """)

    if rows:
        t = Table(title="🕸️ Teia de Relacionamentos: Sócios Conectando Múltiplas Empresas", border_style="magenta")
        t.add_column("Nome do Administrador / Sócio", style="bold white")
        t.add_column("Documento", style="cyan")
        t.add_column("Qtd Empresas", style="bold yellow", justify="center")
        t.add_column("Empresas Vinculadas na Rede", style="white")

        for r in rows:
            t.add_row(r[0], str(r[1] or "N/D"), str(r[2]), r[3][:60] + ("..." if len(r[3]) > 60 else ""))
        console.print(t)
    else:
        console.print(f"[dim green]✓ Nenhum sócio compartilhado entre mais de {min_empresas} empresas encontrado.[/dim green]")


@app.command()
def investigar_socio(
    nome: str = typer.Option(..., "--nome", "-n", help="Nome do sócio para expandir a teia societária"),
):
    """Expande todos os tentáculos societários e contratos de um administrador específico."""
    db = get_db()
    sql = """
        SELECT 
            s.nome_socio,
            s.qualificacao_socio,
            COALESCE(e.razao_social, s.cnpj_raiz) AS empresa,
            s.cnpj_raiz,
            e.capital_social,
            e.opcao_simples
        FROM rfb_socios s
        LEFT JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
        WHERE s.nome_socio ILIKE ?
    """
    db.display_results(sql, [f"%{nome}%"])


if __name__ == "__main__":
    app()
