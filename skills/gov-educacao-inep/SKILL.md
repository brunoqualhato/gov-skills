---
name: gov-educacao-inep
description: Coleta, ingere no DuckDB, consulta e cruza dados educacionais do Ministério da Educação e INEP (Censo Escolar da Educação Básica, IDEB - Índice de Desenvolvimento da Educação Básica, Microdados do ENEM e Censo da Educação Superior).
version: 1.0.0
metadata:
  domain: "Educação Básica e Superior"
  agency: "Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP) / MEC"
  source_urls:
    - "https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["codigo_escola_inep", "codigo_ibge"]
  target_tables: ["inep_escolas_censo", "inep_ideb_municipios"]
---

# 🏛️ Skill: gov-educacao-inep (INEP / MEC)

O **INEP** é responsável pelos grandes censos e avaliações que medem a qualidade e a infraestrutura da educação no Brasil.

---

## 🎯 Capacidades da Skill
1. **Censo Escolar**: Cadastro e infraestrutura de mais de 180.000 escolas no Brasil (acesso à água potável, energia, internet, laboratórios, merenda, número de matrículas por etapa).
2. **IDEB**: Indicadores de fluxo e aprendizagem por escola, rede (municipal/estadual) e município.
3. **Cruzamento com Financiamento**:
   - Cruzar repasses do Fundeb (Siconfi) com a nota do IDEB do município.
   - Cruzar contratos de reformas de escolas e fornecimento de merenda no PNCP com os dados das escolas no INEP.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS inep_escolas_censo (
    codigo_escola VARCHAR PRIMARY KEY,
    nome_escola VARCHAR,
    dependencia_administrativa VARCHAR, -- Federal, Estadual, Municipal, Privada
    codigo_ibge VARCHAR,
    uf VARCHAR,
    municipio VARCHAR,
    situacao_funcionamento VARCHAR,
    tem_agua_potavel BOOLEAN,
    tem_energia_eletrica BOOLEAN,
    tem_esgoto BOOLEAN,
    tem_internet BOOLEAN,
    total_matriculas INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inep_ideb_municipios (
    codigo_ibge VARCHAR,
    ano INTEGER,
    etapa_ensino VARCHAR, -- Anos Iniciais, Anos Finais, Ensino Médio
    rede VARCHAR, -- Municipal, Estadual, Pública
    nota_ideb DOUBLE,
    PRIMARY KEY(codigo_ibge, ano, etapa_ensino, rede)
);
```
