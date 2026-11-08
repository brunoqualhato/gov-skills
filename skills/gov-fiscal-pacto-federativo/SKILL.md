---
name: gov-fiscal-pacto-federativo
description: Analisa o Balanço Fiscal Federativo brasileiro. Cruza a Arrecadação Tributária Federal gerada por cada UF (Receita Federal) com o total de Transferências Constitucionais (FPE/FPM pelo Tesouro Nacional) e Auxílios Sociais (Bolsa Família/BPC pelo MDS). Ranqueia quais estados mais recebem recursos federais do que geram de receita para a União.
version: 1.0.0
metadata:
  domain: "Pacto Federativo, Finanças Públicas e Transferências Intergovernamentais"
  agency: "Secretaria da Receita Federal (RFB) & Secretaria do Tesouro Nacional (STN)"
  source_urls:
    - "https://dados.gov.br/dados/conjuntos-dados/arrecadacao-por-uf"
    - "https://www.tesourotransparente.gov.br"
  auth_required: false
  primary_keys: ["sigla_uf", "ano"]
  target_tables: ["pacto_federativo_balanco"]
---

# 🏛️ Skill: gov-fiscal-pacto-federativo (Balanço Fiscal entre Estados)

Esta skill responde a uma das perguntas mais cruciais das contas públicas brasileiras: **quais estados sustentam o Orçamento Federal e quais estados dependem estruturalmente de transferências e auxílios da União?**

---

## 🧮 Metodologia de Cálculo

$$\text{Razão de Retorno Federativo} = \frac{\text{Transferências Constitucionais (FPE/FPM) } + \text{Auxílios Sociais (Bolsa Família/BPC)}}{\text{Arrecadação de Tributos Federais (RFB)}}$$

- **Razão > 1,0 (Estado Deficitário / Receptor Líquido)**: O estado recebe de volta mais dinheiro federal em auxílios e repasses do que recolhe em tributos para Brasília.
- **Razão < 1,0 (Estado Superavitário / Doador Líquido)**: O estado gera mais riqueza e arrecadação tributária federal do que recebe de volta da União.

---

## 💾 Schema no DuckDB (`pacto_federativo_balanco`)

```sql
CREATE TABLE IF NOT EXISTS pacto_federativo_balanco (
    uf_sigla VARCHAR PRIMARY KEY,
    uf_nome VARCHAR,
    regiao VARCHAR,
    ano INTEGER,
    arrecadacao_federal DOUBLE,   -- IRPF, IRPJ, COFINS, PIS, IPI (em R$ bilhões)
    transferencias_fpe_fpm DOUBLE, -- FPE + FPM recebidos (em R$ bilhões)
    auxilios_sociais_mds DOUBLE,   -- Bolsa Família + BPC pagos no estado (em R$ bilhões)
    total_recebido DOUBLE,         -- Transferências + Auxílios
    saldo_liquido DOUBLE,          -- Arrecadação - Total Recebido
    razao_retorno DOUBLE,          -- Total Recebido / Arrecadação
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pacto_regiao ON pacto_federativo_balanco(regiao);
CREATE INDEX IF NOT EXISTS idx_pacto_razao ON pacto_federativo_balanco(razao_retorno);
```

---

## 🚀 Como Executar

```bash
# Executa o relatório completo de dependência fiscal dos estados
uv run gov-skills balanco-federativo
```
