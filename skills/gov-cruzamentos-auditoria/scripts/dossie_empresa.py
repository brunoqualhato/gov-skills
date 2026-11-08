"""Generate a 360-degree investigative dossier for an enterprise across all government tables."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db
from core.normalizers import normalize_cnpj

app = typer.Typer(help="Generate comprehensive entity dossier cross-referencing all public tables")
console = Console()


@app.command()
def dossie(
    cnpj: str = typer.Option(..., "--cnpj", "-c", help="CNPJ da empresa a ser investigada"),
):
    """Gera dossiê investigativo completo cruzando Receita Federal, PNCP, CEAP e CGU."""
    db = get_db()
    cnpj_limpo, cnpj_fmt, cnpj_raiz = normalize_cnpj(cnpj)

    tables = db.list_tables()
    console.print(Panel(f"[bold white]DOSSIÊ INVESTIGATIVO 360º[/bold white]\n[cyan]CNPJ: {cnpj_fmt} (Raiz: {cnpj_raiz})[/cyan]", border_style="blue"))

    # 1. Dados Receita Federal
    if "rfb_empresas" in tables:
        emp = db.query("SELECT razao_social, situacao_cadastral, porte, opcao_simples, capital_social, uf, municipio, cnae_descricao FROM rfb_empresas WHERE cnpj = ? OR cnpj_raiz = ?", [cnpj_limpo, cnpj_raiz])
        if emp:
            r = emp[0]
            info = f"""[bold]Razão Social:[/bold] {r[0]}
[bold]Situação:[/bold] {r[1]} | [bold]Porte:[/bold] {r[2]} | [bold]Simples Nacional:[/bold] {'Sim' if r[3] else 'Não'}
[bold]Capital Social:[/bold] R$ {r[4]:,.2f}
[bold]Localização:[/bold] {r[6]}/{r[5]}
[bold]Atividade Principal:[/bold] {r[7]}"""
            console.print(Panel(info, title="🏢 Cadastro Receita Federal (RFB)", border_style="green"))
        else:
            console.print("[dim]Empresa não encontrada em rfb_empresas. (Dica: execute fetch_cnpj.py lookup primeiro)[/dim]")

    # 2. Quadro de Sócios (QSA)
    if "rfb_socios" in tables:
        socios = db.query("SELECT nome_socio, qualificacao_socio, cpf_cnpj_socio, faixa_etaria FROM rfb_socios WHERE cnpj_raiz = ?", [cnpj_raiz])
        if socios:
            t_socios = Table(title=f"Quadro Societário (QSA) - {len(socios)} sócios/administradores")
            t_socios.add_column("Nome", style="cyan")
            t_socios.add_column("Cargo/Qualificação", style="magenta")
            t_socios.add_column("Documento", style="yellow")
            t_socios.add_column("Faixa Etária", style="white")
            for s in socios:
                t_socios.add_row(s[0], s[1], s[2], s[3])
            console.print(t_socios)

    # 3. Contratos no PNCP
    if "pncp_contratos" in tables:
        contratos = db.query("""
            SELECT numero_contrato, orgao_nome, orgao_uf, valor_global, data_assinatura, LEFT(objeto, 50) 
            FROM pncp_contratos 
            WHERE ni_fornecedor = ? OR cnpj_raiz_fornecedor = ?
            ORDER BY valor_global DESC
        """, [cnpj_limpo, cnpj_raiz])
        if contratos:
            total_val = sum(c[3] for c in contratos)
            t_contratos = Table(title=f"Contratações Públicas (PNCP) - {len(contratos)} contratos (Total: R$ {total_val:,.2f})")
            t_contratos.add_column("Nº Contrato", style="cyan")
            t_contratos.add_column("Órgão Contratante", style="white")
            t_contratos.add_column("UF", style="dim")
            t_contratos.add_column("Valor Global", style="green")
            t_contratos.add_column("Assinatura", style="yellow")
            t_contratos.add_column("Objeto", style="dim")
            for c in contratos:
                t_contratos.add_row(c[0], c[1][:30], c[2], f"R$ {c[3]:,.2f}", str(c[4]), c[5])
            console.print(t_contratos)
        else:
            console.print("[dim]Nenhum contrato encontrado no PNCP para este CNPJ.[/dim]")

    # 4. Despesas da Cota Parlamentar (Câmara)
    if "camara_ceap_despesas" in tables:
        despesas = db.query("""
            SELECT d.nome, d.sigla_partido, d.sigla_uf, c.tipo_despesa, c.valor_liquido, c.data_documento
            FROM camara_ceap_despesas c
            JOIN camara_deputados d ON c.id_deputado = d.id_deputado
            WHERE c.cnpj_cpf_fornecedor = ? OR c.cnpj_raiz_fornecedor = ?
            ORDER BY c.valor_liquido DESC
            LIMIT 15
        """, [cnpj_limpo, cnpj_raiz])
        if despesas:
            total_ceap = sum(d[4] for d in despesas)
            t_ceap = Table(title=f"Pagamentos da Cota Parlamentar (Câmara dos Deputados) - Amostra (Total: R$ {total_ceap:,.2f})")
            t_ceap.add_column("Deputado", style="cyan")
            t_ceap.add_column("Partido/UF", style="dim")
            t_ceap.add_column("Tipo de Gasto", style="magenta")
            t_ceap.add_column("Valor", style="green")
            t_ceap.add_column("Data", style="yellow")
            for d in despesas:
                t_ceap.add_row(d[0], f"{d[1]}/{d[2]}", d[3][:30], f"R$ {d[4]:,.2f}", str(d[5]))
            console.print(t_ceap)
        else:
            console.print("[dim]Nenhum pagamento registrado na Cota Parlamentar para este fornecedor.[/dim]")

    # 5. Sanções CGU (CEIS / CNEP)
    if "cgu_sancoes" in tables:
        sancoes = db.query("""
            SELECT tipo_cadastro, orgao_sancionador, data_inicio_sancao, data_fim_sancao, motivo
            FROM cgu_sancoes
            WHERE cnpj_sancionado = ? OR cnpj_raiz = ?
        """, [cnpj_limpo, cnpj_raiz])
        if sancoes:
            t_sancoes = Table(title="⚠️ SANÇÕES ATIVAS (CGU CEIS/CNEP)", border_style="bold red")
            t_sancoes.add_column("Tipo", style="bold red")
            t_sancoes.add_column("Órgão", style="white")
            t_sancoes.add_column("Início", style="yellow")
            t_sancoes.add_column("Fim", style="yellow")
            t_sancoes.add_column("Motivo", style="dim")
            for s in sancoes:
                t_sancoes.add_row(s[0], s[1], str(s[2]), str(s[3]), s[4][:50])
            console.print(t_sancoes)
        else:
            console.print("[bold green]✓ Nenhuma sanção registrada na base da CGU.[/bold green]")


if __name__ == "__main__":
    app()
