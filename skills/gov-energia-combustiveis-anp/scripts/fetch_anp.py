"""Fetch and ingest ANP weekly fuel price surveys into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_ibge, parse_currency, parse_date

app = typer.Typer(help="Manage ANP Fuel Prices Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS anp_precos_combustiveis (
        id_coleta VARCHAR PRIMARY KEY,
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        produto VARCHAR, -- GASOLINA, ETANOL, DIESEL S10, GNV
        data_coleta DATE,
        valor_venda DOUBLE,
        valor_compra DOUBLE,
        unidade_medida VARCHAR,
        bandeira VARCHAR,
        cnpj_revenda VARCHAR,
        cnpj_raiz_revenda VARCHAR,
        nome_posto VARCHAR,
        endereco VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_anp_ibge_prod ON anp_precos_combustiveis(codigo_ibge, produto);
    CREATE INDEX IF NOT EXISTS idx_anp_cnpj ON anp_precos_combustiveis(cnpj_revenda);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula histórico representativo de preços médios de combustíveis da ANP."""
    init_tables()
    db = get_db()

    coletas = [
        # São Paulo (3550308)
        {"id": "ANP_2024_SP_GAS_01", "ibge": "3550308", "mun": "São Paulo", "uf": "SP", "prod": "GASOLINA", "dt": "2024-03-10", "venda": 5.69, "compra": 4.80, "unid": "R$/litro", "band": "IPIRANGA", "cnpj": "01234567000101", "nome": "AUTO POSTO PAULISTA LTDA", "end": "AV PAULISTA 1000"},
        {"id": "ANP_2024_SP_ETANOL_01", "ibge": "3550308", "mun": "São Paulo", "uf": "SP", "prod": "ETANOL", "dt": "2024-03-10", "venda": 3.59, "compra": 2.95, "unid": "R$/litro", "band": "VIBRA", "cnpj": "01234567000101", "nome": "AUTO POSTO PAULISTA LTDA", "end": "AV PAULISTA 1000"},
        {"id": "ANP_2024_SP_DIESEL_01", "ibge": "3550308", "mun": "São Paulo", "uf": "SP", "prod": "DIESEL S10", "dt": "2024-03-10", "venda": 5.92, "compra": 5.15, "unid": "R$/litro", "band": "RAIZEN", "cnpj": "02345678000102", "nome": "POSTO BANDEIRANTES LTDA", "end": "AV BANDEIRANTES 500"},
        # Rio de Janeiro (3304557)
        {"id": "ANP_2024_RJ_GAS_01", "ibge": "3304557", "mun": "Rio de Janeiro", "uf": "RJ", "prod": "GASOLINA", "dt": "2024-03-10", "venda": 5.84, "compra": 4.90, "unid": "R$/litro", "band": "VIBRA", "cnpj": "03456789000103", "nome": "POSTO COPACABANA LTDA", "end": "AV ATLANTICA 200"},
        {"id": "ANP_2024_RJ_DIESEL_01", "ibge": "3304557", "mun": "Rio de Janeiro", "uf": "RJ", "prod": "DIESEL S10", "dt": "2024-03-10", "venda": 6.05, "compra": 5.25, "unid": "R$/litro", "band": "IPIRANGA", "cnpj": "03456789000103", "nome": "POSTO COPACABANA LTDA", "end": "AV ATLANTICA 200"},
        # Maracanaú (2307650)
        {"id": "ANP_2024_CE_GAS_01", "ibge": "2307650", "mun": "Maracanaú", "uf": "CE", "prod": "GASOLINA", "dt": "2024-03-10", "venda": 5.99, "compra": 5.10, "unid": "R$/litro", "band": "BRANCA", "cnpj": "04567890000104", "nome": "POSTO DO CEARA LTDA", "end": "ROD CE 060 KM 12"},
        {"id": "ANP_2024_CE_DIESEL_01", "ibge": "2307650", "mun": "Maracanaú", "uf": "CE", "prod": "DIESEL S10", "dt": "2024-03-10", "venda": 6.15, "compra": 5.30, "unid": "R$/litro", "band": "BRANCA", "cnpj": "04567890000104", "nome": "POSTO DO CEARA LTDA", "end": "ROD CE 060 KM 12"},
    ]

    for c in coletas:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(c["cnpj"])
        db.execute("""
            INSERT OR REPLACE INTO anp_precos_combustiveis
            (id_coleta, codigo_ibge, municipio, uf, produto, data_coleta, valor_venda, valor_compra, unidade_medida, bandeira, cnpj_revenda, cnpj_raiz_revenda, nome_posto, endereco)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            c["id"], c["ibge"], c["mun"], c["uf"], c["prod"], c["dt"],
            c["venda"], c["compra"], c["unid"], c["band"], cnpj_limpo,
            cnpj_raiz, c["nome"], c["end"]
        ])

    console.print(f"[green]✓ Inseridos {len(coletas)} registros de preços de combustíveis da ANP no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe estatísticas de preços coletados pela ANP."""
    db = get_db()
    c = db.count("anp_precos_combustiveis")
    console.print(f"[cyan]ANP no Lakehouse:[/cyan] {c} coletas de preços armazenadas.")


if __name__ == "__main__":
    app()
