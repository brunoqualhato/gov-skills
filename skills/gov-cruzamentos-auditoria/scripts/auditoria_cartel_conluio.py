"""Forensic detector of bidding cartels, collusion, and shared identity (same phone, email, address)."""

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

app = typer.Typer(help="Detect cartel collusion: shared email, phone, or address among competing companies")
console = Console()


def init_demo_schema():
    db = get_db()
    # Adiciona campos de contato em rfb_empresas se não existirem
    try:
        db.execute("ALTER TABLE rfb_empresas ADD COLUMN IF NOT EXISTS correio_eletronico VARCHAR;")
        db.execute("ALTER TABLE rfb_empresas ADD COLUMN IF NOT EXISTS telefone VARCHAR;")
        db.execute("ALTER TABLE rfb_empresas ADD COLUMN IF NOT EXISTS cep VARCHAR;")
        db.execute("ALTER TABLE rfb_empresas ADD COLUMN IF NOT EXISTS logradouro VARCHAR;")
    except Exception:
        pass


@app.command()
def semear_casos_cartel():
    """Popula casos de exemplo onde empresas 'concorrentes' compartilham o mesmo contato ou endereço."""
    init_demo_schema()
    db = get_db()

    # Empresas que parecem concorrentes, mas têm o mesmo e-mail de contabilidade ou mesmo telefone
    empresas_cartel = [
        {
            "cnpj": "10222333000144",
            "cnpj_raiz": "10222333",
            "razao_social": "ALFA CONSTRUCOES E SERVICOS LTDA",
            "nome_fantasia": "ALFA ENGENHARIA",
            "situacao_cadastral": "ATIVA",
            "data_inicio_atividade": "2020-01-15",
            "cnae_principal": "4120400",
            "cnae_descricao": "Construção de edifícios",
            "natureza_juridica": "2062",
            "capital_social": 100000.0,
            "porte": "MICRO EMPRESA",
            "uf": "DF",
            "municipio": "BRASILIA",
            "codigo_ibge": "5300108",
            "opcao_simples": True,
            "opcao_mei": False,
            "correio_eletronico": "licitacoes@contabil-uniao.com.br",
            "telefone": "6133445566",
            "cep": "70000000",
            "logradouro": "SCS QUADRA 4 BLOCO A SALA 302",
        },
        {
            "cnpj": "20333444000155",
            "cnpj_raiz": "20333444",
            "razao_social": "BETA OBRAS E REFORMAS LTDA",
            "nome_fantasia": "BETA SERVICOS",
            "situacao_cadastral": "ATIVA",
            "data_inicio_atividade": "2021-03-20",
            "cnae_principal": "4120400",
            "cnae_descricao": "Construção de edifícios",
            "natureza_juridica": "2062",
            "capital_social": 80000.0,
            "porte": "MICRO EMPRESA",
            "uf": "DF",
            "municipio": "BRASILIA",
            "codigo_ibge": "5300108",
            "opcao_simples": True,
            "opcao_mei": False,
            "correio_eletronico": "licitacoes@contabil-uniao.com.br", # MESMO EMAIL!
            "telefone": "6133445566",                                 # MESMO TELEFONE!
            "cep": "70000000",
            "logradouro": "SCS QUADRA 4 BLOCO A SALA 302",           # MESMA SALA!
        },
        {
            "cnpj": "30444555000166",
            "cnpj_raiz": "30444555",
            "razao_social": "GAMA EMPREENDIMENTOS E MANUTENCAO LTDA",
            "nome_fantasia": "GAMA MANUTENCAO",
            "situacao_cadastral": "ATIVA",
            "data_inicio_atividade": "2022-06-10",
            "cnae_principal": "4120400",
            "cnae_descricao": "Construção de edifícios",
            "natureza_juridica": "2062",
            "capital_social": 50000.0,
            "porte": "MICRO EMPRESA",
            "uf": "DF",
            "municipio": "BRASILIA",
            "codigo_ibge": "5300108",
            "opcao_simples": True,
            "opcao_mei": False,
            "correio_eletronico": "licitacoes@contabil-uniao.com.br", # MESMO EMAIL!
            "telefone": "6199887766",
            "cep": "70000000",
            "logradouro": "SCS QUADRA 4 BLOCO A SALA 302",           # MESMA SALA!
        },
    ]

    df = pl.DataFrame(empresas_cartel)
    db.conn.register("tmp_cartel_seed", df.to_arrow())
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
        FROM tmp_cartel_seed
    """)
    console.print("[bold green]✓ Casos de conluio/cartel semeados com sucesso para auditoria![/bold green]")


@app.command()
def scan():
    """Varre a base procurando empresas distintas que compartilham o mesmo e-mail, telefone ou endereço físico."""
    init_demo_schema()
    db = get_db()
    console.print(Panel("[bold red]🚨 DETECÇÃO DE CONLUIO & CARTEL EM LICITAÇÕES PÚBLICAS[/bold red]", border_style="red"))

    # 1. Empresas distintas compartilhando o mesmo E-mail
    console.print("[cyan]1. Identificando empresas distintas com o mesmo e-mail cadastrado na Receita...[/cyan]")
    rows_email = db.query("""
        SELECT 
            correio_eletronico,
            COUNT(DISTINCT cnpj) AS total_empresas,
            STRING_AGG(razao_social, ' | ') AS empresas,
            STRING_AGG(cnpj, ' | ') AS cnpjs
        FROM rfb_empresas
        WHERE correio_eletronico IS NOT NULL 
          AND correio_eletronico != ''
          AND correio_eletronico NOT LIKE '%gmail.com'
          AND correio_eletronico NOT LIKE '%hotmail.com'
        GROUP BY correio_eletronico
        HAVING COUNT(DISTINCT cnpj) >= 2
        ORDER BY total_empresas DESC
    """)
    if rows_email:
        t = Table(title="⚠️ ALERTA: Empresas Distintas Compartilhando o Mesmo E-mail", border_style="bold red")
        t.add_column("E-mail Compartilhado", style="bold yellow")
        t.add_column("Qtd Empresas", style="bold red", justify="center")
        t.add_column("Empresas Vinculadas", style="white")
        for r in rows_email:
            t.add_row(r[0], str(r[1]), r[2][:60])
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhum cluster de e-mail compartilhado identificado.[/dim green]")

    # 2. Empresas distintas compartilhando o mesmo Telefone
    console.print("\n[cyan]2. Identificando empresas distintas com o mesmo telefone cadastrado...[/cyan]")
    rows_tel = db.query("""
        SELECT 
            telefone,
            COUNT(DISTINCT cnpj) AS total_empresas,
            STRING_AGG(razao_social, ' | ') AS empresas
        FROM rfb_empresas
        WHERE telefone IS NOT NULL AND telefone != ''
        GROUP BY telefone
        HAVING COUNT(DISTINCT cnpj) >= 2
        ORDER BY total_empresas DESC
    """)
    if rows_tel:
        t = Table(title="⚠️ ALERTA: Empresas Distintas Compartilhando o Mesmo Telefone", border_style="bold red")
        t.add_column("Telefone", style="bold yellow")
        t.add_column("Qtd Empresas", style="bold red", justify="center")
        t.add_column("Empresas Vinculadas", style="white")
        for r in rows_tel:
            t.add_row(r[0], str(r[1]), r[2][:60])
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhum cluster de telefone identificado.[/dim green]")

    # 3. Empresas compartilhando o mesmo endereço físico exato
    console.print("\n[cyan]3. Identificando 'Sedes Compartilhadas' no mesmo logradouro/sala...[/cyan]")
    rows_addr = db.query("""
        SELECT 
            logradouro,
            uf,
            municipio,
            COUNT(DISTINCT cnpj) AS total_empresas,
            STRING_AGG(razao_social, ' | ') AS empresas
        FROM rfb_empresas
        WHERE logradouro IS NOT NULL AND logradouro != ''
        GROUP BY logradouro, uf, municipio
        HAVING COUNT(DISTINCT cnpj) >= 2
        ORDER BY total_empresas DESC
    """)
    if rows_addr:
        t = Table(title="⚠️ ALERTA: Empresas Distintas no Mesmo Endereço Físico (Possível Sede Compartilhada/Fachada)", border_style="bold yellow")
        t.add_column("Endereço / Logradouro", style="bold cyan")
        t.add_column("UF/Mun", style="white")
        t.add_column("Qtd", style="bold red", justify="center")
        t.add_column("Empresas", style="white")
        for r in rows_addr:
            t.add_row(r[0], f"{r[2]}/{r[1]}", str(r[3]), r[4][:60])
        console.print(t)


if __name__ == "__main__":
    app()
