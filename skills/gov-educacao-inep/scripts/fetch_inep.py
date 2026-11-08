"""Fetch and ingest Ministry of Education (INEP) Censo Escolar and IDEB indicators into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_ibge

app = typer.Typer(help="Manage INEP Education Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS inep_escolas_censo (
        codigo_escola VARCHAR PRIMARY KEY,
        nome_escola VARCHAR,
        dependencia_administrativa VARCHAR, -- Federal, Estadual, Municipal, Privada
        codigo_ibge VARCHAR,
        uf VARCHAR,
        municipio VARCHAR,
        situacao_funcionamento VARCHAR,
        tem_agua_potavel BOOLEAN,
        tem_energia_eletrica BOOLEAN,
        tem_esgoto BOOLEAN,
        tem_internet BOOLEAN,
        total_matriculas INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS inep_ideb_municipios (
        codigo_ibge VARCHAR,
        ano INTEGER,
        etapa_ensino VARCHAR, -- Anos Iniciais, Anos Finais, Ensino Medio
        rede VARCHAR, -- Municipal, Estadual, Publica
        nota_ideb DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(codigo_ibge, ano, etapa_ensino, rede)
    );

    CREATE INDEX IF NOT EXISTS idx_inep_escola_ibge ON inep_escolas_censo(codigo_ibge);
    CREATE INDEX IF NOT EXISTS idx_inep_ideb_ibge ON inep_ideb_municipios(codigo_ibge);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula dados do Censo Escolar e IDEB municipal para análises de eficiência educacional."""
    init_tables()
    db = get_db()

    escolas = [
        {
            "cod": "35000001",
            "nome": "EMEF PRES ARTHUR DA COSTA E SILVA",
            "dep": "MUNICIPAL",
            "ibge": "3550308",
            "uf": "SP",
            "mun": "São Paulo",
            "sit": "EM ATIVIDADE",
            "agua": True, "luz": True, "esgoto": True, "net": True, "matr": 1150
        },
        {
            "cod": "33000002",
            "nome": "ESCOLA MUNICIPAL HENRIQUE FORMOZO",
            "dep": "MUNICIPAL",
            "ibge": "3304557",
            "uf": "RJ",
            "mun": "Rio de Janeiro",
            "sit": "EM ATIVIDADE",
            "agua": True, "luz": True, "esgoto": True, "net": True, "matr": 820
        },
        {
            "cod": "23000003",
            "nome": "EEFM CORONEL JOAO PAULO",
            "dep": "MUNICIPAL",
            "ibge": "2307650",
            "uf": "CE",
            "mun": "Maracanaú",
            "sit": "EM ATIVIDADE",
            "agua": True, "luz": True, "esgoto": True, "net": True, "matr": 640
        },
    ]

    ideb = [
        {"ibge": "3550308", "ano": 2023, "etapa": "ANOS INICIAIS", "rede": "MUNICIPAL", "nota": 6.2},
        {"ibge": "3550308", "ano": 2023, "etapa": "ANOS FINAIS", "rede": "MUNICIPAL", "nota": 5.4},
        {"ibge": "3304557", "ano": 2023, "etapa": "ANOS INICIAIS", "rede": "MUNICIPAL", "nota": 5.8},
        {"ibge": "3304557", "ano": 2023, "etapa": "ANOS FINAIS", "rede": "MUNICIPAL", "nota": 4.9},
        {"ibge": "2307650", "ano": 2023, "etapa": "ANOS INICIAIS", "rede": "MUNICIPAL", "nota": 6.9},
        {"ibge": "2307650", "ano": 2023, "etapa": "ANOS FINAIS", "rede": "MUNICIPAL", "nota": 6.1},
    ]

    for e in escolas:
        db.execute("""
            INSERT OR REPLACE INTO inep_escolas_censo
            (codigo_escola, nome_escola, dependencia_administrativa, codigo_ibge, uf, municipio, situacao_funcionamento, tem_agua_potavel, tem_energia_eletrica, tem_esgoto, tem_internet, total_matriculas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            e["cod"], e["nome"], e["dep"], e["ibge"], e["uf"], e["mun"],
            e["sit"], e["agua"], e["luz"], e["esgoto"], e["net"], e["matr"]
        ])

    for i in ideb:
        db.execute("""
            INSERT OR REPLACE INTO inep_ideb_municipios
            (codigo_ibge, ano, etapa_ensino, rede, nota_ideb)
            VALUES (?, ?, ?, ?, ?)
        """, [
            i["ibge"], i["ano"], i["etapa"], i["rede"], i["nota"]
        ])

    console.print(f"[green]✓ Inseridas {len(escolas)} escolas e {len(ideb)} indicadores do IDEB no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe contagem de escolas e dados educacionais."""
    db = get_db()
    c_esc = db.count("inep_escolas_censo")
    c_ideb = db.count("inep_ideb_municipios")
    console.print(f"[cyan]INEP no Lakehouse:[/cyan] {c_esc} escolas, {c_ideb} registros de IDEB.")


if __name__ == "__main__":
    app()
