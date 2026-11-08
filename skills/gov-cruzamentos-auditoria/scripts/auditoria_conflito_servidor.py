"""Forensic detector of conflicts of interest: federal public servants (SIAPE) as partners/directors of government contractors."""

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

app = typer.Typer(help="Detect public servants registered as business partners or managers of government suppliers")
console = Console()


def init_servidores_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS cgu_servidores_siape (
        id_servidor VARCHAR PRIMARY KEY,
        cpf_servidor VARCHAR,
        nome_servidor VARCHAR,
        cargo VARCHAR,
        orgao_lotacao VARCHAR,
        uorg_lotacao VARCHAR,
        situacao_vinculo VARCHAR, -- ATIVO PERMANENTE, APOSENTADO, CARGO COMISSIONADO
        remuneracao_basica DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_siape_cpf ON cgu_servidores_siape(cpf_servidor);
    """)


@app.command()
def semear_casos_servidor():
    """Popula casos de demonstração de servidores públicos que figuram como administradores de empresas."""
    init_servidores_table()
    db = get_db()

    # Cria empresa onde o administrador é servidor público da ativa
    empresa_servidor = [{
        "cnpj": "44555666000177",
        "cnpj_raiz": "44555666",
        "razao_social": "TECH BRASILIA SOLUCOES DIGITAIS LTDA",
        "nome_fantasia": "TECH BRASILIA",
        "situacao_cadastral": "ATIVA",
        "data_inicio_atividade": "2021-08-15",
        "cnae_principal": "6201501",
        "cnae_descricao": "Desenvolvimento de programas de computador sob encomenda",
        "natureza_juridica": "2062",
        "capital_social": 250000.0,
        "porte": "MICRO EMPRESA",
        "uf": "DF",
        "municipio": "BRASILIA",
        "codigo_ibge": "5300108",
        "opcao_simples": True,
        "opcao_mei": False,
        "correio_eletronico": "diretoria@techbrasilia.com.br",
        "telefone": "6132001122",
        "cep": "70070000",
        "logradouro": "SETOR DE AUTARQUIAS SUL QUADRA 5",
    }]
    df_emp = pl.DataFrame(empresa_servidor)
    db.conn.register("tmp_emp_serv", df_emp.to_arrow())
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
        FROM tmp_emp_serv
    """)

    # Quadro societário
    socio_servidor = [{
        "id_socio": "44555666_MARCOS_AURELIO",
        "cnpj_raiz": "44555666",
        "identificador_socio": "2",
        "nome_socio": "MARCOS AURELIO MENDONCA",
        "cpf_cnpj_socio": "***445566**",
        "qualificacao_socio": "Sócio-Administrador",
        "data_entrada_sociedade": "2021-08-15",
        "faixa_etaria": "Entre 41 a 50 anos",
    }]
    df_soc = pl.DataFrame(socio_servidor)
    db.conn.register("tmp_soc_serv", df_soc.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO rfb_socios 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_soc_serv
    """)

    # Servidor público federal no SIAPE
    servidores = [{
        "id_servidor": "SIAPE_1092834",
        "cpf_servidor": "***445566**",
        "nome_servidor": "MARCOS AURELIO MENDONCA",
        "cargo": "ANALISTA EM TECNOLOGIA DA INFORMACAO",
        "orgao_lotacao": "MINISTERIO DA GESTAO E INOVACAO",
        "uorg_lotacao": "SECRETARIA DE GOVERNO DIGITAL",
        "situacao_vinculo": "ATIVO PERMANENTE",
        "remuneracao_basica": 18450.00,
    }]
    df_serv = pl.DataFrame(servidores)
    db.conn.register("tmp_siape_serv", df_serv.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO cgu_servidores_siape 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_siape_serv
    """)

    console.print("[bold green]✓ Casos de conflito de interesses servidor público semeados com sucesso![/bold green]")


@app.command()
def scan():
    """Cruza a folha de pagamento do SIAPE com a base de sócios-administradores da Receita Federal."""
    init_servidores_table()
    db = get_db()
    console.print(Panel("[bold red]🚨 DETECÇÃO DE CONFLITO DE INTERESSES: SERVIDOR PÚBLICO DA ATIVA COMO ADMINISTRADOR DE EMPRESA[/bold red]", border_style="red"))

    rows = db.query("""
        SELECT 
            sv.nome_servidor,
            sv.cpf_servidor,
            sv.cargo,
            sv.orgao_lotacao,
            sv.situacao_vinculo,
            s.qualificacao_socio,
            e.razao_social,
            e.cnpj,
            printf('R$ %,.2f', e.capital_social) AS capital_social
        FROM cgu_servidores_siape sv
        JOIN rfb_socios s ON sv.cpf_servidor = s.cpf_cnpj_socio 
                         AND LOWER(sv.nome_servidor) = LOWER(s.nome_socio)
        JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
        WHERE sv.situacao_vinculo = 'ATIVO PERMANENTE'
          AND LOWER(s.qualificacao_socio) LIKE '%administrador%'
        ORDER BY sv.orgao_lotacao
    """)

    if rows:
        t = Table(title="⚠️ ILEGALIDADE / CONFLITO DE INTERESSES: Servidor da Ativa Administrando Empresa Privada", border_style="bold red")
        t.add_column("Servidor Público", style="bold yellow")
        t.add_column("Cargo / Órgão", style="white")
        t.add_column("Qualificação na Empresa", style="bold red")
        t.add_column("Empresa Privada", style="cyan")
        t.add_column("Capital Social", style="green")
        for r in rows:
            t.add_row(r[0], f"{r[2]} ({r[3]})", r[5], r[6][:30], r[8])
        console.print(t)
        console.print(Panel(
            "[bold yellow]FUNDAMENTAÇÃO LEGAL:[/bold yellow] O Art. 117, inciso X da Lei nº 8.112/1990 proíbe terminantemente ao servidor público federal [bold red]'participar de gerência ou administração de sociedade privada, personificada ou não personificada'[/bold red]. Além de infração disciplinar passível de demissão, há potencial gravíssimo de direcionamento de contratações públicas caso a empresa forneça para o poder público.",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhum servidor da ativa identificado como administrador de empresa privada.[/green]")


if __name__ == "__main__":
    app()
