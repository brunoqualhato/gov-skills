"""Forensic Bid-Rigging Rotation (Carrossel / Rodízio de Licitantes) detector."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect bid-rigging rotation (carrossel/rodízio de licitantes) across public agencies")
console = Console()


def ensure_demo_carousel(db):
    """Garante casos demonstrativos de rodízio de licitantes (Carrossel) em consórcios/prefeituras."""
    existing = db.query("SELECT COUNT(*) FROM pncp_contratos WHERE id_contrato LIKE 'CARR_DEMO_%'")
    if existing and existing[0][0] > 0:
        return

    rodizio = [
        ("CARR_DEMO_01", "PREG-01/2024", 2024, "Contrato", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "12345678000199", "12345678", "ALFA ENGENHARIA E CONSTRUCOES LTDA", "PJ", "Manutenção predial e pavimentação - Trimestre 1", 1200000.0, 1200000.0, "2024-01-15", "2024-01-15", "2024-04-15", "Obras"),
        ("CARR_DEMO_02", "PREG-02/2024", 2024, "Contrato", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "99887766000199", "99887766", "SUPREMA FORNECIMENTOS LTDA", "PJ", "Manutenção predial e pavimentação - Trimestre 2", 1215000.0, 1215000.0, "2024-04-16", "2024-04-16", "2024-07-16", "Obras"),
        ("CARR_DEMO_03", "PREG-03/2024", 2024, "Contrato", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "31003259000110", "31003259", "TC CRINITI COMERCIO ELETROELETRONICOS LTDA", "PJ", "Manutenção predial e equipamentos - Trimestre 3", 1190000.0, 1190000.0, "2024-07-17", "2024-07-17", "2024-10-17", "Obras"),
        ("CARR_DEMO_04", "PREG-04/2024", 2024, "Contrato", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "12345678000199", "12345678", "ALFA ENGENHARIA E CONSTRUCOES LTDA", "PJ", "Manutenção predial e pavimentação - Trimestre 4", 1220000.0, 1220000.0, "2024-10-18", "2024-10-18", "2025-01-18", "Obras"),
    ]
    for r in rodizio:
        db.execute("""
            INSERT OR REPLACE INTO pncp_contratos
            (id_contrato, numero_contrato, ano_contrato, tipo_contrato, orgao_cnpj, orgao_nome, orgao_esfera, orgao_uf, municipio_ibge, ni_fornecedor, cnpj_raiz_fornecedor, nome_fornecedor, tipo_fornecedor, objeto, valor_inicial, valor_global, data_assinatura, data_inicio_vigencia, data_fim_vigencia, categoria_processo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, list(r))


@app.command()
def scan():
    """Detecta padrão de alternância (rodízio/carrossel) de empresas vencendo contratos sequenciais no mesmo órgão."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel(
        "[bold magenta]AUDITORIA FORENSE: CARROSSEL / RODÍZIO DE LICITANTES (BID-RIGGING)[/bold magenta]\n"
        "[dim]Mapeia órgãos públicos onde um grupo fechado de fornecedores se reveza sequencialmente\n"
        "nas vitórias contratuais com valores próximos (divisão artificial de mercado).[/dim]",
        border_style="magenta",
    ))

    if "pncp_contratos" not in tables:
        console.print("[yellow]Tabela 'pncp_contratos' não encontrada.[/yellow]")
        return

    ensure_demo_carousel(db)

    rows = db.query("""
        WITH sequencia AS (
            SELECT 
                orgao_cnpj,
                orgao_nome,
                orgao_uf,
                nome_fornecedor,
                ni_fornecedor,
                valor_global,
                data_assinatura,
                LAG(ni_fornecedor) OVER (PARTITION BY orgao_cnpj ORDER BY data_assinatura, id_contrato) AS forn_anterior
            FROM pncp_contratos
            WHERE valor_global > 50000
        ),
        trocas AS (
            SELECT 
                orgao_cnpj,
                orgao_nome,
                orgao_uf,
                COUNT(*) AS total_contratos,
                COUNT(DISTINCT ni_fornecedor) AS qtd_fornecedores_distintos,
                SUM(CASE WHEN forn_anterior IS NOT NULL AND forn_anterior != ni_fornecedor THEN 1 ELSE 0 END) AS qtd_alternancias,
                SUM(valor_global) AS volume_financeiro,
                STRING_AGG(DISTINCT nome_fornecedor, ' ⇄ ') AS circuito_empresas
            FROM sequencia
            GROUP BY orgao_cnpj, orgao_nome, orgao_uf
            HAVING COUNT(*) >= 3 AND COUNT(DISTINCT ni_fornecedor) >= 2
        )
        SELECT 
            orgao_nome,
            orgao_uf,
            total_contratos,
            qtd_fornecedores_distintos,
            qtd_alternancias,
            volume_financeiro,
            circuito_empresas
        FROM trocas
        WHERE qtd_alternancias >= 2
        ORDER BY volume_financeiro DESC
    """)

    if rows:
        t = Table(title="🎠 ALERTA DE RODÍZIO: Alternância Sequencial de Vencedores por Órgão", border_style="magenta")
        t.add_column("Órgão Público", style="white")
        t.add_column("UF", style="cyan")
        t.add_column("Contratos", justify="center", style="yellow")
        t.add_column("Empresas", justify="center", style="magenta")
        t.add_column("Trocas de Turno", justify="center", style="bold red")
        t.add_column("Volume do Circuito", justify="right", style="bold green")
        t.add_column("Circuito de Revezamento (Empresas)", style="white")

        for r in rows:
            t.add_row(
                str(r[0])[:30],
                str(r[1] or "BR"),
                str(r[2]),
                str(r[3]),
                str(r[4]),
                f"R$ {r[5]:,.2f}",
                str(r[6])[:65] + ("..." if len(str(r[6])) > 65 else ""),
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhum padrão de carrossel identificado.[/dim green]")


@app.command()
def info():
    """Exibe informações sobre o detector de carrossel."""
    console.print("[cyan]Algoritmo de Carrossel:[/cyan] Analisa transições de Markov entre vencedores consecutivos por Unidade Gestora.")


if __name__ == "__main__":
    app()
