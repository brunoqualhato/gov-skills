---
name: gov-estatistica-ibge
description: Coleta, ingere no DuckDB, consulta e cruza dados geográficos, demográficos e estatísticos do IBGE (Malha Completa de 5.570 Municípios e API SIDRA - Censo, IPCA e PIB Municipal).
version: 1.0.0
metadata:
  domain: "Geografia, Demografia e Estatística Nacional"
  agency: "Instituto Brasileiro de Geografia e Estatística (IBGE)"
  source_urls:
    - "https://servicodados.ibge.gov.br/api/docs/localidades"
    - "https://apisidra.ibge.gov.br"
  auth_required: false
  primary_keys: ["codigo_ibge", "sigla_uf"]
  target_tables: ["ibge_municipios", "ibge_ufs", "ibge_indicadores_municipais"]
---

# 🏛️ Skill: gov-estatistica-ibge (IBGE Localidades & SIDRA)

O **IBGE** é o guardião da infraestrutura geoestatística nacional. O **Código IBGE de 7 dígitos** é a **chave primária geográfica universal** do Brasil, utilizada obrigatoriamente por todos os outros sistemas federais (DataSUS, Censo Escolar/INEP, Tesouro/Siconfi, PNCP e Fundo de Participação dos Municípios).

Esta skill permite ao agente:
1. **Baixar e persistir a tabela dimensional mestra de todos os 5.570 municípios do Brasil**, incluindo microrregiões, mesorregiões e regiões imediatas/intermediárias.
2. **Consultar indicadores demográficos e econômicos** da API SIDRA (População do Censo, PIB Municipal).
3. **Servir como base de enriquecimento geográfico** para cruzar com contratações públicas, transferências do Tesouro e leitos hospitalares.

---

## 📡 Endpoints Oficiais

- **API de Localidades (Municípios)**:
  `GET https://servicodados.ibge.gov.br/api/v1/localidades/municipios`
- **API de Localidades (Estados / UFs)**:
  `GET https://servicodados.ibge.gov.br/api/v1/localidades/estados`
- **API SIDRA (População Censo 2022 - Tabela 4709)**:
  `GET https://apisidra.ibge.gov.br/values/t/4709/v/93/p/last/n6/all`

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS ibge_municipios (
    codigo_ibge VARCHAR PRIMARY KEY,
    nome_municipio VARCHAR,
    uf_sigla VARCHAR,
    uf_nome VARCHAR,
    uf_codigo VARCHAR,
    regiao_nome VARCHAR,
    microrregiao_nome VARCHAR,
    mesorregiao_nome VARCHAR,
    regiao_imediata VARCHAR,
    regiao_intermediaria VARCHAR,
    populacao_censo INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ibge_uf ON ibge_municipios(uf_sigla);
CREATE INDEX IF NOT EXISTS idx_ibge_nome ON ibge_municipios(nome_municipio);
```

---

## 🚀 Como Executar

### 1. Ingestão da Tabela Mestra de Municípios
```bash
# Baixa e carrega todos os 5.570 municípios do Brasil no DuckDB
python skills/gov-estatistica-ibge/scripts/fetch_ibge.py --municipios
```

### 2. Consulta de Municípios
```bash
# Buscar por nome ou UF
python skills/gov-estatistica-ibge/scripts/query_ibge.py --nome "Campinas"
python skills/gov-estatistica-ibge/scripts/query_ibge.py --uf TO --limit 20
```

---

## 🔬 Consultas Analíticas e Cruzamentos Geográficos

### Cruzar Gastos do PNCP com Porte do Município
```sql
SELECT 
    m.nome_municipio,
    m.uf_sigla,
    m.regiao_nome,
    COUNT(c.id_contrato) AS total_contratos,
    SUM(c.valor_global) AS montante_contratado
FROM ibge_municipios m
JOIN pncp_contratos c ON m.codigo_ibge = c.municipio_ibge
GROUP BY m.nome_municipio, m.uf_sigla, m.regiao_nome
ORDER BY montante_contratado DESC
LIMIT 10;
```
