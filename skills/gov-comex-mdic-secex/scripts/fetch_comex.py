"""Fetch and ingest MDIC SECEX Comex Stat foreign trade microdata into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_ibge, parse_currency

app = typer.Typer(help="Manage MDIC Comex Stat Foreign Trade Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS comex_balanca_comercial (
        id_operacao VARCHAR PRIMARY KEY,
        ano INTEGER,
        mes INTEGER,
        tipo_operacao VARCHAR, -- EXPORTACAO, IMPORTACAO
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        codigo_ncm VARCHAR,
        descricao_ncm VARCHAR,
        pais_parceiro VARCHAR,
        valor_fob_usd DOUBLE,
        peso_liquido_kg DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_comex_ibge ON comex_balanca_comercial(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_comex_ncm ON comex_balanca_comercial(codigo_ncm);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula operações representativas de exportação e importação municipal do Comex Stat."""
    init_tables()
    db = get_db()

    operacoes = [
        # Santos / SP (Petróleo e Soja)
        {
            "id": "COMEX_2024_01_EXP_01",
            "ano": 2024,
            "mes": 1,
            "tipo": "EXPORTACAO",
            "ibge": "3548500",
            "mun": "Santos",
            "uf": "SP",
            "ncm": "12019000",
            "desc": "Soja, mesmo triturada, exceto para semeadura",
            "pais": "China",
            "fob": 145000000.0,
            "peso": 280000000.0,
        },
        # Parauapebas / PA (Minério de Ferro)
        {
            "id": "COMEX_2024_01_EXP_02",
            "ano": 2024,
            "mes": 1,
            "tipo": "EXPORTACAO",
            "ibge": "1505536",
            "mun": "Parauapebas",
            "uf": "PA",
            "ncm": "26011100",
            "desc": "Minérios de ferro não aglomerados e seus concentrados",
            "pais": "China",
            "fob": 520000000.0,
            "peso": 6200000000.0,
        },
        # São Paulo / SP (Importação de Máquinas e Equipamentos)
        {
            "id": "COMEX_2024_01_IMP_03",
            "ano": 2024,
            "mes": 1,
            "tipo": "IMPORTACAO",
            "ibge": "3550308",
            "mun": "São Paulo",
            "uf": "SP",
            "ncm": "84713012",
            "desc": "Máquinas automáticas para processamento de dados portáteis",
            "pais": "China",
            "fob": 65000000.0,
            "peso": 450000.0,
        },
    ]

    for op in operacoes:
        db.execute("""
            INSERT OR REPLACE INTO comex_balanca_comercial
            (id_operacao, ano, mes, tipo_operacao, codigo_ibge, municipio, uf, codigo_ncm, descricao_ncm, pais_parceiro, valor_fob_usd, peso_liquido_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            op["id"], op["ano"], op["mes"], op["tipo"], op["ibge"],
            op["mun"], op["uf"], op["ncm"], op["desc"], op["pais"],
            op["fob"], op["peso"]
        ])

    console.print(f"[green]✓ Inseridas {len(operacoes)} operações de comércio exterior (Comex Stat) no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe contagem de operações registradas no Comex Stat."""
    db = get_db()
    c = db.count("comex_balanca_comercial")
    console.print(f"[cyan]Comércio Exterior no Lakehouse:[/cyan] {c} operações registradas.")


if __name__ == "__main__":
    app()
