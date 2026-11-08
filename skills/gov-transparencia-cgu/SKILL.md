---
name: gov-transparencia-cgu
description: Coleta, ingere no DuckDB, consulta e cruza dados do Portal da Transparência do Governo Federal / Controladoria-Geral da União (CEIS, CNEP, CEPIM - Sanções Administrativas, Servidores SIAPE, Despesas e Cartões Corporativos CPGF).
version: 1.0.0
metadata:
  domain: "Controle, Sanções e Integridade Pública"
  agency: "Controladoria-Geral da União (CGU)"
  source_urls:
    - "https://portaldatransparencia.gov.br"
    - "https://api.portaldatransparencia.gov.br/swagger-ui.html"
  auth_required: true
  auth_env_vars: ["CGU_API_KEY", "TRANSPARENCIA_API_KEY"]
  primary_keys: ["cnpj_sancionado", "cnpj_raiz", "cpf_sancionado", "orgao_siafi"]
  target_tables: ["cgu_sancoes", "cgu_servidores", "cgu_despesas_pagamentos"]
---

# 🏛️ Skill: gov-transparencia-cgu (Portal da Transparência / CGU)

O **Portal da Transparência da CGU** é o epicentro do controle social e auditoria do Poder Executivo Federal brasileiro. É nele que residem os cadastros nacionais restritivos de empresas corruptas, despesas federais por credor e dados da folha de pagamento pública federal.

Esta skill permite ao agente:
1. **Consultar e ingerir os cadastros de sanções**:
   - **CEIS**: Cadastro de Empresas Inidôneas e Suspensas.
   - **CNEP**: Cadastro Nacional de Empresas Punidas (Lei Anticorrupção - Lei nº 12.846/2013).
   - **CEPIM**: Entidades privadas sem fins lucrativos impedidas de celebrar convênios.
2. **Armazenar sanções e despesas no DuckDB** para cruzamento com licitações e empresas.
3. **Identificar empresas sancionadas** que continuam participando de contratações públicas no PNCP ou recebendo verbas de cotas parlamentares.

---

## 🔑 Autenticação (Chave de API)

A API REST da CGU exige a chave gratuita de acesso no header `chave-api-dados`.
1. Obtenha sua chave gratuita em: [portaldatransparencia.gov.br/api-de-dados/cadastrar](https://portaldatransparencia.gov.br/api-de-dados/cadastrar).
2. Configure a variável no seu arquivo `.env`:
   ```bash
   CGU_API_KEY=sua_chave_aqui
   ```
> *Nota: Caso não possua chave no momento, a skill também suporta importação direta de arquivos CSV baixados pela seção "Download de Dados" do portal.*

---

## 💾 Schema no DuckDB (`cgu_sancoes`)

```sql
CREATE TABLE IF NOT EXISTS cgu_sancoes (
    id_sancao VARCHAR PRIMARY KEY,
    tipo_cadastro VARCHAR, -- CEIS, CNEP, CEPIM
    cnpj_sancionado VARCHAR,
    cnpj_raiz VARCHAR,
    cpf_sancionado VARCHAR,
    nome_sancionado VARCHAR,
    orgao_sancionador VARCHAR,
    uf_orgao VARCHAR,
    data_inicio_sancao DATE,
    data_fim_sancao DATE,
    motivo VARCHAR,
    fundamentacao_legal VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cgu_cnpj ON cgu_sancoes(cnpj_sancionado);
CREATE INDEX IF NOT EXISTS idx_cgu_cnpj_raiz ON cgu_sancoes(cnpj_raiz);
```

---

## 🚀 Como Executar

### 1. Ingestão via API REST (com chave CGU)
```bash
# Ingerir sanções ativas do CEIS e CNEP
python skills/gov-transparencia-cgu/scripts/fetch_cgu.py sancoes --max-paginas 5
```

### 2. Ingestão de Arquivo CSV (sem necessidade de chave)
```bash
# Importar CSV baixado manualmente do portal da transparência
python skills/gov-transparencia-cgu/scripts/fetch_cgu.py importar-csv --arquivo caminho/do/arquivo.csv --tipo CEIS
```

### 3. Consultas Rápidas
```bash
# Consultar sanção por CNPJ ou nome da empresa
python skills/gov-transparencia-cgu/scripts/query_cgu.py search --cnpj "00.000.000/0001-91"
python skills/gov-transparencia-cgu/scripts/query_cgu.py search --nome "Engenharia"
```
