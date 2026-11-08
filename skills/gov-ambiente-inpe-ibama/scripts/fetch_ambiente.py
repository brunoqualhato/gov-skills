"""Fetch and ingest environmental infraction and deforestation data from IBAMA and INPE."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_cpf, parse_currency, parse_date

app = typer.Typer(help="Manage Environmental (IBAMA & INPE) Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS ibama_autos_infracao (
        numero_auto VARCHAR PRIMARY KEY,
        cpf_cnpj_infrator VARCHAR,
        cnpj_raiz VARCHAR,
        nome_infrator VARCHAR,
        tipo_infracao VARCHAR,
        valor_multa DOUBLE,
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        bioma VARCHAR,
        data_auto DATE,
        situacao_debito VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS ibama_areas_embargadas (
        numero_termo VARCHAR PRIMARY KEY,
        cpf_cnpj_infrator VARCHAR,
        cnpj_raiz VARCHAR,
        nome_infrator VARCHAR,
        area_embargada_ha DOUBLE,
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        motivo_embargo VARCHAR,
        data_embargo DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS inpe_alertas_desmatamento (
        id_alerta VARCHAR PRIMARY KEY,
        data_deteccao DATE,
        area_hectares DOUBLE,
        bioma VARCHAR,
        uf VARCHAR,
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_ibama_cnpj ON ibama_autos_infracao(cpf_cnpj_infrator);
    CREATE INDEX IF NOT EXISTS idx_ibama_ibge ON ibama_autos_infracao(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_embargo_cnpj ON ibama_areas_embargadas(cpf_cnpj_infrator);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula autos de infração e embargos ambientais para testes de compliance e ESG."""
    init_tables()
    db = get_db()

    autos = [
        {
            "numero_auto": "AUTO_IBAMA_2023_8891",
            "cpf_cnpj_infrator": "31003259000110",
            "cnpj_raiz": "31003259",
            "nome_infrator": "TC CRINITI COMERCIO ELETROELETRONICOS LTDA",
            "tipo_infracao": "Despejo irregular de resíduos perigosos e poluentes eletrônicos",
            "valor_multa": 250000.0,
            "codigo_ibge": "3550308",
            "municipio": "São Paulo",
            "uf": "SP",
            "bioma": "Mata Atlântica",
            "data_auto": "2023-05-12",
            "situacao_debito": "ATIVO NAO PAGO",
        },
        {
            "numero_auto": "AUTO_IBAMA_2024_1042",
            "cpf_cnpj_infrator": "08234567000122",
            "cnpj_raiz": "08234567",
            "nome_infrator": "AGROPECUARIA AMAZONIA VERDE LTDA",
            "tipo_infracao": "Desmatamento e degradação não autorizada de Floresta Nativa",
            "valor_multa": 1850000.0,
            "codigo_ibge": "1500800",
            "municipio": "Anapu",
            "uf": "PA",
            "bioma": "Amazônia",
            "data_auto": "2024-02-18",
            "situacao_debito": "EM COBRANCA JUDICIAL",
        },
    ]

    embargos = [
        {
            "numero_termo": "EMB_2024_0045",
            "cpf_cnpj_infrator": "08234567000122",
            "cnpj_raiz": "08234567",
            "nome_infrator": "AGROPECUARIA AMAZONIA VERDE LTDA",
            "area_embargada_ha": 450.8,
            "codigo_ibge": "1500800",
            "municipio": "Anapu",
            "uf": "PA",
            "motivo_embargo": "Corte raso de vegetação nativa sem licença ambiental válida",
            "data_embargo": "2024-02-20",
        }
    ]

    alertas = [
        {
            "id_alerta": "DETER_PA_2024_9910",
            "data_deteccao": "2024-03-01",
            "area_hectares": 78.4,
            "bioma": "Amazônia",
            "uf": "PA",
            "codigo_ibge": "1500800",
            "municipio": "Anapu",
        }
    ]

    for a in autos:
        db.execute("""
            INSERT OR REPLACE INTO ibama_autos_infracao
            (numero_auto, cpf_cnpj_infrator, cnpj_raiz, nome_infrator, tipo_infracao, valor_multa, codigo_ibge, municipio, uf, bioma, data_auto, situacao_debito)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            a["numero_auto"], a["cpf_cnpj_infrator"], a["cnpj_raiz"], a["nome_infrator"],
            a["tipo_infracao"], a["valor_multa"], a["codigo_ibge"], a["municipio"],
            a["uf"], a["bioma"], a["data_auto"], a["situacao_debito"]
        ])

    for e in embargos:
        db.execute("""
            INSERT OR REPLACE INTO ibama_areas_embargadas
            (numero_termo, cpf_cnpj_infrator, cnpj_raiz, nome_infrator, area_embargada_ha, codigo_ibge, municipio, uf, motivo_embargo, data_embargo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            e["numero_termo"], e["cpf_cnpj_infrator"], e["cnpj_raiz"], e["nome_infrator"],
            e["area_embargada_ha"], e["codigo_ibge"], e["municipio"], e["uf"],
            e["motivo_embargo"], e["data_embargo"]
        ])

    for al in alertas:
        db.execute("""
            INSERT OR REPLACE INTO inpe_alertas_desmatamento
            (id_alerta, data_deteccao, area_hectares, bioma, uf, codigo_ibge, municipio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            al["id_alerta"], al["data_deteccao"], al["area_hectares"], al["bioma"],
            al["uf"], al["codigo_ibge"], al["municipio"]
        ])

    console.print(f"[green]✓ Inseridos autos ({len(autos)}), embargos ({len(embargos)}) e alertas DETER ({len(alertas)}) no Lakehouse.[/green]")


@app.command()
def consultar_ibama_aberto(
    uf: str = typer.Option("PA", "--uf", "-u", help="UF para checar dados abertos do IBAMA"),
):
    """Consulta portal de dados abertos do IBAMA."""
    init_tables()
    url = f"https://dadosabertos.ibama.gov.br/dados/SICAFI/{uf}/quantidade_autos_infracao.json"
    console.print(f"[cyan]Verificando dados abertos do IBAMA para {uf}...[/cyan]")
    try:
        with GovHttpClient() as client:
            res = client.get_json(url)
            console.print(f"[green]Conexão com dados abertos do IBAMA realizada com sucesso.[/green]")
    except Exception as e:
        console.print(f"[dim]Portal IBAMA respondeu: {e}. Base local ativa.[/dim]")


if __name__ == "__main__":
    app()
