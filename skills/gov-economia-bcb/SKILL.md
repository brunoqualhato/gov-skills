---
name: gov-economia-bcb
description: Coleta, ingere no DuckDB, consulta e analisa dados macroeconômicos do Banco Central do Brasil (SGS - Séries Temporais e APIs Olinda - Câmbio PTAX, Expectativas Focus, Taxas de Juros e Pix).
version: 1.0.0
metadata:
  domain: "Economia e Política Monetária"
  agency: "Banco Central do Brasil (BACEN)"
  source_urls:
    - "https://dadosabertos.bcb.gov.br"
    - "https://olinda.bcb.gov.br"
    - "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
  auth_required: false
  primary_keys: ["codigo_serie", "data_referencia", "indicador", "moeda"]
  target_tables: ["bcb_series_temporais", "bcb_expectativas_focus", "bcb_cotacoes_moedas"]
---

# 🏛️ Skill: gov-economia-bcb (Banco Central do Brasil)

O **Banco Central do Brasil** disponibiliza duas das mais importantes fontes de dados financeiros e macroeconômicos abertos do país:
1. **SGS (Sistema Gerenciador de Séries Temporais)**: Mais de 20.000 séries históricas oficiais (Selic, IPCA, IGP-M, Reservas Internacionais, Dívida Líquida do Setor Público, Câmbio diário).
2. **API Olinda (OData)**: Plataforma aberta de alta velocidade para dados estruturados de Câmbio/PTAX, Expectativas de Mercado do Relatório Focus, Taxas de Juros por Banco e Estatísticas do Pix.

---

## 📡 Endpoints Oficiais

### 1. SGS (Séries Temporais)
- `GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json[&dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa]`
- **Códigos Principais**:
  - `432`: Meta Selic definida pelo Copom (% a.a.)
  - `11`: Taxa Selic apurada diária (% a.d.)
  - `12`: Taxa CDI anualizada (% a.a.)
  - `433`: IPCA - Variação mensal (% m/m)
  - `189`: IGP-M - Variação mensal
  - `1`: Câmbio Livre - Dólar americano (venda / diário)
  - `3545`: Reservas Internacionais (US$ milhões)

### 2. Olinda OData
- **Expectativas Focus**:
  `https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativaMercadoMensais?$top=100&$orderby=Data desc&$format=json`
- **Cotação de Moedas (PTAX)**:
  `https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@ini,dataFinalCotacao=@fim)?@ini='01-01-2024'&@fim='11-04-2024'&$format=json`

---

## 💾 Schema no DuckDB

```sql
-- Séries temporais macroeconômicas (Selic, IPCA, etc.)
CREATE TABLE IF NOT EXISTS bcb_series_temporais (
    codigo_serie INTEGER,
    nome_serie VARCHAR,
    data_referencia DATE,
    valor DOUBLE,
    unidade VARCHAR,
    PRIMARY KEY(codigo_serie, data_referencia)
);

-- Projeções de mercado (Relatório Focus)
CREATE TABLE IF NOT EXISTS bcb_expectativas_focus (
    indicador VARCHAR,
    data_referencia DATE,
    data_pesquisa DATE,
    mediana DOUBLE,
    media DOUBLE,
    desvio_padrao DOUBLE,
    minimo DOUBLE,
    maximo DOUBLE,
    numero_respondentes INTEGER,
    PRIMARY KEY(indicador, data_referencia, data_pesquisa)
);
```

---

## 🚀 Como Executar

### 1. Ingestão de Séries Principais
```bash
# Ingerir as séries fundamentais (Selic, IPCA, Dólar, CDI)
python skills/gov-economia-bcb/scripts/fetch_bcb.py --series-fundamentais

# Ingerir as últimas projeções do Focus
python skills/gov-economia-bcb/scripts/fetch_bcb.py --focus
```

### 2. Consultas Rápidas
```bash
# Consultar evolução da taxa Selic e IPCA
python skills/gov-economia-bcb/scripts/query_bcb.py series --codigo 432 --limit 12

# Consultar projeções do mercado Focus (IPCA, PIB, Selic)
python skills/gov-economia-bcb/scripts/query_bcb.py focus --indicador IPCA
```
