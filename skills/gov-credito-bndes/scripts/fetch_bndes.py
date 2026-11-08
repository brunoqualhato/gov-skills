"""Fetch and ingest BNDES direct and indirect financing operations into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, parse_currency, parse_date

app = typer.Typer(help="Manage BNDES Financing Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS bndes_operacoes_financiamento (
        numero_contrato VARCHAR PRIMARY KEY,
        data_contrato DATE,
        cnpj_cliente VARCHAR,
        cnpj_raiz_cliente VARCHAR,
        razao_social_cliente VARCHAR,
        forma_apoio VARCHAR, -- DIRETA, INDIRETA
        linha_financiamento VARCHAR,
        valor_contratado DOUBLE,
        valor_desembolsado DOUBLE,
        taxa_juros VARCHAR,
        setor_cnae VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_bndes_cnpj ON bndes_operacoes_financiamento(cnpj_cliente);
    CREATE INDEX IF NOT EXISTS idx_bndes_raiz ON bndes_operacoes_financiamento(cnpj_raiz_cliente);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula operações de crédito do BNDES para cruzamentos forenses e ESG."""
    init_tables()
    db = get_db()

    operacoes = [
        # Agropecuária Amazônia Verde (possui embargo e multa no IBAMA!)
        {
            "contrato": "BNDES_FIN_2023_00192",
            "dt": "2023-06-15",
            "cnpj": "08234567000122",
            "razao": "AGROPECUARIA AMAZONIA VERDE LTDA",
            "apoio": "INDIRETA",
            "linha": "BNDES CREDITO RURAL",
            "contratado": 5000000.0,
            "desembolsado": 5000000.0,
            "juros": "TLP + 2.5% a.a.",
            "cnae": "AGRICULTURA E PECUARIA",
            "mun": "Anapu",
            "uf": "PA",
        },
        # Alfa Engenharia (vencedora de contratos no PNCP)
        {
            "contrato": "BNDES_FIN_2023_00881",
            "dt": "2023-09-20",
            "cnpj": "12345678000199",
            "razao": "ALFA ENGENHARIA E CONSTRUCOES LTDA",
            "apoio": "DIRETA",
            "linha": "BNDES FINEM INFRAESTRUTURA",
            "contratado": 25000000.0,
            "desembolsado": 18000000.0,
            "juros": "TLP + 1.8% a.a.",
            "cnae": "CONSTRUCAO PESADA",
            "mun": "São Paulo",
            "uf": "SP",
        },
    ]

    for op in operacoes:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(op["cnpj"])
        db.execute("""
            INSERT OR REPLACE INTO bndes_operacoes_financiamento
            (numero_contrato, data_contrato, cnpj_cliente, cnpj_raiz_cliente, razao_social_cliente, forma_apoio, linha_financiamento, valor_contratado, valor_desembolsado, taxa_juros, setor_cnae, municipio, uf)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            op["contrato"], op["dt"], cnpj_limpo, cnpj_raiz, op["razao"],
            op["apoio"], op["linha"], op["contratado"], op["desembolsado"],
            op["juros"], op["cnae"], op["mun"], op["uf"]
        ])

    console.print(f"[green]✓ Inseridas {len(operacoes)} operações de financiamento do BNDES no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe contagem de operações do BNDES cadastradas."""
    db = get_db()
    c = db.count("bndes_operacoes_financiamento")
    console.print(f"[cyan]BNDES no Lakehouse:[/cyan] {c} operações de crédito cadastradas.")


if __name__ == "__main__":
    app()
