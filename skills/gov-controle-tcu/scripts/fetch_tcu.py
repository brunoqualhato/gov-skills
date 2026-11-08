"""Fetch and ingest TCU irregular accounts and inidoneous companies into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_cpf, parse_date

app = typer.Typer(help="Manage TCU sanctions database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS tcu_contas_irregulares (
        id_registro VARCHAR PRIMARY KEY,
        cpf_cnpj VARCHAR,
        cnpj_raiz VARCHAR,
        nome_responsavel VARCHAR,
        cargo_funcao VARCHAR,
        orgao_origem VARCHAR,
        uf_orgao VARCHAR,
        numero_processo VARCHAR,
        numero_acordao VARCHAR,
        ano_acordao INTEGER,
        data_julgamento DATE,
        data_transito_julgado DATE,
        data_fim_inelegibilidade DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS tcu_empresas_inidoneas (
        id_inidoneidade VARCHAR PRIMARY KEY,
        cnpj_inidonio VARCHAR,
        cnpj_raiz VARCHAR,
        razao_social VARCHAR,
        numero_processo VARCHAR,
        numero_acordao VARCHAR,
        data_inicio_sancao DATE,
        data_fim_sancao DATE,
        motivo VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula sanções e contas irregulares do TCU para testes de integridade."""
    init_tables()
    db = get_db()

    # Empresas inidôneas declaradas pelo TCU
    inidoneas = [
        {
            "id": "TCU_INID_2024_01",
            "cnpj": "99887766000199",
            "razao": "SUPREMA FORNECIMENTOS LTDA",
            "proc": "TC 012.345/2022-8",
            "acordao": "1420/2023 - Plenário",
            "dt_ini": "2023-08-01",
            "dt_fim": "2028-08-01",
            "motivo": "Fraude comprovada à licitação mediante conluio e sobrepreço em merenda escolar",
        },
        {
            "id": "TCU_INID_2024_02",
            "cnpj": "10222333000144",
            "razao": "ALFA CONSTRUCOES E SERVICOS LTDA",
            "proc": "TC 008.910/2023-1",
            "acordao": "2210/2023 - Plenário",
            "dt_ini": "2023-10-15",
            "dt_fim": "2026-10-15",
            "motivo": "Apresentação de atestado de capacidade técnica ideologicamente falso",
        },
    ]

    records_inid = []
    for it in inidoneas:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(it["cnpj"])
        records_inid.append({
            "id_inidoneidade": it["id"],
            "cnpj_inidonio": cnpj_limpo,
            "cnpj_raiz": cnpj_raiz,
            "razao_social": it["razao"],
            "numero_processo": it["proc"],
            "numero_acordao": it["acordao"],
            "data_inicio_sancao": parse_date(it["dt_ini"]),
            "data_fim_sancao": parse_date(it["dt_fim"]),
            "motivo": it["motivo"],
        })

    df_inid = pl.DataFrame(records_inid)
    db.conn.register("tmp_tcu_inid", df_inid.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO tcu_empresas_inidoneas 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_tcu_inid
    """)

    # Gestores com contas irregulares julgadas pelo TCU
    irregulares = [
        {
            "id": "TCU_IRREG_2024_01",
            "cpf_cnpj": "***445566**",
            "nome": "MARCOS AURELIO MENDONCA",
            "cargo": "Ex-Secretário Municipal de Saúde",
            "orgao": "Prefeitura Municipal de Exemplo",
            "uf": "DF",
            "proc": "TC 033.444/2021-9",
            "acordao": "890/2023 - 2ª Câmara",
            "ano": 2023,
            "dt_julg": "2023-04-12",
            "dt_trans": "2023-09-01",
            "dt_fim_ineleg": "2031-09-01",
        }
    ]
    records_irreg = []
    for r in irregulares:
        records_irreg.append({
            "id_registro": r["id"],
            "cpf_cnpj": r["cpf_cnpj"],
            "cnpj_raiz": None,
            "nome_responsavel": r["nome"],
            "cargo_funcao": r["cargo"],
            "orgao_origem": r["orgao"],
            "uf_orgao": r["uf"],
            "numero_processo": r["proc"],
            "numero_acordao": r["acordao"],
            "ano_acordao": r["ano"],
            "data_julgamento": parse_date(r["dt_julg"]),
            "data_transito_julgado": parse_date(r["dt_trans"]),
            "data_fim_inelegibilidade": parse_date(r["dt_fim_ineleg"]),
        })

    df_irreg = pl.DataFrame(records_irreg)
    db.conn.register("tmp_tcu_irreg", df_irreg.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO tcu_contas_irregulares 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_tcu_irreg
    """)

    console.print("[bold green]✓ Base do TCU semeada com empresas inidôneas e contas julgadas irregulares![/bold green]")


if __name__ == "__main__":
    app()
