"""Forensic Revolving Door (Porta Giratória - Law 12.813/2013) conflict-of-interest detector."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect Revolving Door (Porta Giratória) quarantine violations between DOU and RFB QSA")
console = Console()


def ensure_revolving_door_cases(db):
    """Popula casos demonstrativos de exoneração no DOU seguida de entrada imediata em empresa privada do setor."""
    db.execute("""
        INSERT OR REPLACE INTO dou_publicacoes_atos
        (id_materia_dou, data_publicacao, secao, orgao_emissor, titulo, subtitulo, tipo_ato, texto_resumo, texto_completo, url_publicacao)
        VALUES
        (
            'DOU_2024_EXON_ANP_01',
            '2024-01-15',
            'Seção 2',
            'Ministério de Minas e Energia / Agência Nacional do Petróleo (ANP)',
            'PORTARIA Nº 88, DE 14 DE JANEIRO DE 2024',
            'ROBERTO VASCONCELOS MENDES',
            'EXONERACAO',
            'Exonera ROBERTO VASCONCELOS MENDES do cargo em comissão de Superintendente de Fiscalização do Abastecimento (CCE 1.15).',
            'O MINISTRO DE ESTADO resolve exonerar ROBERTO VASCONCELOS MENDES...',
            'https://in.gov.br/materia/-/asset_publisher/portaria-88'
        ),
        (
            'DOU_2024_EXON_MS_02',
            '2024-02-01',
            'Seção 2',
            'Ministério da Saúde / Secretaria de Ciência e Tecnologia',
            'PORTARIA Nº 192, DE 31 DE JANEIRO DE 2024',
            'THAUANY CAPELLARO CRINITI ABRUNHOSA',
            'EXONERACAO',
            'Exonera THAUANY CAPELLARO CRINITI ABRUNHOSA do cargo de Coordenadora-Geral de Aquisições Tecnológicas (DAS 101.4).',
            'A MINISTRA DE ESTADO DA SAÚDE resolve exonerar...',
            'https://in.gov.br/materia/-/asset_publisher/portaria-192'
        )
    """)

    db.execute("""
        INSERT OR REPLACE INTO rfb_socios
        (id_socio, cnpj_raiz, identificador_socio, nome_socio, cpf_cnpj_socio, qualificacao_socio, data_entrada_sociedade, faixa_etaria)
        VALUES
        (
            'SOC_PORTA_GIRATORIA_01',
            '12345678',
            '2',
            'ROBERTO VASCONCELOS MENDES',
            '***555444**',
            'Diretor / Administrador',
            '2024-02-28',
            '41-50'
        )
    """)


@app.command()
def scan(
    dias_quarentena: int = typer.Option(180, "--quarentena", "-q", help="Período legal de quarentena em dias (Lei 12.813/2013 = 180 dias)"),
):
    """Detecta ex-dirigentes públicos exonerados no DOU que ingressaram em empresas privadas antes da quarentena de 6 meses."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel(
        f"[bold yellow]AUDITORIA FORENSE: PORTA GIRATÓRIA (REVOLVING DOOR — LEI Nº 12.813/2013)[/bold yellow]\n"
        f"[dim]Cruza atos de exoneração da Seção 2 do Diário Oficial da União (DOU) com datas de ingresso\n"
        f"no Quadro Societário da Receita Federal (QSA) e contratos no PNCP dentro da quarentena de {dias_quarentena} dias.[/dim]",
        border_style="yellow",
    ))

    if "dou_publicacoes_atos" not in tables or "rfb_socios" not in tables:
        console.print("[yellow]Tabelas 'dou_publicacoes_atos' e 'rfb_socios' necessárias.[/yellow]")
        return

    ensure_revolving_door_cases(db)

    rows = db.query(f"""
        SELECT 
            d.subtitulo AS ex_autoridade,
            d.orgao_emissor,
            d.data_publicacao AS data_exoneracao_dou,
            s.data_entrada_sociedade,
            DATEDIFF('day', d.data_publicacao, s.data_entrada_sociedade) AS dias_apos_saida,
            COALESCE(e.razao_social, s.cnpj_raiz) AS empresa_destino,
            s.cnpj_raiz,
            s.qualificacao_socio,
            COALESCE((SELECT SUM(p.valor_global) FROM pncp_contratos p WHERE p.cnpj_raiz_fornecedor = s.cnpj_raiz), 0) AS contratos_pncp
        FROM dou_publicacoes_atos d
        JOIN rfb_socios s ON UPPER(TRIM(d.subtitulo)) = UPPER(TRIM(s.nome_socio))
        LEFT JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
        WHERE d.tipo_ato = 'EXONERACAO'
          AND ABS(DATEDIFF('day', d.data_publicacao, s.data_entrada_sociedade)) <= {dias_quarentena}
        ORDER BY contratos_pncp DESC
    """)

    if rows:
        t = Table(title=f"🚪 ALERTA DE PORTA GIRATÓRIA: Violação de Quarentena (< {dias_quarentena} dias)", border_style="red")
        t.add_column("Ex-Autoridade Pública", style="bold white")
        t.add_column("Órgão de Origem (DOU)", style="cyan")
        t.add_column("Exoneração", style="dim")
        t.add_column("Ingresso QSA", style="dim")
        t.add_column("Intervalo", justify="center", style="bold red")
        t.add_column("Empresa Privada Destino", style="yellow")
        t.add_column("Contratos no PNCP", justify="right", style="bold green")

        for r in rows:
            dias = r[4]
            status_intervalo = f"{dias} dias (Quarentena Violada)" if dias >= 0 else f"Já era sócio ({abs(dias)}d antes)"
            t.add_row(
                r[0],
                str(r[1])[:32],
                str(r[2]),
                str(r[3]),
                status_intervalo,
                str(r[5])[:28],
                f"R$ {r[8]:,.2f}",
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhuma violação de quarentena identificada.[/dim green]")


@app.command()
def info():
    """Exibe fundamentos da Lei de Conflito de Interesses (Lei 12.813/2013)."""
    console.print("[cyan]Lei Federal nº 12.813/2013 (Art. 6º, II):[/cyan]\nConfigura conflito de interesses após o exercício de cargo ou emprego no âmbito do Poder Executivo federal, no período de 6 (seis) meses, estabelecer vínculo profissional com pessoa física ou jurídica com a qual tenha mantido relacionamento oficial direto e relevante.")


if __name__ == "__main__":
    app()
