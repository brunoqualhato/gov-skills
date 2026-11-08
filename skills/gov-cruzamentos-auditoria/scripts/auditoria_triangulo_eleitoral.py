"""Forensic tracer of the Electoral Triangle: Campaign Donor (TSE) -> Parliamentary Expense (CEAP) -> Public Procurement (PNCP)."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, parse_date

app = typer.Typer(help="Trace the Electoral Triangle: campaign donor/supplier -> CEAP cabinet expenses -> PNCP contracts")
console = Console()


def init_tse_tables():
    db = get_db()
    db.execute("""
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
    """)


@app.command()
def semear_dados():
    """Popula doações de campanha eleitoral correlacionadas a fornecedores da cota e do PNCP."""
    init_tse_tables()
    db = get_db()

    # Doador de campanha que é sócio da PANTANAL VEÍCULOS LTDA (grande fornecedora da CEAP e do governo)
    doacoes = [
        {
            "id": "TSE_DOA_2022_01",
            "ano": 2022,
            "sq_cand": "CAND_DF_001",
            "cpf_cnpj": "07319323000191",
            "nome": "PANTANAL VEICULOS LTDA",
            "valor": 150000.0,
            "dt": "2022-09-10",
            "origem": "Doação Eleitoral Declarada",
        }
    ]
    records = []
    for d in doacoes:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(d["cpf_cnpj"])
        records.append({
            "id_doacao": d["id"],
            "ano_eleicao": d["ano"],
            "sq_candidato": d["sq_cand"],
            "nr_cpf_cnpj_doador": cnpj_limpo,
            "cnpj_raiz_doador": cnpj_raiz,
            "nm_doador": d["nome"],
            "vr_receita": d["valor"],
            "dt_receita": parse_date(d["dt"]),
            "ds_origem_receita": d["origem"],
        })
    df = pl.DataFrame(records)
    db.conn.register("tmp_tse_seed", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO tse_doacoes 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_tse_seed
    """)
    console.print("[bold green]✓ Doações eleitorais para triangulação semeadas com sucesso![/bold green]")


@app.command()
def scan():
    """Identifica empresas que doaram para campanhas, receberam verbas da cota (CEAP) e ganharam contratos (PNCP)."""
    init_tse_tables()
    db = get_db()
    console.print(Panel("[bold red]🚨 RASTREAMENTO DO 'TRIÂNGULO ELEITORAL': DOAÇÃO DE CAMPANHA -> COTA PARLAMENTAR -> LICITAÇÕES[/bold red]", border_style="red"))

    rows = db.query("""
        SELECT 
            d.nm_doador AS empresa_doadora,
            d.nr_cpf_cnpj_doador AS cnpj,
            printf('R$ %,.2f', d.vr_receita) AS valor_doado_campanha,
            printf('R$ %,.2f', c.total_ceap) AS valor_recebido_cota_deputados,
            c.total_notas_ceap,
            COALESCE(printf('R$ %,.2f', p.total_pncp), 'R$ 0,00') AS total_contratos_governo
        FROM tse_doacoes d
        JOIN (
            SELECT cnpj_raiz_fornecedor, SUM(valor_liquido) AS total_ceap, COUNT(*) AS total_notas_ceap
            FROM camara_ceap_despesas
            GROUP BY cnpj_raiz_fornecedor
        ) c ON d.cnpj_raiz_doador = c.cnpj_raiz_fornecedor
        LEFT JOIN (
            SELECT cnpj_raiz_fornecedor, SUM(valor_global) AS total_pncp
            FROM pncp_contratos
            GROUP BY cnpj_raiz_fornecedor
        ) p ON d.cnpj_raiz_doador = p.cnpj_raiz_fornecedor
        ORDER BY c.total_ceap DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA DE CONEXÃO: Empresa Doadora de Campanha Faturando na Cota Parlamentar e em Contratos Públicos", border_style="bold red")
        t.add_column("Empresa / Fornecedor", style="bold yellow")
        t.add_column("CNPJ", style="dim")
        t.add_column("Doação de Campanha (TSE)", style="cyan", justify="right")
        t.add_column("Recebido da Câmara (CEAP)", style="bold red", justify="right")
        t.add_column("Notas CEAP", style="magenta", justify="center")
        t.add_column("Contratos Federais (PNCP)", style="green", justify="right")
        for r in rows:
            t.add_row(r[0][:30], r[1], r[2], r[3], str(r[4]), r[5])
        console.print(t)
        console.print(Panel(
            "[bold yellow]INDÍCIO DE RETORNO ELEITORAL:[/bold yellow] Empresas financiadoras de campanhas eleitorais que se tornam fornecedoras assíduas dos gabinetes dos próprios deputados ou vencedoras de licitações no poder público representam o clássico ciclo do [bold red]'retorno de investimento eleitoral'[/bold red].",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhuma triangulação direta identificada na amostra.[/green]")


if __name__ == "__main__":
    app()
