---
name: gov-credito-bndes
description: Coleta, ingere no DuckDB, consulta e cruza operações de crédito, financiamentos diretos e indiretos subsidiados e garantias concedidas pelo BNDES (Banco Nacional de Desenvolvimento Econômico e Social).
version: 1.0.0
metadata:
  domain: "Crédito Público, Financiamento e Subsídios Governamentais"
  agency: "Banco Nacional de Desenvolvimento Econômico e Social (BNDES)"
  source_urls:
    - "https://www.bndes.gov.br/wps/portal/site/home/transparencia"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["numero_contrato", "cnpj_cliente"]
  target_tables: ["bndes_operacoes_financiamento"]
---

# 🏛️ Skill: gov-credito-bndes (BNDES Transparente)

O **BNDES** é o principal instrumento de financiamento de longo prazo e investimentos estruturantes da economia brasileira. O portal BNDES Transparente publica dados de todas as operações com recursos públicos concedidas a empresas brasileiras.

---

## 🎯 Capacidades da Skill
1. **Operações Diretas e Indiretas**: Finame, Finem, BNDES Automático e apoio à exportação.
2. **Condições de Financiamento**: Valores contratados e desembolsados, prazos de carência e taxas de juros subsidiadas (TLP/TJLP).
3. **Cruzamentos de Auditoria Forense e ESG**:
   - **Dupla Sanção**: Empresas na Dívida Ativa da União (PGFN) ou no CEIS/TCU captando empréstimos públicos com juros subsidiados.
   - **Risco Socioambiental**: Empresas com embargos por desmatamento no IBAMA recebendo recursos do BNDES.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS bndes_operacoes_financiamento (
    numero_contrato VARCHAR PRIMARY KEY,
    data_contrato DATE,
    cnpj_cliente VARCHAR,
    cnpj_raiz_cliente VARCHAR,
    razao_social_cliente VARCHAR,
    forma_apoio VARCHAR, -- DIRETA, INDIRETA
    linha_financiamento VARCHAR,
    valor_contratado DOUBLE,
    valor_desembolsado DOUBLE,
    taxa_juros VARCHAR,
    setor_cnae VARCHAR,
    municipio VARCHAR,
    uf VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bndes_cnpj ON bndes_operacoes_financiamento(cnpj_cliente);
CREATE INDEX IF NOT EXISTS idx_bndes_raiz ON bndes_operacoes_financiamento(cnpj_raiz_cliente);
```
