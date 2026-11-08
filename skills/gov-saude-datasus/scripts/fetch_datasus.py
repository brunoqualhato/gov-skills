"""Fetch and ingest Ministry of Health (DataSUS / OpenDataSUS) CNES health facilities into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_ibge

app = typer.Typer(help="Manage DataSUS CNES Healthcare Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS datasus_estabelecimentos_cnes (
        codigo_cnes VARCHAR PRIMARY KEY,
        nome_fantasia VARCHAR,
        razao_social VARCHAR,
        cnpj_mantenedora VARCHAR,
        cnpj_raiz_mantenedora VARCHAR,
        tipo_unidade VARCHAR,
        natureza_organizacao VARCHAR,
        codigo_ibge VARCHAR,
        uf VARCHAR,
        municipio VARCHAR,
        possui_atendimento_urgencia BOOLEAN,
        possui_leitos_uti BOOLEAN,
        qtd_leitos_uti INTEGER,
        qtd_leitos_internacao INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_datasus_ibge ON datasus_estabelecimentos_cnes(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_datasus_cnpj ON datasus_estabelecimentos_cnes(cnpj_mantenedora);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula estabelecimentos de saúde, leitos e infraestrutura hospitalar SUS."""
    init_tables()
    db = get_db()

    estabelecimentos = [
        {
            "cnes": "2077485",
            "fantasia": "HOSPITAL DAS CLINICAS DA FMUSP",
            "razao": "HOSPITAL DAS CLINICAS DA FACULDADE DE MEDICINA DA USP",
            "cnpj": "60448040000122",
            "cnpj_raiz": "60448040",
            "tipo": "HOSPITAL GERAL",
            "natureza": "AUTARQUIA ESTADUAL",
            "ibge": "3550308",
            "uf": "SP",
            "municipio": "São Paulo",
            "urgencia": True,
            "tem_uti": True,
            "uti": 250,
            "internacao": 2100,
        },
        {
            "cnes": "2269783",
            "fantasia": "HOSPITAL MUNICIPAL SOUZA AGUIAR",
            "razao": "MUNICIPIO DO RIO DE JANEIRO",
            "cnpj": "42498733000152",
            "cnpj_raiz": "42498733",
            "tipo": "HOSPITAL GERAL",
            "natureza": "ORGAO PUBLICO DO PODER EXECUTIVO MUNICIPAL",
            "ibge": "3304557",
            "uf": "RJ",
            "municipio": "Rio de Janeiro",
            "urgencia": True,
            "tem_uti": True,
            "uti": 60,
            "internacao": 450,
        },
        {
            "cnes": "2499126",
            "fantasia": "HOSPITAL MUNICIPAL DE MARACANAU",
            "razao": "MUNICIPIO DE MARACANAU",
            "cnpj": "07986256000100",
            "cnpj_raiz": "07986256",
            "tipo": "HOSPITAL GERAL",
            "natureza": "ADMINISTRACAO PUBLICA MUNICIPAL",
            "ibge": "2307650",
            "uf": "CE",
            "municipio": "Maracanaú",
            "urgencia": True,
            "tem_uti": True,
            "uti": 15,
            "internacao": 120,
        },
    ]

    for e in estabelecimentos:
        db.execute("""
            INSERT OR REPLACE INTO datasus_estabelecimentos_cnes
            (codigo_cnes, nome_fantasia, razao_social, cnpj_mantenedora, cnpj_raiz_mantenedora, tipo_unidade, natureza_organizacao, codigo_ibge, uf, municipio, possui_atendimento_urgencia, possui_leitos_uti, qtd_leitos_uti, qtd_leitos_internacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            e["cnes"], e["fantasia"], e["razao"], e["cnpj"], e["cnpj_raiz"],
            e["tipo"], e["natureza"], e["ibge"], e["uf"], e["municipio"],
            e["urgencia"], e["tem_uti"], e["uti"], e["internacao"]
        ])

    console.print(f"[green]✓ Inseridos {len(estabelecimentos)} estabelecimentos de saúde CNES no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe estatísticas de leitos e unidades de saúde cadastradas."""
    db = get_db()
    c = db.count("datasus_estabelecimentos_cnes")
    console.print(f"[cyan]Estabelecimentos no CNES/DataSUS:[/cyan] {c} unidades cadastradas.")


if __name__ == "__main__":
    app()
