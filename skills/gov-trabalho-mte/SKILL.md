---
name: gov-trabalho-mte
description: Coleta, ingere no DuckDB, consulta e cruza estatísticas oficiais do mercado de trabalho formal brasileiro (Novo CAGED - Cadastro Geral de Empregados e Desempregados, RAIS e ocupações CBO por município e setor econômico CNAE).
version: 1.0.0
metadata:
  domain: "Trabalho, Emprego Formal e Ocupações"
  agency: "Ministério do Trabalho e Emprego (MTE)"
  source_urls:
    - "http://pdet.mte.gov.br/novo-caged"
    - "ftp://ftp.mtps.gov.br/pdet/microdados/NOVO%20CAGED"
  auth_required: false
  primary_keys: ["codigo_ibge", "ano_mes", "cnae_secao", "codigo_cbo"]
  target_tables: ["mte_caged_saldos_municipais", "mte_cbo_ocupacoes"]
---

# 🏛️ Skill: gov-trabalho-mte (Novo CAGED / MTE)

O **Novo CAGED** registra mensalmente todas as admissões e demissões com carteira assinada (regime CLT) em todo o território nacional, fornecendo o pulso real da criação de empregos por município, setor econômico e faixa salarial.

---

## 🎯 Capacidades da Skill
1. **Saldo de Empregos**: Coleta de saldo líquido (admissões - demissões) por município e mês.
2. **Distribuição Setorial**: Análise por grandes setores econômicos (Indústria, Comércio, Serviços, Agropecuária, Construção Civil).
3. **Cruzamentos Macroeconômicos & Territoriais**:
   - Cruzar a criação de empregos locais com repasses de recursos federais e grandes obras licitadas no PNCP.
   - Cruzar crescimento econômico local com taxa de juros do BCB e inflação.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS mte_caged_saldos_municipais (
    id_registro VARCHAR PRIMARY KEY,
    ano INTEGER,
    mes INTEGER,
    codigo_ibge VARCHAR,
    uf VARCHAR,
    setor_economico VARCHAR, -- Servicos, Comercio, Industria, Construcao, Agro
    total_admissoes INTEGER,
    total_desligamentos INTEGER,
    saldo_liquido INTEGER,
    salario_medio_admissao DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_caged_ibge ON mte_caged_saldos_municipais(codigo_ibge);
CREATE INDEX IF NOT EXISTS idx_caged_ano_mes ON mte_caged_saldos_municipais(ano, mes);
```
