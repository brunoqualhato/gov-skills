---
name: gov-cruzamentos-auditoria
description: Meta-skill de inteligência e cruzamento investigativo de dados públicos federais brasileiros. Cruza CNPJ (Receita), Contratos (PNCP), Sanções (CGU/TCU), Cota Parlamentar (Câmara/Senado), Judiciário (DataJud), Finanças (Siconfi), Emprego (CAGED) e Indicadores (IBGE/ANP/CMED) para auditorias forenses completas.
version: 2.0.0
metadata:
  domain: "Auditoria Forense, Econometria e Inteligência de Dados"
  agency: "Multi-órgãos (RFB, CGU, TCU, PNCP, Câmara, Senado, CNJ, TSE, IBGE, ANP, CMED, IBAMA, BNDES)"
  auth_required: false
  primary_keys: ["cnpj", "cnpj_raiz", "cpf_mascarado", "codigo_ibge"]
  target_tables: ["rfb_empresas", "rfb_socios", "pncp_contratos", "camara_ceap_despesas", "cgu_sancoes", "ibge_municipios", "cnj_processos_judiciais"]
---

# 🕵️ Skill: gov-cruzamentos-auditoria (Inteligência & Cruzamentos Forenses)

Esta é a **meta-skill analítica** do repositório. Ela conecta todas as 47 tabelas do Data Lakehouse DuckDB através das 4 chaves mestras do Estado brasileiro para executar **29 motores de auditoria forense, detecção matemática de fraudes e econometria pública**.

---

## 🎯 Suíte Completa de Motores Forenses (`uv run gov-skills <comando>`)

| Comando CLI | Script | Objetivo Analítico / Forense |
| :--- | :--- | :--- |
| `dossie <cnpj>` | `dossie_empresa.py` | Dossiê 360º de empresa (RFB + QSA + PNCP + CEAP + Sanções + PGFN + CNJ). |
| `score-risco-contratos` | `auditoria_risco_contratos.py` | Pontuação unificada de risco licitatório (0 a 100) combinando múltiplos sinais fracos. |
| `auditoria-benford` | `auditoria_benford.py` | Lei de Benford (Teste Qui-Quadrado e MAD) para detectar notas fiscais e recibos forjados. |
| `auditoria-fracionamento` | `auditoria_fracionamento.py` | Detecção de fatiamento de compras/dispensas para burlar o teto da Lei 14.133/21. |
| `auditoria-carrossel` | `auditoria_carrossel_licitacoes.py` | Detecção de rodízio sequencial de licitantes (Bid-Rigging Rotation) por órgão. |
| `auditoria-acumulo-cargos` | `auditoria_acumulo_cargos.py` | Super-Servidores com acúmulo ilegal, violação de Dedicação Exclusiva ou jornada > 60h/sem. |
| `auditoria-porta-giratoria` | `auditoria_porta_giratoria.py` | Violação de quarentena (Lei 12.813/13) entre exonerações no DOU e ingresso no QSA. |
| `auditoria-voto-emenda` | `auditoria_voto_emenda.py` | Econometria eleitoral cruzando Emendas Pix com desempenho nas urnas (TSE). |
| `auditoria-ongs-fachada` | `auditoria_ongs_fachada.py` | Triângulo das ONGs (MROSC Lei 13.019/14) sem empregados ou recém-abertas. |
| `auditoria-supercompra-medicamentos` | `auditoria_supercompra_medicamentos.py` | Volume de doses compradas incompatível com a população (IBGE) e leitos SUS (DataSUS). |
| `auditoria-logistica-impossivel` | `auditoria_logistica_impossivel.py` | Fornecimento perecível/diário vencido por empresas a milhares de km (Haversine) sem filial. |
| `auditoria-insolvencia` | `auditoria_insolvencia_fornecedor.py` | Modelo preditivo *Gov Z-Score* de risco de quebra ou abandono de contrato público. |
| `auditoria-cartel` | `auditoria_cartel_conluio.py` | Empresas distintas compartilhando mesmo telefone, e-mail ou endereço na Receita. |
| `auditoria-laranjas` | `auditoria_laranjas.py` | Sócios de empresas licitantes inscritos no Bolsa Família ou BPC. |
| `auditoria-servidores` | `auditoria_conflito_servidor.py` | Servidores públicos federais ativos no SIAPE administrando empresas. |
| `auditoria-emendas-pix` | `auditoria_emendas_pix.py` | Rastreamento completo do ciclo Parlamentar → Emenda Pix → Município → Fornecedor. |
| `auditoria-pgfn` | `auditoria_pgfn_licitantes.py` | Devedores da Dívida Ativa da União (PGFN) recebendo contratos no PNCP. |
| `auditoria-capacidade` | `auditoria_capacidade_operacional.py` | Empresas com 0 funcionários no CAGED/RAIS vencendo contratos milionários. |
| `auditoria-cronologia` | `auditoria_cronologia_suspeita.py` | Empresas recém-abertas vencendo licitações dias após a fundação. |
| `auditoria-medicamentos` | `auditoria_medicamentos_cmed.py` | Compras públicas de medicamentos acima do teto obrigatório PMVG da CMED/Anvisa. |
| `auditoria-combustiveis` | `auditoria_combustiveis.py` | Abastecimento de frotas e cota parlamentar acima dos preços da ANP. |
| `auditoria-obras` | `auditoria_obras_paralisadas.py` | Empreiteiras com obras paralisadas no Obrasgov vencendo novos contratos no PNCP. |
| `auditoria-eficiencia` | `auditoria_eficiencia_gastos.py` | Benchmark de gastos municipais em Educação (Siconfi) × nota do IDEB (INEP). |
| `auditoria-esg` | `auditoria_esg_desmatamento.py` | Empresas autuadas/embargadas pelo IBAMA contratadas no PNCP ou financiadas pelo BNDES. |
| `auditoria-teia` | `auditoria_teia_societaria.py` | Grafo de sócios em comum conectando múltiplos CNPJs e grupos econômicos ocultos. |
| `auditoria-triangulo` | `auditoria_triangulo_eleitoral.py` | Triângulo Eleitoral: Doador TSE → Cota Parlamentar CEAP → Contratos PNCP. |
| `auditoria-nepotismo` | `auditoria_nepotismo_parentesco.py` | Cruzamento de sobrenomes e parentesco entre gestores municipais e licitantes locais. |
| `auditoria-anomalias` | `detector_anomalias.py` | Varredura de extrapolação do Simples Nacional e capital social desproporcional. |
