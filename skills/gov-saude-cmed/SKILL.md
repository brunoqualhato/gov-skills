---
name: gov-saude-cmed
description: Coleta, ingere no DuckDB, consulta e audita preços de medicamentos regulados pela CMED (Câmara de Regulação do Mercado de Medicamentos / Anvisa). Controla Preço Fabricante (PF), Preço Máximo ao Consumidor (PMC) e desconto obrigatório do Coeficiente de Adequação de Preços (CAP) para compras públicas no SUS.
version: 1.0.0
metadata:
  domain: "Saúde Pública, Regulação Farmacêutica e Preços de Medicamentos"
  agency: "CMED (Câmara de Regulação do Mercado de Medicamentos) / Anvisa"
  source_urls:
    - "https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/cmed/precos"
    - "https://dados.gov.br/dados/conjuntos-dados/cmed-medicamentos"
  auth_required: false
  primary_keys: ["codigo_ggrem", "registro_anvisa", "substancia"]
  target_tables: ["cmed_precos_medicamentos"]
---

# 🏛️ Skill: gov-saude-cmed (CMED / Anvisa - Teto de Preços de Medicamentos)

A **CMED** estabelece os preços máximos que laboratórios e distribuidoras podem cobrar no Brasil. Em compras públicas da União, Estados e Municípios, a aplicação do **CAP (Coeficiente de Adequação de Preços)** é um desconto obrigatório por lei.

---

## 💾 Schema no DuckDB (`cmed_precos_medicamentos`)

```sql
CREATE TABLE IF NOT EXISTS cmed_precos_medicamentos (
    codigo_ggrem VARCHAR PRIMARY KEY,
    registro_anvisa VARCHAR,
    substancia VARCHAR,
    laboratorio VARCHAR,
    apresentacao VARCHAR,
    classe_terapeutica VARCHAR,
    preco_fabricante_pf DOUBLE,
    preco_maximo_consumidor_pmc DOUBLE,
    percentual_cap DOUBLE, -- Ex: 21.75%
    preco_teto_governo_cap DOUBLE,
    data_vigencia DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cmed_substancia ON cmed_precos_medicamentos(substancia);
CREATE INDEX IF NOT EXISTS idx_cmed_laboratorio ON cmed_precos_medicamentos(laboratorio);
```

---

## 🔬 Auditoria de Superfaturamento de Medicamentos no SUS
```sql
SELECT 
    i.descricao_item AS medicamento_comprado,
    i.orgao_nome,
    i.orgao_uf,
    i.valor_unitario AS preco_pago_governo,
    c.preco_teto_governo_cap AS teto_maximo_cmed,
    ROUND(((i.valor_unitario - c.preco_teto_governo_cap) / c.preco_teto_governo_cap) * 100, 1) AS percentual_acima_do_teto,
    ROUND((i.valor_unitario - c.preco_teto_governo_cap) * i.quantidade, 2) AS superfaturamento_total
FROM compras_itens_licitados i
JOIN cmed_precos_medicamentos c ON LOWER(i.descricao_item) LIKE '%' || LOWER(c.substancia) || '%'
WHERE i.valor_unitario > c.preco_teto_governo_cap
ORDER BY superfaturamento_total DESC;
```
