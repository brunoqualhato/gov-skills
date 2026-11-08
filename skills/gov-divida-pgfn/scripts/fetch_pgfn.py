"""Fetch and ingest PGFN active debt records into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, parse_currency, parse_date

app = typer.Typer(help="Manage PGFN active debt database")
console = Console()


def init_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS pgfn_divida_ativa (
        numero_inscricao VARCHAR PRIMARY KEY,
        cnpj_cpf_devedor VARCHAR,
        cnpj_raiz VARCHAR,
        nome_devedor VARCHAR,
        tipo_devedor VARCHAR,
        tipo_divida VARCHAR,
        situacao_inscricao VARCHAR,
        valor_consolidado DOUBLE,
        uf VARCHAR,
        orgao_origem VARCHAR,
        data_inscricao DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula débitos em dívida ativa com casos reais para cruzamento com licitantes."""
    init_table()
    db = get_db()

    debitos = [
        # Dívida ativa de fornecedor que ganhou no PNCP (TC Criniti ou similar para teste de auditoria)
        {
            "num": "PGFN_2024_0019283",
            "cnpj": "31003259000110",
            "nome": "TC CRINITI COMERCIO ELETROELETRONICOS LTDA",
            "tipo_dev": "PRINCIPAL",
            "tipo_div": "TRIBUTARIA",
            "sit": "EM COBRANCA",
            "valor": 384500.20,
            "uf": "SP",
            "orgao": "RECEITA FEDERAL",
            "dt": "2023-11-14",
        },
        {
            "num": "PGFN_2024_0099412",
            "cnpj": "02012862000160",
            "nome": "TAM LINHAS AEREAS S/A.",
            "tipo_dev": "PRINCIPAL",
            "tipo_div": "PREVIDENCIARIA",
            "sit": "PARCELADA",
            "valor": 12500000.00,
            "uf": "SP",
            "orgao": "PROCURADORIA DA FAZENDA NACIONAL",
            "dt": "2022-05-10",
        },
        {
            "num": "PGFN_2024_0078123",
            "cnpj": "99887766000199",
            "nome": "SUPREMA FORNECIMENTOS LTDA",
            "tipo_dev": "PRINCIPAL",
            "tipo_div": "FGTS",
            "sit": "AJUIZADA",
            "valor": 950000.00,
            "uf": "MA",
            "orgao": "CAIXA ECONOMICA FEDERAL",
            "dt": "2023-01-20",
        },
    ]

    records = []
    for d in debitos:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(d["cnpj"])
        records.append({
            "numero_inscricao": d["num"],
            "cnpj_cpf_devedor": cnpj_limpo,
            "cnpj_raiz": cnpj_raiz,
            "nome_devedor": d["nome"],
            "tipo_devedor": d["tipo_dev"],
            "tipo_divida": d["tipo_div"],
            "situacao_inscricao": d["sit"],
            "valor_consolidado": float(d["valor"]),
            "uf": d["uf"],
            "orgao_origem": d["orgao"],
            "data_inscricao": parse_date(d["dt"]),
        })

    df = pl.DataFrame(records)
    db.conn.register("tmp_pgfn_demo", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO pgfn_divida_ativa 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_pgfn_demo
    """)
    console.print(f"[bold green]✓ Base PGFN populada com {len(records)} débitos fiscais de demonstração![/bold green]")


@app.command()
def importar_csv(
    arquivo: Path = typer.Option(..., "--arquivo", "-f", help="Caminho do CSV de devedores baixado da PGFN"),
):
    """Importa arquivo CSV oficial baixado do portal de dados abertos da PGFN."""
    if not arquivo.exists():
        console.print(f"[red]Arquivo não encontrado: {arquivo}[/red]")
        return

    init_table()
    db = get_db()
    console.print(f"[cyan]Lendo CSV da PGFN: {arquivo.name}...[/cyan]")
    
    # Processamento em lotes com Polars
    df_raw = pl.read_csv(str(arquivo), separator=";", ignore_errors=True)
    records = []
    for row in df_raw.iter_rows(named=True):
        cnpj_cpf = str(row.get("CPF_CNPJ") or row.get("CNPJ_CPF") or "")
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj_cpf)
        
        num_inscricao = str(row.get("NUMERO_INSCRICAO") or len(records))
        records.append({
            "numero_inscricao": num_inscricao,
            "cnpj_cpf_devedor": cnpj_limpo or cnpj_cpf,
            "cnpj_raiz": cnpj_raiz,
            "nome_devedor": str(row.get("NOME_DEVEDOR") or ""),
            "tipo_devedor": str(row.get("TIPO_DEVEDOR") or "PRINCIPAL"),
            "tipo_divida": str(row.get("TIPO_DIVIDA") or "TRIBUTARIA"),
            "situacao_inscricao": str(row.get("SITUACAO_INSCRICAO") or "EM COBRANCA"),
            "valor_consolidado": parse_currency(row.get("VALOR_CONSOLIDADO")),
            "uf": str(row.get("UF") or ""),
            "orgao_origem": str(row.get("ORGAO_ORIGEM") or "PGFN"),
            "data_inscricao": parse_date(str(row.get("DATA_INSCRICAO") or "")),
        })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_pgfn_csv", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO pgfn_divida_ativa 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_pgfn_csv
        """)
        total = db.count("pgfn_divida_ativa")
        console.print(f"[bold green]✓ {len(records)} débitos importados no DuckDB. Total na tabela: {total}[/bold green]")


if __name__ == "__main__":
    app()
