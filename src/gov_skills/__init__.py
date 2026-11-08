"""Main entry point and CLI for gov-skills."""

import sys
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure base repo is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.db import get_db
from core.config import settings

app = typer.Typer(help="gov-skills: Plataforma de Inteligência e Domínio dos Dados Públicos do Governo Federal")
console = Console()


@app.command()
def info():
    """Exibe o status do Data Lakehouse DuckDB e o volume de dados acumulado."""
    db = get_db()
    tables = db.list_tables()
    db_size_mb = (settings.DB_PATH.stat().st_size / (1024 * 1024)) if settings.DB_PATH.exists() else 0.0

    console.print(Panel(
        f"[bold white]🏛️ GOV-SKILLS: DATA LAKEHOUSE CENTRAL[/bold white]\n"
        f"[cyan]Arquivo do Banco:[/cyan] {settings.DB_PATH}\n"
        f"[cyan]Tamanho em Disco:[/cyan] {db_size_mb:.2f} MB\n"
        f"[cyan]Tabelas Ativas:[/cyan] {len(tables)}",
        border_style="green",
    ))

    if tables:
        t = Table(title="Tabelas Armazenadas no DuckDB")
        t.add_column("Tabela", style="cyan")
        t.add_column("Total de Registros", style="green", justify="right")
        t.add_column("Domínio Governamental", style="yellow")

        domain_map = {
            "ibge_municipios": "IBGE (Malha Territorial)",
            "pncp_contratos": "PNCP / Compras.gov.br",
            "bcb_series_temporais": "Banco Central (SGS Macroeconomia)",
            "bcb_expectativas_focus": "Banco Central (Relatório Focus)",
            "camara_deputados": "Câmara dos Deputados (Parlamentares)",
            "camara_ceap_despesas": "Câmara dos Deputados (Cota CEAP)",
            "camara_emendas_parlamentares": "Câmara dos Deputados (Emendas Pix)",
            "cgu_sancoes": "CGU (Sanções CEIS/CNEP)",
            "cgu_servidores_siape": "CGU (Servidores Federais SIAPE)",
            "cgu_beneficios_cidadao": "MDS & CGU (Bolsa Família & BPC)",
            "rfb_empresas": "Receita Federal (Empresas CNPJ)",
            "rfb_socios": "Receita Federal (Quadro Societário QSA)",
            "pgfn_divida_ativa": "PGFN (Dívida Ativa da União)",
            "tcu_contas_irregulares": "TCU (Contas Irregulares Ficha Limpa)",
            "tcu_empresas_inidoneas": "TCU (Empresas Inidôneas)",
            "tse_candidatos": "TSE (Candidaturas Oficiais)",
            "tse_doacoes": "TSE (Doações de Campanha)",
            "tse_bens_declarados": "TSE (Declaração de Bens)",
            "cmed_precos_medicamentos": "CMED / Anvisa (Teto de Medicamentos)",
            "anp_precos_combustiveis": "ANP (Preços de Combustíveis)",
            "transferegov_convenios": "MGI / Transferegov (Convênios Federais)",
            "obrasgov_obras_publicas": "MGI / Obrasgov (Obras Públicas Federais)",
            "cnj_processos_judiciais": "CNJ / DataJud (Processos & Falências)",
            "comex_balanca_comercial": "MDIC / Comex Stat (Comércio Exterior)",
            "bndes_operacoes_financiamento": "BNDES (Financiamentos & Crédito)",
            "inep_escolas_censo": "INEP / MEC (Censo Escolar)",
            "inep_ideb_municipios": "INEP / MEC (Indicadores do IDEB)",
            "datasus_estabelecimentos_cnes": "DataSUS (Hospitais & Leitos CNES)",
            "mte_caged_saldos_municipais": "Ministério do Trabalho (Novo CAGED)",
            "mte_caged_empresas_quadro": "Ministério do Trabalho (Quadro Empregados)",
            "ibama_autos_infracao": "IBAMA (Multas e Fiscalização Ambiental)",
            "ibama_areas_embargadas": "IBAMA (Áreas Rurais Embargadas)",
            "inpe_alertas_desmatamento": "INPE (DETER Alertas de Desmatamento)",
            "senado_senadores": "Senado Federal (Parlamentares)",
            "senado_ceaps_despesas": "Senado Federal (Cota CEAPS)",
            "dou_publicacoes_atos": "Imprensa Nacional (Diário Oficial DOU)",
            "catalogo_conjuntos_dados": "dados.gov.br (Catálogo de Dados Abertos)",
            "siconfi_transferencias": "Tesouro Nacional (Repasses Siconfi)",
            "siconfi_gastos_funcao": "Tesouro Nacional (Gastos por Função)",
            "querido_diario_publicacoes": "Querido Diário (Diários Municipais)",
            "pacto_federativo_balanco": "Receita & STN (Balanço Federativo)",
            "auditoria_vinculos_profissionais": "Multi-órgãos (Vínculos SIAPE/CNES/INEP/CLT)",
            "tse_votacao_municipio": "TSE (Votação Nominal por Município)",
            "transferegov_termos_mrosc": "MGI / Transferegov (Parcerias ONGs MROSC)",
            "auditoria_compras_medicamentos_volume": "SUS / PNCP (Volume de Medicamentos)",
            "auditoria_logistica_contratos": "Geointeligência (Malha Logística de Contratos)",
        }

        for tbl in sorted(tables):
            cnt = db.count(tbl)
            dom = domain_map.get(tbl, "Governo Federal")
            t.add_row(tbl, f"{cnt:,}", dom)

        console.print(t)
    else:
        console.print("[yellow]Nenhuma tabela criada ainda. Execute uma das skills para popular o banco.[/yellow]")


