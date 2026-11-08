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

        return report

    def list_available_linkages(self) -> List[Dict[str, str]]:
        """Lists what tables currently exist in DuckDB and what connections are available."""
        current_tables = self.db.list_tables()
        relations = [
            {
                "chave": "CNPJ / CNPJ Raiz",
                "tabelas_conectadas": [t for t in ["rfb_empresas", "rfb_socios", "pncp_contratos", "cgu_sancoes", "tse_doacoes", "camara_ceap"] if t in current_tables],
                "descricao": "Cruza contratos públicos com sócios de empresas, sanções do CEIS/CNEP e doações de campanha.",
            },
            {
                "chave": "Código IBGE Município",
                "tabelas_conectadas": [t for t in ["ibge_municipios", "siconfi_orcamentos", "inep_censo_escolar", "datasus_leitos", "caged_emprego"] if t in current_tables],
                "descricao": "Cruza demografia do Censo com finanças municipais, educação (IDEB), saúde e emprego formal.",
            },
            {
                "chave": "CPF Mascarado / Nome",
                "tabelas_conectadas": [t for t in ["rfb_socios", "cgu_servidores", "tse_candidatos", "camara_deputados"] if t in current_tables],
                "descricao": "Identifica servidores públicos federais ou políticos que constam como sócios de empresas ou fornecedores.",
            },
        ]
        return relations


matcher = CrossMatcher()
