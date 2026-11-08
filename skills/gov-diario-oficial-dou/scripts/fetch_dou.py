"""Fetch and ingest Official Gazette (Diário Oficial da União - DOU) legal publications into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Manage Diário Oficial da União (DOU) Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS dou_publicacoes_atos (
        id_materia_dou VARCHAR PRIMARY KEY,
        data_publicacao DATE,
        secao VARCHAR, -- Seção 1, 2, 3 ou Edição Extra
        orgao_emissor VARCHAR,
        titulo VARCHAR,
        subtitulo VARCHAR,
        tipo_ato VARCHAR, -- DECRETO, PORTARIA, NOMEAÇÃO, EXTRATO DE CONTRATO
        texto_resumo VARCHAR,
        texto_completo VARCHAR,
        url_publicacao VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_dou_data ON dou_publicacoes_atos(data_publicacao);
    CREATE INDEX IF NOT EXISTS idx_dou_orgao ON dou_publicacoes_atos(orgao_emissor);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula matérias e atos normativos das Seções 1, 2 e 3 do DOU."""
    init_tables()
    db = get_db()

    publicacoes = [
        {
            "id": "DOU_2024_03_S1_001",
            "data": "2024-03-15",
            "secao": "Seção 1",
            "orgao": "Presidência da República / Casa Civil",
            "titulo": "DECRETO Nº 11.950, DE 14 DE MARÇO DE 2024",
            "subtitulo": "Regulamenta dispositivos da Nova Lei de Licitações e Contratos Administrativos",
            "tipo": "DECRETO",
            "resumo": "Estabelece diretrizes para a governança das contratações públicas federais.",
            "completo": "O PRESIDENTE DA REPÚBLICA, no uso da atribuição que lhe confere o art. 84, caput, inciso IV, da Constituição...",
            "url": "https://in.gov.br/materia/-/asset_publisher/decreto-11950",
        },
        {
            "id": "DOU_2024_03_S2_002",
            "data": "2024-03-15",
            "secao": "Seção 2",
            "orgao": "Ministério da Fazenda / Gabinete do Ministro",
            "titulo": "PORTARIA DE PESSOAL Nº 412, DE 14 DE MARÇO DE 2024",
            "subtitulo": "Nomeação para cargo em comissão",
            "tipo": "NOMEACAO",
            "resumo": "Nomeia Diretor de Programa da Secretaria Especial da Receita Federal.",
            "completo": "O MINISTRO DE ESTADO DA FAZENDA resolve nomear para exercer o cargo de Diretor de Programa...",
            "url": "https://in.gov.br/materia/-/asset_publisher/portaria-412",
        },
        {
            "id": "DOU_2024_03_S3_003",
            "data": "2024-03-15",
            "secao": "Seção 3",
            "orgao": "Ministério da Saúde / Fundo Nacional de Saúde",
            "titulo": "EXTRATO DE CONTRATO Nº 45/2024",
            "subtitulo": "Fornecimento de equipamentos médicos hospitalares",
            "tipo": "EXTRATO DE CONTRATO",
            "resumo": "Contratada: TC CRINITI COMERCIO ELETROELETRONICOS LTDA (CNPJ 31.003.259/0001-10). Valor Global: R$ 4.250.000,00.",
            "completo": "Processo nº 25000.012345/2024-81. Contratante: Ministério da Saúde. Contratada: TC CRINITI COMERCIO...",
            "url": "https://in.gov.br/materia/-/asset_publisher/extrato-45",
        },
    ]

    for p in publicacoes:
        db.execute("""
            INSERT OR REPLACE INTO dou_publicacoes_atos
            (id_materia_dou, data_publicacao, secao, orgao_emissor, titulo, subtitulo, tipo_ato, texto_resumo, texto_completo, url_publicacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            p["id"], p["data"], p["secao"], p["orgao"], p["titulo"],
            p["subtitulo"], p["tipo"], p["resumo"], p["completo"], p["url"]
        ])

    console.print(f"[green]✓ Inseridas {len(publicacoes)} matérias do Diário Oficial da União no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe contagem de atos e matérias do DOU cadastradas."""
    db = get_db()
    c = db.count("dou_publicacoes_atos")
    console.print(f"[cyan]Publicações no DOU:[/cyan] {c} atos e matérias indexadas.")


if __name__ == "__main__":
    app()
