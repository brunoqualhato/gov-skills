"""Forensic detector of strawmen (laranjas): social benefit recipients registered as owners of contractors."""

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
from core.normalizers import normalize_cpf, parse_currency, parse_date

app = typer.Typer(help="Detect strawmen (laranjas): partners of public contractors receiving social benefits")
console = Console()


def init_beneficios_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS cgu_beneficios_cidadao (
        id_beneficio VARCHAR PRIMARY KEY,
        tipo_beneficio VARCHAR, -- BOLSA FAMILIA, BPC, AUXILIO GAS
        cpf_beneficiario VARCHAR,
        nome_beneficiario VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        codigo_ibge VARCHAR,
        mes_competencia VARCHAR,
        valor_parcela DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_beneficio_cpf ON cgu_beneficios_cidadao(cpf_beneficiario);
    """)


@app.command()
def semear_casos_laranja():
    """Popula casos de demonstração de sócios 'laranjas' que recebem Bolsa Família e são donos de empresas licitantes."""
    init_beneficios_table()
    db = get_db()

    # Cria empresa fictícia de fachada com sócio humilde recebendo benefício social
    empresa_laranja = [{
        "cnpj": "99887766000199",
        "cnpj_raiz": "99887766",
        "razao_social": "SUPREMA FORNECIMENTOS LTDA",
        "nome_fantasia": "SUPREMA COMERCIO",
        "situacao_cadastral": "ATIVA",
        "data_inicio_atividade": "2023-01-10",
        "cnae_principal": "4712100",
        "cnae_descricao": "Comércio varejista",
        "natureza_juridica": "2062",
        "capital_social": 10000.0,
        "porte": "MICRO EMPRESA",
        "uf": "MA",
        "municipio": "SAO LUIS",
        "codigo_ibge": "2111300",
        "opcao_simples": True,
        "opcao_mei": False,
        "correio_eletronico": "contato@suprema.com",
        "telefone": "9899887766",
        "cep": "65000000",
        "logradouro": "RUA DA PAZ 10",
    }]

    df_emp = pl.DataFrame(empresa_laranja)
    db.conn.register("tmp_emp_laranja", df_emp.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO rfb_empresas (
            cnpj, cnpj_raiz, razao_social, nome_fantasia, situacao_cadastral, 
            data_inicio_atividade, cnae_principal, cnae_descricao, natureza_juridica, 
            capital_social, porte, uf, municipio, codigo_ibge, opcao_simples, opcao_mei, 
            correio_eletronico, telefone, cep, logradouro, created_at
        )
        SELECT 
            cnpj, cnpj_raiz, razao_social, nome_fantasia, situacao_cadastral, 
            CAST(data_inicio_atividade AS DATE), cnae_principal, cnae_descricao, natureza_juridica, 
            capital_social, porte, uf, municipio, codigo_ibge, opcao_simples, opcao_mei, 
            correio_eletronico, telefone, cep, logradouro, CURRENT_TIMESTAMP
        FROM tmp_emp_laranja
    """)

    # Sócio da empresa
    socio_laranja = [{
        "id_socio": "99887766_RAIMUNDO_DA_SILVA",
        "cnpj_raiz": "99887766",
        "identificador_socio": "2",
        "nome_socio": "RAIMUNDO NONATO DA SILVA",
        "cpf_cnpj_socio": "***123456**",
        "qualificacao_socio": "Sócio-Administrador",
        "data_entrada_sociedade": "2023-01-10",
        "faixa_etaria": "Entre 51 a 60 anos",
    }]
    df_soc = pl.DataFrame(socio_laranja)
    db.conn.register("tmp_soc_laranja", df_soc.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO rfb_socios 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_soc_laranja
    """)

    # Benefício social registrado no mesmo CPF
    beneficios = [{
        "id_beneficio": "BENEF_BF_2024_01",
        "tipo_beneficio": "BOLSA FAMILIA",
        "cpf_beneficiario": "***123456**",
        "nome_beneficiario": "RAIMUNDO NONATO DA SILVA",
        "municipio": "SAO LUIS",
        "uf": "MA",
        "codigo_ibge": "2111300",
        "mes_competencia": "202401",
        "valor_parcela": 650.00,
    }]
    df_ben = pl.DataFrame(beneficios)
    db.conn.register("tmp_ben_laranja", df_ben.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO cgu_beneficios_cidadao 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_ben_laranja
    """)

    console.print("[bold green]✓ Casos de sócio laranja beneficiário de programa social semeados com sucesso![/bold green]")


@app.command()
def scan():
    """Identifica sócios e administradores de empresas que recebem programas sociais (Bolsa Família, BPC)."""
    init_beneficios_table()
    db = get_db()
    console.print(Panel("[bold red]🚨 DETECÇÃO DE SÓCIOS LARANJAS (BENEFICIÁRIOS DO BOLSA FAMÍLIA / BPC)[/bold red]", border_style="red"))

    rows = db.query("""
        SELECT 
            s.nome_socio,
            s.cpf_cnpj_socio AS cpf_socio,
            e.razao_social,
            e.cnpj,
            e.porte,
            printf('R$ %,.2f', e.capital_social) AS capital_social,
            b.tipo_beneficio,
            printf('R$ %,.2f', b.valor_parcela) AS valor_beneficio_recebido,
            COALESCE(printf('R$ %,.2f', p.total_contratos), 'R$ 0,00') AS total_contratos_publicos
        FROM rfb_socios s
        JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
        JOIN cgu_beneficios_cidadao b ON s.cpf_cnpj_socio = b.cpf_beneficiario 
                                     AND LOWER(s.nome_socio) = LOWER(b.nome_beneficiario)
        LEFT JOIN (
            SELECT cnpj_raiz_fornecedor, SUM(valor_global) AS total_contratos
            FROM pncp_contratos 
            GROUP BY cnpj_raiz_fornecedor
        ) p ON e.cnpj_raiz = p.cnpj_raiz_fornecedor
        ORDER BY e.capital_social DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA GRAVE: Sócio / Administrador de Empresa Consta como Beneficiário de Programa Social", border_style="bold red")
        t.add_column("Nome do Sócio", style="bold yellow")
        t.add_column("CPF", style="dim")
        t.add_column("Empresa Controlada", style="white")
        t.add_column("Porte", style="magenta")
        t.add_column("Capital Social", style="green")
        t.add_column("Benefício Social", style="bold red")
        t.add_column("Parcela", style="red")
        for r in rows:
            t.add_row(r[0], r[1], r[2][:30], r[4], r[5], r[6], r[7])
        console.print(t)
        console.print(Panel(
            "[bold yellow]INDÍCIO FORENSE:[/bold yellow] Pessoas em situação de extrema vulnerabilidade socioeconômica cadastradas no CadÚnico/Bolsa Família figurando formalmente no contrato social de empresas participantes de compras públicas configuram a clássica figura do [bold red]'sócio laranja'[/bold red] para ocultação de patrimônio e blindagem dos verdadeiros operadores do esquema.",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhum beneficiário de programa social encontrado no quadro societário.[/green]")


if __name__ == "__main__":
    app()
