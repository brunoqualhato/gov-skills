---
name: gov-comex-mdic-secex
description: Coleta, ingere no DuckDB, consulta e cruza dados oficiais de comércio exterior brasileiro (Comex Stat / MDIC - SECEX), mapeando balança comercial, exportações e importações por município, país de destino e código NCM.
version: 1.0.0
metadata:
  domain: "Comércio Exterior, Indústria e Balança Comercial"
  agency: "Secretaria de Comércio Exterior (SECEX) / MDIC"
  source_urls:
    - "https://www.gov.br/produtividade-e-comercio-exterior/pt-br/assuntos/comercio-exterior/estatisticas/base-de-dados-bruta"
    - "https://comexstat.mdic.gov.br"
  auth_required: false
  primary_keys: ["ano", "mes", "tipo_operacao", "codigo_ibge", "codigo_ncm"]
  target_tables: ["comex_balanca_comercial"]
---

# 🏛️ Skill: gov-comex-mdic-secex (Comex Stat / MDIC)

O **Comex Stat** disponibiliza os microdados detalhados de todas as operações de exportação e importação registradas no Siscomex, categorizadas pela Nomenclatura Comum do Mercosul (NCM) e pelo município do domicílio fiscal das empresas operadoras.

---

## 🎯 Capacidades da Skill
1. **Balança Comercial por Município**: Saldo comercial (Superávit/Déficit), valor FOB em dólares e volume em quilogramas líquidos de cada um dos 5.570 municípios.
2. **Produtos e Mercados**: Principais commodities e manufaturas exportadas (soja, minério, petróleo, carne bovina, calçados, aviões) e países parceiros comerciais.
3. **Cruzamentos Econômicos**:
   - Cruzar crescimento de exportações municipais com arrecadação de tributos (Siconfi/Receita Federal) e criação de empregos (Novo CAGED).

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS comex_balanca_comercial (
    id_operacao VARCHAR PRIMARY KEY,
    ano INTEGER,
    mes INTEGER,
    tipo_operacao VARCHAR, -- EXPORTACAO, IMPORTACAO
    codigo_ibge VARCHAR,
    municipio VARCHAR,
    uf VARCHAR,
    codigo_ncm VARCHAR,
    descricao_ncm VARCHAR,
    pais_parceiro VARCHAR,
    valor_fob_usd DOUBLE,
    peso_liquido_kg DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_comex_ibge ON comex_balanca_comercial(codigo_ibge);
CREATE INDEX IF NOT EXISTS idx_comex_ncm ON comex_balanca_comercial(codigo_ncm);
```
