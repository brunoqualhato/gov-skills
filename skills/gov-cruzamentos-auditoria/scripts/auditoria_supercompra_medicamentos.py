"""Forensic pharmaceutical over-procurement detector (Supercompra de Medicamentos per capita — DataSUS x IBGE x PNCP)."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect disproportionate pharmaceutical procurement volume vs population and SUS beds")
console = Console()


def ensure_supercompra_table(db):
    """Inicializa e popula dados de compras municipais de medicamentos cruzados com demografia e leitos SUS."""
    db.execute("""
    CREATE TABLE IF NOT EXISTS auditoria_compras_medicamentos_volume (
        id_compra_med VARCHAR PRIMARY KEY,
        codigo_ibge VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        populacao_estimada INTEGER,
        leitos_sus_municipio INTEGER,
        orgao_comprador VARCHAR,
        principio_ativo VARCHAR,
        apresentacao VARCHAR,
        quantidade_doses_adquiridas BIGINT,
        valor_unitario_pago DOUBLE,
        valor_total_compra DOUBLE,
        fornecedor_cnpj VARCHAR,
        fornecedor_nome VARCHAR,
        data_compra DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    if db.count("auditoria_compras_medicamentos_volume") > 0:
        return

    compras = [
        (
            "MED_VOL_2024_01",
            "1500800",
            "Anapu",
            "PA",
            29800,
            18,
            "FUNDO MUNICIPAL DE SAUDE DE ANAPU",
            "DIPIRONA SODICA 500MG",
            "COMPRIMIDO SIMPLES",
            4500000, # 4.5 milhões de comprimidos para 29.800 habitantes (151 doses/hab!)
            0.85,
            3825000.0,
            "99887766000199",
            "SUPREMA FORNECIMENTOS LTDA",
            "2024-02-20",
        ),
        (
            "MED_VOL_2024_02",
            "2307650",
            "Maracanaú",
            "CE",
            234500,
            120,
            "SECRETARIA DE SAUDE DE MARACANAU",
            "OMEPRAZOL 20MG",
            "CAPSULA DURA",
            12000000, # 12 milhões de cápsulas (51 doses/hab!)
            0.48,
            5760000.0,
            "31003259000110",
            "TC CRINITI COMERCIO ELETROELETRONICOS LTDA",
            "2024-03-08",
        ),
    ]
    for c in compras:
        db.execute("""
            INSERT OR REPLACE INTO auditoria_compras_medicamentos_volume
            (id_compra_med, codigo_ibge, municipio, uf, populacao_estimada, leitos_sus_municipio, orgao_comprador, principio_ativo, apresentacao, quantidade_doses_adquiridas, valor_unitario_pago, valor_total_compra, fornecedor_cnpj, fornecedor_nome, data_compra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, list(c))


@app.command()
def scan(
    max_doses_hab: float = typer.Option(20.0, "--max-doses-hab", "-d", help="Limite de alerta de doses adquiridas por habitante"),
):
    """Detecta compras de medicamentos em quantidades fisicamente incompatíveis com a população e leitos SUS locais."""
    db = get_db()
    ensure_supercompra_table(db)

    console.print(Panel(
        f"[bold red]AUDITORIA FORENSE: SUPERCOMPRA DE MEDICAMENTOS PER CAPITA (DataSUS × IBGE × PNCP)[/bold red]\n"
        f"[dim]Identifica prefeituras adquirindo milhões de doses de fármacos (> {max_doses_hab:.0f} unidades/habitante),\n"
        f"padrão clássico de emissão de notas fiscais frias ou desvio de estoque do SUS.[/dim]",
        border_style="red",
    ))

    rows = db.query(f"""
        SELECT 
            municipio || '/' || uf AS localidade,
            populacao_estimada,
            leitos_sus_municipio,
            principio_ativo,
            quantidade_doses_adquiridas,
            CAST(quantidade_doses_adquiridas AS DOUBLE) / NULLIF(populacao_estimada, 0) AS doses_por_habitante,
            CAST(quantidade_doses_adquiridas AS DOUBLE) / NULLIF(leitos_sus_municipio, 0) AS doses_por_leito_sus,
            valor_total_compra,
            fornecedor_nome,
            fornecedor_cnpj
        FROM auditoria_compras_medicamentos_volume
        WHERE (CAST(quantidade_doses_adquiridas AS DOUBLE) / NULLIF(populacao_estimada, 0)) >= {max_doses_hab}
        ORDER BY doses_por_habitante DESC
    """)

    if rows:
        t = Table(title="💊 ALERTA SANITÁRIO: Volume de Medicamentos Incompatível com a População Local", border_style="red")
        t.add_column("Município", style="bold white")
        t.add_column("População / Leitos", justify="right", style="cyan")
        t.add_column("Fármaco Adquirido", style="yellow")
        t.add_column("Qtd Doses Compradas", justify="right", style="bold red")
        t.add_column("Doses / Habitante", justify="center", style="bold yellow")
        t.add_column("Valor do Contrato", justify="right", style="bold green")
        t.add_column("Fornecedor Contratado", style="magenta")

        for r in rows:
            t.add_row(
                r[0],
                f"{r[1]:,} hab\n({r[2]} leitos SUS)",
                r[3],
                f"{r[4]:,}",
                f"{r[5]:.1f} doses/hab\n({r[6]:,.0f}/leito)",
                f"R$ {r[7]:,.2f}",
                f"{r[8][:26]}\n({r[9]})",
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhuma desproporção volumétrica de medicamentos detectada.[/dim green]")


@app.command()
def info():
    """Exibe parâmetros epidemiológicos da auditoria de volume de medicamentos."""
    console.print("[cyan]Parâmetro Forense CGU/PF:[/cyan] Aquisições que superam em mais de 10x a demanda epidemiológica anual da rede básica indicam simulação de fornecimento (Operação 'Remédio Amargo').")


if __name__ == "__main__":
    app()
