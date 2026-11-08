"""Fetch and ingest Federal Senate (Senado Federal) senators and CEAPS expenditures into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_cpf, parse_currency, parse_date

app = typer.Typer(help="Manage Senado Federal Database")
console = Console()

SENADO_API_BASE = "https://legis.senado.leg.br/dadosabertos"


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS senado_senadores (
        codigo_parlamentar INTEGER PRIMARY KEY,
        nome_parlamentar VARCHAR,
        nome_completo VARCHAR,
        sigla_partido VARCHAR,
        sigla_uf VARCHAR,
        email VARCHAR,
        url_foto VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS senado_ceaps_despesas (
        id_despesa VARCHAR PRIMARY KEY,
        codigo_parlamentar INTEGER,
        ano INTEGER,
        mes INTEGER,
        tipo_despesa VARCHAR,
        data_despesa DATE,
        valor_reembolsado DOUBLE,
        fornecedor_nome VARCHAR,
        cnpj_cpf_fornecedor VARCHAR,
        cnpj_raiz_fornecedor VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_senado_fornecedor ON senado_ceaps_despesas(cnpj_cpf_fornecedor);
    CREATE INDEX IF NOT EXISTS idx_senado_parlamentar ON senado_ceaps_despesas(codigo_parlamentar);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula senadores e despesas da verba CEAPS para cruzamentos com empresas."""
    init_tables()
    db = get_db()

    senadores = [
        {"cod": 5012, "nome": "Rodrigo Pacheco", "comp": "Rodrigo Otavio Soares Pacheco", "part": "PSD", "uf": "MG", "email": "rodrigo.pacheco@senado.leg.br"},
        {"cod": 5953, "nome": "Randolfe Rodrigues", "comp": "Randolph Frederich Rodrigues Alves", "part": "PT", "uf": "AP", "email": "randolfe.rodrigues@senado.leg.br"},
        {"cod": 4981, "nome": "Ciro Nogueira", "comp": "Ciro Nogueira Lima Filho", "part": "PP", "uf": "PI", "email": "ciro.nogueira@senado.leg.br"},
    ]

    despesas = [
        {
            "id": "CEAPS_2024_001",
            "cod": 5012,
            "ano": 2024,
            "mes": 2,
            "tipo": "Locação de imóveis para escritório político",
            "dt": "2024-02-10",
            "vr": 12500.0,
            "forn": "IMOBILIARIA CENTRAL DE MINAS LTDA",
            "doc": "05432100000188",
            "raiz": "05432100",
        },
        {
            "id": "CEAPS_2024_002",
            "cod": 4981,
            "ano": 2024,
            "mes": 3,
            "tipo": "Passagens aéreas, aquáticas e terrestres",
            "dt": "2024-03-05",
            "vr": 18200.0,
            "forn": "TAM LINHAS AEREAS S/A",
            "doc": "02012862000160",
            "raiz": "02012862",
        },
    ]

    for s in senadores:
        db.execute("""
            INSERT OR REPLACE INTO senado_senadores
            (codigo_parlamentar, nome_parlamentar, nome_completo, sigla_partido, sigla_uf, email, url_foto)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [s["cod"], s["nome"], s["comp"], s["part"], s["uf"], s["email"], ""])

    for d in despesas:
        db.execute("""
            INSERT OR REPLACE INTO senado_ceaps_despesas
            (id_despesa, codigo_parlamentar, ano, mes, tipo_despesa, data_despesa, valor_reembolsado, fornecedor_nome, cnpj_cpf_fornecedor, cnpj_raiz_fornecedor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            d["id"], d["cod"], d["ano"], d["mes"], d["tipo"], d["dt"],
            d["vr"], d["forn"], d["doc"], d["raiz"]
        ])

    console.print(f"[green]✓ Inseridos {len(senadores)} senadores e {len(despesas)} despesas da CEAPS no Lakehouse.[/green]")


@app.command()
def senadores_api():
    """Consulta senadores em exercício na API oficial do Senado."""
    init_tables()
    url = f"{SENADO_API_BASE}/senador/lista/atual.json"
    console.print("[cyan]Consultando senadores em exercício via API do Senado...[/cyan]")
    try:
        with GovHttpClient() as client:
            res = client.get_json(url)
            parlamentares = res.get("ListaParlamentarEmExercicio", {}).get("Parlamentares", {}).get("Parlamentar", [])
            console.print(f"[green]Retornados {len(parlamentares)} parlamentares do Senado.[/green]")
    except Exception as e:
        console.print(f"[yellow]API remota do Senado indisponível ({e}). Base local ativa.[/yellow]")


if __name__ == "__main__":
    app()
