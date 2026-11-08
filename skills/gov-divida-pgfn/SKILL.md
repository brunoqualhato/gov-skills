---
name: gov-divida-pgfn
description: Coleta, ingere no DuckDB, consulta e cruza a lista de Devedores da Dívida Ativa da União e do FGTS da Procuradoria-Geral da Fazenda Nacional (PGFN). Identifica empresas devedoras de tributos e FGTS que continuam faturando em licitações públicas.
version: 1.0.0
metadata:
  domain: "Crédito Tributário, Dívida Ativa e Regularidade Fiscal"
  agency: "Procuradoria-Geral da Fazenda Nacional (PGFN) / Ministério da Fazenda"
  source_urls:
    - "https://dadosabertos.pgfn.gov.br"
    - "https://www.regularize.pgfn.gov.br"
  auth_required: false
  primary_keys: ["numero_inscricao", "cnpj_cpf_devedor", "cnpj_raiz"]
  target_tables: ["pgfn_divida_ativa"]
---

# 🏛️ Skill: gov-divida-pgfn (PGFN - Dívida Ativa da União)

A **PGFN** mantém o cadastro oficial de todas as pessoas físicas e jurídicas que possuem débitos tributários, previdenciários e de FGTS não quitados inscritos em Dívida Ativa da União.

---

## 🎯 Capacidades da Skill
1. **Mapeamento de Débitos Federais**: Valor consolidado de dívidas com a Previdência, FGTS, IRPJ, CSLL e multas trabalhistas.
2. **Auditoria de Regularidade Fiscal em Contratos**:
   - Pela Lei 14.133/2021, empresas licitantes devem manter regularidade fiscal durante toda a execução do contrato.
   - Cruzar a lista da PGFN com o PNCP revela empresas inadimplentes que continuam recebendo verbas públicas sem retenção.

---

## 💾 Schema no DuckDB (`pgfn_divida_ativa`)

```sql
CREATE TABLE IF NOT EXISTS pgfn_divida_ativa (
    numero_inscricao VARCHAR PRIMARY KEY,
    cnpj_cpf_devedor VARCHAR,
    cnpj_raiz VARCHAR,
    nome_devedor VARCHAR,
    tipo_devedor VARCHAR, -- PRINCIPAL, CORESPONSAVEL
    tipo_divida VARCHAR,   -- TRIBUTARIA, PREVIDENCIARIA, FGTS, MULTA ELEITORAL
    situacao_inscricao VARCHAR, -- EM COBRANCA, AJUIZADA, PARCELADA
    valor_consolidado DOUBLE,
    uf VARCHAR,
    orgao_origem VARCHAR,
    data_inscricao DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pgfn_cnpj ON pgfn_divida_ativa(cnpj_cpf_devedor);
CREATE INDEX IF NOT EXISTS idx_pgfn_cnpj_raiz ON pgfn_divida_ativa(cnpj_raiz);
```

---

## 🔬 Consulta Investigativa: Vencedores de Licitações com Dívida Ativa
```sql
SELECT 
    p.nome_fornecedor,
    p.ni_fornecedor,
    p.numero_contrato,
    p.valor_global AS valor_contrato_governo,
    d.tipo_divida,
    d.situacao_inscricao,
    d.valor_consolidado AS valor_divida_governo
FROM pncp_contratos p
JOIN pgfn_divida_ativa d ON p.cnpj_raiz_fornecedor = d.cnpj_raiz
WHERE d.situacao_inscricao = 'EM COBRANCA'
ORDER BY d.valor_consolidado DESC;
```
