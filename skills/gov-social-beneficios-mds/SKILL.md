---
name: gov-social-beneficios-mds
description: Coleta, ingere no DuckDB, consulta e cruza dados oficiais de programas sociais e transferência de renda (Bolsa Família, Auxílio Gás, BPC / LOAS e Seguro Defeso) do Ministério do Desenvolvimento Social (MDS) e Portal da Transparência da CGU.
version: 1.0.0
metadata:
  domain: "Assistência Social, Benefícios e Seguridade"
  agency: "Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome (MDS) & CGU"
  source_urls:
    - "https://portaldatransparencia.gov.br/api-de-dados"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["id_beneficio", "cpf_beneficiario", "codigo_ibge"]
  target_tables: ["cgu_beneficios_cidadao"]
---

# 🏛️ Skill: gov-social-beneficios-mds (MDS & Benefícios Sociais)

A base de dados de **Benefícios ao Cidadão** reúne os pagamentos realizados aos beneficiários de programas sociais federais destinados a famílias em situação de vulnerabilidade e extrema pobreza.

---

## 🎯 Capacidades da Skill
1. **Programas Rastreados**: Novo Bolsa Família, Benefício de Prestação Continuada (BPC), Auxílio Gás e Seguro Defeso ao Pescador Artesanal.
2. **Nível Município e Beneficiário**: Valor recebido por mês de competência, NIS/CPF e localidade.
3. **Cruzamentos de Auditoria Forense**:
   - **Sócios Laranjas**: Identificar beneficiários do Bolsa Família ou BPC cadastrados como sócios ou administradores de empresas que vencem licitações milionárias ou emitem notas para o poder público.
   - **Emprego Formal Simultâneo**: Cruzar beneficiários com vínculos CLT de alta renda no Novo CAGED.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS cgu_beneficios_cidadao (
    id_beneficio VARCHAR PRIMARY KEY,
    tipo_beneficio VARCHAR, -- BOLSA FAMILIA, BPC, AUXILIO GAS, SEGURO DEFESO
    cpf_beneficiario VARCHAR,
    nome_beneficiario VARCHAR,
    municipio VARCHAR,
    uf VARCHAR,
    codigo_ibge VARCHAR,
    mes_competencia VARCHAR,
    valor_parcela DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_benef_cpf ON cgu_beneficios_cidadao(cpf_beneficiario);
CREATE INDEX IF NOT EXISTS idx_benef_ibge ON cgu_beneficios_cidadao(codigo_ibge);
```
