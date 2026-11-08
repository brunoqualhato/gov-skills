"""Forensic Risk Scoring Engine (0-100) for Public Procurement Contracts."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Calculate Forensic Risk Score (0-100) for PNCP contracts")
console = Console()


@app.command()
def scan(
    min_score: int = typer.Option(25, "--min-score", "-s", help="Score mínimo de risco para exibição"),
):
    """Calcula score de risco forense multidimensional (0-100) para todos os contratos públicos."""
    db = get_db()
    tables = db.list_tables()

    console.print(Panel("[bold red]MATRIZ FORENSE: SCORE DE RISCO LICITATÓRIO (0 A 100)[/bold red]\n"
                        "[dim]Calcula pontuação acumulada baseada em sinais fracos e evidências cruzadas de múltiplos órgãos.[/dim]",
                        border_style="red"))

    if "pncp_contratos" not in tables:
        console.print("[yellow]Tabela 'pncp_contratos' não encontrada.[/yellow]")
        return

    # Fetch contracts
    contratos = db.query("""
        SELECT 
            id_contrato,
            numero_contrato,
            cnpj_raiz_fornecedor,
            ni_fornecedor,
            nome_fornecedor,
            orgao_cnpj,
            valor_global,
            data_assinatura
        FROM pncp_contratos
        ORDER BY valor_global DESC
    """)

    if not contratos:
        console.print("[yellow]Nenhum contrato cadastrado no PNCP.[/yellow]")
        return

    scored_contracts = []

    for c in contratos:
        cid, num_pncp, cnpj_raiz, cnpj_forn, razao, orgao, valor, dt_pub = c
        score = 0
        flags = []

        # 1. Checar Simples Nacional extrapolado
        if "rfb_empresas" in tables and cnpj_raiz:
            emp = db.query("SELECT opcao_simples, capital_social, data_inicio_atividade FROM rfb_empresas WHERE cnpj_raiz = ?", [cnpj_raiz])
            if emp:
                opt_simples, cap_social, dt_abertura = emp[0]
                if opt_simples and valor and valor > 4800000:
                    score += 25
                    flags.append("Simples > R$ 4,8M (+25)")
                if cap_social and valor and valor > (cap_social * 50):
                    score += 15
                    flags.append(f"Contrato > 50x Capital (+15)")

        # 2. Checar Capacidade Operacional (CAGED funcionários)
        if "mte_caged_empresas_quadro" in tables and cnpj_raiz:
            caged = db.query("SELECT total_empregados_ativos FROM mte_caged_empresas_quadro WHERE cnpj_raiz = ?", [cnpj_raiz])
            if caged and caged[0][0] is not None:
                qtd_func = caged[0][0]
                if qtd_func <= 1 and valor and valor > 500000:
                    score += 25
                    flags.append(f"0-1 Func. no CAGED (+25)")

        # 3. Checar Dívida Ativa da União (PGFN)
        if "pgfn_divida_ativa" in tables and cnpj_raiz:
            pgfn = db.query("SELECT valor_consolidado FROM pgfn_divida_ativa WHERE cnpj_raiz = ?", [cnpj_raiz])
            if pgfn:
                score += 20
                flags.append("Inscrito na Dívida Ativa PGFN (+20)")

        # 4. Checar Sanções no TCU (Empresas inidôneas)
        if "tcu_empresas_inidoneas" in tables and cnpj_raiz:
            tcu = db.query("SELECT id_inidoneidade FROM tcu_empresas_inidoneas WHERE cnpj_raiz = ?", [cnpj_raiz])
            if tcu:
                score += 35
                flags.append("Declarada Inidônea pelo TCU (+35)")

        # 5. Checar Processos de Falência no DataJud
        if "cnj_processos_judiciais" in tables and cnpj_raiz:
            cnj = db.query("SELECT classe_processual FROM cnj_processos_judiciais WHERE cnpj_raiz_parte = ? AND classe_processual ILIKE '%FALENCIA%'", [cnpj_raiz])
            if cnj:
                score += 30
                flags.append("Processo de Falência no DataJud (+30)")

        # 6. Checar Sócios no Bolsa Família / BPC (Laranjas)
        if "rfb_socios" in tables and "cgu_beneficios_cidadao" in tables and cnpj_raiz:
            laranja = db.query("""
                SELECT b.nome_beneficiario 
                FROM rfb_socios s
                JOIN cgu_beneficios_cidadao b ON s.nome_socio = b.nome_beneficiario
                WHERE s.cnpj_raiz = ?
            """, [cnpj_raiz])
            if laranja:
                score += 30
                flags.append(f"Sócio em Benefício Social: {laranja[0][0]} (+30)")

        # 7. Checar Multas Ambientais do IBAMA
        if "ibama_autos_infracao" in tables and cnpj_raiz:
            ibama = db.query("SELECT numero_auto FROM ibama_autos_infracao WHERE cnpj_raiz = ?", [cnpj_raiz])
            if ibama:
                score += 15
                flags.append("Autuação Ambiental IBAMA (+15)")

        # Cap score at 100
        score = min(score, 100)

        if score >= min_score:
            scored_contracts.append({
                "id": cid,
                "razao": razao or "N/D",
                "cnpj": cnpj_forn or "N/D",
                "valor": valor or 0.0,
                "score": score,
                "flags": " | ".join(flags) if flags else "Nenhum sinal detectado",
            })

    scored_contracts.sort(key=lambda x: x["score"], reverse=True)

    if scored_contracts:
        t = Table(title=f"🚨 CONTRATOS CLASSIFICADOS POR SCORE DE RISCO (Corte: >= {min_score} pontos)", border_style="red")
        t.add_column("Score", justify="center", style="bold")
        t.add_column("Fornecedor", style="white")
        t.add_column("CNPJ", style="cyan")
        t.add_column("Valor Global", style="green", justify="right")
        t.add_column("Sinais de Alerta Detectados (Flags)", style="yellow")

        for sc in scored_contracts:
            score_color = "red" if sc["score"] >= 60 else ("yellow" if sc["score"] >= 35 else "cyan")
            score_badge = f"[{score_color}]{sc['score']}[/{score_color}]"
            t.add_row(
                score_badge,
                sc["razao"][:35],
                sc["cnpj"],
                f"R$ {sc['valor']:,.2f}",
                sc["flags"]
            )
        console.print(t)
    else:
        console.print(f"[green]✓ Nenhum contrato atingiu o score mínimo de risco de {min_score} pontos.[/green]")


@app.command()
def criterios():
    """Exibe a tabela de pontuação e critérios forenses do algoritmo."""
    t = Table(title="Critérios da Matriz de Risco Licitatório", border_style="cyan")
    t.add_column("Critério / Sinal Fraco", style="white")
    t.add_column("Órgão / Base", style="cyan")
    t.add_column("Pontos Adicionados", style="bold red", justify="right")

    t.add_row("Empresa Inidônea / Declarada pelo TCU", "TCU / Acórdãos", "+35 pts")
    t.add_row("Processo de Falência em Andamento", "CNJ / DataJud", "+30 pts")
    t.add_row("Sócio Beneficiário de Programa Social (Laranja)", "MDS / Bolsa Família", "+30 pts")
    t.add_row("Incompatibilidade Funcional (0-1 empregados)", "MTE / CAGED", "+25 pts")
    t.add_row("Faturamento do Simples Acima do Teto Legal", "Receita Federal", "+25 pts")
    t.add_row("Fornecedor Inscrito na Dívida Ativa da União", "PGFN / DAU", "+20 pts")
    t.add_row("Contrato Desproporcional (> 50x Capital Social)", "Receita Federal", "+15 pts")
    t.add_row("Autuação Ambiental por Desmatamento / Resíduos", "IBAMA", "+15 pts")
    console.print(t)


if __name__ == "__main__":
    app()
