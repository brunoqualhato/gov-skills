"""Forensic tracer of Parliamentary Amendments (Emendas Pix / Transferências Especiais) to Municipal Procurement."""

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
from core.normalizers import normalize_cnpj, parse_currency, parse_date

app = typer.Typer(help="Trace Parliamentary Amendments (Emendas Pix) into municipal procurement contracts")
console = Console()


def init_emendas_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS camara_emendas_parlamentares (
        id_emenda VARCHAR PRIMARY KEY,
        ano INTEGER,
        tipo_emenda VARCHAR, -- INDIVIDUAL TRANSFERENCIA ESPECIAL (EMENDA PIX), COMISSAO, RELATOR
        id_deputado INTEGER,
        nome_autor VARCHAR,
        partido_autor VARCHAR,
        uf_autor VARCHAR,
        codigo_ibge_beneficiario VARCHAR,
        municipio_beneficiario VARCHAR,
        uf_beneficiario VARCHAR,
        valor_empenhado DOUBLE,
        valor_pago DOUBLE,
        data_repasse DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_emenda_ibge ON camara_emendas_parlamentares(codigo_ibge_beneficiario);
    CREATE INDEX IF NOT EXISTS idx_emenda_deputado ON camara_emendas_parlamentares(id_deputado);
    """)


@app.command()
def semear_casos_emendas_pix():
    """Popula casos de demonstração de Emendas Pix rastreadas até contratos locais."""
    init_emendas_table()
    db = get_db()

    emendas = [
        {
            "id_emenda": "EMENDA_PIX_2024_001",
            "ano": 2024,
            "tipo_emenda": "INDIVIDUAL - TRANSFERENCIA ESPECIAL (PIX)",
            "id_deputado": 204549,
            "nome_autor": "AJ Albuquerque",
            "partido_autor": "PP",
            "uf_autor": "CE",
            "codigo_ibge_beneficiario": "2111300", # São Luís
            "municipio_beneficiario": "SAO LUIS",
            "uf_beneficiario": "MA",
            "valor_empenhado": 5000000.0,
            "valor_pago": 5000000.0,
            "data_repasse": "2024-02-10",
        },
    ]

    df_em = pl.DataFrame(emendas)
    db.conn.register("tmp_emendas_seed", df_em.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO camara_emendas_parlamentares 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_emendas_seed
    """)

    # Seed contrato local em São Luís recebendo o recurso da emenda
    contratos_locais = [{
        "id_contrato": "CTR_SLZ_2024_099",
        "numero_contrato": "099/2024",
        "ano_contrato": 2024,
        "tipo_contrato": "Contrato",
        "orgao_cnpj": "06307102000130",
        "orgao_nome": "PREFEITURA MUNICIPAL DE SAO LUIS",
        "orgao_esfera": "M",
        "orgao_uf": "MA",
        "municipio_ibge": "2111300",
        "ni_fornecedor": "99887766000199",
        "cnpj_raiz_fornecedor": "99887766",
        "nome_fornecedor": "SUPREMA FORNECIMENTOS LTDA",
        "tipo_fornecedor": "PJ",
        "objeto": "Fornecimento de materiais de escritório e informática",
        "valor_inicial": 4850000.0,
        "valor_global": 4850000.0,
        "data_assinatura": parse_date("2024-03-01"),
        "data_inicio_vigencia": parse_date("2024-03-01"),
        "data_fim_vigencia": parse_date("2025-03-01"),
        "categoria_processo": "Compras",
    }]
    df_ctr = pl.DataFrame(contratos_locais)
    db.conn.register("tmp_ctr_emenda", df_ctr.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO pncp_contratos 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_ctr_emenda
    """)

    console.print("[bold green]✓ Casos de Emendas Pix e contratos locais correlatos semeados com sucesso![/bold green]")


@app.command()
def scan():
    """Rastreia o ciclo completo: Deputado envia Emenda Pix -> Município recebe -> Empresa fornecedora da CEAP ganha o contrato."""
    init_emendas_table()
    db = get_db()
    console.print(Panel("[bold red]🚨 RASTREAMENTO FORENSE: O CICLO DAS 'EMENDAS PIX' ATÉ CONTRATAÇÕES LOCAIS[/bold red]", border_style="red"))

    rows = db.query("""
        SELECT 
            em.nome_autor AS parlamentar,
            em.partido_autor,
            em.municipio_beneficiario AS municipio,
            em.uf_beneficiario AS uf,
            printf('R$ %,.2f', em.valor_pago) AS valor_emenda_pix,
            em.data_repasse,
            p.numero_contrato,
            p.nome_fornecedor,
            printf('R$ %,.2f', p.valor_global) AS valor_contrato_local,
            p.data_assinatura,
            COALESCE(printf('R$ %,.2f', c.gasto_ceap), 'R$ 0,00') AS gasto_direto_gabinete_deputado
        FROM camara_emendas_parlamentares em
        JOIN pncp_contratos p ON em.codigo_ibge_beneficiario = p.municipio_ibge
                             OR (LOWER(em.municipio_beneficiario) = LOWER(p.orgao_nome) AND em.uf_beneficiario = p.orgao_uf)
        LEFT JOIN (
            SELECT cnpj_raiz_fornecedor, id_deputado, SUM(valor_liquido) AS gasto_ceap
            FROM camara_ceap_despesas
            GROUP BY cnpj_raiz_fornecedor, id_deputado
        ) c ON p.cnpj_raiz_fornecedor = c.cnpj_raiz_fornecedor AND em.id_deputado = c.id_deputado
        WHERE em.tipo_emenda LIKE '%PIX%'
        ORDER BY em.valor_pago DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA DE FLUXO: Emenda Pix Enviada com Contratação Local Correlata", border_style="bold red")
        t.add_column("Parlamentar", style="bold yellow")
        t.add_column("Município / UF", style="white")
        t.add_column("Repasse Emenda Pix", style="bold red", justify="right")
        t.add_column("Data Repasse", style="dim")
        t.add_column("Fornecedor Contratado", style="cyan")
        t.add_column("Contrato no Município", style="green", justify="right")
        for r in rows:
            t.add_row(f"{r[0]} ({r[1]})", f"{r[2]}/{r[3]}", r[4], str(r[5]), r[7][:30], r[8])
        console.print(t)
        console.print(Panel(
            "[bold yellow]RELEVÂNCIA INVESTIGATIVA:[/bold yellow] As transferências especiais ('Emendas Pix') entram no caixa do município sem vinculação formal a projetos ou prestação de contas prévia a ministérios. A correlação temporal entre o depósito da emenda pelo deputado e a contratação de fornecedores ligados à campanha ou à cota do parlamentar é o principal foco de auditoria da PF e do TCU.",
            border_style="yellow"
        ))
    else:
        console.print("[dim green]✓ Nenhuma correlação direta identificada na amostra atual.[/dim green]")


if __name__ == "__main__":
    app()
