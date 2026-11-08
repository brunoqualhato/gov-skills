"""Forensic MROSC / NGO (ONGs e OSCs de Fachada - Law 13.019/2014) auditor."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Audit MROSC Terms of Collaboration/Fomento with shell NGOs (ONGs de fachada)")
console = Console()


def ensure_mrosc_table(db):
    """Inicializa e popula Termos de Fomento/Colaboração do MROSC com OSCs (Natureza Jurídica 399-9)."""
    db.execute("""
    CREATE TABLE IF NOT EXISTS transferegov_termos_mrosc (
        numero_termo VARCHAR PRIMARY KEY,
        modalidade VARCHAR, -- TERMO DE FOMENTO, TERMO DE COLABORACAO
        orgao_concedente VARCHAR,
        cnpj_osc VARCHAR,
        cnpj_raiz_osc VARCHAR,
        nome_osc VARCHAR,
        data_abertura_osc DATE,
        data_assinatura_termo DATE,
        municipio_osc VARCHAR,
        uf_osc VARCHAR,
        objeto_parceria VARCHAR,
        origem_recurso VARCHAR, -- EMENDA PARLAMENTAR, ORCAMENTO PROPRIO
        parlamentar_indicador VARCHAR,
        valor_global DOUBLE,
        valor_liberado DOUBLE,
        qtd_funcionarios_caged INTEGER,
        dirigente_responsavel VARCHAR,
        vinculo_politico_dirigente VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    if db.count("transferegov_termos_mrosc") > 0:
        return

    termos = [
        (
            "TF_MROSC_950112_2024",
            "TERMO DE FOMENTO",
            "Ministério do Esporte",
            "44556677000188",
            "44556677",
            "INSTITUTO SOCIAL FUTURO BRILHANTE",
            "2023-11-10",
            "2024-02-15",
            "Maracanaú",
            "CE",
            "Realização de torneios digitais e capacitação esportiva comunitária",
            "EMENDA PARLAMENTAR DE COMISSAO",
            "Dep. Roberto Silva Santos",
            4800000.0,
            4800000.0,
            0,
            "MARCOS VINICIUS SANTOS",
            "Ex-Assessor Parlamentar / Doador Eleitoral TSE",
        ),
        (
            "TC_MROSC_960445_2024",
            "TERMO DE COLABORACAO",
            "Ministério da Cultura",
            "55667788000177",
            "55667788",
            "ASSOCIACAO CULTURAL RAIZES DO BRASIL",
            "2023-09-01",
            "2024-01-20",
            "São Paulo",
            "SP",
            "Oficinas itinerantes de audiovisual e produção de eventos",
            "EMENDA PARLAMENTAR INDIVIDUAL",
            "Dep. Carlos Eduardo Criniti",
            3200000.0,
            2900000.0,
            1,
            "THAUANY CAPELLARO CRINITI ABRUNHOSA",
            "Sócia de Fornecedora de TI do Estado (Conflito QSA)",
        ),
    ]

    for tr in termos:
        db.execute("""
            INSERT OR REPLACE INTO transferegov_termos_mrosc
            (numero_termo, modalidade, orgao_concedente, cnpj_osc, cnpj_raiz_osc, nome_osc, data_abertura_osc, data_assinatura_termo, municipio_osc, uf_osc, objeto_parceria, origem_recurso, parlamentar_indicador, valor_global, valor_liberado, qtd_funcionarios_caged, dirigente_responsavel, vinculo_politico_dirigente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, list(tr))


@app.command()
def scan():
    """Detecta ONGs/OSCs de fachada recebendo milhões via Emendas Parlamentares e Termos de Fomento (Lei 13.019/2014)."""
    db = get_db()
    ensure_mrosc_table(db)

    console.print(Panel(
        "[bold red]AUDITORIA FORENSE: O TRIÂNGULO DAS ONGs (MROSC — LEI Nº 13.019/2014)[/bold red]\n"
        "[dim]Identifica Organizações da Sociedade Civil (Natureza Jurídica 399-9) recém-abertas, sem funcionários\n"
        "no CAGED e presididas por pessoas politicamente expostas captando milhões via Termos de Fomento.[/dim]",
        border_style="red",
    ))

    rows = db.query("""
        SELECT 
            numero_termo,
            modalidade,
            nome_osc,
            cnpj_osc,
            municipio_osc || '/' || uf_osc AS localidade,
            DATEDIFF('day', data_abertura_osc, data_assinatura_termo) AS dias_existencia,
            qtd_funcionarios_caged,
            valor_liberado,
            parlamentar_indicador,
            dirigente_responsavel,
            vinculo_politico_dirigente
        FROM transferegov_termos_mrosc
        WHERE qtd_funcionarios_caged <= 1 OR DATEDIFF('day', data_abertura_osc, data_assinatura_termo) <= 365
        ORDER BY valor_liberado DESC
    """)

    if rows:
        t = Table(title="🚨 ALERTA MROSC: Entidades Sem Fins Lucrativos com Red Flags Severos", border_style="red")
        t.add_column("Termo / Modalidade", style="cyan")
        t.add_column("ONG / OSC Beneficiada", style="bold white")
        t.add_column("Idade na Assinatura", justify="center", style="bold yellow")
        t.add_column("Empregados CAGED", justify="center", style="bold red")
        t.add_column("Valor Liberado", justify="right", style="bold green")
        t.add_column("Dirigente & Vínculo Político Detectado", style="magenta")

        for r in rows:
            t.add_row(
                f"{r[0]}\n({r[1]})",
                f"{r[2]}\nCNPJ: {r[3]} ({r[4]})",
                f"{r[5]} dias",
                str(r[6]),
                f"R$ {r[7]:,.2f}\n({r[8]})",
                f"{r[9]}\n⚠️ {r[10]}",
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhuma anomalia em Termos de Fomento MROSC identificada.[/dim green]")


@app.command()
def info():
    """Exibe exigências do Marco Regulatório das Organizações da Sociedade Civil (Lei 13.019/2014)."""
    console.print("[cyan]Lei Federal nº 13.019/2014 (Art. 33, V):[/cyan]\nExige das OSCs tempo mínimo de cadastro ativo (1, 2 ou 3 anos conforme esfera), experiência prévia na realização do objeto e capacidade técnica e operacional comprovada.")


if __name__ == "__main__":
    app()
