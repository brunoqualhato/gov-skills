"""Cross-matching and entity correlation engine for Brazilian Federal Public Data."""

from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel

from .db import get_db
from .normalizers import normalize_cnpj, normalize_cpf, strip_accents

console = Console()


class CrossMatcher:
    """Correlates entities across diverse government datasets using universal keys."""

    def __init__(self):
        self.db = get_db()

    def audit_company(self, cnpj_query: str) -> Dict[str, Any]:
        """
        Cross-examines a company across all available government tables:
        1. Receita Federal (Cadastral status, partners/QSA, capital social)
        2. PNCP / Compras.gov (Public procurement, contracts, awards)
        3. CGU Sanções (CEIS - inidoneidade, CNEP - anticorrupção, CEPIM)
        4. TSE Doações (Donations made to electoral campaigns)
        5. CGU Despesas (Direct federal government payments received)
        """
        cnpj_limpo, cnpj_fmt, cnpj_raiz = normalize_cnpj(cnpj_query)
        report: Dict[str, Any] = {
            "cnpj_pesquisado": cnpj_query,
            "cnpj_limpo": cnpj_limpo,
            "cnpj_formatado": cnpj_fmt,
            "cnpj_raiz": cnpj_raiz,
            "dados_cadastrais": None,
            "socios_qsa": [],
            "contratos_publicos": [],
            "sancoes_ativas": [],
            "doacoes_eleitorais": [],
            "pagamentos_diretos": [],
        }

        tables = self.db.list_tables()

        # 1. Receita Federal CNPJ
        if "rfb_empresas" in tables:
            rows = self.db.query(
                "SELECT * FROM rfb_empresas WHERE cnpj = ? OR cnpj_raiz = ?",
                [cnpj_limpo, cnpj_raiz],
            )
            if rows:
                report["dados_cadastrais"] = rows[0]

        # 2. Sócios (QSA)
        if "rfb_socios" in tables:
            socios = self.db.query(
                "SELECT * FROM rfb_socios WHERE cnpj_raiz = ?",
                [cnpj_raiz],
            )
            report["socios_qsa"] = socios

        # 3. PNCP Contratos
        if "pncp_contratos" in tables:
            contratos = self.db.query(
                "SELECT * FROM pncp_contratos WHERE ni_fornecedor = ? OR ni_fornecedor LIKE ?",
                [cnpj_limpo, f"%{cnpj_limpo}%"],
            )
            report["contratos_publicos"] = contratos

        # 4. Sanções CGU (CEIS / CNEP / CEPIM)
        if "cgu_sancoes" in tables:
            sancoes = self.db.query(
                "SELECT * FROM cgu_sancoes WHERE cnpj_sancionado = ? OR cnpj_raiz = ?",
                [cnpj_limpo, cnpj_raiz],
            )
            report["sancoes_ativas"] = sancoes

        # 5. Doações Eleitorais TSE
        if "tse_doacoes" in tables:
            doacoes = self.db.query(
                "SELECT * FROM tse_doacoes WHERE nr_cpf_cnpj_doador = ?",
                [cnpj_limpo],
            )
            report["doacoes_eleitorais"] = doacoes

        # 6. Dívida Ativa PGFN
        if "pgfn_divida_ativa" in tables:
            report["divida_ativa_pgfn"] = self.db.query(
                "SELECT * FROM pgfn_divida_ativa WHERE cnpj_cpf_devedor = ? OR cnpj_raiz = ?",
                [cnpj_limpo, cnpj_raiz],
            )

        # 7. Processos Judiciais DataJud / CNJ
        if "cnj_processos_judiciais" in tables:
            report["processos_judiciais"] = self.db.query(
                "SELECT * FROM cnj_processos_judiciais WHERE cpf_cnpj_parte = ? OR cnpj_raiz_parte = ?",
                [cnpj_limpo, cnpj_raiz],
            )

        # 8. Meio Ambiente IBAMA
        if "ibama_autos_infracao" in tables:
            report["autos_ibama"] = self.db.query(
                "SELECT * FROM ibama_autos_infracao WHERE cpf_cnpj_infrator = ? OR cnpj_raiz = ?",
                [cnpj_limpo, cnpj_raiz],
            )

        # 9. Obras Públicas Obrasgov
        if "obrasgov_obras_publicas" in tables:
            report["obras_executadas"] = self.db.query(
                "SELECT * FROM obrasgov_obras_publicas WHERE cnpj_executor = ? OR cnpj_raiz_executor = ?",
                [cnpj_limpo, cnpj_raiz],
            )

        # 10. Crédito BNDES
        if "bndes_operacoes_financiamento" in tables:
            report["financiamentos_bndes"] = self.db.query(
                "SELECT * FROM bndes_operacoes_financiamento WHERE cnpj_cliente = ? OR cnpj_raiz_cliente = ?",
                [cnpj_limpo, cnpj_raiz],
            )

        return report

    def list_available_linkages(self) -> List[Dict[str, str]]:
        """Lists what tables currently exist in DuckDB and what connections are available."""
        current_tables = self.db.list_tables()
        relations = [
            {
                "chave": "CNPJ / CNPJ Raiz",
                "tabelas_conectadas": [t for t in ["rfb_empresas", "rfb_socios", "pncp_contratos", "cgu_sancoes", "tse_doacoes", "camara_ceap_despesas", "pgfn_divida_ativa", "tcu_empresas_inidoneas", "cnj_processos_judiciais", "ibama_autos_infracao", "obrasgov_obras_publicas", "bndes_operacoes_financiamento", "anp_precos_combustiveis"] if t in current_tables],
                "descricao": "Cruza contratos públicos com sócios, sanções, dívida ativa, falências, desmatamento, obras e crédito do BNDES.",
            },
            {
                "chave": "Código IBGE Município",
                "tabelas_conectadas": [t for t in ["ibge_municipios", "siconfi_transferencias", "siconfi_gastos_funcao", "inep_escolas_censo", "inep_ideb_municipios", "datasus_estabelecimentos_cnes", "mte_caged_saldos_municipais", "anp_precos_combustiveis", "transferegov_convenios", "obrasgov_obras_publicas", "comex_balanca_comercial"] if t in current_tables],
                "descricao": "Cruza demografia do Censo com finanças municipais, educação (IDEB), saúde (SUS), emprego (CAGED), comércio exterior e preços ANP.",
            },
            {
                "chave": "CPF Mascarado / Nome",
                "tabelas_conectadas": [t for t in ["rfb_socios", "cgu_servidores_siape", "cgu_beneficios_cidadao", "tse_candidatos", "camara_deputados", "senado_senadores"] if t in current_tables],
                "descricao": "Identifica servidores federais, beneficiários de auxílios (laranjas) ou políticos atuando como sócios de empresas licitantes.",
            },
        ]
        return relations


matcher = CrossMatcher()
