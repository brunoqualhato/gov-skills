---
name: gov-cruzamentos-auditoria
description: Meta-skill de inteligência e cruzamento investigativo de dados públicos federais brasileiros. Cruza CNPJ (Receita), Contratos (PNCP), Sanções (CGU), Cota Parlamentar (Câmara), Indicadores (IBGE e BCB) para auditorias completas e detecção de anomalias.
version: 1.0.0
metadata:
  domain: "Auditoria, Inteligência e Cruzamento de Dados"
  agency: "Multi-órgãos (RFB, CGU, PNCP, Câmara, IBGE, BCB)"
  auth_required: false
  primary_keys: ["cnpj", "cnpj_raiz", "cpf_mascarado", "codigo_ibge"]
  target_tables: ["rfb_empresas", "rfb_socios", "pncp_contratos", "camara_ceap_despesas", "cgu_sancoes", "ibge_municipios"]
---

# 🕵️ Skill: gov-cruzamentos-auditoria (Inteligência & Cruzamentos)

Esta é a **meta-skill analítica** do repositório. Enquanto as outras skills são especialistas em coletar e padronizar dados de seus respectivos órgãos, a `gov-cruzamentos-auditoria` é responsável por **conectar todos os pontos** no Data Lakehouse DuckDB.

---

## 🎯 Capacidades de Cruzamento

1. **Dossiê 360º de Fornecedor / Empresa**:
   - Informações cadastrais da Receita Federal (capital social, CNAE, endereço, porte).
   - Quadro de Sócios e Administradores (QSA) e outras empresas dos sócios.
   - Histórico completo de Contratos Públicos no PNCP (valores, órgãos contratantes, objetos).
   - Histórico de pagamentos recebidos de Deputados Federais via Cota Parlamentar (CEAP).
   - Verificação em listas de sanções (CEIS / CNEP / CEPIM da CGU).

2. **Detecção de Anomalias & Red Flags**:
   - **Teto do Simples Nacional Estourado**: Empresas optantes pelo Simples que faturaram contratos acima de R$ 4,8 milhões/ano.
   - **Capital Social Desproporcional**: Empresas com capital social minúsculo (ex: R$ 10.000) vencendo contratos de milhões.
   - **Dupla Fonte (Legislativo + Executivo)**: Empresas simultaneamente contratadas por gabinetes parlamentares e órgãos do governo.
   - **Fornecedores Sancionados**: Empresas punidas pela CGU com contratos ou empenhos vigentes.

---

## 🚀 Como Executar

### 1. Dossiê Completo de uma Empresa
```bash
# Gera dossiê consolidando Receita Federal, PNCP, CEAP e Sanções
python skills/gov-cruzamentos-auditoria/scripts/dossie_empresa.py --cnpj 31003259000110
python skills/gov-cruzamentos-auditoria/scripts/dossie_empresa.py --cnpj 02012862000160
```

### 2. Varredura de Anomalias Automáticas
```bash
# Executa algoritmos de auditoria sobre todas as bases carregadas
python skills/gov-cruzamentos-auditoria/scripts/detector_anomalias.py
```
