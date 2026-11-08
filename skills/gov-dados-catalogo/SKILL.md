---
name: gov-dados-catalogo
description: Explora, pesquisa e cataloga metadados de todos os conjuntos de dados públicos federais do Brasil via API CKAN do Portal Brasileiro de Dados Abertos (dados.gov.br).
version: 1.0.0
metadata:
  domain: "Catálogo de Metadados e Descoberta de Dados"
  agency: "Governo Digital / Ministério da Gestão e Inovação (MGI)"
  source_urls:
    - "https://dados.gov.br"
    - "https://dados.gov.br/api/publico"
  auth_required: false
  primary_keys: ["id_dataset", "organizacao_id"]
  target_tables: ["catalogo_conjuntos_dados", "catalogo_recursos_arquivos"]
---

# 🏛️ Skill: gov-dados-catalogo (Meta-catálogo dados.gov.br)

O portal **dados.gov.br** é o catálogo oficial centralizador de todos os planos de dados abertos da Administração Pública Federal brasileira. Esta skill atua como um **rastreador e indexador contínuo**, descobrindo novos datasets e APIs publicados por qualquer ministério, autarquia ou universidade federal.

---

## 📡 API do Catálogo (CKAN)

- **Busca de Conjuntos de Dados**:
  `GET https://dados.gov.br/api/publico/conjuntos-dados?q={termo}&pagina=1`
- **Detalhes de um Conjunto e Recursos**:
  `GET https://dados.gov.br/api/publico/conjuntos-dados/{id}`

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS catalogo_conjuntos_dados (
    id_dataset VARCHAR PRIMARY KEY,
    titulo VARCHAR,
    nome_identificador VARCHAR,
    orgao_responsavel VARCHAR,
    descricao VARCHAR,
    frequencia_atualizacao VARCHAR,
    qtd_recursos INTEGER,
    url_portal VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
