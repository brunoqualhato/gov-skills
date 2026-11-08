"""Fetch and ingest Ministry of Labor (MTE / Novo CAGED) employment data into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_ibge, parse_currency

app = typer.Typer(help="Manage MTE Novo CAGED Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS mte_caged_saldos_municipais (
        id_registro VARCHAR PRIMARY KEY,
        ano INTEGER,
        mes INTEGER,
        codigo_ibge VARCHAR,
        uf VARCHAR,
        setor_economico VARCHAR, -- Servicos, Comercio, Industria, Construcao, Agro
        total_admissoes INTEGER,
        total_desligamentos INTEGER,
        saldo_liquido INTEGER,
        salario_medio_admissao DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS mte_caged_empresas_quadro (
        cnpj VARCHAR PRIMARY KEY,
        cnpj_raiz VARCHAR,
        total_empregados_ativos INTEGER,
        admissoes_ultimos_12m INTEGER,
        desligamentos_ultimos_12m INTEGER,
        ano_mes_referencia VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_caged_ibge ON mte_caged_saldos_municipais(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_caged_ano_mes ON mte_caged_saldos_municipais(ano, mes);
    CREATE INDEX IF NOT EXISTS idx_caged_emp_cnpj ON mte_caged_empresas_quadro(cnpj_raiz);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula estatísticas do CAGED municipal e quadro de empregados por empresa."""
    init_tables()
    db = get_db()

    saldos = [
        {"id": "CAGED_2024_01_SP_SERV", "ano": 2024, "mes": 1, "ibge": "3550308", "uf": "SP", "setor": "SERVICOS", "adm": 85000, "des": 72000, "saldo": 13000, "sal": 3450.0},
        {"id": "CAGED_2024_01_SP_IND", "ano": 2024, "mes": 1, "ibge": "3550308", "uf": "SP", "setor": "INDUSTRIA", "adm": 24000, "des": 21500, "saldo": 2500, "sal": 3100.0},
        {"id": "CAGED_2024_01_RJ_SERV", "ano": 2024, "mes": 1, "ibge": "3304557", "uf": "RJ", "setor": "SERVICOS", "adm": 42000, "des": 39000, "saldo": 3000, "sal": 3200.0},
        {"id": "CAGED_2024_01_CE_IND", "ano": 2024, "mes": 1, "ibge": "2307650", "uf": "CE", "setor": "INDUSTRIA", "adm": 3500, "des": 2100, "saldo": 1400, "sal": 2100.0},
    ]

    empresas = [
        {"cnpj": "31003259000110", "cnpj_raiz": "31003259", "ativos": 1, "adm": 0, "des": 2, "ref": "2024-01"},
        {"cnpj": "12345678000199", "cnpj_raiz": "12345678", "ativos": 150, "adm": 12, "des": 8, "ref": "2024-01"},
        {"cnpj": "08234567000122", "cnpj_raiz": "08234567", "ativos": 42, "adm": 5, "des": 3, "ref": "2024-01"},
        {"cnpj": "99887766000199", "cnpj_raiz": "99887766", "ativos": 0, "adm": 0, "des": 0, "ref": "2024-01"},
    ]

    for s in saldos:
        db.execute("""
            INSERT OR REPLACE INTO mte_caged_saldos_municipais
            (id_registro, ano, mes, codigo_ibge, uf, setor_economico, total_admissoes, total_desligamentos, saldo_liquido, salario_medio_admissao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            s["id"], s["ano"], s["mes"], s["ibge"], s["uf"], s["setor"],
            s["adm"], s["des"], s["saldo"], s["sal"]
        ])

    for e in empresas:
        db.execute("""
            INSERT OR REPLACE INTO mte_caged_empresas_quadro
            (cnpj, cnpj_raiz, total_empregados_ativos, admissoes_ultimos_12m, desligamentos_ultimos_12m, ano_mes_referencia)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            e["cnpj"], e["cnpj_raiz"], e["ativos"], e["adm"], e["des"], e["ref"]
        ])

    console.print(f"[green]✓ Inseridos {len(saldos)} saldos do CAGED e {len(empresas)} registros de quadro funcional de empresas no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe informações sobre os dados do MTE no Lakehouse."""
    db = get_db()
    c1 = db.count("mte_caged_saldos_municipais")
    c2 = db.count("mte_caged_empresas_quadro")
    console.print(f"[cyan]Registros no CAGED:[/cyan] {c1} saldos municipais, {c2} empresas cadastradas.")


if __name__ == "__main__":
    app()
