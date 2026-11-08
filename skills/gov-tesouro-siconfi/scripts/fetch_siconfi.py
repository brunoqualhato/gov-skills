"""Fetch and ingest National Treasury (STN / Siconfi) fiscal transfers and municipal budgets into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_ibge, parse_currency, parse_date

app = typer.Typer(help="Manage Siconfi / Tesouro Nacional Database")
console = Console()

SICONFI_BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS siconfi_transferencias (
        id_transferencia VARCHAR PRIMARY KEY,
        ano_exercicio INTEGER,
        mes_exercicio INTEGER,
        codigo_ibge VARCHAR,
        uf VARCHAR,
        tipo_transferencia VARCHAR, -- FPM, FPE, FUNDEB, ROYALTIES, SUS
        valor_bruto DOUBLE,
        valor_deducoes DOUBLE,
        valor_liquido DOUBLE,
        data_repasse DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS siconfi_gastos_funcao (
        id_gasto VARCHAR PRIMARY KEY,
        ano_exercicio INTEGER,
        codigo_ibge VARCHAR,
        uf VARCHAR,
        funcao_governo VARCHAR, -- Educacao, Saude, Seguranca, etc.
        valor_empenhado DOUBLE,
        valor_liquidado DOUBLE,
        valor_pago DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_siconfi_ibge ON siconfi_transferencias(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_siconfi_tipo ON siconfi_transferencias(tipo_transferencia);
    CREATE INDEX IF NOT EXISTS idx_siconfi_funcao ON siconfi_gastos_funcao(funcao_governo);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula repasses constitucionais (FPM, FUNDEB) e despesas por função de municípios chave."""
    init_tables()
    db = get_db()

    transferencias = [
        # São Paulo (3550308)
        {"id": "TR_2024_SP_FPM", "ano": 2024, "mes": 1, "ibge": "3550308", "uf": "SP", "tipo": "FPM", "bruto": 85000000.0, "ded": 17000000.0, "liq": 68000000.0, "dt": "2024-01-10"},
        {"id": "TR_2024_SP_FUNDEB", "ano": 2024, "mes": 1, "ibge": "3550308", "uf": "SP", "tipo": "FUNDEB", "bruto": 120000000.0, "ded": 0.0, "liq": 120000000.0, "dt": "2024-01-15"},
        # Rio de Janeiro (3304557)
        {"id": "TR_2024_RJ_FPM", "ano": 2024, "mes": 1, "ibge": "3304557", "uf": "RJ", "tipo": "FPM", "bruto": 65000000.0, "ded": 13000000.0, "liq": 52000000.0, "dt": "2024-01-10"},
        {"id": "TR_2024_RJ_FUNDEB", "ano": 2024, "mes": 1, "ibge": "3304557", "uf": "RJ", "tipo": "FUNDEB", "bruto": 95000000.0, "ded": 0.0, "liq": 95000000.0, "dt": "2024-01-15"},
        # Maracanaú - CE (2307650)
        {"id": "TR_2024_CE_FPM", "ano": 2024, "mes": 1, "ibge": "2307650", "uf": "CE", "tipo": "FPM", "bruto": 14000000.0, "ded": 2800000.0, "liq": 11200000.0, "dt": "2024-01-10"},
        {"id": "TR_2024_CE_FUNDEB", "ano": 2024, "mes": 1, "ibge": "2307650", "uf": "CE", "tipo": "FUNDEB", "bruto": 18000000.0, "ded": 0.0, "liq": 18000000.0, "dt": "2024-01-15"},
    ]

    gastos = [
        {"id": "GF_2024_SP_EDU", "ano": 2024, "ibge": "3550308", "uf": "SP", "funcao": "EDUCACAO", "emp": 4500000000.0, "liq": 4200000000.0, "pago": 4100000000.0},
        {"id": "GF_2024_SP_SAU", "ano": 2024, "ibge": "3550308", "uf": "SP", "funcao": "SAUDE", "emp": 5200000000.0, "liq": 4900000000.0, "pago": 4800000000.0},
        {"id": "GF_2024_RJ_EDU", "ano": 2024, "ibge": "3304557", "uf": "RJ", "funcao": "EDUCACAO", "emp": 2800000000.0, "liq": 2600000000.0, "pago": 2500000000.0},
        {"id": "GF_2024_RJ_SAU", "ano": 2024, "ibge": "3304557", "uf": "RJ", "funcao": "SAUDE", "emp": 3400000000.0, "liq": 3100000000.0, "pago": 3000000000.0},
        {"id": "GF_2024_CE_EDU", "ano": 2024, "ibge": "2307650", "uf": "CE", "funcao": "EDUCACAO", "emp": 190000000.0, "liq": 180000000.0, "pago": 175000000.0},
        {"id": "GF_2024_CE_SAU", "ano": 2024, "ibge": "2307650", "uf": "CE", "funcao": "SAUDE", "emp": 210000000.0, "liq": 195000000.0, "pago": 190000000.0},
    ]

    for t in transferencias:
        db.execute("""
            INSERT OR REPLACE INTO siconfi_transferencias
            (id_transferencia, ano_exercicio, mes_exercicio, codigo_ibge, uf, tipo_transferencia, valor_bruto, valor_deducoes, valor_liquido, data_repasse)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            t["id"], t["ano"], t["mes"], t["ibge"], t["uf"], t["tipo"],
            t["bruto"], t["ded"], t["liq"], t["dt"]
        ])

    for g in gastos:
        db.execute("""
            INSERT OR REPLACE INTO siconfi_gastos_funcao
            (id_gasto, ano_exercicio, codigo_ibge, uf, funcao_governo, valor_empenhado, valor_liquidado, valor_pago)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            g["id"], g["ano"], g["ibge"], g["uf"], g["funcao"],
            g["emp"], g["liq"], g["pago"]
        ])

    console.print(f"[green]✓ Inseridos repasses do Siconfi ({len(transferencias)} registros) e gastos por função ({len(gastos)} registros) no Lakehouse.[/green]")


@app.command()
def repasses_api(
    ano: int = typer.Option(2024, "--ano", "-a", help="Ano de exercício"),
    ibge: str = typer.Option("3550308", "--ibge", "-i", help="Código IBGE do Ente"),
):
    """Consulta API Siconfi do Tesouro Nacional para transferências constitucionais."""
    init_tables()
    endpoint = f"{SICONFI_BASE}/rreo"
    console.print(f"[cyan]Consultando dados do Siconfi para IBGE {ibge} ({ano})...[/cyan]")
    try:
        with GovHttpClient() as client:
            res = client.get_json(endpoint, params={"an_exercicio": ano, "id_ente": ibge, "nr_periodo": 1})
            itens = res.get("items", [])
            console.print(f"[green]Retornados {len(itens)} itens fiscais do Siconfi.[/green]")
    except Exception as e:
        console.print(f"[yellow]Aviso: Falha na conexão com API remota Siconfi ({e}). Registros locais prontos para consulta.[/yellow]")


if __name__ == "__main__":
    app()
