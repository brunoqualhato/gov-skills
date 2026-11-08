---
name: gov-legislativo-camara
description: Coleta, ingere no DuckDB, consulta e cruza dados abertos da Câmara dos Deputados (Deputados em exercício, Despesas da Cota Parlamentar CEAP, Proposições Legislativas e Votações Nominais).
version: 1.0.0
metadata:
  domain: "Poder Legislativo Federal"
  agency: "Câmara dos Deputados"
  source_urls:
    - "https://dadosabertos.camara.leg.br"
    - "https://dadosabertos.camara.leg.br/swagger/api.html"
  auth_required: false
  primary_keys: ["id_deputado", "cnpj_cpf_fornecedor", "id_proposicao"]
  target_tables: ["camara_deputados", "camara_ceap_despesas"]
---

# 🏛️ Skill: gov-legislativo-camara (Câmara dos Deputados)

A API v2 de Dados Abertos da **Câmara dos Deputados** disponibiliza em tempo real as atividades parlamentares, presenças, tramitação de leis e, principalmente, a execução financeira da **Cota para o Exercício da Atividade Parlamentar (CEAP)**.

Esta skill permite ao agente:
1. **Baixar e manter a lista atualizada de 513 deputados federais**, com partido, UF, contatos e gabinete.
2. **Ingerir as despesas detalhadas da CEAP**, incluindo tipo de gasto (combustíveis, consultorias, divulgação, passagens), data, valor líquido e o **CNPJ/CPF do fornecedor contratado**.
3. **Cruzar fornecedores da CEAP com a Receita Federal e Sanções**, identificando se empresas contratadas por deputados pertencem a servidores, possuem restrições ou são doadoras eleitorais.

---

## 📡 Endpoints Oficiais (API v2)

- **Base URL**: `https://dadosabertos.camara.leg.br/api/v2`
- **Deputados**:
  `GET /deputados?ordem=ASC&ordenarPor=nome`
- **Despesas da Cota (CEAP)**:
  `GET /deputados/{id}/despesas?ano={ano}&ordem=ASC&ordenarPor=ano`
- **Proposições (PLs, PECs)**:
  `GET /proposicoes?dataInicio={YYYY-MM-DD}&ordem=DESC&ordenarPor=id`

---

## 💾 Schema no DuckDB

```sql
-- Tabela de Deputados Federais
CREATE TABLE IF NOT EXISTS camara_deputados (
    id_deputado INTEGER PRIMARY KEY,
    nome VARCHAR,
    sigla_partido VARCHAR,
    sigla_uf VARCHAR,
    id_legislatura INTEGER,
    url_foto VARCHAR,
    email VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de Despesas da Cota Parlamentar (CEAP)
CREATE TABLE IF NOT EXISTS camara_ceap_despesas (
    id_despesa VARCHAR PRIMARY KEY,
    id_deputado INTEGER,
    ano INTEGER,
    mes INTEGER,
    tipo_despesa VARCHAR,
    data_documento DATE,
    valor_documento DOUBLE,
    valor_glosa DOUBLE,
    valor_liquido DOUBLE,
    nome_fornecedor VARCHAR,
    cnpj_cpf_fornecedor VARCHAR,
    cnpj_raiz_fornecedor VARCHAR,
    num_ressarcimento VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ceap_deputado ON camara_ceap_despesas(id_deputado);
CREATE INDEX IF NOT EXISTS idx_ceap_fornecedor ON camara_ceap_despesas(cnpj_cpf_fornecedor);
CREATE INDEX IF NOT EXISTS idx_ceap_cnpj_raiz ON camara_ceap_despesas(cnpj_raiz_fornecedor);
```

---

## 🚀 Como Executar

### 1. Ingestão de Deputados e Amostra de Despesas
```bash
# Ingerir todos os 513 deputados federais em exercício
python skills/gov-legislativo-camara/scripts/fetch_camara.py deputados

# Ingerir despesas da CEAP de deputados
python skills/gov-legislativo-camara/scripts/fetch_camara.py despesas --ano 2024 --limite-deputados 20
```

### 2. Consultas Rápidas
```bash
# Maiores fornecedores que receberam verba de cota parlamentar
python skills/gov-legislativo-camara/scripts/query_camara.py top-fornecedores --limit 15

# Maiores gastos por tipo de despesa (combustível, consultoria, divulgação)
python skills/gov-legislativo-camara/scripts/query_camara.py gastos-tipo
```

---

## 🔬 Consultas Analíticas e Cruzamentos

### Cruzar Fornecedores da CEAP com Contratos do PNCP
```sql
SELECT 
    d.nome AS deputado,
    d.sigla_partido,
    d.sigla_uf,
    c.nome_fornecedor,
    c.cnpj_cpf_fornecedor,
    c.valor_liquido AS valor_gasto_cota,
    p.numero_contrato,
    p.orgao_nome,
    p.valor_global AS valor_contrato_governo
FROM camara_ceap_despesas c
JOIN camara_deputados d ON c.id_deputado = d.id_deputado
JOIN pncp_contratos p ON c.cnpj_raiz_fornecedor = p.cnpj_raiz_fornecedor
ORDER BY c.valor_liquido DESC
LIMIT 10;
```
