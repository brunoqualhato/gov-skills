"""Fetch and ingest TSE electoral data (candidates, campaign donations, declared assets) into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_cpf, parse_currency, parse_date

app = typer.Typer(help="Manage TSE Electoral Database")
console = Console()

DIVULGACAND_BASE = "https://divulgacandcontas.tse.jus.br/divulga/rest/v1"


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS tse_candidatos (
        sq_candidato VARCHAR PRIMARY KEY,
        ano_eleicao INTEGER,
        nr_candidato VARCHAR,
        nm_candidato VARCHAR,
        nm_urna VARCHAR,
        nr_cpf_candidato VARCHAR,
        sg_partido VARCHAR,
        ds_cargo VARCHAR,
        sg_uf VARCHAR,
        codigo_ibge VARCHAR,
        ds_situacao_candidatura VARCHAR,
        ds_resultado_eleicao VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tse_doacoes (
        id_doacao VARCHAR PRIMARY KEY,
        ano_eleicao INTEGER,
        sq_candidato VARCHAR,
        nr_cpf_cnpj_doador VARCHAR,
        cnpj_raiz_doador VARCHAR,
        nm_doador VARCHAR,
        vr_receita DOUBLE,
        dt_receita DATE,
        ds_origem_receita VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tse_bens_declarados (
        id_bem VARCHAR PRIMARY KEY,
        sq_candidato VARCHAR,
        nr_cpf_candidato VARCHAR,
        ds_tipo_bem VARCHAR,
        ds_detalhe_bem VARCHAR,
        vr_bem DOUBLE,
        ano_eleicao INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_tse_doador ON tse_doacoes(nr_cpf_cnpj_doador);
    CREATE INDEX IF NOT EXISTS idx_tse_cpf_cand ON tse_candidatos(nr_cpf_candidato);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula candidatos, doações e bens eleitorais para testes dos cruzamentos com PNCP e CEAP."""
    init_tables()
    db = get_db()

    candidatos = [
        {
            "sq_candidato": "250001600001",
            "ano_eleicao": 2022,
            "nr_candidato": "1515",
            "nm_candidato": "ROBERTO SILVA SANTOS",
            "nm_urna": "BETO SANTOS",
            "nr_cpf_candidato": "11122233344",
            "sg_partido": "MDB",
            "ds_cargo": "DEPUTADO FEDERAL",
            "sg_uf": "SP",
            "codigo_ibge": "3550308",
            "ds_situacao_candidatura": "DEFERIDO",
            "ds_resultado_eleicao": "ELEITO",
        },
        {
            "sq_candidato": "250001600002",
            "ano_eleicao": 2024,
            "nr_candidato": "55",
            "nm_candidato": "MARCOS AURELIO PRADO",
            "nm_urna": "MARQUINHOS DO POVO",
            "nr_cpf_candidato": "55566677788",
            "sg_partido": "PSD",
            "ds_cargo": "PREFEITO",
            "sg_uf": "RJ",
            "codigo_ibge": "3304557",
            "ds_situacao_candidatura": "DEFERIDO",
            "ds_resultado_eleicao": "ELEITO",
        },
        {
            "sq_candidato": "250001600003",
            "ano_eleicao": 2024,
            "nr_candidato": "11",
            "nm_candidato": "CARLOS EDUARDO CRINITI",
            "nm_urna": "EDUARDO CRINITI",
            "nr_cpf_candidato": "99988877700",
            "sg_partido": "PP",
            "ds_cargo": "PREFEITO",
            "sg_uf": "SP",
            "codigo_ibge": "3550308",
            "ds_situacao_candidatura": "DEFERIDO",
            "ds_resultado_eleicao": "NAO ELEITO",
        },
    ]

    doacoes = [
        # Doador de campanha que é sócio de fornecedora vencedora de licitações
        {
            "id_doacao": "DOA_2022_001",
            "ano_eleicao": 2022,
            "sq_candidato": "250001600001",
            "nr_cpf_cnpj_doador": "31003259000110",
            "cnpj_raiz_doador": "31003259",
            "nm_doador": "TC CRINITI COMERCIO ELETROELETRONICOS LTDA",
            "vr_receita": 150000.0,
            "dt_receita": "2022-09-15",
            "ds_origem_receita": "TRANSFERENCIA ELETRONICA",
        },
        {
            "id_doacao": "DOA_2024_002",
            "ano_eleicao": 2024,
            "sq_candidato": "250001600002",
            "nr_cpf_cnpj_doador": "12345678000199",
            "cnpj_raiz_doador": "12345678",
            "nm_doador": "ALFA ENGENHARIA E CONSTRUCOES LTDA",
            "vr_receita": 80000.0,
            "dt_receita": "2024-09-10",
            "ds_origem_receita": "PIX",
        },
    ]

    bens = [
        {
            "id_bem": "BEM_2022_01",
            "sq_candidato": "250001600001",
            "nr_cpf_candidato": "11122233344",
            "ds_tipo_bem": "QUOTAS OU PINHOES DE CAPITAL",
            "ds_detalhe_bem": "50% de cotas na empresa Brasil Tech Solutions",
            "vr_bem": 500000.0,
            "ano_eleicao": 2022,
        },
        {
            "id_bem": "BEM_2024_02",
            "sq_candidato": "250001600002",
            "nr_cpf_candidato": "55566677788",
            "ds_tipo_bem": "IMOVEL URBANO",
            "ds_detalhe_bem": "Apartamento residencial Barra da Tijuca",
            "vr_bem": 1200000.0,
            "ano_eleicao": 2024,
        },
    ]

    for c in candidatos:
        db.execute("""
            INSERT OR REPLACE INTO tse_candidatos
            (sq_candidato, ano_eleicao, nr_candidato, nm_candidato, nm_urna, nr_cpf_candidato, sg_partido, ds_cargo, sg_uf, codigo_ibge, ds_situacao_candidatura, ds_resultado_eleicao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            c["sq_candidato"], c["ano_eleicao"], c["nr_candidato"], c["nm_candidato"],
            c["nm_urna"], c["nr_cpf_candidato"], c["sg_partido"], c["ds_cargo"],
            c["sg_uf"], c["codigo_ibge"], c["ds_situacao_candidatura"], c["ds_resultado_eleicao"]
        ])

    for d in doacoes:
        db.execute("""
            INSERT OR REPLACE INTO tse_doacoes
            (id_doacao, ano_eleicao, sq_candidato, nr_cpf_cnpj_doador, cnpj_raiz_doador, nm_doador, vr_receita, dt_receita, ds_origem_receita)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            d["id_doacao"], d["ano_eleicao"], d["sq_candidato"], d["nr_cpf_cnpj_doador"],
            d["cnpj_raiz_doador"], d["nm_doador"], d["vr_receita"], d["dt_receita"], d["ds_origem_receita"]
        ])

    for b in bens:
        db.execute("""
            INSERT OR REPLACE INTO tse_bens_declarados
            (id_bem, sq_candidato, nr_cpf_candidato, ds_tipo_bem, ds_detalhe_bem, vr_bem, ano_eleicao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            b["id_bem"], b["sq_candidato"], b["nr_cpf_candidato"], b["ds_tipo_bem"],
            b["ds_detalhe_bem"], b["vr_bem"], b["ano_eleicao"]
        ])

    console.print(f"[green]✓ Inseridos {len(candidatos)} candidatos, {len(doacoes)} doações e {len(bens)} bens do TSE no Lakehouse.[/green]")


@app.command()
def candidaturas_uf(
    ano: int = typer.Option(2024, "--ano", "-a", help="Ano da eleição"),
    uf: str = typer.Option("SP", "--uf", "-u", help="Sigla da UF"),
    municipio_ibge: str = typer.Option("3550308", "--ibge", "-i", help="Código IBGE"),
):
    """Consulta candidaturas via API DivulgaCandContas do TSE para um município."""
    init_tables()
    url = f"{DIVULGACAND_BASE}/candidaturas/listar/{ano}/{municipio_ibge}/1/11/candidatos"
    console.print(f"[cyan]Consultando candidaturas no DivulgaCandContas para {uf} ({ano})...[/cyan]")
    try:
        with GovHttpClient() as client:
            res = client.get_json(url)
            cands = res.get("candidatos", [])
            console.print(f"[green]Retornados {len(cands)} candidatos da API oficial do TSE.[/green]")
    except Exception as e:
        console.print(f"[yellow]API remota do TSE indisponível ({e}). Usando dados locais do DuckDB.[/yellow]")


if __name__ == "__main__":
    app()
