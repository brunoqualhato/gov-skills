"""Main entry point and CLI for gov-skills."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure base repo is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.db import get_db
from core.config import settings

app = typer.Typer(help="gov-skills: Plataforma de Inteligência e Domínio dos Dados Públicos do Governo Federal")
console = Console()


@app.command()
def info():
    """Exibe o status do Data Lakehouse DuckDB e o volume de dados acumulado."""
    db = get_db()
    tables = db.list_tables()
    db_size_mb = (settings.DB_PATH.stat().st_size / (1024 * 1024)) if settings.DB_PATH.exists() else 0.0

    console.print(Panel(
        f"[bold white]🏛️ GOV-SKILLS: DATA LAKEHOUSE CENTRAL[/bold white]\n"
        f"[cyan]Arquivo do Banco:[/cyan] {settings.DB_PATH}\n"
        f"[cyan]Tamanho em Disco:[/cyan] {db_size_mb:.2f} MB\n"
        f"[cyan]Tabelas Ativas:[/cyan] {len(tables)}",
        border_style="green",
    ))

    if tables:
        t = Table(title="Tabelas Armazenadas no DuckDB")
        t.add_column("Tabela", style="cyan")
        t.add_column("Total de Registros", style="green", justify="right")
        t.add_column("Domínio Governamental", style="yellow")

        domain_map = {
            "ibge_municipios": "IBGE (Malha Territorial)",
            "pncp_contratos": "PNCP / Compras.gov.br",
            "bcb_series_temporais": "Banco Central (SGS Macroeconomia)",
            "bcb_expectativas_focus": "Banco Central (Relatório Focus)",
            "camara_deputados": "Câmara dos Deputados (Parlamentares)",
            "camara_ceap_despesas": "Câmara dos Deputados (Cota CEAP)",
            "cgu_sancoes": "CGU (Sanções CEIS/CNEP)",
            "rfb_empresas": "Receita Federal (Empresas CNPJ)",
            "rfb_socios": "Receita Federal (Quadro Societário QSA)",
        }

        for tbl in sorted(tables):
            cnt = db.count(tbl)
            dom = domain_map.get(tbl, "Governo Federal")
            t.add_row(tbl, f"{cnt:,}", dom)

        console.print(t)
    else:
        console.print("[yellow]Nenhuma tabela criada ainda. Execute uma das skills para popular o banco.[/yellow]")


@app.command()
def skills():
    """Lista todas as skills do repositório, com órgão e objetivos."""
    skills_dir = settings.SKILLS_DIR
    skill_folders = [f for f in sorted(skills_dir.iterdir()) if f.is_dir() and not f.name.startswith(".")]

    t = Table(title=f"Catálogo de Skills ({len(skill_folders)} skills)")
    t.add_column("Skill", style="cyan", no_wrap=True)
    t.add_column("Órgão / Fonte", style="magenta")
    t.add_column("Descrição", style="white")

    for f in skill_folders:
        skill_md = f / "SKILL.md"
        desc = "Módulo de dados públicos"
        agency = "Governo Federal"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("description:"):
                    desc = line.replace("description:", "").strip()
                if "agency:" in line:
                    agency = line.split("agency:")[1].strip().strip('"').strip("'")
        t.add_row(f.name, agency, desc[:80] + ("..." if len(desc) > 80 else ""))

    console.print(t)


@app.command()
def dossie(cnpj: str = typer.Argument(..., help="CNPJ da empresa para gerar dossiê")):
    """Atalho para gerar dossiê 360º de um CNPJ cruzando todas as bases."""
    from skills.gov_cruzamentos_auditoria.scripts.dossie_empresa import dossie as run_dossie
    run_dossie(cnpj=cnpj)


def main():
    app()


if __name__ == "__main__":
    main()
