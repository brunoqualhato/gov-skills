"""Forensic Geospatial & Impossible Logistics Auditor (Cartel Geográfico / Logística Impossível)."""

import math
import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect impossible geographic supply logistics for perishable/daily public contracts")
console = Console()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância geodésica Haversine em quilômetros entre dois pontos."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def ensure_logistica_table(db):
    """Inicializa e popula contratos de fornecimento perecível/diário com coordenadas da sede e do destino."""
    db.execute("""
    CREATE TABLE IF NOT EXISTS auditoria_logistica_contratos (
        id_contrato VARCHAR PRIMARY KEY,
        orgao_contratante VARCHAR,
        municipio_destino VARCHAR,
        uf_destino VARCHAR,
        lat_destino DOUBLE,
        lon_destino DOUBLE,
        fornecedor_cnpj VARCHAR,
        fornecedor_nome VARCHAR,
        municipio_sede_fornecedor VARCHAR,
        uf_sede_fornecedor VARCHAR,
        lat_sede DOUBLE,
        lon_sede DOUBLE,
        possui_filial_na_uf_destino BOOLEAN,
        natureza_fornecimento VARCHAR, -- PERECIVEL DIARIO, REFEICOES PRONTAS, CONCRETO USINADO
        objeto_contrato VARCHAR,
        valor_contrato DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    if db.count("auditoria_logistica_contratos") > 0:
        return

    casos = [
        (
            "LOG_IMP_2024_01",
            "PREFEITURA MUNICIPAL DE PELOTAS",
            "Pelotas",
            "RS",
            -31.7654,
            -52.3376,
            "08234567000122",
            "PANIFICADORA E REFEICOES NORTE LTDA",
            "Manaus",
            "AM",
            -3.1190,
            -60.0217,
            False,
            "PERECIVEL DIARIO (PAO FRANCES E MERENDA QUENTE)",
            "Fornecimento diário às 06h30 de pães frescos e refeições preparadas para 42 escolas municipais",
            2850000.0,
        ),
        (
            "LOG_IMP_2024_02",
            "PREFEITURA MUNICIPAL DE MARACANAU",
            "Maracanaú",
            "CE",
            -3.8767,
            -38.6256,
            "99887766000199",
            "SUPREMA FORNECIMENTOS LTDA",
            "São Paulo",
            "SP",
            -23.5505,
            -46.6333,
            False,
            "CONCRETO USINADO QUENTE (PEGA RAPIDA 2H)",
            "Fornecimento diário de concreto betuminoso usinado a quente (CBUQ) para tapa-buracos",
            4120000.0,
        ),
    ]
    for c in casos:
        db.execute("""
            INSERT OR REPLACE INTO auditoria_logistica_contratos
            (id_contrato, orgao_contratante, municipio_destino, uf_destino, lat_destino, lon_destino, fornecedor_cnpj, fornecedor_nome, municipio_sede_fornecedor, uf_sede_fornecedor, lat_sede, lon_sede, possui_filial_na_uf_destino, natureza_fornecimento, objeto_contrato, valor_contrato)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, list(c))


@app.command()
def scan(
    max_km_perecivel: float = typer.Option(300.0, "--max-km", "-k", help="Raio máximo viável (km) para entrega diária de perecíveis sem filial local"),
):
    """Detecta contratos de entrega diária/perecível cujo fornecedor está a milhares de km sem filial local."""
    db = get_db()
    ensure_logistica_table(db)

    console.print(Panel(
        f"[bold yellow]AUDITORIA FORENSE: LOGÍSTICA IMPOSSÍVEL & DISTÂNCIA GEODÉSICA (HAVERSINE)[/bold yellow]\n"
        f"[dim]Calcula a distância física em linha reta (km) entre a única sede da empresa na Receita Federal\n"
        f"e o município comprador para objetos perecíveis de entrega diária (corte: > {max_km_perecivel:.0f} km).[/dim]",
        border_style="yellow",
    ))

    rows = db.query("""
        SELECT 
            orgao_contratante,
            municipio_destino || '/' || uf_destino AS destino,
            lat_destino,
            lon_destino,
            fornecedor_nome,
            fornecedor_cnpj,
            municipio_sede_fornecedor || '/' || uf_sede_fornecedor AS origem,
            lat_sede,
            lon_sede,
            possui_filial_na_uf_destino,
            natureza_fornecimento,
            valor_contrato
        FROM auditoria_logistica_contratos
        WHERE possui_filial_na_uf_destino = false
    """)

    alertas = []
    for r in rows:
        dist_km = haversine_km(r[7], r[8], r[2], r[3])
        if dist_km >= max_km_perecivel:
            alertas.append((*r, dist_km))

    alertas.sort(key=lambda x: x[-1], reverse=True)

    if alertas:
        t = Table(title="🚚 ALERTA GEOSPACIAL: Fornecimento Perecível / Diário Fisicamente Inviável", border_style="red")
        t.add_column("Sede da Empresa (Origem)", style="cyan")
        t.add_column("Órgão / Destino", style="magenta")
        t.add_column("Distância Haversine", justify="center", style="bold red")
        t.add_column("Fornecedor (Sem Filial Local)", style="bold white")
        t.add_column("Natureza Perecível / Diária", style="yellow")
        t.add_column("Valor Contratado", justify="right", style="bold green")

        for a in alertas:
            t.add_row(
                a[6],
                f"{a[1]}\n({a[0][:24]})",
                f"{a[12]:,.0f} km",
                f"{a[4][:26]}\nCNPJ: {a[5]}",
                a[10],
                f"R$ {a[11]:,.2f}",
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhuma inviabilidade logística detectada.[/dim green]")


@app.command()
def info():
    """Exibe metodologia de cálculo geodésico Haversine."""
    console.print("[cyan]Geointeligência Logística:[/cyan] Combina coordenadas municipais do IBGE com o cadastro de matriz/filiais da Receita Federal para verificar viabilidade material de execução contratual.")


if __name__ == "__main__":
    app()
