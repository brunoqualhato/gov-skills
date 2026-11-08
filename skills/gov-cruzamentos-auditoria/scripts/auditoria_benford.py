"""Forensic Benford's Law (First-Digit Law) statistical anomaly detector for public expenses and contracts."""

import math
import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Apply Benford's Law statistical test to detect fabricated invoices and contracts")
console = Console()

BENFORD_PROBS = {d: math.log10(1 + 1 / d) for d in range(1, 10)}


@app.command()
def scan(
    min_notas: int = typer.Option(150, "--min-notas", "-m", help="Mínimo de notas fiscais por parlamentar/fornecedor para teste estatístico"),
):
    """Aplica a Lei de Benford (Teste Qui-Quadrado e MAD) em despesas parlamentares e contratos públicos."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel(
        "[bold yellow]AUDITORIA ESTATÍSTICA: LEI DE BENFORD (DETECÇÃO DE NOTAS FABRICADAS)[/bold yellow]\n"
        "[dim]Avalia se o primeiro dígito significativo (1 a 9) segue a distribuição logarítmica natural de Benford.\n"
        "Desvios extremos (Qui-Quadrado > 15.51 para p < 0.05) indicam possível manipulação humana ou recibos forjados.[/dim]",
        border_style="yellow",
    ))

    if "camara_ceap_despesas" not in tables:
        console.print("[yellow]Tabela 'camara_ceap_despesas' não encontrada.[/yellow]")
        return

    # 1. Distribuição Global na CEAP
    console.print("\n[cyan]1. Analisando distribuição global de primeiros dígitos nas despesas da CEAP...[/cyan]")
    rows_global = db.query("""
        WITH digitos AS (
            SELECT 
                CAST(SUBSTR(REGEXP_REPLACE(CAST(ABS(valor_liquido) AS VARCHAR), '^0+\\.?0*', ''), 1, 1) AS INTEGER) AS d
            FROM camara_ceap_despesas
            WHERE valor_liquido >= 10
        )
        SELECT d, COUNT(*) AS qtd
        FROM digitos
        WHERE d BETWEEN 1 AND 9
        GROUP BY d
        ORDER BY d
    """)

    if rows_global:
        total_global = sum(r[1] for r in rows_global)
        obs_map = {r[0]: r[1] for r in rows_global}

        t_glob = Table(title=f"📊 Distribuição de Benford Global (Amostra: {total_global:,} notas fiscais)", border_style="cyan")
        t_glob.add_column("Dígito (1-9)", justify="center", style="bold white")
        t_glob.add_column("Qtd Observada", justify="right", style="cyan")
        t_glob.add_column("% Observado", justify="right", style="yellow")
        t_glob.add_column("% Esperado (Benford)", justify="right", style="green")
        t_glob.add_column("Desvio Absoluto", justify="right", style="magenta")

        chi_sq_global = 0.0
        mad_sum = 0.0
        for d in range(1, 10):
            obs = obs_map.get(d, 0)
            pct_obs = obs / total_global if total_global else 0.0
            pct_exp = BENFORD_PROBS[d]
            exp_count = pct_exp * total_global
            diff = abs(pct_obs - pct_exp)
            mad_sum += diff
            if exp_count > 0:
                chi_sq_global += ((obs - exp_count) ** 2) / exp_count

            t_glob.add_row(
                str(d),
                f"{obs:,}",
                f"{pct_obs * 100:.2f}%",
                f"{pct_exp * 100:.2f}%",
                f"{diff * 100:+.2f}%",
            )
        console.print(t_glob)
        mad = mad_sum / 9.0
        console.print(f"[dim]Estatísticas Globais: MAD = {mad:.4f} | Qui-Quadrado (χ²) = {chi_sq_global:.2f}[/dim]")

    # 2. Ranking de Fornecedores / Parlamentares com maior anomalia de Benford (concentração em dígitos 7, 8, 9)
    console.print("\n[cyan]2. Varrendo fornecedores e parlamentares com maior distorção estatística (concentração artificial)...[/cyan]")
    rows_forn = db.query(f"""
        WITH base AS (
            SELECT 
                nome_fornecedor,
                cnpj_cpf_fornecedor,
                valor_liquido,
                CAST(SUBSTR(REGEXP_REPLACE(CAST(ABS(valor_liquido) AS VARCHAR), '^0+\\.?0*', ''), 1, 1) AS INTEGER) AS digito
            FROM camara_ceap_despesas
            WHERE valor_liquido >= 10 AND nome_fornecedor IS NOT NULL
        ),
        resumo AS (
            SELECT 
                nome_fornecedor,
                cnpj_cpf_fornecedor,
                COUNT(*) AS total_notas,
                SUM(valor_liquido) AS valor_total,
                SUM(CASE WHEN digito IN (7, 8, 9) THEN 1 ELSE 0 END) AS qtd_digitos_altos,
                SUM(CASE WHEN digito = 1 THEN 1 ELSE 0 END) AS qtd_digito_1
            FROM base
            WHERE digito BETWEEN 1 AND 9
            GROUP BY nome_fornecedor, cnpj_cpf_fornecedor
            HAVING COUNT(*) >= {min_notas}
        )
        SELECT 
            nome_fornecedor,
            cnpj_cpf_fornecedor,
            total_notas,
            valor_total,
            (CAST(qtd_digitos_altos AS DOUBLE) / total_notas) * 100 AS pct_altos,
            (CAST(qtd_digito_1 AS DOUBLE) / total_notas) * 100 AS pct_d1
        FROM resumo
        WHERE (CAST(qtd_digitos_altos AS DOUBLE) / total_notas) > 0.35
        ORDER BY pct_altos DESC
        LIMIT 10
    """)

    if rows_forn:
        t_anom = Table(
            title="🚨 ALERTA FORENSE DE BENFORD: Fornecedores com Concentração Anormal em Dígitos Altos (7, 8, 9 > 35% vs Esperado 15.5%)",
            border_style="red",
        )
        t_anom.add_column("Fornecedor", style="white")
        t_anom.add_column("CNPJ / CPF", style="cyan")
        t_anom.add_column("Qtd Notas", justify="right", style="magenta")
        t_anom.add_column("Total Recebido", justify="right", style="green")
        t_anom.add_column("% Dígito 1 (Esp: 30.1%)", justify="right", style="yellow")
        t_anom.add_column("% Dígitos 7-8-9 (Esp: 15.5%)", justify="right", style="bold red")

        for r in rows_forn:
            t_anom.add_row(
                str(r[0])[:35],
                str(r[1]),
                f"{r[2]:,}",
                f"R$ {r[3]:,.2f}",
                f"{r[5]:.1f}%",
                f"{r[4]:.1f}%",
            )
        console.print(t_anom)
    else:
        console.print("[dim green]✓ Nenhuma anomalia severa de Benford encontrada para o corte atual.[/dim green]")


@app.command()
def referencia():
    """Exibe a tabela teórica de probabilidades da Lei de Benford."""
    t = Table(title="Referência Teórica da Lei de Benford — P(d) = log10(1 + 1/d)", border_style="green")
    t.add_column("Primeiro Dígito", justify="center", style="bold cyan")
    t.add_column("Probabilidade Esperada (%)", justify="right", style="green")
    for d, p in BENFORD_PROBS.items():
        t.add_row(str(d), f"{p * 100:.2f}%")
    console.print(t)


if __name__ == "__main__":
    app()
