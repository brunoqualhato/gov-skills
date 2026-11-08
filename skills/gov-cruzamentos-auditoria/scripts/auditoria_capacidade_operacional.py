"""Forensic detector of operational incapacity: companies with 0 or 1 employees in CAGED/RAIS winning multi-million contracts."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect companies with 0 or minimal employees winning multi-million labor-intensive public contracts")
console = Console()


def init_caged_empresa_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS mte_caged_empresas_quadro (
        cnpj VARCHAR PRIMARY KEY,
        cnpj_raiz VARCHAR,
        total_empregados_ativos INTEGER,
        admissoes_ultimos_12m INTEGER,
        desligamentos_ultimos_12m INTEGER,
        ano_mes_referencia VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def semear_dados():
    """Popula dados de quadro de funcionários do CAGED/RAIS para testes de capacidade operacional."""
    init_caged_empresa_table()
    db = get_db()

    quadros = [
        # SUPREMA FORNECIMENTOS LTDA: Contrato de R$ 4,8M e apenas 1 funcionário!
        {"cnpj": "99887766000199", "raiz": "99887766", "emp": 1, "adm": 0, "desl": 0, "ref": "202401"},
        # ALFA CONSTRUCOES: Contrato de milhões e 0 funcionários registrados!
        {"cnpj": "10222333000144", "raiz": "10222333", "emp": 0, "adm": 0, "desl": 1, "ref": "202401"},
        # TAM Linhas Aéreas: 12.000 funcionários (capacidade normal)
        {"cnpj": "02012862000160", "raiz": "02012862", "emp": 12500, "adm": 450, "desl": 380, "ref": "202401"},
    ]

    records = []
    for q in quadros:
        records.append({
            "cnpj": q["cnpj"],
            "cnpj_raiz": q["raiz"],
            "total_empregados_ativos": q["emp"],
            "admissoes_ultimos_12m": q["adm"],
            "desligamentos_ultimos_12m": q["desl"],
            "ano_mes_referencia": q["ref"],
        })

    df = pl.DataFrame(records)
    db.conn.register("tmp_caged_seed", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO mte_caged_empresas_quadro 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_caged_seed
    """)
    console.print("[bold green]✓ Base de capacidade operacional do CAGED semeada com sucesso![/bold green]")


@app.command()
def scan(
    min_contrato: float = typer.Option(500000.0, "--min-contrato", help="Valor mínimo de contrato para exigir quadro funcional"),
    max_funcionarios: int = typer.Option(2, "--max-funcionarios", help="Número máximo de funcionários para considerar incapacidade"),
):
    """Identifica empresas com contratos de alto valor no PNCP mas com 0 ou quase nenhum funcionário no CAGED."""
    init_caged_empresa_table()
    db = get_db()
    console.print(Panel("[bold red]🚨 DETECÇÃO DE INCAPACIDADE OPERACIONAL: 'A EMPRESA SEM FUNCIONÁRIOS'[/bold red]", border_style="red"))

    rows = db.query(f"""
        SELECT 
            p.nome_fornecedor,
            p.ni_fornecedor,
            p.orgao_nome,
            printf('R$ %,.2f', p.valor_global) AS valor_contrato,
            LEFT(p.objeto, 40) AS objeto,
            COALESCE(q.total_empregados_ativos, 0) AS total_funcionarios,
            COALESCE(q.ano_mes_referencia, 'Não informado') AS ref_caged
        FROM pncp_contratos p
        JOIN mte_caged_empresas_quadro q ON p.cnpj_raiz_fornecedor = q.cnpj_raiz
        WHERE p.valor_global >= {min_contrato}
          AND COALESCE(q.total_empregados_ativos, 0) <= {max_funcionarios}
        ORDER BY p.valor_global DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA: Contratos Vultosos Vencidos por Empresas Sem Quadro Funcional (Possível Empresa de Fachada / Gaveta)", border_style="bold red")
        t.add_column("Fornecedor", style="bold yellow")
        t.add_column("CNPJ", style="dim")
        t.add_column("Órgão", style="white")
        t.add_column("Valor do Contrato", style="bold red", justify="right")
        t.add_column("Objeto", style="dim")
        t.add_column("Funcionários CLT", style="bold red", justify="center")
        for r in rows:
            t.add_row(r[0][:25], r[1], r[2][:20], r[3], r[4], str(r[5]))
        console.print(t)
        console.print(Panel(
            "[bold yellow]INDÍCIO DE FRAUDE:[/bold yellow] Empresas que faturam milhões prestando serviços ou fornecendo bens sem quadro funcional registrado no CAGED/MTE configuram o clássico modelo de [bold red]'empresa de fachada ou intermediária quarteirizadora'[/bold red]. Ela vence a licitação pública e terceiriza 100% da execução para terceiros cobrando pedágio sobre o erário.",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhuma divergência crítica de capacidade operacional identificada.[/green]")


if __name__ == "__main__":
    app()
