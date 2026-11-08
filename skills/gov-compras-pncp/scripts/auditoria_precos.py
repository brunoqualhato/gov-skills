"""Statistical price auditing and overpricing (sobrepreço) detector for procurement items."""

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
from core.normalizers import parse_currency

app = typer.Typer(help="Audit unit prices in public procurement to detect overpricing and outliers (e.g. mouse a R$ 1.000)")
console = Console()


def init_itens_table():
    db = get_db()
    db.execute("""
    CREATE TABLE IF NOT EXISTS compras_itens_licitados (
        id_item VARCHAR PRIMARY KEY,
        id_contrato VARCHAR,
        numero_item INTEGER,
        descricao_item VARCHAR,
        descricao_padronizada VARCHAR,
        quantidade DOUBLE,
        unidade_medida VARCHAR,
        valor_unitario DOUBLE,
        valor_total DOUBLE,
        orgao_nome VARCHAR,
        orgao_uf VARCHAR,
        fornecedor_nome VARCHAR,
        fornecedor_cnpj VARCHAR,
        data_compra DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)


@app.command()
def semear_dados_demonstracao():
    """Popula uma base de itens licitados com casos normais e exemplos reais de sobrepreço/anomalias."""
    init_itens_table()
    db = get_db()

    # Exemplos de compras públicas com variações de mercado e outliers (como mouse a R$ 980,00)
    itens = [
        # Mouses (Preço de mercado médio: R$ 35 - R$ 60)
        {"id": "item_m1", "desc": "MOUSE OPTICO USB 1200 DPI", "std": "MOUSE OPTICO USB", "qtd": 100, "un": "UN", "unit": 38.50, "orgao": "TRIBUNAL REGIONAL FEDERAL", "uf": "DF", "forn": "INFO TECH LTDA", "cnpj": "12345678000101", "dt": "2024-03-10"},
        {"id": "item_m2", "desc": "MOUSE OPTICO COM FIO 3 BOTOES", "std": "MOUSE OPTICO USB", "qtd": 50, "un": "UN", "unit": 42.00, "orgao": "UNIVERSIDADE FEDERAL DE MINAS GERAIS", "uf": "MG", "forn": "PAPELARIA E INFORMATICA SILVA", "cnpj": "23456789000102", "dt": "2024-04-15"},
        {"id": "item_m3", "desc": "MOUSE USB PRETO PADRAO ABNT", "std": "MOUSE OPTICO USB", "qtd": 200, "un": "UN", "unit": 35.00, "orgao": "MINISTERIO DA JUSTICA", "uf": "DF", "forn": "DELTA SUPRIMENTOS LTDA", "cnpj": "34567890000103", "dt": "2024-05-20"},
        {"id": "item_m4", "desc": "MOUSE OPTICO ERGONOMICO USB", "std": "MOUSE OPTICO USB", "qtd": 80, "un": "UN", "unit": 49.90, "orgao": "INSTITUTO FEDERAL DE SAO PAULO", "uf": "SP", "forn": "COMERCIAL TECH BRASIL", "cnpj": "45678901000104", "dt": "2024-06-01"},
        {"id": "item_m5", "desc": "MOUSE USB BASICO PARA ESCRITORIO", "std": "MOUSE OPTICO USB", "qtd": 120, "un": "UN", "unit": 36.80, "orgao": "EMBRAPA", "uf": "DF", "forn": "MEGA DISTRIBUIDORA", "cnpj": "56789012000105", "dt": "2024-07-12"},
        # ⚠️ OUTLIER CRÍTICO: Mouse a R$ 980,00!
        {"id": "item_m_outlier", "desc": "MOUSE OPTICO USB PRETO PARA GABINETE", "std": "MOUSE OPTICO USB", "qtd": 150, "un": "UN", "unit": 980.00, "orgao": "PREFEITURA MUNICIPAL EXEMPLO", "uf": "MA", "forn": "SUPREMA FORNECIMENTOS LTDA", "cnpj": "99887766000199", "dt": "2024-08-05"},

        # Resmas de Papel A4 75g (Preço de mercado médio: R$ 22 - R$ 28)
        {"id": "item_p1", "desc": "PAPEL SULFITE A4 75G PCT C/ 500 FOLHAS", "std": "RESMA PAPEL A4 75G", "qtd": 500, "un": "PCT", "unit": 24.50, "orgao": "MINISTERIO DA EDUCACAO", "uf": "DF", "forn": "PAPEL & CIA DISTRIBUIDORA", "cnpj": "11223344000155", "dt": "2024-02-18"},
        {"id": "item_p2", "desc": "RESMA DE PAPEL BRANCO A4 75G/M2", "std": "RESMA PAPEL A4 75G", "qtd": 1000, "un": "PCT", "unit": 23.90, "orgao": "POLICIA RODOVIARIA FEDERAL", "uf": "PR", "forn": "PAPEL & CIA DISTRIBUIDORA", "cnpj": "11223344000155", "dt": "2024-03-22"},
        {"id": "item_p3", "desc": "PAPEL A4 REPROGRAFICO 75GR", "std": "RESMA PAPEL A4 75G", "qtd": 300, "un": "PCT", "unit": 26.00, "orgao": "IBGE REGIONAL", "uf": "RJ", "forn": "GRAFICA EXPRESS LTDA", "cnpj": "66778899000111", "dt": "2024-04-10"},
        # ⚠️ OUTLIER: Resma de papel a R$ 145,00!
        {"id": "item_p_outlier", "desc": "PAPEL A4 ESPECIAL ALTO BRILHO RESMA", "std": "RESMA PAPEL A4 75G", "qtd": 400, "un": "PCT", "unit": 145.00, "orgao": "SECRETARIA MUNICIPAL DE EDUCACAO", "uf": "PA", "forn": "NOVA ERA COMERCIO GERAL", "cnpj": "77889900000122", "dt": "2024-05-14"},

        # Café Torrado e Moído 500g (Preço médio: R$ 14 - R$ 19)
        {"id": "item_c1", "desc": "CAFE EM PO SUPERIOR VACUO 500G", "std": "CAFE TORRADO E MOIDO 500G", "qtd": 200, "un": "PCT", "unit": 16.50, "orgao": "MINISTERIO DA SAUDE", "uf": "DF", "forn": "ALIMENTOS DO BRASIL", "cnpj": "33445566000188", "dt": "2024-01-25"},
        {"id": "item_c2", "desc": "CAFE TORRADO E MOIDO PACOTE 500G", "std": "CAFE TORRADO E MOIDO 500G", "qtd": 150, "un": "PCT", "unit": 17.20, "orgao": "INSS REGIONAL", "uf": "SP", "forn": "ALIMENTOS DO BRASIL", "cnpj": "33445566000188", "dt": "2024-02-28"},
        # ⚠️ OUTLIER: Café a R$ 92,00!
        {"id": "item_c_outlier", "desc": "CAFE TRADICIONAL 500G", "std": "CAFE TORRADO E MOIDO 500G", "qtd": 300, "un": "PCT", "unit": 92.00, "orgao": "CAMARA MUNICIPAL DO INTERIOR", "uf": "BA", "forn": "DISTRIBUIDORA HORIZONTE", "cnpj": "88990011000133", "dt": "2024-06-19"},
    ]

    records = []
    for it in itens:
        records.append({
            "id_item": it["id"],
            "id_contrato": f"CTR_{it['id']}",
            "numero_item": 1,
            "descricao_item": it["desc"],
            "descricao_padronizada": it["std"],
            "quantidade": float(it["qtd"]),
            "unidade_medida": it["un"],
            "valor_unitario": float(it["unit"]),
            "valor_total": float(it["qtd"] * it["unit"]),
            "orgao_nome": it["orgao"],
            "orgao_uf": it["uf"],
            "fornecedor_nome": it["forn"],
            "fornecedor_cnpj": it["cnpj"],
            "data_compra": it["dt"],
        })

    df = pl.DataFrame(records)
    db.conn.register("tmp_itens_demo", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO compras_itens_licitados 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_itens_demo
    """)
    console.print(f"[bold green]✓ Base de itens licitados populada com {len(records)} registros para demonstração analítica![/bold green]")


