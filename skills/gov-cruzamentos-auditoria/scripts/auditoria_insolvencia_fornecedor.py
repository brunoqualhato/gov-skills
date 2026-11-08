"""Predictive Supplier Insolvency & Contract Default Model (Gov Z-Score)."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Calculate predictive supplier insolvency & contract abandonment risk (Gov Z-Score)")
console = Console()


@app.command()
def scan():
    """Calcula a probabilidade de quebra ou abandono de contrato (Gov Z-Score) cruzando PGFN, DataJud, CAGED e RFB."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel(
        "[bold red]MODELO PREDITIVO: RISCO DE INSOLVÊNCIA E QUEBRA DE FORNECEDOR (GOV Z-SCORE)[/bold red]\n"
        "[dim]Combina Alavancagem (Contratos/Capital Social), Passivo Fiscal (PGFN), Litígios Judiciais (DataJud),\n"
        "Evasão de Mão de Obra (CAGED) e Obras Paralisadas para prever default contratual.[/dim]",
        border_style="red",
    ))

    if "pncp_contratos" not in tables:
        console.print("[yellow]Tabela 'pncp_contratos' não encontrada.[/yellow]")
        return

    rows = db.query("""
        WITH fornecedores AS (
            SELECT 
                cnpj_raiz_fornecedor AS cnpj_raiz,
                MAX(ni_fornecedor) AS cnpj,
                MAX(nome_fornecedor) AS razao_social,
                COUNT(id_contrato) AS qtd_contratos,
                SUM(valor_global) AS carteira_pncp
            FROM pncp_contratos
            WHERE cnpj_raiz_fornecedor IS NOT NULL AND cnpj_raiz_fornecedor != ''
            GROUP BY cnpj_raiz_fornecedor
        )
        SELECT 
            f.cnpj,
            f.cnpj_raiz,
            f.razao_social,
            f.qtd_contratos,
            f.carteira_pncp,
            COALESCE((SELECT MAX(e.capital_social) FROM rfb_empresas e WHERE e.cnpj_raiz = f.cnpj_raiz), 10000.0) AS capital_social,
            COALESCE((SELECT SUM(d.valor_consolidado) FROM pgfn_divida_ativa d WHERE d.cnpj_raiz = f.cnpj_raiz), 0.0) AS divida_pgfn,
            COALESCE((SELECT SUM(j.valor_causa) FROM cnj_processos_judiciais j WHERE j.cnpj_raiz_parte = f.cnpj_raiz), 0.0) AS passivo_judicial,
            COALESCE((SELECT MAX(CASE WHEN j.classe_processual ILIKE '%FALENCIA%' THEN 1 ELSE 0 END) FROM cnj_processos_judiciais j WHERE j.cnpj_raiz_parte = f.cnpj_raiz), 0) AS tem_falencia,
            COALESCE((SELECT MAX(c.total_empregados_ativos) FROM mte_caged_empresas_quadro c WHERE c.cnpj_raiz = f.cnpj_raiz), -1) AS empregados_caged
        FROM fornecedores f
        ORDER BY f.carteira_pncp DESC
    """)

    resultados = []
    for r in rows:
        cnpj, raiz, razao, qtd_c, carteira, cap, pgfn, jud, falencia, emp = r
        alavancagem = carteira / max(cap, 1.0)
        passivo_total = pgfn + jud

        # Cálculo de Probabilidade de Default / Insolvência (0 a 99%)
        prob_default = 5.0
        fatores = []

        if falencia == 1:
            prob_default += 45.0
            fatores.append("Falência no DataJud")
        if passivo_total > cap:
            prob_default += 25.0
            fatores.append(f"Passivo > Capital (R$ {passivo_total:,.0f})")
        elif passivo_total > 0:
            prob_default += 15.0
            fatores.append("Dívida PGFN/Judicial")
        if alavancagem > 50:
            prob_default += 15.0
            fatores.append(f"Alavancagem {alavancagem:,.0f}x")
        if 0 <= emp <= 1 and carteira > 500000:
            prob_default += 15.0
            fatores.append(f"Déficit Operacional ({emp} func.)")

        prob_default = min(prob_default, 99.0)
        if prob_default >= 20.0:
            zona = "🔴 COLAPSO IMINENTE" if prob_default >= 70 else ("🟡 ALERTA FINANCEIRO" if prob_default >= 40 else "🟢 MONITORAMENTO")
            resultados.append((razao, cnpj, carteira, cap, passivo_total, prob_default, zona, " | ".join(fatores)))

    resultados.sort(key=lambda x: (x[5], x[2]), reverse=True)

    if resultados:
        t = Table(title="📉 Rating Preditivo de Insolvência de Fornecedores Públicos (Gov Z-Score)", border_style="red")
        t.add_column("Fornecedor", style="bold white")
        t.add_column("Carteira PNCP", justify="right", style="green")
        t.add_column("Capital Social", justify="right", style="cyan")
        t.add_column("Passivo PGFN + CNJ", justify="right", style="bold red")
        t.add_column("Risco de Quebra", justify="center", style="bold yellow")
        t.add_column("Classificação Z-Score", style="white")
        t.add_column("Vetores de Estresse Financeiro", style="magenta")

        for res in resultados[:10]:
            t.add_row(
                f"{res[0][:28]}\n({res[1]})",
                f"R$ {res[2]:,.2f}",
                f"R$ {res[3]:,.2f}",
                f"R$ {res[4]:,.2f}",
                f"{res[5]:.1f}%",
                res[6],
                res[7],
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhum fornecedor em zona de estresse financeiro crítico.[/dim green]")


@app.command()
def info():
    """Exibe a metodologia do Gov Z-Score de solvência de licitantes."""
    console.print("[cyan]Gov Z-Score (Adaptado de Altman Z-Score para Compras Públicas):[/cyan]\nAvalia a capacidade econômico-financeira (Art. 69 da Lei 14.133/21) cruzando exposição contratual ativa com passivos fiscais e judiciais.")


if __name__ == "__main__":
    app()
