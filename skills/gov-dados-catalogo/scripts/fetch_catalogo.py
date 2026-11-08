"""Fetch and index public datasets metadata from dados.gov.br into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db

app = typer.Typer(help="Manage dados.gov.br Catalog Database")
console = Console()

CATALOGO_API_BASE = "https://dados.gov.br/api/publico"


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS catalogo_conjuntos_dados (
        id_dataset VARCHAR PRIMARY KEY,
        titulo VARCHAR,
        nome_identificador VARCHAR,
        orgao_responsavel VARCHAR,
        descricao VARCHAR,
        frequencia_atualizacao VARCHAR,
        qtd_recursos INTEGER,
        url_portal VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_catalogo_orgao ON catalogo_conjuntos_dados(orgao_responsavel);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula catálogo com conjuntos de dados fundamentais do Governo Federal."""
    init_tables()
    db = get_db()

    datasets = [
        {
            "id": "ds_rfb_cnpj",
            "titulo": "Cadastro Nacional da Pessoa Jurídica - CNPJ",
            "slug": "cnpj-dados-abertos",
            "orgao": "Secretaria Especial da Receita Federal do Brasil",
            "desc": "Dados públicos do cadastro de empresas, sócios QSA e estabelecimentos.",
            "freq": "MENSAL",
            "rec": 10,
            "url": "https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica-cnpj",
        },
        {
            "id": "ds_cgu_ceis",
            "titulo": "Cadastro de Empresas Inidôneas e Suspensas - CEIS",
            "slug": "ceis-sancoes",
            "orgao": "Controladoria-Geral da União",
            "desc": "Empresas e pessoas físicas impedidas de licitar ou contratar com a administração pública.",
            "freq": "DIARIA",
            "rec": 2,
            "url": "https://dados.gov.br/dados/conjuntos-dados/ceis",
        },
        {
            "id": "ds_mgi_pncp",
            "titulo": "Portal Nacional de Contratações Públicas - PNCP",
            "slug": "pncp-licitacoes",
            "orgao": "Ministério da Gestão e da Inovação em Serviços Públicos",
            "desc": "Licitações, contratos e atas de registro de preço de todos os entes federativos.",
            "freq": "CONTINUA",
            "rec": 4,
            "url": "https://dados.gov.br/dados/conjuntos-dados/pncp",
        },
    ]

    for d in datasets:
        db.execute("""
            INSERT OR REPLACE INTO catalogo_conjuntos_dados
            (id_dataset, titulo, nome_identificador, orgao_responsavel, descricao, frequencia_atualizacao, qtd_recursos, url_portal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            d["id"], d["titulo"], d["slug"], d["orgao"], d["desc"],
            d["freq"], d["rec"], d["url"]
        ])

    console.print(f"[green]✓ Inseridos {len(datasets)} conjuntos de dados do catálogo federal no Lakehouse.[/green]")


@app.command()
def buscar_api(
    termo: str = typer.Option("licitacoes", "--termo", "-t", help="Termo de pesquisa"),
):
    """Pesquisa conjuntos de dados em tempo real no portal dados.gov.br."""
    init_tables()
    url = f"{CATALOGO_API_BASE}/conjuntos-dados"
    console.print(f"[cyan]Buscando '{termo}' na API do dados.gov.br...[/cyan]")
    try:
        with GovHttpClient() as client:
            res = client.get_json(url, params={"q": termo, "pagina": 1})
            itens = res.get("registros", []) if isinstance(res, dict) else []
            console.print(f"[green]Retornados {len(itens)} conjuntos de dados do portal oficial.[/green]")
    except Exception as e:
        console.print(f"[yellow]Portal dados.gov.br respondeu: {e}. Base local ativa.[/yellow]")


if __name__ == "__main__":
    app()
