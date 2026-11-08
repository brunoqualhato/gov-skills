---
name: gov-controle-tcu
description: Coleta, ingere no DuckDB, consulta e cruza decisões, condenações e cadastros sancionatórios do Tribunal de Contas da União (TCU) - Relação de Responsáveis com Contas Julgadas Irregulares (Lei da Ficha Limpa), Empresas Declaradas Inidôneas (art. 46 Lei 8.443/92) e Inabilitados para Cargos Públicos.
version: 1.0.0
metadata:
  domain: "Controle Externo, Julgamento de Contas e Sanções Constitucionais"
  agency: "Tribunal de Contas da União (TCU)"
  source_urls:
    - "https://contasirregulares.tcu.gov.br"
    - "https://portal.tcu.gov.br/dados-abertos"
  auth_required: false
  primary_keys: ["cpf_cnpj_responsavel", "numero_processo_tcu", "numero_acordao"]
  target_tables: ["tcu_contas_irregulares", "tcu_empresas_inidoneas"]
---

# 🏛️ Skill: gov-controle-tcu (Tribunal de Contas da União)

O **TCU** é o órgão de controle externo constitucional responsável por fiscalizar a aplicação de todo recurso público federal. Suas sanções possuem eficácia imediata em todo o território nacional.

---

## 🎯 Bases Oficiais do TCU
1. **Contas Julgadas Irregulares**: Gestores públicos condenados por dano ao erário ou desvio de recursos públicos federais (base da inelegibilidade da Lei da Ficha Limpa).
2. **Empresas Inidôneas**: Pessoas jurídicas proibidas de participar de licitações com a Administração Pública por até 5 anos (art. 46 da Lei 8.443/1992).
3. **Inabilitados para Função Pública**: Indivíduos impedidos de ocupar cargos em comissão ou funções de confiança na administração federal por até 8 anos.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS tcu_contas_irregulares (
    id_registro VARCHAR PRIMARY KEY,
    cpf_cnpj VARCHAR,
    cnpj_raiz VARCHAR,
    nome_responsavel VARCHAR,
    cargo_funcao VARCHAR,
    orgao_origem VARCHAR,
    uf_orgao VARCHAR,
    numero_processo VARCHAR,
    numero_acordao VARCHAR,
    ano_acordao INTEGER,
    data_julgamento DATE,
    data_transito_julgado DATE,
    data_fim_inelegibilidade DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tcu_empresas_inidoneas (
    id_inidoneidade VARCHAR PRIMARY KEY,
    cnpj_inidonio VARCHAR,
    cnpj_raiz VARCHAR,
    razao_social VARCHAR,
    numero_processo VARCHAR,
    numero_acordao VARCHAR,
    data_inicio_sancao DATE,
    data_fim_sancao DATE,
    motivo VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tcu_cnpj ON tcu_empresas_inidoneas(cnpj_inidonio);
CREATE INDEX IF NOT EXISTS idx_tcu_contas_cpf ON tcu_contas_irregulares(cpf_cnpj);
```

---

## 🔬 Consulta Investigativa: Licitante Inidôneo pelo TCU com Contrato no PNCP
```sql
SELECT 
    p.numero_contrato,
    p.orgao_nome,
    p.nome_fornecedor,
    p.valor_global,
    t.numero_acordao,
    t.data_inicio_sancao,
    t.data_fim_sancao,
    t.motivo
FROM pncp_contratos p
JOIN tcu_empresas_inidoneas t ON p.cnpj_raiz_fornecedor = t.cnpj_raiz
WHERE p.data_assinatura BETWEEN t.data_inicio_sancao AND t.data_fim_sancao;
```
