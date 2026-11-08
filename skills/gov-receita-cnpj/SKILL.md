---
name: gov-receita-cnpj
description: Consulta, ingere no DuckDB e cruza dados cadastrais da base oficial de CNPJs da Receita Federal do Brasil (Razão Social, Quadro de Sócios e Administradores QSA, Capital Social, CNAEs, Filiais e Simples Nacional/MEI).
version: 1.0.0
metadata:
  domain: "Empresas e Atividade Econômica"
  agency: "Secretaria Especial da Receita Federal do Brasil (RFB)"
  source_urls:
    - "https://dadosabertos.rfb.gov.br/CNPJ"
    - "https://brasilapi.com.br/api/cnpj/v1"
    - "https://minhareceita.org"
  auth_required: false
  primary_keys: ["cnpj", "cnpj_raiz", "cpf_cnpj_socio"]
  target_tables: ["rfb_empresas", "rfb_socios"]
---

# 🏛️ Skill: gov-receita-cnpj (Receita Federal do Brasil - CNPJ & QSA)

A base de dados abertos da Receita Federal do Brasil é o **coração das investigações corporativas e auditorias públicas**. Nela residem mais de 50 milhões de pessoas jurídicas registradas no país, com a estrutura completa de sócios (QSA).

Esta skill permite ao agente:
1. **Consultar CNPJs pontualmente em tempo real** via mirrors públicos abertos (sem token e com alta disponibilidade) e salvá-los no DuckDB.
2. **Ingerir dados em lote** dos dumps mensais oficiais (`dadosabertos.rfb.gov.br`).
3. **Mapear a teia societária**: Descobrir todas as empresas ligadas a um mesmo sócio (pessoa física ou jurídica).
4. **Cruzar com Contratos do PNCP e Cota Parlamentar**: Revelar se sócios de empresas contratadas pelo governo têm outras empresas, vínculos políticos ou sanções ativas.

---

## 💾 Schema no DuckDB

```sql
-- Empresas / Estabelecimentos
CREATE TABLE IF NOT EXISTS rfb_empresas (
    cnpj VARCHAR PRIMARY KEY,
    cnpj_raiz VARCHAR,
    razao_social VARCHAR,
    nome_fantasia VARCHAR,
    situacao_cadastral VARCHAR,
    data_inicio_atividade DATE,
    cnae_principal VARCHAR,
    cnae_descricao VARCHAR,
    natureza_juridica VARCHAR,
    capital_social DOUBLE,
    porte VARCHAR,
    uf VARCHAR,
    municipio VARCHAR,
    codigo_ibge VARCHAR,
    opcao_simples BOOLEAN,
    opcao_mei BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quadro de Sócios e Administradores (QSA)
CREATE TABLE IF NOT EXISTS rfb_socios (
    id_socio VARCHAR PRIMARY KEY,
    cnpj_raiz VARCHAR,
    identificador_socio VARCHAR, -- Pessoa Física (1), Jurídica (2), Estrangeiro (3)
    nome_socio VARCHAR,
    cpf_cnpj_socio VARCHAR,
    qualificacao_socio VARCHAR,
    data_entrada_sociedade DATE,
    faixa_etaria VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rfb_cnpj_raiz ON rfb_empresas(cnpj_raiz);
CREATE INDEX IF NOT EXISTS idx_rfb_socios_raiz ON rfb_socios(cnpj_raiz);
CREATE INDEX IF NOT EXISTS idx_rfb_socios_nome ON rfb_socios(nome_socio);
```

---

## 🚀 Como Executar

### 1. Consulta e Ingestão de CNPJ
```bash
# Consulta um CNPJ na API aberta e persiste no DuckDB junto com os sócios
python skills/gov-receita-cnpj/scripts/fetch_cnpj.py lookup 00000000000191
python skills/gov-receita-cnpj/scripts/fetch_cnpj.py lookup 02012862000160  # TAM Linhas Aéreas
```

### 2. Ingestão em Lote dos Fornecedores do PNCP e CEAP
```bash
# Ingerir automaticamente o cadastro de todas as empresas encontradas no PNCP e na CEAP
python skills/gov-receita-cnpj/scripts/fetch_cnpj.py enriquecer-fornecedores --limit 10
```

### 3. Consultas e Teia Societária
```bash
# Exibir dados e sócios de uma empresa
python skills/gov-receita-cnpj/scripts/query_cnpj.py empresa --cnpj 00000000000191

# Pesquisar todas as empresas onde uma pessoa é sócia
python skills/gov-receita-cnpj/scripts/query_cnpj.py socio --nome "SILVA"
```

---

## 🔬 Consultas Analíticas e Cruzamentos

### Cruzamento: Sócios que receberam dinheiro da Câmara e ganharam Licitação
```sql
SELECT 
    s.nome_socio,
    s.qualificacao_socio,
    e.razao_social,
    e.cnpj,
    c.valor_gasto_cota,
    p.valor_contrato_governo
FROM rfb_socios s
JOIN rfb_empresas e ON s.cnpj_raiz = e.cnpj_raiz
LEFT JOIN (
    SELECT cnpj_raiz_fornecedor, SUM(valor_liquido) AS valor_gasto_cota
    FROM camara_ceap_despesas GROUP BY cnpj_raiz_fornecedor
) c ON e.cnpj_raiz = c.cnpj_raiz_fornecedor
LEFT JOIN (
    SELECT cnpj_raiz_fornecedor, SUM(valor_global) AS valor_contrato_governo
    FROM pncp_contratos GROUP BY cnpj_raiz_fornecedor
) p ON e.cnpj_raiz = p.cnpj_raiz_fornecedor
WHERE c.valor_gasto_cota > 0 AND p.valor_contrato_governo > 0
ORDER BY p.valor_contrato_governo DESC;
```
