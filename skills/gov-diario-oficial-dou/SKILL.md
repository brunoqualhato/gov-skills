---
name: gov-diario-oficial-dou
description: Coleta, ingere no DuckDB, consulta e processa atos normativos, decretos, portarias, nomeações e extratos de contratos publicados no Diário Oficial da União (Imprensa Nacional / INCom - Seções 1, 2 e 3 e Edições Extras).
version: 1.0.0
metadata:
  domain: "Publicidade Legal e Atos Oficiais"
  agency: "Imprensa Nacional / Casa Civil da Presidência da República"
  source_urls:
    - "https://www.in.gov.br"
    - "https://dados.gov.br"
  auth_required: false
  primary_keys: ["id_materia_dou", "data_publicacao", "secao"]
  target_tables: ["dou_publicacoes_atos"]
---

# 🏛️ Skill: gov-diario-oficial-dou (Diário Oficial da União)

O **Diário Oficial da União (DOU)** é o jornal oficial do Estado brasileiro. Tudo o que tem validade jurídica na administração pública federal só passa a vigorar após publicação no DOU.

---

## 🎯 Divisão das Seções do DOU
- **Seção 1**: Atos normativos (Leis, Decretos Presidenciais, Resoluções, Instruções Normativas e Portarias).
- **Seção 2**: Atos de pessoal (Nomeações, exonerações, aposentadorias e designações para cargos comissionados DAS/CCE).
- **Seção 3**: Contratos, editais de licitação, avisos de dispensa, atas de registro de preços e acordos bilaterais.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS dou_publicacoes_atos (
    id_materia_dou VARCHAR PRIMARY KEY,
    data_publicacao DATE,
    secao VARCHAR, -- Seção 1, 2, 3 ou Edição Extra
    orgao_emissor VARCHAR,
    titulo VARCHAR,
    subtitulo VARCHAR,
    tipo_ato VARCHAR, -- DECRETO, PORTARIA, NOMEAÇÃO, EXTRATO DE CONTRATO
    texto_resumo VARCHAR,
    texto_completo VARCHAR,
    url_publicacao VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dou_data ON dou_publicacoes_atos(data_publicacao);
CREATE INDEX IF NOT EXISTS idx_dou_orgao ON dou_publicacoes_atos(orgao_emissor);
```
