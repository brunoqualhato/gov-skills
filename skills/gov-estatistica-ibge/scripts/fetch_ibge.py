"""Fetch Brazilian municipalities hierarchy from IBGE and store in DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db

app = typer.Typer(help="Fetch IBGE municipalities and regional hierarchies")
console = Console()

IBGE_MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def init_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS ibge_municipios (
        codigo_ibge VARCHAR PRIMARY KEY,
        nome_municipio VARCHAR,
        uf_sigla VARCHAR,
        uf_nome VARCHAR,
        uf_codigo VARCHAR,
        regiao_nome VARCHAR,
        microrregiao_nome VARCHAR,
        mesorregiao_nome VARCHAR,
        regiao_imediata VARCHAR,
        regiao_intermediaria VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def municipios():
    """Baixa todos os municípios brasileiros com hierarquia territorial completa."""
    init_table()
    db = get_db()

    console.print("[bold cyan]🔍 Baixando malha oficial de municípios do IBGE...[/bold cyan]")
    with GovHttpClient() as client:
        try:
            data = client.get_json(IBGE_MUNICIPIOS_URL)
        except Exception as e:
            console.print(f"[red]Erro ao consultar API do IBGE: {e}[/red]")
            return

    if not data or not isinstance(data, list):
        console.print("[yellow]Nenhum dado retornado da API do IBGE.[/yellow]")
        return

    records = []
    for m in data:
        cod = str(m.get("id"))
        nome = m.get("nome", "")
        
        micro = m.get("microrregiao") or {}
        meso = micro.get("mesorregiao") or {}
        uf = meso.get("UF") or {}
        regiao = uf.get("regiao") or {}

        reg_imediata = m.get("regiao-imediata") or {}
        reg_inter = reg_imediata.get("regiao-intermediaria") or {}

        records.append({
            "codigo_ibge": cod,
            "nome_municipio": nome,
            "uf_sigla": uf.get("sigla", ""),
            "uf_nome": uf.get("nome", ""),
            "uf_codigo": str(uf.get("id", "")),
            "regiao_nome": regiao.get("nome", ""),
            "microrregiao_nome": micro.get("nome", ""),
            "mesorregiao_nome": meso.get("nome", ""),
            "regiao_imediata": reg_imediata.get("nome", ""),
            "regiao_intermediaria": reg_inter.get("nome", ""),
        })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_ibge_mun", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO ibge_municipios 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_ibge_mun
        """)
        total = db.count("ibge_municipios")
        console.print(f"[bold green]✓ Sucesso! {len(records)} municípios ingeridos no DuckDB. Total na base: {total}[/bold green]")


if __name__ == "__main__":
    app()
