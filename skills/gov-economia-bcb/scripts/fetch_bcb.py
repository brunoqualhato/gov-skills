"""Script to fetch economic series and Focus market expectations from Banco Central do Brasil."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import parse_currency, parse_date

app = typer.Typer(help="Fetch BCB economic series and Olinda OData")
console = Console()

SERIES_MAP = {
    432: ("Meta Selic (% a.a.)", "% a.a."),
    11: ("Taxa Selic Diária", "% a.d."),
    12: ("Taxa CDI Diária", "% a.a."),
    433: ("IPCA Mensal", "% m/m"),
    189: ("IGP-M Mensal", "% m/m"),
    1: ("Taxa de Câmbio - Dólar (venda)", "R$ / US$"),
    3545: ("Reservas Internacionais", "US$ milhões"),
}


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS bcb_series_temporais (
        codigo_serie INTEGER,
        nome_serie VARCHAR,
        data_referencia DATE,
        valor DOUBLE,
        unidade VARCHAR,
        PRIMARY KEY(codigo_serie, data_referencia)
    );

    CREATE TABLE IF NOT EXISTS bcb_expectativas_focus (
        indicador VARCHAR,
        data_referencia DATE,
        data_pesquisa DATE,
        mediana DOUBLE,
        media DOUBLE,
        desvio_padrao DOUBLE,
        minimo DOUBLE,
        maximo DOUBLE,
        numero_respondentes INTEGER,
        PRIMARY KEY(indicador, data_referencia, data_pesquisa)
    );
    """)


@app.command()
def series(
    codigo: int = typer.Option(432, "--codigo", "-c", help="Código da série SGS (ex: 432=Selic, 433=IPCA, 1=Dólar)"),
    anos: int = typer.Option(2, "--anos", "-a", help="Quantidade de anos retroativos"),
):
    """Coleta o histórico de uma série temporal do SGS/BCB."""
    init_tables()
    db = get_db()

    nome_serie, unidade = SERIES_MAP.get(codigo, (f"Série SGS {codigo}", "unidade"))
    
    # BCB aceita janela de até 10 anos usando dataInicial e dataFinal (DD/MM/AAAA)
    from datetime import datetime, timedelta
    dt_fim = datetime.now()
    dt_ini = dt_fim - timedelta(days=anos * 365)
    
    dt_ini_str = dt_ini.strftime("%d/%m/%Y")
    dt_fim_str = dt_fim.strftime("%d/%m/%Y")

    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={dt_ini_str}&dataFinal={dt_fim_str}"

    console.print(f"[bold cyan]🔍 Baixando série SGS {codigo} ({nome_serie}) de {dt_ini_str} a {dt_fim_str}...[/bold cyan]")
    with GovHttpClient() as client:
        try:
            data = client.get_json(url)
        except Exception as e:
            console.print(f"[red]Erro ao buscar dados do BCB: {e}[/red]")
            return

    if not data:
        console.print("[yellow]Nenhum dado retornado para a série.[/yellow]")
        return

    records = []
    for item in data:
        d = parse_date(item.get("data"))
        v = parse_currency(item.get("valor"))
        if d:
            records.append({
                "codigo_serie": codigo,
                "nome_serie": nome_serie,
                "data_referencia": d,
                "valor": v,
                "unidade": unidade,
            })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_bcb_series", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO bcb_series_temporais 
            SELECT * FROM tmp_bcb_series
        """)
        total = db.count("bcb_series_temporais")
        console.print(f"[bold green]✓ {len(records)} registros gravados da série {nome_serie}. Total na tabela: {total}[/bold green]")


@app.command()
def series_fundamentais():
    """Baixa em lote as séries fundamentais da economia brasileira (Selic, IPCA, CDI, Dólar, Reservas)."""
    init_tables()
    for cod in [432, 12, 433, 1, 3545]:
        series(codigo=cod, ultimos=100)


@app.command()
def focus(
    top: int = typer.Option(100, "--top", "-t", help="Quantidade de registros a buscar"),
):
    """Coleta as últimas expectativas mensais do mercado financeiro (Relatório Focus)."""
    init_tables()
    db = get_db()

    url = f"https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativaMercadoMensais?$top={top}&$orderby=Data desc&$format=json"
    console.print("[bold cyan]🔍 Baixando projeções de mercado do Relatório Focus (Olinda OData)...[/bold cyan]")

    with GovHttpClient() as client:
        try:
            res = client.get_json(url)
        except Exception as e:
            console.print(f"[red]Erro ao consultar API Olinda: {e}[/red]")
            return

    items = res.get("value", []) if isinstance(res, dict) else []
    if not items:
        console.print("[yellow]Nenhum dado retornado da API Focus.[/yellow]")
        return

    records = []
    for item in items:
        dt_ref = parse_date(item.get("DataReferencia"))
        dt_pesq = parse_date(item.get("Data"))
        if dt_ref and dt_pesq:
            records.append({
                "indicador": item.get("Indicador", ""),
                "data_referencia": dt_ref,
                "data_pesquisa": dt_pesq,
                "mediana": parse_currency(item.get("Mediana")),
                "media": parse_currency(item.get("Media")),
                "desvio_padrao": parse_currency(item.get("DesvioPadrao")),
                "minimo": parse_currency(item.get("Minimo")),
                "maximo": parse_currency(item.get("Maximo")),
                "numero_respondentes": int(item.get("numeroRespondentes") or 0),
            })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_bcb_focus", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO bcb_expectativas_focus 
            SELECT * FROM tmp_bcb_focus
        """)
        total = db.count("bcb_expectativas_focus")
        console.print(f"[bold green]✓ {len(records)} projeções do Focus gravadas no DuckDB. Total: {total}[/bold green]")


if __name__ == "__main__":
    app()
