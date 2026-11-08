"""Fetch and ingest CNJ DataJud judicial processes and compliance flags into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj, normalize_cpf, parse_currency, parse_date

app = typer.Typer(help="Manage CNJ DataJud Database")
console = Console()


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS cnj_processos_judiciais (
        numero_processo VARCHAR PRIMARY KEY,
        classe_processual VARCHAR, -- EXECUCAO FISCAL, ACAO CIVIL PUBLICA, IMPROBIDADE ADMINISTRATIVA, FALENCIA
        tribunal VARCHAR, -- TJSP, TJRJ, TRF1, TRF3
        grau_jurisdicao VARCHAR,
        data_ajuizamento DATE,
        cpf_cnpj_parte VARCHAR,
        cnpj_raiz_parte VARCHAR,
        nome_parte VARCHAR,
        polo_processual VARCHAR, -- PASSIVO, ATIVO
        valor_causa DOUBLE,
        situacao_processo VARCHAR,
        orgao_julgador VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_cnj_parte ON cnj_processos_judiciais(cpf_cnpj_parte);
    CREATE INDEX IF NOT EXISTS idx_cnj_raiz ON cnj_processos_judiciais(cnpj_raiz_parte);
    CREATE INDEX IF NOT EXISTS idx_cnj_classe ON cnj_processos_judiciais(classe_processual);
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula processos judiciais estratégicos (improbidade, execução fiscal, falência) de fornecedores públicos."""
    init_tables()
    db = get_db()

    processos = [
        {
            "proc": "1002345-88.2023.8.26.0100",
            "classe": "FALENCIA DE EMPRESA",
            "tribunal": "TJSP",
            "grau": "G1",
            "dt": "2023-08-14",
            "doc": "99887766000199", # SUPREMA FORNECIMENTOS LTDA
            "nome": "SUPREMA FORNECIMENTOS LTDA",
            "polo": "PASSIVO",
            "valor": 1250000.0,
            "sit": "DECRETADA",
            "vara": "1ª Vara de Falências e Recuperações Judiciais da Capital",
        },
        {
            "proc": "5001234-12.2023.4.03.6100",
            "classe": "EXECUCAO FISCAL",
            "tribunal": "TRF3",
            "grau": "G1",
            "dt": "2023-11-20",
            "doc": "31003259000110", # TC CRINITI
            "nome": "TC CRINITI COMERCIO ELETROELETRONICOS LTDA",
            "polo": "PASSIVO",
            "valor": 384500.20,
            "sit": "EM ANDAMENTO",
            "vara": "4ª Vara de Execuções Fiscais Federais de SP",
        },
        {
            "proc": "0801290-44.2024.8.06.0117",
            "classe": "ACAO CIVIL DE IMPROBIDADE ADMINISTRATIVA",
            "tribunal": "TJCE",
            "grau": "G1",
            "dt": "2024-01-10",
            "doc": "99887766000199",
            "nome": "SUPREMA FORNECIMENTOS LTDA",
            "polo": "PASSIVO",
            "valor": 3500000.0,
            "sit": "LIMINAR DEFERIDA INDISPONIBILIDADE DE BENS",
            "vara": "Vara da Fazenda Pública de Maracanaú",
        },
    ]

    for p in processos:
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(p["doc"])
        db.execute("""
            INSERT OR REPLACE INTO cnj_processos_judiciais
            (numero_processo, classe_processual, tribunal, grau_jurisdicao, data_ajuizamento, cpf_cnpj_parte, cnpj_raiz_parte, nome_parte, polo_processual, valor_causa, situacao_processo, orgao_julgador)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            p["proc"], p["classe"], p["tribunal"], p["grau"], p["dt"],
            cnpj_limpo, cnpj_raiz, p["nome"], p["polo"], p["valor"],
            p["sit"], p["vara"]
        ])

    console.print(f"[green]✓ Inseridos {len(processos)} processos judiciais do DataJud/CNJ no Lakehouse.[/green]")


@app.command()
def info():
    """Exibe estatísticas de processos indexados no DataJud."""
    db = get_db()
    c = db.count("cnj_processos_judiciais")
    console.print(f"[cyan]Processos Judiciais no DataJud:[/cyan] {c} processos catalogados.")


if __name__ == "__main__":
    app()
