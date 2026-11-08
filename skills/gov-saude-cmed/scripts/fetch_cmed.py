"""Fetch and ingest CMED/Anvisa medicine price regulations into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import parse_currency, parse_date

app = typer.Typer(help="Manage CMED/Anvisa medicine price ceiling database")
console = Console()


def init_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS cmed_precos_medicamentos (
        codigo_ggrem VARCHAR PRIMARY KEY,
        registro_anvisa VARCHAR,
        substancia VARCHAR,
        laboratorio VARCHAR,
        apresentacao VARCHAR,
        classe_terapeutica VARCHAR,
        preco_fabricante_pf DOUBLE,
        preco_maximo_consumidor_pmc DOUBLE,
        percentual_cap DOUBLE,
        preco_teto_governo_cap DOUBLE,
        data_vigencia DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula medicamentos essenciais com teto regulatório CMED para auditoria de preços."""
    init_table()
    db = get_db()

    # Preços oficiais CMED para itens de alto volume no SUS
    remedios = [
        {
            "ggrem": "50231901001",
            "anvisa": "1004300100018",
            "substancia": "DIPIRONA SODICA",
            "lab": "EMS S/A",
            "apres": "500 MG/ML SOL INJ CX 100 AMP VD AMB X 2 ML",
            "classe": "ANALGESICOS",
            "pf": 85.50, # Cx com 100 ampolas = R$ 0,85/ampola
            "pmc": 118.20,
            "cap": 21.75,
            "teto_cap": 66.90, # R$ 0,66/ampola para o governo
            "dt": "2024-01-01",
        },
        {
            "ggrem": "50341802002",
            "anvisa": "1004700200029",
            "substancia": "PARACETAMOL",
            "lab": "ACHE LABORATORIOS FARMACEUTICOS S.A",
            "apres": "750 MG COM BL AL PLAS TRANS X 20",
            "classe": "ANALGESICOS E ANTITERMICOS",
            "pf": 8.20,
            "pmc": 11.35,
            "cap": 21.75,
            "teto_cap": 6.41,
            "dt": "2024-01-01",
        },
        {
            "ggrem": "50451703003",
            "anvisa": "1006800300030",
            "substancia": "AMOXICILINA",
            "lab": "EUROFARMA LABORATORIOS S.A.",
            "apres": "500 MG CAPS DURA BL AL PLAS INC X 21",
            "classe": "ANTIBACTERIANOS SISTEMICOS",
            "pf": 14.50,
            "pmc": 20.05,
            "cap": 21.75,
            "teto_cap": 11.34,
            "dt": "2024-01-01",
        },
        {
            "ggrem": "50561604004",
            "anvisa": "1018000400041",
            "substancia": "INSULINA HUMANA",
            "lab": "NOVO NORDISK FARMACEUTICA DO BRASIL LTDA",
            "apres": "100 UI/ML SUS INJ CT FA VD INC X 10 ML (NPH)",
            "classe": "INSULINAS E ANALOGOS",
            "pf": 42.00,
            "pmc": 58.10,
            "cap": 21.75,
            "teto_cap": 32.86,
            "dt": "2024-01-01",
        },
    ]

    records = []
    for r in remedios:
        records.append({
            "codigo_ggrem": r["ggrem"],
            "registro_anvisa": r["anvisa"],
            "substancia": r["substancia"],
            "laboratorio": r["lab"],
            "apresentacao": r["apres"],
            "classe_terapeutica": r["classe"],
            "preco_fabricante_pf": float(r["pf"]),
            "preco_maximo_consumidor_pmc": float(r["pmc"]),
            "percentual_cap": float(r["cap"]),
            "preco_teto_governo_cap": float(r["teto_cap"]),
            "data_vigencia": parse_date(r["dt"]),
        })

    df = pl.DataFrame(records)
    db.conn.register("tmp_cmed_seed", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO cmed_precos_medicamentos 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_cmed_seed
    """)
    console.print(f"[bold green]✓ Base da CMED/Anvisa populada com {len(records)} medicamentos de referência regulatória![/bold green]")


if __name__ == "__main__":
    app()
