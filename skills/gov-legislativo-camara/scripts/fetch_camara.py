"""Fetch Federal Deputies and CEAP (Cota Parlamentar) expenses from Câmara dos Deputados into DuckDB."""

import sys
from pathlib import Path
import typer
from rich.console import Console
import polars as pl

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.client import GovHttpClient
from core.db import get_db
from core.normalizers import normalize_cnpj, parse_currency, parse_date

app = typer.Typer(help="Fetch Deputies and CEAP expenses from Brazilian Chamber of Deputies")
console = Console()

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"


def init_tables():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS camara_deputados (
        id_deputado INTEGER PRIMARY KEY,
        nome VARCHAR,
        sigla_partido VARCHAR,
        sigla_uf VARCHAR,
        id_legislatura INTEGER,
        url_foto VARCHAR,
        email VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS camara_ceap_despesas (
        id_despesa VARCHAR PRIMARY KEY,
        id_deputado INTEGER,
        ano INTEGER,
        mes INTEGER,
        tipo_despesa VARCHAR,
        data_documento DATE,
        valor_documento DOUBLE,
        valor_glosa DOUBLE,
        valor_liquido DOUBLE,
        nome_fornecedor VARCHAR,
        cnpj_cpf_fornecedor VARCHAR,
        cnpj_raiz_fornecedor VARCHAR,
        num_ressarcimento VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def deputados():
    """Baixa a lista completa de deputados em exercício na legislatura atual."""
    init_tables()
    db = get_db()

    url = f"{CAMARA_BASE_URL}/deputados?itens=1000&ordem=ASC&ordenarPor=nome"
    console.print("[bold cyan]🔍 Baixando relação de deputados da Câmara dos Deputados...[/bold cyan]")

    with GovHttpClient() as client:
        try:
            res = client.get_json(url)
        except Exception as e:
            console.print(f"[red]Erro ao buscar deputados: {e}[/red]")
            return

    dados = res.get("dados", []) if isinstance(res, dict) else []
    if not dados:
        console.print("[yellow]Nenhum deputado retornado.[/yellow]")
        return

    records = []
    for d in dados:
        records.append({
            "id_deputado": int(d.get("id")),
            "nome": d.get("nome", ""),
            "sigla_partido": d.get("siglaPartido", ""),
            "sigla_uf": d.get("siglaUf", ""),
            "id_legislatura": int(d.get("idLegislatura") or 0),
            "url_foto": d.get("urlFoto", ""),
            "email": d.get("email", ""),
        })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_camara_dep", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO camara_deputados 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_camara_dep
        """)
        total = db.count("camara_deputados")
        console.print(f"[bold green]✓ {len(records)} deputados ingeridos no DuckDB. Total na tabela: {total}[/bold green]")


@app.command()
def despesas_lote(
    ano: int = typer.Option(2024, "--ano", "-a", help="Ano das despesas para download em lote"),
):
    """Baixa o arquivo em lote completo de despesas da CEAP do ano (muito mais rápido e completo)."""
    import zipfile
    import io
    init_tables()
    db = get_db()

    url = f"https://www.camara.leg.br/cotas/Ano-{ano}.csv.zip"
    console.print(f"[bold cyan]🔍 Baixando pacote anual consolidado da CEAP ({ano})...[/bold cyan]")

    with GovHttpClient() as client:
        try:
            res = client.client.get(url, timeout=60.0)
            res.raise_for_status()
        except Exception as e:
            console.print(f"[red]Erro ao baixar arquivo da CEAP: {e}[/red]")
            return

    console.print("[cyan]Descompactando e lendo CSV...[/cyan]")
    with zipfile.ZipFile(io.BytesIO(res.content)) as z:
        filename = [n for n in z.namelist() if n.endswith(".csv")][0]
        with z.open(filename) as f:
            # Polars reads semicolon-delimited CSV with Latin-1 or UTF-8
            df_raw = pl.read_csv(f.read(), separator=";", ignore_errors=True)

    console.print(f"[cyan]Processando {len(df_raw)} despesas brutas...[/cyan]")
    
    # Mapear e normalizar colunas
    # Colunas padrão da CEAP: ideCadastro, txNomeParlamentar, sgPartido, sgUF, numAno, numMes, txtDescricao, datEmissao, vlrLiquido, txtFornecedor, txtCNPJCPF
    records = []
    for row in df_raw.iter_rows(named=True):
        cnpj_cpf = str(row.get("txtCNPJCPF") or "")
        cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj_cpf)
        
        id_dep = int(row.get("ideCadastro") or 0) if str(row.get("ideCadastro") or "").isdigit() else 0
        id_despesa = f"{id_dep}_{ano}_{row.get('numSubCota', '')}_{row.get('numDocumento', '')}_{len(records)}"

        records.append({
            "id_despesa": id_despesa,
            "id_deputado": id_dep,
            "ano": int(row.get("numAno") or ano),
            "mes": int(row.get("numMes") or 0),
            "tipo_despesa": str(row.get("txtDescricao") or ""),
            "data_documento": parse_date(str(row.get("datEmissao") or "")),
            "valor_documento": parse_currency(row.get("vlrDocumento")),
            "valor_glosa": parse_currency(row.get("vlrGlosa")),
            "valor_liquido": parse_currency(row.get("vlrLiquido")),
            "nome_fornecedor": str(row.get("txtFornecedor") or ""),
            "cnpj_cpf_fornecedor": cnpj_limpo or cnpj_cpf,
            "cnpj_raiz_fornecedor": cnpj_raiz,
            "num_ressarcimento": str(row.get("numRessarcimento") or ""),
        })

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_camara_ceap_bulk", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO camara_ceap_despesas 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_camara_ceap_bulk
        """)
        total = db.count("camara_ceap_despesas")
        console.print(f"[bold green]✨ Sucesso absoluto! {len(records)} despesas da CEAP ingeridas no DuckDB. Total: {total}[/bold green]")


@app.command()
def despesas(
    ano: int = typer.Option(2026, "--ano", "-a", help="Ano das despesas"),
    mes: int = typer.Option(None, "--mes", "-m", help="Mês específico das despesas (1 a 12)"),
    limite_deputados: int = typer.Option(10, "--limite-deputados", "-l", help="Quantidade de deputados a processar"),
):
    """Baixa despesas da cota parlamentar (CEAP) dos deputados."""
    init_tables()
    db = get_db()

    # Busca deputados cadastrados
    deputados_rows = db.query(f"SELECT id_deputado, nome FROM camara_deputados LIMIT {limite_deputados}")
    if not deputados_rows:
        console.print("[yellow]Nenhum deputado encontrado na tabela. Executando coleta de deputados primeiro...[/yellow]")
        deputados()
        deputados_rows = db.query(f"SELECT id_deputado, nome FROM camara_deputados LIMIT {limite_deputados}")

    records = []
    console.print(f"[bold cyan]🔍 Baixando despesas CEAP de {len(deputados_rows)} deputados (ano {ano})...[/bold cyan]")

    with GovHttpClient() as client:
        for id_dep, nome_dep in deputados_rows:
            url = f"{CAMARA_BASE_URL}/deputados/{id_dep}/despesas?ano={ano}&itens=100"
            if mes:
                url += f"&mes={mes}"

            try:
                res = client.get_json(url)
            except Exception as e:
                console.print(f"[yellow]Aviso ao buscar despesas de {nome_dep}: {e}[/yellow]")
                continue

            itens = res.get("dados", []) if isinstance(res, dict) else []
            for item in itens:
                cnpj_cpf_raw = item.get("cnpjCpfFornecedor", "")
                cnpj_limpo, _, cnpj_raiz = normalize_cnpj(cnpj_cpf_raw)
                
                # Gera id único da despesa
                id_despesa = f"{id_dep}_{ano}_{item.get('numDocumento', '')}_{item.get('codDocumento', '')}_{len(records)}"

                records.append({
                    "id_despesa": id_despesa,
                    "id_deputado": id_dep,
                    "ano": int(item.get("ano") or ano),
                    "mes": int(item.get("mes") or 0),
                    "tipo_despesa": item.get("tipoDespesa", ""),
                    "data_documento": parse_date(item.get("dataDocumento")),
                    "valor_documento": parse_currency(item.get("valorDocumento")),
                    "valor_glosa": parse_currency(item.get("valorGlosa")),
                    "valor_liquido": parse_currency(item.get("valorLiquido")),
                    "nome_fornecedor": item.get("nomeFornecedor", ""),
                    "cnpj_cpf_fornecedor": cnpj_limpo or cnpj_cpf_raw,
                    "cnpj_raiz_fornecedor": cnpj_raiz,
                    "num_ressarcimento": str(item.get("numRessarcimento") or ""),
                })

            console.print(f"[dim]✓ {nome_dep}: {len(itens)} despesas coletadas.[/dim]")

    if records:
        df = pl.DataFrame(records)
        db.conn.register("tmp_camara_ceap", df.to_arrow())
        db.execute("""
            INSERT OR REPLACE INTO camara_ceap_despesas 
            SELECT *, CURRENT_TIMESTAMP FROM tmp_camara_ceap
        """)
        total = db.count("camara_ceap_despesas")
        console.print(f"[bold green]✨ Sucesso! {len(records)} despesas da CEAP ingeridas no DuckDB. Total: {total}[/bold green]")
    else:
        console.print("[yellow]Nenhuma despesa encontrada para os parâmetros informados.[/yellow]")


if __name__ == "__main__":
    app()
