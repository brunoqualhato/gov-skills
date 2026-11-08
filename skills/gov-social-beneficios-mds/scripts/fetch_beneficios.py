"""Fetch and ingest MDS & CGU social benefits (Bolsa Família, BPC) into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cpf, parse_currency

app = typer.Typer(help="Manage MDS Social Benefits Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS cgu_beneficios_cidadao (
        id_beneficio VARCHAR PRIMARY KEY,
        tipo_beneficio VARCHAR, -- BOLSA FAMILIA, BPC, AUXILIO GAS, SEGURO DEFESO
        cpf_beneficiario VARCHAR,
        nome_beneficiario VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        codigo_ibge VARCHAR,
        mes_competencia VARCHAR,
        valor_parcela DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_benef_cpf ON cgu_beneficios_cidadao(cpf_beneficiario);
    CREATE INDEX IF NOT EXISTS idx_benef_ibge ON cgu_beneficios_cidadao(codigo_ibge);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula beneficiários de programas sociais para testes do detector de laranjas."""
    init_tables()
    db = get_db()

    beneficiarios = [
        # Francisca Silva (sócia laranja da Suprema Fornecimentos)
        {
            "id": "BENEF_BF_2024_01",
            "tipo": "BOLSA FAMILIA",
            "cpf": "***.123.456-**",
            "nome": "FRANCISCA SILVA",
            "mun": "Maracanaú",
            "uf": "CE",
            "ibge": "2307650",
            "mes": "2024-01",
            "valor": 650.0,
        },
        # João Pereira dos Santos (BPC / idoso em situação de vulnerabilidade)
        {
            "id": "BENEF_BPC_2024_02",
            "tipo": "BPC - IDOSO",
            "cpf": "***.789.012-**",
            "nome": "JOAO PEREIRA DOS SANTOS",
            "mun": "São Paulo",
            "uf": "SP",
            "ibge": "3550308",
            "mes": "2024-01",
            "valor": 1412.0,
        },
    ]

    for b in beneficiarios:
        db.execute("""
            INSERT OR REPLACE INTO cgu_beneficios_cidadao
            (id_beneficio, tipo_beneficio, cpf_beneficiario, nome_beneficiario, municipio, uf, codigo_ibge, mes_competencia, valor_parcela)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            b["id"], b["tipo"], b["cpf"], b["nome"], b["mun"],
            b["uf"], b["ibge"], b["mes"], b["valor"]
        ])

    console.print(f"[green]✓ Inseridos {len(beneficiarios)} beneficiários de programas sociais no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe contagem de registros de benefícios sociais."""
    db = get_db()
    c = db.count("cgu_beneficios_cidadao")
    console.print(f"[cyan]Benefícios Sociais no Lakehouse:[/cyan] {c} parcelas de benefícios registradas.")


if __name__ == "__main__":
    app()
