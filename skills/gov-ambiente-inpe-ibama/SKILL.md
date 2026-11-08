---
name: gov-ambiente-inpe-ibama
description: Coleta, ingere no DuckDB, consulta e cruza dados geoespaciais e fiscalizatórios do Meio Ambiente brasileiro - INPE (DETER alertas de desmatamento, PRODES taxas anuais e Queimadas) e IBAMA (Autos de Infração e Áreas Embargadas).
version: 1.0.0
metadata:
  domain: "Meio Ambiente, Clima e Fiscalização Ambiental"
  agency: "INPE (Instituto Nacional de Pesquisas Espaciais) & IBAMA"
  source_urls:
    - "https://terrabrasilis.dpi.inpe.br"
    - "https://queimadas.dgi.inpe.br/queimadas/dados-abertos"
    - "https://dadosabertos.ibama.gov.br"
  auth_required: false
  primary_keys: ["codigo_ibge", "bioma", "cpf_cnpj_infrator", "numero_auto_infracao"]
  target_tables: ["inpe_alertas_desmatamento", "ibama_autos_infracao", "ibama_areas_embargadas"]
---

# 🏛️ Skill: gov-ambiente-inpe-ibama (INPE TerraBrasilis & IBAMA)

O Brasil possui um dos sistemas de monitoramento por satélite mais avançados do mundo (INPE) e uma base pública de autuações e embargos ambientais (IBAMA).

---

## 🎯 Capacidades da Skill
1. **DETER & PRODES**: Alertas diários e polígonos de desmatamento na Amazônia Legal e no Cerrado.
2. **Queimadas**: Focos de calor diários captados pelos satélites Aqua, Terra e GOES.
3. **Autos de Infração e Embargos do IBAMA**: Multas ambientais aplicadas e fazendas/áreas embargadas com seus respectivos CNPJs e CPFs.
4. **Cruzamentos de Compliance & ESG**:
   - Descobrir se empresas vencedoras de licitações públicas ou compradoras de títulos públicos possuem embargos por desmatamento ilegal.
   - Cruzar municípios campeões de desmatamento com atividades econômicas do Novo CAGED.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS ibama_autos_infracao (
    numero_auto VARCHAR PRIMARY KEY,
    cpf_cnpj_infrator VARCHAR,
    cnpj_raiz VARCHAR,
    nome_infrator VARCHAR,
    tipo_infracao VARCHAR,
    valor_multa DOUBLE,
    codigo_ibge VARCHAR,
    municipio VARCHAR,
    uf VARCHAR,
    bioma VARCHAR,
    data_auto DATE,
    situacao_debito VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inpe_alertas_desmatamento (
    id_alerta VARCHAR PRIMARY KEY,
    data_deteccao DATE,
    area_hectares DOUBLE,
    bioma VARCHAR,
    uf VARCHAR,
    codigo_ibge VARCHAR,
    municipio VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ibama_cnpj ON ibama_autos_infracao(cpf_cnpj_infrator);
CREATE INDEX IF NOT EXISTS idx_ibama_ibge ON ibama_autos_infracao(codigo_ibge);
```
