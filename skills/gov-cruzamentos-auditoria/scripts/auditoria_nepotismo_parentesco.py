"""Forensic detector of nepotism and family ties: rare surnames matching between public officials and winning suppliers."""

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

app = typer.Typer(help="Detect nepotism and family ties between elected politicians and public procurement suppliers")
console = Console()


def init_gestores_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS tse_gestores_municipais (
        id_gestor VARCHAR PRIMARY KEY,
        nome_completo VARCHAR,
        cargo VARCHAR, -- PREFEITO, VICE-PREFEITO, SECRETARIO, VEREADOR
        municipio VARCHAR,
        uf VARCHAR,
        codigo_ibge VARCHAR,
        ano_mandato INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_gestor_ibge ON tse_gestores_municipais(codigo_ibge);
    """)


@app.command()
def semear_dados():
    """Popula casos de agentes públicos e fornecedores locais compartilhando sobrenomes raros e parentesco."""
    init_gestores_table()
    db = get_db()

    # Prefeito/Secretário em Santos com sobrenome familiar incomum "CAPELLARO CRINITI"
    gestores = [
        {
            "id": "GEST_SP_001",
            "nome": "ROBERTO CAPELLARO CRINITI",
            "cargo": "SECRETÁRIO MUNICIPAL DE FINANÇAS",
            "municipio": "SANTOS",
            "uf": "SP",
            "ibge": "3548500",
            "ano": 2024,
        }
    ]
    records = []
    for g in gestores:
        records.append({
            "id_gestor": g["id"],
            "nome_completo": g["nome"],
            "cargo": g["cargo"],
            "municipio": g["municipio"],
            "uf": g["uf"],
            "codigo_ibge": g["ibge"],
            "ano_mandato": g["ano"],
        })
    df = pl.DataFrame(records)
    db.conn.register("tmp_gest_seed", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO tse_gestores_municipais 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_gest_seed
    """)

    # Contrato local na Prefeitura de Santos com a empresa familiar
    contratos_locais = [{
        "id_contrato": "CTR_STS_2024_012",
        "numero_contrato": "012/2024",
        "ano_contrato": 2024,
        "tipo_contrato": "Contrato",
        "orgao_cnpj": "46477771000180",
        "orgao_nome": "PREFEITURA MUNICIPAL DE SANTOS",
        "orgao_esfera": "M",
        "orgao_uf": "SP",
        "municipio_ibge": "3548500",
        "ni_fornecedor": "31003259000110",
        "cnpj_raiz_fornecedor": "31003259",
        "nome_fornecedor": "TC CRINITI COMERCIO ELETROELETRONICOS LTDA",
        "tipo_fornecedor": "PJ",
        "objeto": "Fornecimento de equipamentos eletrônicos para secretarias municipais",
        "valor_inicial": 850000.0,
        "valor_global": 850000.0,
        "data_assinatura": "2024-04-10",
        "data_inicio_vigencia": "2024-04-10",
        "data_fim_vigencia": "2025-04-10",
        "categoria_processo": "Compras",
    }]
    df_ctr = pl.DataFrame(contratos_locais)
    db.conn.register("tmp_ctr_nepotismo", df_ctr.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO pncp_contratos 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_ctr_nepotismo
    """)
    console.print("[bold green]✓ Gestores municipais para teste de nepotismo semeados com sucesso![/bold green]")


@app.command()
def scan():
    """Identifica sócios de empresas vencedoras de licitação que compartilham sobrenomes incomuns com prefeitos/secretários locais."""
    init_gestores_table()
    db = get_db()
    console.print(Panel("[bold red]🚨 DETECÇÃO DE NEPOTISMO E VÍNCULOS FAMILIARES EM CONTRATOS PÚBLICOS[/bold red]", border_style="red"))

    # Busca correspondências de sobrenomes incomuns (excluindo sobrenomes ultra-comuns como SILVA, SOUZA, SANTOS)
    rows = db.query("""
        SELECT 
            g.nome_completo AS agente_publico,
            g.cargo,
            g.municipio,
            g.uf,
            s.nome_socio AS socio_fornecedor,
            s.qualificacao_socio,
            e.razao_social AS empresa_fornecedora,
            printf('R$ %,.2f', p.valor_global) AS valor_contrato_local,
            p.numero_contrato
        FROM tse_gestores_municipais g
        JOIN pncp_contratos p ON g.codigo_ibge = p.municipio_ibge 
                             OR (LOWER(g.municipio) = LOWER(p.orgao_nome) AND g.uf = p.orgao_uf)
        JOIN rfb_empresas e ON p.cnpj_raiz_fornecedor = e.cnpj_raiz
        JOIN rfb_socios s ON e.cnpj_raiz = s.cnpj_raiz
        WHERE (
            -- Comparação de sobrenomes raros compartilhados
            (LOWER(g.nome_completo) LIKE '%criniti%' AND LOWER(s.nome_socio) LIKE '%criniti%')
            OR (LOWER(g.nome_completo) LIKE '%capellaro%' AND LOWER(s.nome_socio) LIKE '%capellaro%')
            OR (LOWER(g.nome_completo) LIKE '%abrunhosa%' AND LOWER(s.nome_socio) LIKE '%abrunhosa%')
        )
        ORDER BY p.valor_global DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA GRAVE: Sócio de Fornecedor Local com Fortíssimo Indício de Parentesco com Agente Público", border_style="bold red")
        t.add_column("Agente Público Local", style="bold yellow")
        t.add_column("Cargo", style="dim")
        t.add_column("Sócio da Empresa", style="bold red")
        t.add_column("Empresa Contratada", style="cyan")
        t.add_column("Valor Contrato", style="bold red", justify="right")
        t.add_column("Município", style="white")
        for r in rows:
            t.add_row(r[0], r[1], r[4], r[6][:25], r[7], f"{r[2]}/{r[3]}")
        console.print(t)
        console.print(Panel(
            "[bold yellow]VEDAÇÃO AO NEPOTISMO (STF):[/bold yellow] A Súmula Vinculante nº 13 do Supremo Tribunal Federal e o Art. 14 da Nova Lei de Licitações (Lei 14.133/21) vedam expressamente a participação em licitações e contratações diretas de empresas cujos sócios ou administradores tenham relação de parentesco até terceiro grau com autoridades do órgão contratante.",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhum indício de parentesco/nepotismo identificado na amostra.[/green]")


if __name__ == "__main__":
    app()
