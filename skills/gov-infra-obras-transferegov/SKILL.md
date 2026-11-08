---
name: gov-infra-obras-transferegov
description: Coleta, ingere no DuckDB, consulta e cruza dados de transferências voluntárias da União (Transferegov / SICONV) e obras públicas federais (Obrasgov.br / Painel Obras Brasil), monitorando obras paralisadas, prazos e fornecedores.
version: 1.0.0
metadata:
  domain: "Infraestrutura, Convênios e Obras Públicas"
  agency: "Ministério da Gestão e da Inovação em Serviços Públicos (MGI)"
  source_urls:
    - "https://www.transferegov.sistema.gov.br"
    - "https://painel.obrasgov.gestao.gov.br"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["numero_convenio", "id_obra", "codigo_ibge", "cnpj_executor"]
  target_tables: ["transferegov_convenios", "obrasgov_obras_publicas"]
---

# 🏛️ Skill: gov-infra-obras-transferegov (Transferegov & Obrasgov)

O **Transferegov** (antigo SICONV) operacionaliza todas as transferências voluntárias de recursos da União para Estados, Municípios e Organizações da Sociedade Civil (OSCs). O **Obrasgov.br** é o painel central de georreferenciamento e acompanhamento físico-financeiro das obras públicas federais.

---

## 🎯 Capacidades da Skill
1. **Monitoramento de Convênios**: Repasses voluntários, contrapartidas, valores liberados e prestação de contas.
2. **Radar de Obras Paralisadas**: Identificação de creches, escolas, hospitais, pontes e pavimentações paralisadas ou atrasadas.
3. **Cruzamentos de Auditoria Forense**:
   - **Fornecedores Recidivistas**: Empreiteiras que abandonaram obras em um município e continuam vencendo licitações no PNCP em outros municípios.
   - **Aditivos Excessivos**: Obras que receberam aditivos acima do limite legal de 25% (Lei 14.133/21 e Lei 8.666/93).

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS transferegov_convenios (
    numero_convenio VARCHAR PRIMARY KEY,
    ano_convenio INTEGER,
    orgao_concedente VARCHAR,
    codigo_ibge_proponente VARCHAR,
    municipio_proponente VARCHAR,
    uf_proponente VARCHAR,
    objeto VARCHAR,
    situacao_convenio VARCHAR,
    valor_global DOUBLE,
    valor_repasse DOUBLE,
    valor_contrapartida DOUBLE,
    valor_pago DOUBLE,
    data_inicio DATE,
    data_fim DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS obrasgov_obras_publicas (
    id_obra VARCHAR PRIMARY KEY,
    numero_convenio VARCHAR,
    nome_obra VARCHAR,
    codigo_ibge VARCHAR,
    municipio VARCHAR,
    uf VARCHAR,
    situacao_obra VARCHAR, -- PARALISADA, EM EXECUCAO, CONCLUIDA, ATRASADA
    motivo_paralisacao VARCHAR,
    cnpj_executor VARCHAR,
    cnpj_raiz_executor VARCHAR,
    razao_social_executor VARCHAR,
    valor_investimento DOUBLE,
    percentual_execucao DOUBLE,
    data_inicio DATE,
    data_prevista_conclusao DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_obras_cnpj ON obrasgov_obras_publicas(cnpj_executor);
CREATE INDEX IF NOT EXISTS idx_obras_ibge ON obrasgov_obras_publicas(codigo_ibge);
CREATE INDEX IF NOT EXISTS idx_obras_situacao ON obrasgov_obras_publicas(situacao_obra);
```
