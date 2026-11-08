---
name: gov-tesouro-siconfi
description: Coleta, ingere no DuckDB, consulta e cruza dados fiscais e orçamentários do Tesouro Nacional e Siconfi (Orçamento Federal LOA, Transferências Constitucionais FPM/FPE/Fundeb, Balanços de Prefeituras e Estados RREO/RGF e Dívida Pública).
version: 1.0.0
metadata:
  domain: "Orçamento Público, Finanças Fiscais e Transferências"
  agency: "Secretaria do Tesouro Nacional (STN) / Ministério da Fazenda"
  source_urls:
    - "https://apidatalake.tesouro.gov.br/docs/siconfi"
    - "https://www.tesourotransparente.gov.br"
  auth_required: false
  primary_keys: ["codigo_ibge", "ano_exercicio", "codigo_orgao_siafi", "tipo_transferencia"]
  target_tables: ["siconfi_transferencias", "siconfi_balancos_municipais", "tesouro_orcamento_loa"]
---

# 🏛️ Skill: gov-tesouro-siconfi (Tesouro Nacional & Siconfi)

O **Siconfi (Sistema de Informações Contábeis e Fiscais do Setor Público Brasileiro)** e o portal **Tesouro Transparente** são as fontes definitivas para saber para onde vai o dinheiro arrecadado pela União e quanto cada município e estado recebe.

---

## 📡 Endpoints Oficiais (API Siconfi)

- **Base URL**: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt`
- **Transferências Constitucionais e Legais**:
  `GET /transferencias?an_exercicio={ano}&id_ente={codigo_ibge}`
  (Fundo de Participação dos Municípios - FPM, FPE, Fundeb, ITR, Royalties do Petróleo).
- **RREO (Relatório Resumido de Execução Orçamentária)**:
  `GET /rreo?an_exercicio={ano}&nr_periodo={bimestre}&co_tipo_demonstrativo=RREO&id_ente={codigo_ibge}`
- **RGF (Relatório de Gestão Fiscal - Limites da Lei de Responsabilidade Fiscal)**:
  `GET /rgf?an_exercicio={ano}&nr_periodo={quadrimestre}&id_ente={codigo_ibge}`

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS siconfi_transferencias (
    id_transferencia VARCHAR PRIMARY KEY,
    ano_exercicio INTEGER,
    mes_exercicio INTEGER,
    codigo_ibge VARCHAR,
    uf VARCHAR,
    tipo_transferencia VARCHAR, -- FPM, FPE, FUNDEB, ROYALTIES, SUS
    valor_bruto DOUBLE,
    valor_deducoes DOUBLE,
    valor_liquido DOUBLE,
    data_repasse DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_siconfi_ibge ON siconfi_transferencias(codigo_ibge);
CREATE INDEX IF NOT EXISTS idx_siconfi_tipo ON siconfi_transferencias(tipo_transferencia);
```

---

## 🔬 Consulta: Repasses Federais x Contratos Públicos Locais
```sql
SELECT 
    m.nome_municipio,
    m.uf_sigla,
    SUM(t.valor_liquido) AS total_repasses_fpm_fundeb,
    SUM(c.valor_global) AS total_contratos_licitados
FROM ibge_municipios m
JOIN siconfi_transferencias t ON m.codigo_ibge = t.codigo_ibge
LEFT JOIN pncp_contratos c ON m.codigo_ibge = c.municipio_ibge
GROUP BY m.nome_municipio, m.uf_sigla
ORDER BY total_repasses_fpm_fundeb DESC
LIMIT 10;
```
