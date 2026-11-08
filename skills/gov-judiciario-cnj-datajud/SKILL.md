---
name: gov-judiciario-cnj-datajud
description: Coleta, ingere no DuckDB, consulta e cruza dados processuais do Poder Judiciário brasileiro (DataJud / Conselho Nacional de Justiça - CNJ), identificando ações civis públicas, improbidade administrativa, execuções fiscais e falências.
version: 1.0.0
metadata:
  domain: "Poder Judiciário, Processos e Due Diligence Jurídica"
  agency: "Conselho Nacional de Justiça (CNJ)"
  source_urls:
    - "https://datajud.cnj.jus.br"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["numero_processo", "cpf_cnpj_parte"]
  target_tables: ["cnj_processos_judiciais"]
---

# 🏛️ Skill: gov-judiciario-cnj-datajud (DataJud / CNJ)

O **DataJud** (Resolução CNJ nº 331/2020) é a Base Nacional de Dados do Poder Judiciário, consolidando metadados de processos de todos os 90 tribunais brasileiros (Justiça Estadual, Federal, do Trabalho, Militar e Tribunais Superiores).

---

## 🎯 Capacidades da Skill
1. **Due Diligence Jurídica de Fornecedores**: Identificar se empresas licitantes ou seus sócios respondem por **Improbidade Administrativa**, **Execução Fiscal**, **Trabalho Análogo à Escravidão**, **Recuperação Judicial** ou **Falência**.
2. **Histórico Contencioso**: Mapear tribunais, varas judiciais, valores das causas e situação processual.
3. **Cruzamentos de Auditoria**:
   - Fornecedor faturando milhões no PNCP enquanto está em processo de Falência ou Recuperação Judicial não declarada.
   - Sócio de empresa com bens bloqueados por improbidade administrativa disputando novas licitações.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS cnj_processos_judiciais (
    numero_processo VARCHAR PRIMARY KEY,
    classe_processual VARCHAR, -- EXECUCAO FISCAL, ACAO CIVIL PUBLICA, IMPROBIDADE ADMINISTRATIVA, FALENCIA
    tribunal VARCHAR, -- TJSP, TJRJ, TRF1, TRF3
    grau_jurisdicao VARCHAR,
    data_ajuizamento DATE,
    cpf_cnpj_parte VARCHAR,
    cnpj_raiz_parte VARCHAR,
    nome_parte VARCHAR,
    polo_processual VARCHAR, -- PASSIVO, ATIVO
    valor_causa DOUBLE,
    situacao_processo VARCHAR,
    orgao_julgador VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cnj_parte ON cnj_processos_judiciais(cpf_cnpj_parte);
CREATE INDEX IF NOT EXISTS idx_cnj_raiz ON cnj_processos_judiciais(cnpj_raiz_parte);
CREATE INDEX IF NOT EXISTS idx_cnj_classe ON cnj_processos_judiciais(classe_processual);
```
