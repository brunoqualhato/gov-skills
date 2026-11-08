---
name: gov-template-skill
description: Modelo padrão para criação de skills de dados públicos do Governo Federal brasileiro.
version: 1.0.0
metadata:
  domain: "Categoria do Dado"
  agency: "Nome do Órgão Responsável (ex: CGU, IBGE, RFB)"
  auth_required: false
  primary_keys: ["cnpj", "codigo_ibge"]
  target_tables: ["gov_nome_tabela"]
---

# 🏛️ Skill: [Nome do Domínio Governamental]

Esta skill capacita agentes de inteligência a **coletar, persistir em banco de dados analítico (DuckDB), analisar e correlacionar** os dados públicos disponibilizados por [Nome do Órgão].

---

## 🎯 Objetivo & Casos de Uso
- **Download Automatizado**: Coleta de dados via API REST, OData, CKAN ou download de dumps em lote.
- **Armazenamento Estruturado**: Ingestão no DuckDB local (`data/gov_data.duckdb`) com tipagem e índices nas chaves universais.
- **Cruzamento de Inteligência**: Junções com outras bases (Receita Federal, PNCP, CGU, TSE, IBGE) para identificar anomalias, auditorias e padrões.

---

## 🔑 Chaves Universais de Relacionamento
Esta base se conecta a outras fontes através de:
- `cnpj` / `cnpj_raiz`: Conecta com Receita Federal, Licitações PNCP, Sanções CGU.
- `codigo_ibge`: Conecta com demografia IBGE, orçamentos municipais Siconfi, IDEB.
- `cpf_mascarado` / `nome`: Conecta com folha SIAPE, quadro societário QSA, candidaturas TSE.

---

## 💾 Modelo de Dados no DuckDB

```sql
CREATE TABLE IF NOT EXISTS gov_exemplo_tabela (
    id VARCHAR PRIMARY KEY,
    cnpj_limpo VARCHAR,
    cnpj_raiz VARCHAR,
    codigo_ibge VARCHAR,
    valor_total DOUBLE,
    data_registro DATE,
    descricao VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_exemplo_cnpj ON gov_exemplo_tabela(cnpj_limpo);
CREATE INDEX IF NOT EXISTS idx_exemplo_ibge ON gov_exemplo_tabela(codigo_ibge);
```

---

## 🛠️ Scripts Operacionais

### 1. Coleta e Ingestão
```bash
# Executa coleta da API / download de dados e carrega no DuckDB
python skills/gov-template-skill/scripts/fetch.py --ano 2024
```

### 2. Consulta Rápida
```bash
# Consulta via CLI para agentes ou usuários
python skills/gov-template-skill/scripts/query.py --termo "termo de busca"
```

---

## 🔍 Exemplos de Consultas Analíticas (SQL)

```sql
-- Cruzamento de exemplo: relacionando com empresas da Receita Federal
SELECT 
    e.razao_social,
    t.valor_total,
    t.descricao
FROM gov_exemplo_tabela t
JOIN rfb_empresas e ON t.cnpj_raiz = e.cnpj_raiz
ORDER BY t.valor_total DESC
LIMIT 10;
```
