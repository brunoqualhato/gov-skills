"""Forensic auditor of pharmaceutical procurement: check purchases against CMED/Anvisa mandatory legal ceilings."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Audit medicines bought by public hospitals/health departments against CMED/Anvisa regulatory price ceilings")
console = Console()


@app.command()
def semear_compras_medicamentos():
    """Popula compras de medicamentos no SUS com casos normais e superfaturados."""
    db = get_db()
    compras_med = [
        # Dipirona comprada a R$ 2,50/ampola quando o teto CMED com CAP é R$ 0,67! (Superfaturamento de +270%)
        {
            "id": "med_item_01",
            "id_ctr": "CTR_MED_01",
            "num": 1,
            "desc": "DIPIRONA SODICA 500MG/ML SOLUCAO INJETAVEL AMPOLA 2ML",
            "std": "DIPIRONA SODICA",
            "qtd": 50000.0,
            "un": "AMPOLA",
            "unit": 2.50,
            "tot": 125000.0,
            "orgao": "HOSPITAL REGIONAL MUNICIPAL",
            "uf": "MA",
            "forn": "DISTRIBUIDORA DE MEDICAMENTOS FARMA LTDA",
            "cnpj": "99887766000199",
            "dt": "2024-03-15",
        },
        # Insulina Humana comprada a R$ 85,00/frasco quando o teto CMED com CAP é R$ 32,86! (+158% superfaturada)
        {
            "id": "med_item_02",
            "id_ctr": "CTR_MED_02",
            "num": 2,
            "desc": "INSULINA HUMANA NPH 100 UI/ML FRASCO 10ML",
            "std": "INSULINA HUMANA",
            "qtd": 2000.0,
            "un": "FRASCO",
            "unit": 85.00,
            "tot": 170000.0,
            "orgao": "SECRETARIA ESTADUAL DE SAUDE",
            "uf": "BA",
            "forn": "DISTRIBUIDORA DE MEDICAMENTOS FARMA LTDA",
            "cnpj": "99887766000199",
            "dt": "2024-04-10",
        },
    ]

    import polars as pl
    records = []
    for c in compras_med:
        records.append({
            "id_item": c["id"],
            "id_contrato": c["id_ctr"],
            "numero_item": c["num"],
            "descricao_item": c["desc"],
            "descricao_padronizada": c["std"],
            "quantidade": c["qtd"],
            "unidade_medida": c["un"],
            "valor_unitario": c["unit"],
            "valor_total": c["tot"],
            "orgao_nome": c["orgao"],
            "orgao_uf": c["uf"],
            "fornecedor_nome": c["forn"],
            "fornecedor_cnpj": c["cnpj"],
            "data_compra": c["dt"],
        })
    df = pl.DataFrame(records)
    db.conn.register("tmp_med_seed", df.to_arrow())
    db.execute("""
        INSERT OR REPLACE INTO compras_itens_licitados 
        SELECT *, CURRENT_TIMESTAMP FROM tmp_med_seed
    """)
    console.print("[bold green]✓ Compras de medicamentos para auditoria semeadas com sucesso![/bold green]")


@app.command()
def scan():
    """Cruza itens comprados no SUS com a tabela oficial de teto de preços da CMED/Anvisa."""
    db = get_db()
    tables = db.list_tables()
    if "cmed_precos_medicamentos" not in tables or "compras_itens_licitados" not in tables:
        console.print("[yellow]As tabelas 'cmed_precos_medicamentos' e 'compras_itens_licitados' precisam existir.[/yellow]")
        return

    console.print(Panel("[bold red]🚨 AUDITORIA REGULATÓRIA: MEDICAMENTOS COMPRADOS ACIMA DO TETO DA CMED/ANVISA[/bold red]", border_style="red"))

    # Cruza o princípio ativo comprado com o teto da CMED (com desconto obrigatório do CAP)
    rows = db.query("""
        SELECT 
            i.descricao_item AS medicamento_comprado,
            i.orgao_nome,
            i.orgao_uf,
            i.fornecedor_nome,
            i.quantidade,
            i.valor_unitario AS preco_pago_unidade,
            c.preco_teto_governo_cap AS teto_maximo_cmed,
            ROUND(((i.valor_unitario - c.preco_teto_governo_cap) / c.preco_teto_governo_cap) * 100, 1) AS percentual_acima_do_teto,
            ROUND((i.valor_unitario - c.preco_teto_governo_cap) * i.quantidade, 2) AS superfaturamento_total
        FROM compras_itens_licitados i
        JOIN cmed_precos_medicamentos c ON LOWER(i.descricao_padronizada) = LOWER(c.substancia)
                                        OR LOWER(i.descricao_item) LIKE '%' || LOWER(c.substancia) || '%'
        WHERE i.valor_unitario > c.preco_teto_governo_cap
        ORDER BY superfaturamento_total DESC
    """)

    if rows:
        t = Table(title="⚠️ ALERTA GRAVE: Medicamentos Hospitalares Adquiridos Acima do Teto Legal Obrigatório", border_style="bold red")
        t.add_column("Medicamento", style="bold yellow")
        t.add_column("Órgão / UF", style="white")
        t.add_column("Preço Pago (Unit)", style="bold red", justify="right")
        t.add_column("Teto CMED (CAP)", style="green", justify="right")
        t.add_column("Acima do Teto", style="bold red", justify="center")
        t.add_column("Superfaturamento Estimado", style="bold red", justify="right")

        total_dano = 0.0
        for r in rows:
            total_dano += r[8]
            t.add_row(
                r[0][:30],
                f"{r[1][:20]} ({r[2]})",
                f"R$ {r[5]:,.2f}",
                f"R$ {r[6]:,.2f}",
                f"+{r[7]:,.1f}%",
                f"R$ {r[8]:,.2f}",
            )
        console.print(t)
        console.print(Panel(
            f"[bold yellow]DANO TOTAL REGULATÓRIO IDENTIFICADO:[/bold yellow] [bold red]R$ {total_dano:,.2f}[/bold red]\n"
            f"[dim]A compra de medicamentos pelo Poder Público acima do Preço Fabricante (PF) com Coeficiente de Adequação de Preços (CAP) constitui infração à Resolução CMED nº 3/2011 e superfaturamento direto em desfavor do SUS.[/dim]",
            border_style="yellow"
        ))
    else:
        console.print("[green]✓ Nenhuma compra acima do teto regulatório da CMED identificada.[/green]")


if __name__ == "__main__":
    app()
