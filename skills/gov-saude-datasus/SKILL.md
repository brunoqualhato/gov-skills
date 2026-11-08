---
name: gov-saude-datasus
description: Coleta, ingere no DuckDB, consulta e cruza dados do Sistema Único de Saúde (DataSUS / OpenDataSUS) - CNES (Cadastro Nacional de Estabelecimentos de Saúde, Leitos e Equipes), SIHSUS (Internações Hospitalares), SIM (Mortalidade) e Vigilância Epidemiológica.
version: 1.0.0
metadata:
  domain: "Saúde Pública e Sistema Único de Saúde (SUS)"
  agency: "Ministério da Saúde / DataSUS"
  source_urls:
    - "https://datasus.saude.gov.br"
    - "https://opendatasus.saude.gov.br"
    - "ftp://ftp.datasus.gov.br/dissemin/publicos"
  auth_required: false
  primary_keys: ["codigo_cnes", "cnpj_mantenedora", "codigo_ibge"]
  target_tables: ["datasus_estabelecimentos_cnes", "datasus_leitos_hospitalares"]
---

# 🏛️ Skill: gov-saude-datasus (DataSUS / OpenDataSUS)

O **DataSUS** gerencia a maior base de dados de saúde pública das Américas. Ele abrange desde a infraestrutura física hospitalar até os procedimentos de alta complexidade financiados pelo SUS.

---

## 🎯 Capacidades da Skill
1. **CNES (Estabelecimentos de Saúde)**: Mapeamento de hospitais, UPAs, postos de saúde, clínicas e maternidades públicas e privadas credenciadas.
2. **Capacidade Instalada**: Contagem de leitos de UTI, leitos de internação clínica, leitos cirúrgicos e respiradores por município.
3. **Cruzamento com CNPJs e Contratos**:
   - Descobrir quais organizações sociais (OSs) e empresas privadas administram unidades de saúde públicas.
   - Cruzar compras de medicamentos e equipamentos no PNCP com hospitais do SUS.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS datasus_estabelecimentos_cnes (
    codigo_cnes VARCHAR PRIMARY KEY,
    nome_fantasia VARCHAR,
    razao_social VARCHAR,
    cnpj_mantenedora VARCHAR,
    cnpj_raiz_mantenedora VARCHAR,
    tipo_unidade VARCHAR,
    natureza_organizacao VARCHAR,
    codigo_ibge VARCHAR,
    uf VARCHAR,
    municipio VARCHAR,
    possui_atendimento_urgencia BOOLEAN,
    possui_leitos_uti BOOLEAN,
    qtd_leitos_uti INTEGER,
    qtd_leitos_internacao INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_datasus_ibge ON datasus_estabelecimentos_cnes(codigo_ibge);
CREATE INDEX IF NOT EXISTS idx_datasus_cnpj ON datasus_estabelecimentos_cnes(cnpj_mantenedora);
```
