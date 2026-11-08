"""Fetch and ingest Transferegov federal convênios and Obrasgov public works into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_ibge, parse_currency, parse_date

app = typer.Typer(help="Manage Transferegov & Obrasgov Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS transferegov_convenios (
        numero_convenio VARCHAR PRIMARY KEY,
        ano_convenio INTEGER,
        orgao_concedente VARCHAR,
        codigo_ibge_proponente VARCHAR,
        municipio_proponente VARCHAR,
        uf_proponente VARCHAR,
        objeto VARCHAR,
        situacao_convenio VARCHAR,
        valor_global DOUBLE,
        valor_repasse DOUBLE,
        valor_contrapartida DOUBLE,
        valor_pago DOUBLE,
        data_inicio DATE,
        data_fim DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS obrasgov_obras_publicas (
        id_obra VARCHAR PRIMARY KEY,
        numero_convenio VARCHAR,
        nome_obra VARCHAR,
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        situacao_obra VARCHAR, -- PARALISADA, EM EXECUCAO, CONCLUIDA, ATRASADA
        motivo_paralisacao VARCHAR,
        cnpj_executor VARCHAR,
        cnpj_raiz_executor VARCHAR,
        razao_social_executor VARCHAR,
        valor_investimento DOUBLE,
        percentual_execucao DOUBLE,
        data_inicio DATE,
        data_prevista_conclusao DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_obras_cnpj ON obrasgov_obras_publicas(cnpj_executor);
    CREATE INDEX IF NOT EXISTS idx_obras_ibge ON obrasgov_obras_publicas(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_obras_situacao ON obrasgov_obras_publicas(situacao_obra);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula convênios e obras públicas federais para monitoramento de paralisações."""
    init_tables()
    db = get_db()

    convenios = [
        {
            "num": "CONV_890123_2022",
            "ano": 2022,
            "orgao": "Ministério da Educação / FNDE",
            "ibge": "2307650",
            "mun": "Maracanaú",
            "uf": "CE",
            "obj": "Construção de Creche Municipal Proinfância Tipo 1",
            "sit": "EM EXECUCAO",
            "global": 3500000.0,
            "repasse": 3200000.0,
            "contra": 300000.0,
            "pago": 1800000.0,
            "dt_ini": "2022-06-01",
            "dt_fim": "2024-12-31",
        },
        {
            "num": "CONV_912345_2023",
            "ano": 2023,
            "orgao": "Ministério das Cidades",
            "ibge": "3550308",
            "mun": "São Paulo",
            "uf": "SP",
            "obj": "Pavimentação asfáltica e drenagem de águas pluviais",
            "sit": "CONCLUIDO",
            "global": 12000000.0,
            "repasse": 10000000.0,
            "contra": 2000000.0,
            "pago": 10000000.0,
            "dt_ini": "2023-01-15",
            "dt_fim": "2023-11-30",
        },
    ]

    obras = [
        {
            "id": "OBRA_CRECHE_2307650_01",
            "conv": "CONV_890123_2022",
            "nome": "Creche Proinfância Bairro Novo Maracanaú",
            "ibge": "2307650",
            "mun": "Maracanaú",
            "uf": "CE",
            "sit": "PARALISADA",
            "motivo": "Abandono injustificado pela empresa contratada após recebimento de medição",
            "cnpj": "99887766000199", # Mesma do TCU/CAGED zero func!
            "razao": "SUPREMA FORNECIMENTOS LTDA",
            "invest": 3500000.0,
            "exec": 35.5,
            "dt_ini": "2022-07-01",
            "dt_fim": "2023-12-31",
        },
        {
            "id": "OBRA_PAV_3550308_02",
            "conv": "CONV_912345_2023",
            "nome": "Recapeamento Asfáltico Zona Leste",
            "ibge": "3550308",
            "mun": "São Paulo",
            "uf": "SP",
            "sit": "CONCLUIDA",
            "motivo": "",
            "cnpj": "12345678000199",
            "razao": "ALFA ENGENHARIA E CONSTRUCOES LTDA",
            "invest": 12000000.0,
            "exec": 100.0,
            "dt_ini": "2023-02-01",
            "dt_fim": "2023-11-15",
        },
    ]

    for c in convenios:
        db.execute("""
            INSERT OR REPLACE INTO transferegov_convenios
            (numero_convenio, ano_convenio, orgao_concedente, codigo_ibge_proponente, municipio_proponente, uf_proponente, objeto, situacao_convenio, valor_global, valor_repasse, valor_contrapartida, valor_pago, data_inicio, data_fim)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            c["num"], c["ano"], c["orgao"], c["ibge"], c["mun"], c["uf"],
            c["obj"], c["sit"], c["global"], c["repasse"], c["contra"],
            c["pago"], c["dt_ini"], c["dt_fim"]
        ])

    for o in obras:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(o["cnpj"])
        db.execute("""
            INSERT OR REPLACE INTO obrasgov_obras_publicas
            (id_obra, numero_convenio, nome_obra, codigo_ibge, municipio, uf, situacao_obra, motivo_paralisacao, cnpj_executor, cnpj_raiz_executor, razao_social_executor, valor_investimento, percentual_execucao, data_inicio, data_prevista_conclusao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            o["id"], o["conv"], o["nome"], o["ibge"], o["mun"], o["uf"],
            o["sit"], o["motivo"], cnpj_limpo, cnpj_raiz, o["razao"],
            o["invest"], o["exec"], o["dt_ini"], o["dt_fim"]
        ])

    console.print(f"[green]✓ Inseridos {len(convenios)} convênios e {len(obras)} obras públicas no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe contagem de convênios e obras públicas federais."""
    db = get_db()
    c_conv = db.count("transferegov_convenios")
    c_obra = db.count("obrasgov_obras_publicas")
    console.print(f"[cyan]Obras & Convênios:[/cyan] {c_conv} convênios, {c_obra} obras registradas.")


if __name__ == "__main__":
    app()
