---
name: gov-compras-pncp
description: Coleta, ingere no DuckDB, consulta e cruza dados do Portal Nacional de Contratações Públicas (PNCP) e Compras.gov.br (Licitações, Editais, Contratos e Atas de Registro de Preços sob a Lei 14.133/2021).
version: 1.0.0
metadata:
  domain: "Contratações Públicas e Licitações"
  agency: "Governo Federal / Ministério da Gestão e da Inovação em Serviços Públicos (MGI)"
  source_urls:
    - "https://pncp.gov.br"
    - "https://pncp.gov.br/api/consulta/swagger-ui/index.html"
  auth_required: false
  primary_keys: ["ni_fornecedor", "cnpj_orgao", "numero_contrato", "codigo_ibge"]
  target_tables: ["pncp_contratos", "pncp_itens_contrato"]
---

# 🏛️ Skill: gov-compras-pncp (Portal Nacional de Contratações Públicas)

O **PNCP** é o sistema central obrigatório instituído pela Nova Lei de Licitações (Lei nº 14.133/2021) para divulgação centralizada de todos os atos de compras públicas do Brasil (União, Estados e Municípios).

Esta skill permite ao agente:
1. **Baixar contratos e licitações** diretamente da API pública do PNCP (sem necessidade de token ou cadastro).
2. **Armazenar de forma estruturada no DuckDB local** (`pncp_contratos`).
3. **Cruzar fornecedores públicos com seus CNPJs**, verificando quadros societários (Receita Federal), histórico de sanções (CGU CEIS/CNEP) e doações eleitorais (TSE).

---

## 📡 Endpoints Oficiais da API

- **Base URL Consulta**: `https://pncp.gov.br/api/consulta/v1`
- **Base URL Transacional**: `https://pncp.gov.br/api/pncp/v1`
- **Swagger / OpenAPI**: `https://pncp.gov.br/api/consulta/swagger-ui/index.html`

### Endpoints Principais:
1. `GET /consulta/v1/contratos`:
   - Parâmetros: `dataInicial` (YYYYMMDD), `dataFinal` (YYYYMMDD), `codigoModalidadeContratacao`, `uf`, `municipioIbge`, `pagina`, `tamanhoPagina` (máx 50).
2. `GET /consulta/v1/contratacoes/publicacao`:
   - Licitações publicadas por intervalo de datas.
3. `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}`:
   - Detalhamento completo do contrato com itens e valores unitários.

---

## 💾 Schema no DuckDB (`pncp_contratos`)

```sql
CREATE TABLE IF NOT EXISTS pncp_contratos (
    id_contrato VARCHAR PRIMARY KEY,
    numero_contrato VARCHAR,
    ano_contrato INTEGER,
    tipo_contrato VARCHAR,
    orgao_cnpj VARCHAR,
    orgao_nome VARCHAR,
    orgao_esfera VARCHAR,
    orgao_uf VARCHAR,
    municipio_ibge VARCHAR,
    ni_fornecedor VARCHAR,
    cnpj_raiz_fornecedor VARCHAR,
    nome_fornecedor VARCHAR,
    tipo_fornecedor VARCHAR,
    objeto VARCHAR,
    valor_inicial DOUBLE,
    valor_global DOUBLE,
    data_assinatura DATE,
    data_inicio_vigencia DATE,
    data_fim_vigencia DATE,
    categoria_processo VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pncp_fornecedor ON pncp_contratos(ni_fornecedor);
CREATE INDEX IF NOT EXISTS idx_pncp_cnpj_raiz ON pncp_contratos(cnpj_raiz_fornecedor);
CREATE INDEX IF NOT EXISTS idx_pncp_ibge ON pncp_contratos(municipio_ibge);
CREATE INDEX IF NOT EXISTS idx_pncp_orgao ON pncp_contratos(orgao_cnpj);
```

---

## 🚀 Como Executar

### 1. Ingestão de Contratos Recentes ou por Filtro
```bash
# Ingestão de contratos recentes (últimos 7 dias ou intervalo de datas)
python skills/gov-compras-pncp/scripts/fetch_pncp.py --dias 7 --max-paginas 5

# Coleta por UF específica
python skills/gov-compras-pncp/scripts/fetch_pncp.py --uf DF --dias 15
```

### 2. Consulta Rápida via CLI
```bash
# Buscar contratos por CNPJ do fornecedor ou termo no objeto
python skills/gov-compras-pncp/scripts/query_pncp.py --fornecedor "00000000000191"
python skills/gov-compras-pncp/scripts/query_pncp.py --objeto "software" --limit 15
```

---

## 🔬 Consultas Analíticas e Cruzamentos

### 1. Maiores Fornecedores Contratados
```sql
SELECT 
    nome_fornecedor,
    ni_fornecedor,
    COUNT(*) AS total_contratos,
    SUM(valor_global) AS montante_total
FROM pncp_contratos
GROUP BY nome_fornecedor, ni_fornecedor
ORDER BY montante_total DESC
LIMIT 10;
```

### 2. Cruzamento com Sanções CGU (Detectar Contratos de Empresas Punidas)
```sql
SELECT 
    c.numero_contrato,
    c.orgao_nome,
    c.nome_fornecedor,
    c.ni_fornecedor,
    c.valor_global,
    s.tipo_sancao,
    s.orgao_sancionador,
    s.data_inicio_sancao
FROM pncp_contratos c
JOIN cgu_sancoes s ON c.cnpj_raiz_fornecedor = s.cnpj_raiz
WHERE c.data_assinatura >= s.data_inicio_sancao;
```
