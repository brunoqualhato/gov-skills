---
name: gov-energia-combustiveis-anp
description: Coleta, ingere no DuckDB, consulta e cruza dados oficiais de preços médios, mínimos e máximos de combustíveis automotivos (Gasolina, Etanol, Diesel S10 e GNV) da Agência Nacional do Petróleo (ANP).
version: 1.0.0
metadata:
  domain: "Energia, Combustíveis e Regulação de Preços"
  agency: "Agência Nacional do Petróleo, Gás Natural e Biocombustíveis (ANP)"
  source_urls:
    - "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["codigo_ibge", "produto", "data_coleta", "cnpj_revenda"]
  target_tables: ["anp_precos_combustiveis"]
---

# 🏛️ Skill: gov-energia-combustiveis-anp (Agência Nacional do Petróleo)

A **ANP** realiza o Levantamento de Preços de Combustíveis (LPC) cobrindo semanalmente milhares de postos revendedores em todo o Brasil. Esse conjunto de dados fornece a referência oficial de preços de mercado para o abastecimento de veículos.

---

## 🎯 Capacidades da Skill
1. **Preços de Referência**: Gasolina Comum, Gasolina Aditivada, Etanol Hidratado, Óleo Diesel S10, Diesel S500 e Gás Natural Veicular (GNV).
2. **Nível Posto e Município**: Preços de bomba, distribuidora, margem de revenda, bandeira e endereço do posto.
3. **Cruzamentos de Auditoria de Alto Impacto**:
   - **Sobrepreço em Frotas Municipais**: Comparar preços unitários de combustíveis comprados por prefeituras no PNCP com a média semanal da ANP na mesma cidade.
   - **Cota Parlamentar (CEAP)**: Verificar reembolsos de abastecimento de deputados e senadores em postos com preços discrepantes.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS anp_precos_combustiveis (
    id_coleta VARCHAR PRIMARY KEY,
    codigo_ibge VARCHAR,
    municipio VARCHAR,
    uf VARCHAR,
    produto VARCHAR, -- GASOLINA, ETANOL, DIESEL S10, GNV
    data_coleta DATE,
    valor_venda DOUBLE,
    valor_compra DOUBLE,
    unidade_medida VARCHAR, -- R$ / litro ou R$ / m3
    bandeira VARCHAR,
    cnpj_revenda VARCHAR,
    cnpj_raiz_revenda VARCHAR,
    nome_posto VARCHAR,
    endereco VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_anp_ibge_prod ON anp_precos_combustiveis(codigo_ibge, produto);
CREATE INDEX IF NOT EXISTS idx_anp_cnpj ON anp_precos_combustiveis(cnpj_revenda);
```
