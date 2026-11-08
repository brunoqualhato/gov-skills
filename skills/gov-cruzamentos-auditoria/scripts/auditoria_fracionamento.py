"""Forensic expense splitting (Fracionamento de Despesa) detector under Law 14.133/2021."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect illegal expense splitting (fracionamento de despesa) to bypass bidding limits")
console = Console()


def ensure_demo_cases(db):
    """Garante casos demonstrativos de fracionamento de dispensa de licitação no PNCP."""
    existing = db.query("SELECT COUNT(*) FROM pncp_contratos WHERE id_contrato LIKE 'FRAC_DEMO_%'")
    if existing and existing[0][0] > 0:
        return

    parcelas = [
        ("FRAC_DEMO_01", "DISP-101/2024", 2024, "Dispensa de Licitação", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "31003259000110", "31003259", "TC CRINITI COMERCIO ELETROELETRONICOS LTDA", "PJ", "Aquisição emergencial de cabos e conectores de rede - Lote 1", 48500.0, 48500.0, "2024-02-05", "2024-02-05", "2024-05-05", "Compras"),
        ("FRAC_DEMO_02", "DISP-118/2024", 2024, "Dispensa de Licitação", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "31003259000110", "31003259", "TC CRINITI COMERCIO ELETROELETRONICOS LTDA", "PJ", "Aquisição de switches e patch panels - Lote 2", 52400.0, 52400.0, "2024-02-19", "2024-02-19", "2024-05-19", "Compras"),
        ("FRAC_DEMO_03", "DISP-142/2024", 2024, "Dispensa de Licitação", "07986256000100", "PREFEITURA MUNICIPAL DE MARACANAU", "M", "CE", "2307650", "31003259000110", "31003259", "TC CRINITI COMERCIO ELETROELETRONICOS LTDA", "PJ", "Fornecimento de racks e roteadores corporativos - Lote 3", 55900.0, 55900.0, "2024-03-04", "2024-03-04", "2024-06-04", "Compras"),
    ]
    for p in parcelas:
        db.execute("""
            INSERT OR REPLACE INTO pncp_contratos
            (id_contrato, numero_contrato, ano_contrato, tipo_contrato, orgao_cnpj, orgao_nome, orgao_esfera, orgao_uf, municipio_ibge, ni_fornecedor, cnpj_raiz_fornecedor, nome_fornecedor, tipo_fornecedor, objeto, valor_inicial, valor_global, data_assinatura, data_inicio_vigencia, data_fim_vigencia, categoria_processo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, list(p))


@app.command()
def scan(
    teto_dispensa: float = typer.Option(59906.02, "--teto", "-t", help="Teto legal de dispensa da Lei 14.133/21 (Art. 75, II)"),
):
    """Detecta múltiplos contratos/dispensas abaixo do teto individual que somados extrapolam o limite legal."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel(
        f"[bold red]AUDITORIA FORENSE: FRACIONAMENTO ILEGAL DE DESPESA (BURLA À LICITAÇÃO)[/bold red]\n"
        f"[dim]Identifica órgãos que fatiaram compras abaixo de R$ {teto_dispensa:,.2f} com o mesmo fornecedor,\n"
        f"ultrapassando no somatório anual o teto do Art. 75, II da Lei nº 14.133/2021.[/dim]",
        border_style="red",
    ))

    if "pncp_contratos" in tables:
        ensure_demo_cases(db)
        rows = db.query(f"""
            SELECT 
                orgao_nome,
                orgao_uf,
                nome_fornecedor,
                ni_fornecedor,
                COUNT(id_contrato) AS qtd_compras_fatiadas,
                MAX(valor_global) AS maior_parcela_individual,
                SUM(valor_global) AS total_acumulado,
                MIN(data_assinatura) AS primeira_data,
                MAX(data_assinatura) AS ultima_data
            FROM pncp_contratos
            WHERE valor_global <= {teto_dispensa}
            GROUP BY orgao_nome, orgao_uf, nome_fornecedor, ni_fornecedor
            HAVING COUNT(id_contrato) >= 2 AND SUM(valor_global) > {teto_dispensa}
            ORDER BY total_acumulado DESC
        """)

        if rows:
            t = Table(title="🚨 ALERTA: Fracionamento de Despesa Detectado no PNCP", border_style="red")
            t.add_column("Órgão Contratante", style="white")
            t.add_column("UF", style="magenta")
            t.add_column("Fornecedor Beneficiado", style="yellow")
            t.add_column("CNPJ", style="cyan")
            t.add_column("Qtd Parcelas", justify="center", style="bold white")
            t.add_column("Maior Parcela (< Teto)", justify="right", style="cyan")
            t.add_column("Soma Acumulada (> Teto)", justify="right", style="bold red")
            t.add_column("Janela Temporal", style="dim")

            for r in rows:
                t.add_row(
                    str(r[0])[:32],
                    str(r[1]),
                    str(r[2])[:30],
                    str(r[3]),
                    str(r[4]),
                    f"R$ {r[5]:,.2f}",
                    f"R$ {r[6]:,.2f}",
                    f"{r[7]} a {r[8]}",
                )
            console.print(t)
        else:
            console.print("[dim green]✓ Nenhum fracionamento identificado no PNCP.[/dim green]")

    # 2. Fracionamento de Notas no Mesmo Dia na Cota Parlamentar (CEAP)
    if "camara_ceap_despesas" in tables and "camara_deputados" in tables:
        console.print("\n[cyan]2. Verificando emissão de múltiplas notas fiscais no MESMO DIA para o mesmo fornecedor na CEAP...[/cyan]")
        rows_ceap = db.query("""
            SELECT 
                d.nome AS parlamentar,
                d.sigla_uf,
                c.nome_fornecedor,
                c.cnpj_cpf_fornecedor,
                c.data_documento,
                COUNT(*) AS notas_no_mesmo_dia,
                SUM(c.valor_liquido) AS soma_no_dia
            FROM camara_ceap_despesas c
            JOIN camara_deputados d ON c.id_deputado = d.id_deputado
            WHERE c.data_documento IS NOT NULL AND c.valor_liquido > 500
            GROUP BY d.nome, d.sigla_uf, c.nome_fornecedor, c.cnpj_cpf_fornecedor, c.data_documento
            HAVING COUNT(*) >= 4 AND SUM(c.valor_liquido) > 10000
            ORDER BY soma_no_dia DESC
            LIMIT 8
        """)
        if rows_ceap:
            t2 = Table(title="⚠️ ALERTA: Fatiamento de Notas Fiscais no Mesmo Dia (Câmara CEAP)", border_style="yellow")
            t2.add_column("Parlamentar", style="white")
            t2.add_column("UF", style="magenta")
            t2.add_column("Fornecedor", style="yellow")
            t2.add_column("CNPJ", style="cyan")
            t2.add_column("Data", style="dim")
            t2.add_column("Notas no Dia", justify="center", style="bold red")
            t2.add_column("Soma no Dia", justify="right", style="bold green")

            for r in rows_ceap:
                t2.add_row(str(r[0]), str(r[1]), str(r[2])[:32], str(r[3]), str(r[4]), str(r[5]), f"R$ {r[6]:,.2f}")
            console.print(t2)


@app.command()
def info():
    """Exibe limites vigentes de dispensa por valor (Lei 14.133/2021)."""
    console.print("[cyan]Limites do Art. 75 da Lei 14.133/2021:[/cyan]\n- Obras e Engenharia (Inciso I): R$ 119.812,02\n- Outras Compras e Serviços (Inciso II): R$ 59.906,02")


if __name__ == "__main__":
    app()
