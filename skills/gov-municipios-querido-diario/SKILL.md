---
name: gov-municipios-querido-diario
description: Coleta, ingere no DuckDB e pesquisa atos, licitações, decretos e dispensas de contratação em milhares de Diários Oficiais Municipais (DOMs) de todo o Brasil via API do Querido Diário (Open Knowledge Brasil).
version: 1.0.0
metadata:
  domain: "Publicidade Municipal e Diários Oficiais dos Municípios"
  agency: "Open Knowledge Brasil (OKBR) / Municípios Brasileiros"
  source_urls:
    - "https://queridodiario.ok.org.br"
    - "https://queridodiario.ok.org.br/api/docs"
  auth_required: false
  primary_keys: ["id_publicacao", "codigo_ibge", "data_publicacao"]
  target_tables: ["querido_diario_publicacoes"]
---

# 🏛️ Skill: gov-municipios-querido-diario (Querido Diário - OKBR)

O **Querido Diário** é um projeto de código aberto da Open Knowledge Brasil (OKBR) que liberta e indexa os Diários Oficiais dos Municípios brasileiros, permitindo busca textual por licitações, compras emergenciais e atos de prefeitos.

---

## 📡 API Oficial

- **Base URL**: `https://queridodiario.ok.org.br/api`
- **Busca Textual em Diários**:
  `GET /gazettes?querystring={termo}&territory_ids={codigo_ibge}&since={YYYY-MM-DD}&size={10}`

---

## 💾 Schema no DuckDB (`querido_diario_publicacoes`)

```sql
CREATE TABLE IF NOT EXISTS querido_diario_publicacoes (
    id_publicacao VARCHAR PRIMARY KEY,
    codigo_ibge VARCHAR,
    nome_municipio VARCHAR,
    uf_sigla VARCHAR,
    data_publicacao DATE,
    termo_pesquisado VARCHAR,
    trecho_destaque VARCHAR,
    url_pdf VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qd_ibge ON querido_diario_publicacoes(codigo_ibge);
CREATE INDEX IF NOT EXISTS idx_qd_data ON querido_diario_publicacoes(data_publicacao);
```

---

## 🚀 Como Executar

```bash
# Pesquisar compras suspeitas ou termos em diários municipais
python skills/gov-municipios-querido-diario/scripts/fetch_querido_diario.py search --termo "mouse" --limit 20
python skills/gov-municipios-querido-diario/scripts/fetch_querido_diario.py search --termo "dispensa de licitacao" --limit 20
```