@app.command()
def skills():
    """Lista todas as skills do repositório, com órgão e objetivos."""
    skills_dir = settings.SKILLS_DIR
    skill_folders = [f for f in sorted(skills_dir.iterdir()) if f.is_dir() and not f.name.startswith(".")]

    t = Table(title=f"Catálogo de Skills ({len(skill_folders)} skills)")
    t.add_column("Skill", style="cyan", no_wrap=True)
    t.add_column("Órgão / Fonte", style="magenta")
    t.add_column("Descrição", style="white")

    for f in skill_folders:
        skill_md = f / "SKILL.md"
        desc = "Módulo de dados públicos"
        agency = "Governo Federal"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("description:"):
                    desc = line.replace("description:", "").strip()
                if "agency:" in line:
                    agency = line.split("agency:")[1].strip().strip('"').strip("'")
        t.add_row(f.name, agency, desc[:80] + ("..." if len(desc) > 80 else ""))

    console.print(t)


@app.command()
def dossie(cnpj: str = typer.Argument(..., help="CNPJ da empresa para gerar dossiê")):
    """Atalho para gerar dossiê 360º de um CNPJ cruzando todas as bases."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "dossie_empresa.py"
    spec = importlib.util.spec_from_file_location("dossie_empresa", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.dossie(cnpj=cnpj)


@app.command()
def auditoria_precos(
    fator: float = typer.Option(2.0, "--fator", "-f", help="Multiplicador sobre a mediana de mercado"),
):
    """Executa auditoria de sobrepreço em itens licitados (ex: mouse a R$ 1.000, café a R$ 90)."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-compras-pncp" / "scripts" / "auditoria_precos.py"
    spec = importlib.util.spec_from_file_location("auditoria_precos", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.auditar_sobrepreco(fator_sobrepreco=fator)


@app.command()
def auditoria_anomalias():
    """Varre todas as bases em busca de empresas de fachada, estouro do Simples e contratos desproporcionais."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "detector_anomalias.py"
    spec = importlib.util.spec_from_file_location("detector_anomalias", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_cartel():
    """Detecta conluio e cartel: empresas distintas que compartilham o mesmo e-mail, telefone ou endereço físico."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_cartel_conluio.py"
    spec = importlib.util.spec_from_file_location("auditoria_cartel_conluio", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_laranjas():
    """Identifica sócios/administradores de empresas licitantes que recebem Bolsa Família ou BPC."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_laranjas.py"
    spec = importlib.util.spec_from_file_location("auditoria_laranjas", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_servidores():
    """Identifica servidores públicos federais da ativa (SIAPE) atuando como administradores de empresas."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_conflito_servidor.py"
    spec = importlib.util.spec_from_file_location("auditoria_conflito_servidor", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_emendas_pix():
    """Rastreia o ciclo das Emendas Pix: do parlamentar ao município e ao fornecedor contratado."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_emendas_pix.py"
    spec = importlib.util.spec_from_file_location("auditoria_emendas_pix", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_pgfn():
    """Identifica fornecedores públicos vencedores de licitação que possuem Dívida Ativa da União na PGFN."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_pgfn_licitantes.py"
    spec = importlib.util.spec_from_file_location("auditoria_pgfn_licitantes", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def balanco_federativo(
    ano: int = typer.Option(2024, "--ano", "-a", help="Ano de referência das contas fiscais"),
):
    """Analisa os estados que mais recebem auxílios e transferências em relação ao que geram de tributos federais."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-fiscal-pacto-federativo" / "scripts" / "balanco_federativo.py"
    spec = importlib.util.spec_from_file_location("balanco_federativo", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.exibir_relatorio()


@app.command()
def auditoria_capacidade(
    min_contrato: float = typer.Option(500000.0, "--min-contrato", help="Valor mínimo de contrato"),
    max_funcionarios: int = typer.Option(2, "--max-funcionarios", help="Máximo de funcionários para considerar incapacidade"),
):
    """Detecta empresas sem funcionários registrados no CAGED/MTE vencendo contratos milionários."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_capacidade_operacional.py"
    spec = importlib.util.spec_from_file_location("auditoria_capacidade_operacional", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(min_contrato=min_contrato, max_funcionarios=max_funcionarios)


@app.command()
def auditoria_cronologia(
    dias: int = typer.Option(180, "--dias", "-d", help="Diferença máxima de dias entre abertura da empresa e contrato"),
):
    """Detecta empresas recém-criadas que venceram contratos de alto valor logo após a sua fundação."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_cronologia_suspeita.py"
    spec = importlib.util.spec_from_file_location("auditoria_cronologia_suspeita", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(dias_maximos=dias)


@app.command()
def auditoria_medicamentos():
    """Audita medicamentos comprados no SUS contra o teto obrigatório da CMED/Anvisa."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_medicamentos_cmed.py"
    spec = importlib.util.spec_from_file_location("auditoria_medicamentos_cmed", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_triangulo():
    """Rastreia o Triângulo Eleitoral: Doador de Campanha (TSE) -> Cota Parlamentar (CEAP) -> Licitações (PNCP)."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_triangulo_eleitoral.py"
    spec = importlib.util.spec_from_file_location("auditoria_triangulo_eleitoral", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_nepotismo():
    """Identifica laços de parentesco e nepotismo velado entre gestores locais e empresas licitantes."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_nepotismo_parentesco.py"
    spec = importlib.util.spec_from_file_location("auditoria_nepotismo_parentesco", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def score_risco_contratos(
    min_score: int = typer.Option(25, "--min-score", "-s", help="Score mínimo de risco (0 a 100)"),
):
    """Calcula score unificado de risco forense (0 a 100) para todos os contratos do PNCP."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_risco_contratos.py"
    spec = importlib.util.spec_from_file_location("auditoria_risco_contratos", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(min_score=min_score)


@app.command()
def auditoria_combustiveis(
    fator: float = typer.Option(1.25, "--fator", "-f", help="Multiplicador sobre a média da ANP"),
):
    """Audita sobrepreço de combustíveis em compras de frotas e cotas parlamentares contra a ANP."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_combustiveis.py"
    spec = importlib.util.spec_from_file_location("auditoria_combustiveis", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(fator_alerta=fator)


@app.command()
def auditoria_obras():
    """Identifica empreiteiras com obras públicas paralisadas/abandonadas vencendo novos contratos no PNCP."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_obras_paralisadas.py"
    spec = importlib.util.spec_from_file_location("auditoria_obras_paralisadas", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_eficiencia():
    """Benchmark de eficiência municipal: Gastos em Educação (Siconfi) x Nota do IDEB (INEP)."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_eficiencia_gastos.py"
    spec = importlib.util.spec_from_file_location("auditoria_eficiencia_gastos", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_esg():
    """Rastreia empresas com multas ambientais ou embargos do IBAMA contratadas pelo governo ou financiadas pelo BNDES."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_esg_desmatamento.py"
    spec = importlib.util.spec_from_file_location("auditoria_esg_desmatamento", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_teia(
    min_empresas: int = typer.Option(2, "--min-empresas", "-m", help="Mínimo de empresas compartilhadas por um sócio"),
):
    """Mapeia teia de relacionamentos societários, sócios em comum e grupos econômicos ocultos."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_teia_societaria.py"
    spec = importlib.util.spec_from_file_location("auditoria_teia_societaria", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(min_empresas=min_empresas)


@app.command()
def auditoria_benford(
    min_notas: int = typer.Option(150, "--min-notas", "-m", help="Mínimo de notas por fornecedor"),
):
    """Aplica a Lei de Benford (Teste Qui-Quadrado e MAD) para detectar notas fiscais e recibos forjados."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_benford.py"
    spec = importlib.util.spec_from_file_location("auditoria_benford", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(min_notas=min_notas)


@app.command()
def auditoria_fracionamento(
    teto: float = typer.Option(59906.02, "--teto", "-t", help="Teto legal de dispensa de licitação (Lei 14.133/21)"),
):
    """Detecta fracionamento ilegal de despesas (fatiamento de compras para burlar licitação)."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_fracionamento.py"
    spec = importlib.util.spec_from_file_location("auditoria_fracionamento", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(teto_dispensa=teto)


@app.command()
def auditoria_carrossel():
    """Detecta padrão de rodízio / carrossel de licitantes (bid-rigging rotation) em órgãos públicos."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_carrossel_licitacoes.py"
    spec = importlib.util.spec_from_file_location("auditoria_carrossel_licitacoes", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_acumulo_cargos(
    max_horas: int = typer.Option(60, "--max-horas", "-h", help="Limite máximo de carga horária semanal"),
):
    """Identifica 'Super-Servidores' com acúmulo ilegal de cargos, violação de DE ou jornada > 60h/semana."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_acumulo_cargos.py"
    spec = importlib.util.spec_from_file_location("auditoria_acumulo_cargos", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(max_horas=max_horas)


@app.command()
def auditoria_porta_giratoria(
    quarentena: int = typer.Option(180, "--quarentena", "-q", help="Período legal de quarentena em dias"),
):
    """Detecta conflito de interesses por 'Porta Giratória' (Lei 12.813/2013) entre exonerações no DOU e QSA."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_porta_giratoria.py"
    spec = importlib.util.spec_from_file_location("auditoria_porta_giratoria", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(dias_quarentena=quarentena)


@app.command()
def auditoria_voto_emenda():
    """Econometria Eleitoral: calcula o retorno de votos e o custo por voto das Emendas Pix (TSE x Câmara)."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_voto_emenda.py"
    spec = importlib.util.spec_from_file_location("auditoria_voto_emenda", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_ongs_fachada():
    """Audita o Triângulo das ONGs: Termos de Fomento/Colaboração (MROSC) com entidades sem estrutura operacional."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_ongs_fachada.py"
    spec = importlib.util.spec_from_file_location("auditoria_ongs_fachada", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


@app.command()
def auditoria_supercompra_medicamentos(
    max_doses_hab: float = typer.Option(20.0, "--max-doses-hab", "-d", help="Corte de alerta em doses por habitante"),
):
    """Detecta supercompra de medicamentos em volume incompatível com a população e leitos SUS locais."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_supercompra_medicamentos.py"
    spec = importlib.util.spec_from_file_location("auditoria_supercompra_medicamentos", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(max_doses_hab=max_doses_hab)


@app.command()
def auditoria_logistica_impossivel(
    max_km: float = typer.Option(300.0, "--max-km", "-k", help="Distância máxima viável (km) para entrega diária sem filial"),
):
    """Detecta contratos de itens perecíveis/entrega diária vencidos por empresas a milhares de km sem filial."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_logistica_impossivel.py"
    spec = importlib.util.spec_from_file_location("auditoria_logistica_impossivel", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan(max_km_perecivel=max_km)


@app.command()
def auditoria_insolvencia():
    """Calcula o Gov Z-Score preditivo de risco de quebra/abandono contratual de fornecedores públicos."""
    import importlib.util
    script_path = BASE_DIR / "skills" / "gov-cruzamentos-auditoria" / "scripts" / "auditoria_insolvencia_fornecedor.py"
    spec = importlib.util.spec_from_file_location("auditoria_insolvencia_fornecedor", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.scan()


def main():
    app()


if __name__ == "__main__":
    main()
