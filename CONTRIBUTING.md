# Guia de Contribuição: gov-skills

Obrigado por ajudar a construir o maior repositório aberto de inteligência de dados públicos do Brasil!

---

## 📐 Padrão Obrigatório de uma Skill

Toda skill adicionada ao diretório `skills/` deve seguir rigorosamente a convenção:

```plaintext
skills/gov-[dominio]-[orgao]/
├── SKILL.md                  # Documentação completa e guia para o agente de IA
└── scripts/
    ├── fetch_[dominio].py    # Script de coleta e persistência no DuckDB
    └── query_[dominio].py    # CLI rápido de consulta formatada
```

---

## 📝 Estrutura do `SKILL.md`

Todo `SKILL.md` deve conter o frontmatter YAML com metadados obrigatórios:

```yaml
---
name: gov-nome-da-skill
description: Resumo conciso de até duas linhas sobre a finalidade da skill.
version: 1.0.0
metadata:
  domain: "Categoria do Dado"
  agency: "Órgão Responsável"
  source_urls: ["https://link-oficial.gov.br"]
  auth_required: false # ou true se exigir token
  auth_env_vars: ["MINHA_VAR_KEY"] # opcional
  primary_keys: ["cnpj", "codigo_ibge"]
  target_tables: ["tabela_duckdb"]
---
```

---

## 🔑 Regras de Normalização (Core)

Ao processar novos dados, sempre utilize as funções do módulo `core.normalizers`:
- `normalize_cnpj(valor)`: Retorna `(cnpj_limpo, cnpj_formatado, cnpj_raiz)`.
- `normalize_cpf(valor)`: Trata CPFs completos e mascarados (ex: `***.123.456-**`).
- `normalize_ibge(codigo)`: Padroniza códigos municipais de 6 ou 7 dígitos.
- `parse_currency(valor)`: Converte valores monetários no formato brasileiro (`R$ 1.250,50`) para `float`.
- `parse_date(valor)`: Converte datas brasileiras (`DD/MM/AAAA`) e mensais (`MM/AAAA`) para padrão ISO (`YYYY-MM-DD`).

---

## 🧪 Checklist de Validação

Antes de submeter uma nova skill, verifique:
- [ ] A tabela é criada com tipos adequados e índices nas chaves de relacionamento no DuckDB.
- [ ] O script de fetch possui tratamento de erros e retries (`GovHttpClient`).
- [ ] O script de query exibe resultados bonitos via `rich`.
- [ ] A skill foi testada com dados reais do órgão governamental.
- [ ] A skill foi registrada no `src/gov_skills/__init__.py`.
