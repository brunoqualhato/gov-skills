"""Automated anomaly detector across public procurement, corporate registry, and parliament expenses."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect red flags and anomalies across linked government datasets")
console = Console()


@app.command()
def scan():
    """Varre todas as bases em busca de inconsistências e anomalias de auditoria."""
    db = get_db()
    tables = db.list_tables()
    console.print(Panel("[bold yellow]AUDITORIA AUTOMATIZADA: DETECTOR DE ANOMALIAS[/bold yellow]", border_style="yellow"))

    # 1. Simples Nacional com faturamento de contratos acima do teto (R$ 4,8 milhões/ano)
    if "rfb_empresas" in tables and "pncp_contratos" in tables:
        console.print("[cyan]1. Verificando empresas do Simples Nacional com contratos acima do teto (R$ 4,8M)...[/cyan]")
        rows = db.query("""
            SELECT 
                e.cnpj,
                e.razao_social,
                e.porte,
                printf('R$ %,.2f', SUM(p.valor_global)) AS total_contratado,
                COUNT(p.id_contrato) AS qtd_contratos
            FROM rfb_empresas e
            JOIN pncp_contratos p ON e.cnpj_raiz = p.cnpj_raiz_fornecedor
            WHERE e.opcao_simples = true
            GROUP BY e.cnpj, e.razao_social, e.porte
            HAVING SUM(p.valor_global) > 4800000
            ORDER BY SUM(p.valor_global) DESC
        """)
        if rows:
            t = Table(title="⚠️ ALERTA: Empresas do Simples Nacional Excedendo Teto de R$ 4,8M no PNCP", border_style="red")
            t.add_column("CNPJ", style="cyan")
            t.add_column("Razão Social", style="white")
            t.add_column("Porte", style="yellow")
            t.add_column("Total Contratado", style="bold red")
            t.add_column("Qtd Contratos", style="magenta")
            for r in rows:
                t.add_row(r[0], r[1], r[2], r[3], str(r[4]))
            console.print(t)
        else:
            console.print("[dim green]✓ Nenhuma extrapolação do Simples Nacional identificada até o momento.[/dim green]")

    # 2. Capital social desproporcional (Contratos > 50x o Capital Social da empresa)
    if "rfb_empresas" in tables and "pncp_contratos" in tables:
        console.print("\n[cyan]2. Verificando desproporção entre Capital Social e Volume de Contratos...[/cyan]")
        rows = db.query("""
            SELECT 
                e.cnpj,
                e.razao_social,
                printf('R$ %,.2f', e.capital_social) AS capital_social,
                printf('R$ %,.2f', SUM(p.valor_global)) AS total_contratado,
                ROUND(SUM(p.valor_global) / NULLIF(e.capital_social, 0), 1) AS multiplicador
            FROM rfb_empresas e
            JOIN pncp_contratos p ON e.cnpj_raiz = p.cnpj_raiz_fornecedor
            WHERE e.capital_social > 0
            GROUP BY e.cnpj, e.razao_social, e.capital_social
            HAVING SUM(p.valor_global) > (e.capital_social * 20)
            ORDER BY multiplicador DESC
        """)
        if rows:
            t = Table(title="⚠️ ALERTA: Contratos com Alta Desproporção em Relação ao Capital Social (> 20x)", border_style="yellow")
            t.add_column("CNPJ", style="cyan")
            t.add_column("Razão Social", style="white")
            t.add_column("Capital Social", style="yellow")
            t.add_column("Total Contratos", style="green")
            t.add_column("Multiplicador", style="bold red")
            for r in rows:
                t.add_row(r[0], r[1], r[2], r[3], f"{r[4]}x")
            console.print(t)
        else:
            console.print("[dim green]✓ Nenhuma desproporção crítica encontrada.[/dim green]")

    # 3. Fornecedores que faturaram simultaneamente na Câmara (CEAP) e no Governo (PNCP)
    if "camara_ceap_despesas" in tables and "pncp_contratos" in tables:
        console.print("\n[cyan]3. Verificando fornecedores que recebem da Câmara dos Deputados E de Contratos do Governo...[/cyan]")
        rows = db.query("""
            SELECT 
                c.cnpj_raiz_fornecedor,
                COALESCE(e.razao_social, c.nome_fornecedor) AS fornecedor,
                printf('R$ %,.2f', c.total_ceap) AS total_camara,
                printf('R$ %,.2f', p.total_pncp) AS total_governo
            FROM (
                SELECT cnpj_raiz_fornecedor, MAX(nome_fornecedor) AS nome_fornecedor, SUM(valor_liquido) AS total_ceap 
                FROM camara_ceap_despesas 
                WHERE cnpj_raiz_fornecedor IS NOT NULL
                GROUP BY cnpj_raiz_fornecedor
            ) c
            JOIN (
                SELECT cnpj_raiz_fornecedor, SUM(valor_global) AS total_pncp 
                FROM pncp_contratos 
                WHERE cnpj_raiz_fornecedor IS NOT NULL
                GROUP BY cnpj_raiz_fornecedor
            ) p ON c.cnpj_raiz_fornecedor = p.cnpj_raiz_fornecedor
            LEFT JOIN rfb_empresas e ON c.cnpj_raiz_fornecedor = e.cnpj_raiz
            ORDER BY (c.total_ceap + p.total_pncp) DESC
            LIMIT 10
        """)
        if rows:
            t = Table(title="🔍 Conexão Legislativo + Executivo: Fornecedores com Contratos em Ambos os Poderes", border_style="blue")
            t.add_column("CNPJ Raiz", style="cyan")
            t.add_column("Fornecedor", style="white")
            t.add_column("Total Câmara (CEAP)", style="magenta")
            t.add_column("Total Governo (PNCP)", style="green")
            for r in rows:
                t.add_row(r[0], r[1][:35], r[2], r[3])
            console.print(t)


if __name__ == "__main__":
    app()