@app.command()
def auditar_sobrepreco(
    termo: str = typer.Option(None, "--termo", "-t", help="Item a auditar (ex: MOUSE, PAPEL, CAFE)"),
    fator_sobrepreco: float = typer.Option(2.0, "--fator", "-f", help="Multiplicador sobre a mediana de mercado para considerar anomalia (ex: 2.0 = 100% mais caro)"),
):
    """
    Executa algoritmo estatístico de detecção de sobrepreço (outlier detection) sobre os itens licitados.
    Calcula Mediana de Mercado, Desvio, Percentil 75 e destaca compras com preços absurdos.
    """
    init_itens_table()
    db = get_db()

    # Unwrap Typer Option if called programmatically
    termo_str = str(termo) if (termo is not None and not hasattr(termo, "default")) else None
    where_filter = f"WHERE LOWER(descricao_padronizada) LIKE '%{termo_str.lower()}%'" if termo_str else ""

    # SQL analítico que calcula a mediana e IQR de cada grupo de itens padronizados
    sql = f"""
    WITH estatisticas_mercado AS (
        SELECT 
            descricao_padronizada,
            COUNT(*) AS total_compras,
            MEDIAN(valor_unitario) AS mediana_preco_mercado,
            AVG(valor_unitario) AS media_preco,
            QUANTILE_CONT(valor_unitario, 0.75) AS p75_preco,
            MIN(valor_unitario) AS menor_preco,
            MAX(valor_unitario) AS maior_preco
        FROM compras_itens_licitados
        {where_filter}
        GROUP BY descricao_padronizada
        HAVING COUNT(*) >= 2
    )
    SELECT 
        i.descricao_padronizada AS item,
        i.descricao_item AS descricao_edital,
        i.orgao_nome AS orgao,
        i.orgao_uf AS uf,
        i.fornecedor_nome AS fornecedor,
        i.quantidade,
        i.valor_unitario,
        m.mediana_preco_mercado AS preco_referencia,
        ROUND(((i.valor_unitario - m.mediana_preco_mercado) / m.mediana_preco_mercado) * 100, 1) AS percentual_acima_mediana,
        ROUND(i.valor_unitario / m.mediana_preco_mercado, 1) AS vezes_mais_caro,
        i.valor_total AS valor_pago_total,
        ROUND((i.valor_unitario - m.mediana_preco_mercado) * i.quantidade, 2) AS potencial_superfaturamento
    FROM compras_itens_licitados i
    JOIN estatisticas_mercado m ON i.descricao_padronizada = m.descricao_padronizada
    WHERE i.valor_unitario > (m.mediana_preco_mercado * {fator_sobrepreco})
    ORDER BY percentual_acima_mediana DESC;
    """

    rows = db.query(sql)

    console.print(Panel(
        f"[bold red]🚨 AUDITORIA FORENSE DE PREÇOS: DETECÇÃO DE SOBREPREÇO E ANOMALIAS[/bold red]\n"
        f"[white]Regra de Alerta:[/white] Preço Unitário > [bold yellow]{fator_sobrepreco}x a Mediana do Mercado Governamental[/bold yellow]",
        border_style="red"
    ))

    if not rows:
        console.print("[green]✓ Nenhuma anomalia crítica de sobrepreço identificada com os parâmetros informados.[/green]")
        return

    table = Table(title=f"⚠️ {len(rows)} ITENS COM FORTE INDÍCIO DE SOBREPREÇO IDENTIFICADOS", border_style="bold red")
    table.add_column("Item Padronizado", style="cyan")
    table.add_column("Órgão / UF", style="white")
    table.add_column("Fornecedor", style="yellow")
    table.add_column("Preço Pago (Unit)", style="bold red", justify="right")
    table.add_column("Mediana de Mercado", style="green", justify="right")
    table.add_column("Sobrepreço (%)", style="bold red", justify="right")
    table.add_column("Multiplicador", style="bold magenta", justify="center")
    table.add_column("Potencial Dano ao Erário", style="bold red", justify="right")

    dano_total = 0.0
    for r in rows:
        dano = r[11]
        dano_total += dano
        table.add_row(
            r[0],
            f"{r[2][:25]} ({r[3]})",
            r[4][:25],
            f"R$ {r[6]:,.2f}",
            f"R$ {r[7]:,.2f}",
            f"+{r[8]:,.1f}%",
            f"{r[9]}x",
            f"R$ {dano:,.2f}",
        )

    console.print(table)
    console.print(Panel(
        f"[bold yellow]RESUMO DO DANO POTENCIAL AO ERÁRIO (SOBREPREÇO ESTIMADO):[/bold yellow] [bold red]R$ {dano_total:,.2f}[/bold red]\n"
        f"[dim]Cálculo: (Preço Unitário Contratado - Mediana de Referência) × Quantidade Adquirida[/dim]",
        border_style="yellow"
    ))


if __name__ == "__main__":
    app()
