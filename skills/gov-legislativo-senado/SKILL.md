---
name: gov-legislativo-senado
description: Coleta, ingere no DuckDB, consulta e cruza dados abertos do Senado Federal brasileiro (Senadores em exercício, Proposições Legislativas e Matérias, Votações Nominais e Verba Indenizatória CEAPS).
version: 1.0.0
metadata:
  domain: "Poder Legislativo Federal (Senado)"
  agency: "Senado Federal"
  source_urls:
    - "https://legis.senado.leg.br/dadosabertos/docs/ui/index.html"
  auth_required: false
  primary_keys: ["codigo_parlamentar", "cnpj_cpf_fornecedor", "codigo_materia"]
  target_tables: ["senado_senadores", "senado_ceaps_despesas"]
---

# 🏛️ Skill: gov-legislativo-senado (Senado Federal)

A API de Dados Abertos do **Senado Federal** provê informações estruturadas sobre a Câmara Alta do Congresso Nacional, complementando a visão do Poder Legislativo ao lado da Câmara dos Deputados.

---

## 📡 Endpoints Oficiais

- **Base URL**: `https://legis.senado.leg.br/dadosabertos`
- **Senadores em Exercício**:
  `GET /senador/lista/atual`
- **Matérias / Projetos de Lei**:
  `GET /materia/pesquisa/lista`
- **Verba Indenizatória (CEAPS)**:
  `GET /dados/ceaps/{ano}`

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS senado_senadores (
    codigo_parlamentar INTEGER PRIMARY KEY,
    nome_parlamentar VARCHAR,
    nome_completo VARCHAR,
    sigla_partido VARCHAR,
    sigla_uf VARCHAR,
    email VARCHAR,
    url_foto VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS senado_ceaps_despesas (
    id_despesa VARCHAR PRIMARY KEY,
    codigo_parlamentar INTEGER,
    ano INTEGER,
    mes INTEGER,
    tipo_despesa VARCHAR,
    data_despesa DATE,
    valor_reembolsado DOUBLE,
    fornecedor_nome VARCHAR,
    cnpj_cpf_fornecedor VARCHAR,
    cnpj_raiz_fornecedor VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
