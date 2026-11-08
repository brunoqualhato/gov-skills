"""Forensic incompatible workload and illegal multiple public jobs (Acúmulo de Cargos / Super-Servidor) detector."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add repository root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from core.db import get_db

app = typer.Typer(help="Detect impossible weekly workloads and illegal accumulation of public jobs")
console = Console()


def ensure_vinculos_table(db):
    """Inicializa e popula vínculos funcionais multi-órgãos (SIAPE, CNES/SUS, Educação Municipal e CLT)."""
    db.execute("""
    CREATE TABLE IF NOT EXISTS auditoria_vinculos_profissionais (
        id_vinculo VARCHAR PRIMARY KEY,
        cpf_mascarado VARCHAR,
        nome_profissional VARCHAR,
        origem_base VARCHAR, -- SIAPE, CNES_SUS, CENSO_ESCOLAR, CAGED_CLT
        orgao_ou_unidade VARCHAR,
        municipio VARCHAR,
        uf VARCHAR,
        cargo_funcao VARCHAR,
        regime_juridico VARCHAR, -- DEDICACAO EXCLUSIVA, ESTATUTARIO 40H, PLANTONISTA SUS, CLT
        carga_horaria_semanal INTEGER,
        remuneracao_mensal DOUBLE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cnt = db.count("auditoria_vinculos_profissionais")
    if cnt > 0:
        return

    vinculos = [
        # Caso 1: Médico com 112h semanais em 3 cidades distintas (SP, RJ e CE)
        ("VINC_01", "***.444.555-**", "DR. HENRIQUE ALMEIDA PRADO", "SIAPE_FEDERAL", "HOSPITAL FEDERAL DE BONSUCESSO", "Rio de Janeiro", "RJ", "MEDICO CLINICO", "ESTATUTARIO 40H", 40, 18500.0),
        ("VINC_02", "***.444.555-**", "DR. HENRIQUE ALMEIDA PRADO", "CNES_DATASUS", "HOSPITAL MUNICIPAL SOUZA AGUIAR", "Rio de Janeiro", "RJ", "MEDICO PLANTONISTA UTI", "PLANTONISTA SUS", 36, 14200.0),
        ("VINC_03", "***.444.555-**", "DR. HENRIQUE ALMEIDA PRADO", "CNES_DATASUS", "HOSPITAL MUNICIPAL DE MARACANAU", "Maracanaú", "CE", "MEDICO CIRURGIAO", "CONTRATO TEMPORARIO", 36, 16000.0),
        # Caso 2: Professor Federal com Dedicação Exclusiva (DE) acumulando outros 2 vínculos
        ("VINC_04", "***.888.999-**", "CARLOS EDUARDO NOGUEIRA", "SIAPE_FEDERAL", "UNIVERSIDADE FEDERAL DO CEARA", "Fortaleza", "CE", "PROFESSOR DO MAGISTERIO SUPERIOR", "DEDICACAO EXCLUSIVA (DE)", 40, 22400.0),
        ("VINC_05", "***.888.999-**", "CARLOS EDUARDO NOGUEIRA", "INEP_REDE_MUNICIPAL", "EEFM CORONEL JOAO PAULO", "Maracanaú", "CE", "PROFESSOR ENSINO FUNDAMENTAL", "ESTATUTARIO", 40, 6800.0),
        ("VINC_06", "***.888.999-**", "CARLOS EDUARDO NOGUEIRA", "CAGED_PRIVADO", "ALFA ENGENHARIA E CONSTRUCOES LTDA", "São Paulo", "SP", "CONSULTOR TECNICO", "CLT", 20, 9500.0),
    ]

    for v in vinculos:
        db.execute("""
            INSERT OR REPLACE INTO auditoria_vinculos_profissionais
            (id_vinculo, cpf_mascarado, nome_profissional, origem_base, orgao_ou_unidade, municipio, uf, cargo_funcao, regime_juridico, carga_horaria_semanal, remuneracao_mensal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, list(v))


@app.command()
def scan(
    max_horas: int = typer.Option(60, "--max-horas", "-h", help="Limite máximo constitucional/operacional de horas semanais"),
):
    """Identifica servidores e profissionais acumulando cargas horárias impossíveis (> 60h/semana) ou violando Dedicação Exclusiva."""
    db = get_db()
    ensure_vinculos_table(db)

    console.print(Panel(
        f"[bold red]AUDITORIA FORENSE: SUPER-SERVIDORES & JORNADA DE TRABALHO IMPOSSÍVEL[/bold red]\n"
        f"[dim]Cruza SIAPE + CNES/DataSUS + Censo Escolar + CAGED para detectar acúmulo ilegal de cargos\n"
        f"(CF/88 Art. 37, XVI), violação de Dedicação Exclusiva e jornadas > {max_horas}h/semana em cidades distintas.[/dim]",
        border_style="red",
    ))

    rows = db.query(f"""
        SELECT 
            nome_profissional,
            cpf_mascarado,
            COUNT(id_vinculo) AS qtd_vinculos,
            SUM(carga_horaria_semanal) AS total_horas_semanais,
            COUNT(DISTINCT municipio || '/' || uf) AS qtd_cidades_distintas,
            SUM(remuneracao_mensal) AS renda_mensal_acumulada,
            STRING_AGG(origem_base || ': ' || orgao_ou_unidade || ' (' || municipio || '/' || uf || ' - ' || CAST(carga_horaria_semanal AS VARCHAR) || 'h)', ' | ') AS detalhe_vinculos,
            MAX(CASE WHEN regime_juridico ILIKE '%DEDICACAO EXCLUSIVA%' THEN 1 ELSE 0 END) AS tem_dedicacao_exclusiva
        FROM auditoria_vinculos_profissionais
        GROUP BY nome_profissional, cpf_mascarado
        HAVING SUM(carga_horaria_semanal) > {max_horas} OR (MAX(CASE WHEN regime_juridico ILIKE '%DEDICACAO EXCLUSIVA%' THEN 1 ELSE 0 END) = 1 AND COUNT(id_vinculo) > 1)
        ORDER BY total_horas_semanais DESC
    """)

    if rows:
        t = Table(title="🚨 ALERTA: Acúmulo Ilegal de Cargos / Carga Horária Fisicamente Incompatível", border_style="red")
        t.add_column("Profissional / Servidor", style="bold white")
        t.add_column("CPF", style="cyan")
        t.add_column("Vínculos", justify="center", style="yellow")
        t.add_column("Carga Semanal", justify="right", style="bold red")
        t.add_column("Cidades", justify="center", style="magenta")
        t.add_column("Violação DE?", justify="center", style="bold yellow")
        t.add_column("Renda Acumulada", justify="right", style="bold green")
        t.add_column("Detalhamento das Lotacões Simultâneas", style="white")

        for r in rows:
            de_flag = "SIM (ILEGAL)" if r[7] == 1 else "Não"
            t.add_row(
                r[0],
                r[1],
                str(r[2]),
                f"{r[3]}h / sem",
                str(r[4]),
                de_flag,
                f"R$ {r[5]:,.2f}",
                r[6],
            )
        console.print(t)
    else:
        console.print("[dim green]✓ Nenhum acúmulo ilegal de jornada identificado.[/dim green]")


@app.command()
def info():
    """Exibe regras constitucionais de acúmulo de cargos (Art. 37, XVI da CF/88)."""
    console.print("[cyan]Regras de Acúmulo (Art. 37, XVI CF/88 e Jurisprudência TCU):[/cyan]\n- Máximo de 2 cargos (2 de professor, 1 de professor + 1 técnico, ou 2 de profissionais de saúde)\n- Compatibilidade de horários exigida (teto operacional de 60h semanais pelo TCU)\n- Proibido qualquer segundo vínculo para regime de Dedicação Exclusiva (DE).")


if __name__ == "__main__":
    app()
