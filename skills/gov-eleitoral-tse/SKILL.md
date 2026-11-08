---
name: gov-eleitoral-tse
description: Coleta, ingere no DuckDB, consulta e cruza dados do Tribunal Superior Eleitoral (TSE) - Candidaturas, Bens Declarados de Políticos, Doações e Despesas de Campanhas Eleitorais e Resultados de Pleitos.
version: 1.0.0
metadata:
  domain: "Eleições, Partidos e Financiamento Político"
  agency: "Tribunal Superior Eleitoral (TSE)"
  source_urls:
    - "https://dadosabertos.tse.jus.br"
    - "https://divulgacandcontas.tse.jus.br"
  auth_required: false
  primary_keys: ["sq_candidato", "nr_cpf_candidato", "nr_cpf_cnpj_doador", "codigo_ibge"]
  target_tables: ["tse_candidatos", "tse_bens_declarados", "tse_doacoes"]
---

# 🏛️ Skill: gov-eleitoral-tse (Tribunal Superior Eleitoral)

O repositório de dados abertos do **TSE** é o pilar da transparência eleitoral no Brasil. Os dados de doações e bens declarados fornecem uma das mais ricas oportunidades de cruzamento com as contas públicas do Poder Executivo e Legislativo.

---

## 🎯 Capacidades da Skill
1. **Ingestão de Candidaturas**: Nome na urna, partido, cargo disputado, UF, município e situação da candidatura.
2. **Declaração de Bens**: Evolução patrimonial declarada de candidatos eleitos (imóveis, empresas, participações societárias).
3. **Doações de Campanha**: Identificação de CPFs e CNPJs que financiaram campanhas políticas.
4. **Cruzamentos de Ouro**:
   - Doadores de campanha que se tornaram sócios de empresas vencedoras de licitações no governo eleito.
   - Políticos eleitos que possuem cotas em empresas que continuam faturando no serviço público.

---

## 💾 Schema no DuckDB

```sql
CREATE TABLE IF NOT EXISTS tse_candidatos (
    sq_candidato VARCHAR PRIMARY KEY,
    ano_eleicao INTEGER,
    nr_candidato VARCHAR,
    nm_candidato VARCHAR,
    nm_urna VARCHAR,
    nr_cpf_candidato VARCHAR,
    sg_partido VARCHAR,
    ds_cargo VARCHAR,
    sg_uf VARCHAR,
    codigo_ibge VARCHAR,
    ds_situacao_candidatura VARCHAR,
    ds_resultado_eleicao VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tse_doacoes (
    id_doacao VARCHAR PRIMARY KEY,
    ano_eleicao INTEGER,
    sq_candidato VARCHAR,
    nr_cpf_cnpj_doador VARCHAR,
    cnpj_raiz_doador VARCHAR,
    nm_doador VARCHAR,
    vr_receita DOUBLE,
    dt_receita DATE,
    ds_origem_receita VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tse_doador ON tse_doacoes(nr_cpf_cnpj_doador);
CREATE INDEX IF NOT EXISTS idx_tse_cpf_cand ON tse_candidatos(nr_cpf_candidato);
```

---

## 🔬 Consulta Investigativa: Doadores Vencedores de Licitações
```sql
SELECT 
    d.nm_doador,
    d.nr_cpf_cnpj_doador,
    d.vr_receita AS total_doado_campanha,
    c.nm_urna AS candidato_beneficiado,
    c.sg_partido,
    p.numero_contrato,
    p.orgao_nome,
    p.valor_global AS valor_contrato_governo
FROM tse_doacoes d
JOIN tse_candidatos c ON d.sq_candidato = c.sq_candidato
JOIN pncp_contratos p ON d.cnpj_raiz_doador = p.cnpj_raiz_fornecedor
WHERE c.ds_resultado_eleicao = 'ELEITO'
ORDER BY p.valor_global DESC;
```
