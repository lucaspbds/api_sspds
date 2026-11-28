# Entrega de marco

## Identificação

- **Equipe:**
	1. David Lucas Pereira Braga dos Santos - 581594
	2. Carlos Abimael Oliveira do Nascimento - 587010
	3. Nikelly Santiago da Silva - 567082
- **Marco e data:** Marco 3 - 27/11/2026
- **Trilha:** A — API pública de dados abertos (`docs/plano-de-acao.md`)
- **Endereço público do produto:** https://api-sspds.onrender.com (documentação interativa em `/docs` e `/redoc`; listado em `docs/api.md`). Código: https://github.com/lucaspbds/api_sspds
- **Commit ou tag desta entrega:** `2f1b071d7ef3e046f7bd6ecd55373a902c65e5c9` (branch `main`). O repositório não possui tags.

## Campo 1 — O que funciona hoje

1. Rodar `curl "https://api-sspds.onrender.com/crimes/cvli?limit=5"` e receber um objeto JSON com `items` (até 5 ocorrências de CVLI, das mais recentes para as mais antigas por `id`, cada uma com `municipio`, `ais`, `data_fato`, `hora_fato`, `dia_semana`, `natureza`, `meio_empregado` e perfil da vítima) e `pagination` (`limit`, `next_cursor`, `has_next`). Sem dados, a resposta é `404` com `{"detail": "Nenhum dado de CVLI encontrado."}`.
2. Rodar `curl "https://api-sspds.onrender.com/crimes/?municipio=Fortaleza&tipo_crime=FURTO&data_inicio=2025-01-01&data_fim=2025-03-31&limit=10"` e receber os furtos de Fortaleza no 1º trimestre de 2025. Para a página seguinte, repetir a chamada acrescentando `&cursor=<next_cursor>` enquanto `has_next` for `true`.
3. Rodar `curl "https://api-sspds.onrender.com/historico-ingestoes/?limit=1"` e receber a execução mais recente da ingestão (status, arquivos encontrados/processados/com falha e mensagem de erro). A evidência `docs/evidencias/historico_ingestoes_rows_27-11.csv` mostra a execução `id=7` em 27/11: `status=SUCESSO`, 26 arquivos encontrados, 3 carregados (os demais já estavam publicados) e 0 falhas.
4. Abrir `https://api-sspds.onrender.com/docs` e ver todas as rotas documentadas (OpenAPI/Swagger), com parâmetros, schemas e exemplos de erro `404`, `422`, `500` e `503` executáveis pelo botão "Try it out".

## Campo 2 — O que mudou desde o marco anterior

Comparação entre o commit do Marco 2 (`887489fc8934ada3b4344e8557d9ba54f262cf63`) e o commit desta entrega.

- **Passou a existir:**
  - **Paginação por cursor** em todas as rotas `/crimes/*` e em `/historico-ingestoes/`: nova função `consultar_registros_paginados` em `database/repository.py` (ordem `id DESC`, padrão de 100 e máximo de 500 registros por página, filtro `IN` para múltiplos tipos), envelope de resposta `items` + `pagination` (`limit`, `next_cursor`, `has_next`) e parâmetro `cursor`. A função `consultar_registros` foi preservada. Testes unitários e de integração em `tests/test_database.py`; testes das rotas em `tests/test_crimes.py` e `tests/test_historico_ingestoes.py` passaram a usar mocks do repositório paginado.
  - **Recorte temporal da série histórica**: variável `INTERVALO_MAXIMO_ANOS` (valor de produção: 6; `0` ou `None` desativam o recorte), função `recorte_temporal` em `ingestion/pipeline.py` e `get_intervalo_maximo_anos` em `ingestion/config.py`, aplicada só às planilhas históricas. Incluída no `.env.example` e no workflow `.github/workflows/ingestion.yml`, com testes. Resolve o estouro do limite de armazenamento do plano gratuito do Supabase.
  - **Carga completa dos 26 arquivos**: a SSPDS/CE corrigiu as planilhas de Salvamento, Incêndios e Armas de Fogo (solicitação via e-SIC de 22/11) e a ingestão de 27/11 terminou com `SUCESSO` e 0 falhas (`docs/evidencias/historico_ingestoes_rows_27-11.csv`).
  - **Avaliação por usuários externos**: formulário no Google Forms respondido por 2 pessoas (24/11 e 26/11), arquivado em `docs/evidencias/avaliacao-uso-api_26-11.csv` e indexado em `docs/evidencias.csv`.
  - Documentação atualizada: `docs/api.md` (paginação e limitações), `docs/ingestion.md` (seção 8.1 "Cobertura atual dos dados em produção"), `README.md` (aviso de cobertura histórica reduzida), `docs/database.md` e diário de bordo (semana de 27/11).
- **Foi cortado, e por quê:**
  - **Registro de acessos (indicador de Contagem).** O middleware que preencheria a tabela `api_request_logs` não foi implementado: a tabela existe no banco e está documentada, mas a API não grava nela. Cortado por falta de tempo hábil para planejar e desenvolver, depois de o prazo ter sido consumido pela resolução da carga dos dados e do limite de armazenamento. Consequência: não há como comprovar "≥ 15 consultas".
  - **Série histórica completa (2009 em diante).** Cortada para os 6 anos mais recentes de cada planilha, por causa do limite de 500 MB do plano gratuito do Supabase (a carga completa chegou a ~531 MB, 106%). Dados anteriores a esse intervalo não estão na API; podem ser recarregados aumentando `INTERVALO_MAXIMO_ANOS` ou usando `0`/`None`, se houver mais armazenamento.
  - **Contagem total de resultados e ordenação por `data_fato`.** Sugeridas no formulário de avaliação e não implementadas; a ordem atual é por `id` decrescente (ver Campo 3).

## Campo 3 — Alcance

| Indicador | Planejado | Obtido até hoje | Onde está a evidência |
| :---- | :---- | :---- | :---- |
| Contagem (acessos à API, sem bots nem equipe) | ≥ 15 consultas | Sem dado. O middleware de registro de acessos não foi implementado. | Nenhuma. A tabela `api_request_logs` existe (`docs/database.md`), mas não é preenchida pela API. |
| Qualitativa (pessoas externas que usaram e avaliaram) | ≥ 2 pessoas externas, com feedback registrado e pelo menos uma melhoria incorporada | 2 respondentes do formulário (24/11 e 26/11) + 1 teste informal anterior (04/10), totalizando 3 pessoas externas. Melhoria: ver abaixo. | `docs/evidencias/avaliacao-uso-api_26-11.csv` e `docs/evidencias/teste-aplicacao01_04-10.pdf` (linhas de 2026-11-26 e 2026-10-04 em `docs/evidencias.csv`) |

**O que o público externo disse.** Um desenvolvedor externo (nota 4 de 5) respondeu que os filtros atenderam parcialmente e pediu um total de registros encontrados para a consulta e que os acontecimentos mais recentes apareçam primeiro; o segundo respondente (nota 5 de 5) disse que os filtros atenderam totalmente.

**Melhoria incorporada.** A paginação por cursor retorna os registros em ordem decrescente de `id` (os mais recentes carregados primeiro), o que responde em parte ao pedido de priorizar os mais recentes. Ressalva: é ordem de carga, não ordenação por `data_fato`, e o total de resultados continua não implementado. O primeiro teste externo (04/10) também havia gerado uma correção anterior, a do parâmetro `limit` (diário de 12/10).

## Campo 4 — Obstáculo e replanejamento

**Inconsistências nas planilhas da SSPDS/CE (22/11 a 27/11).** Na primeira carga em produção, 3 dos 26 arquivos falharam (`Arma-de-Fogo_Outubro.xlsx` com mês do nome divergente dos dados; `Salvamento_2022-a-2024.xlsx` e `Incendios_2022-a-2024.xlsx` com cabeçalhos fora do padrão e sem a coluna `AIS`). Custou cerca de 5 dias, entre a notificação via e-SIC e a correção na fonte. Resolvido: a ingestão de 27/11 carregou os arquivos corrigidos, com 0 falhas (`historico_ingestoes_rows_27-11.csv`).

**Limite de armazenamento do Supabase.** A série histórica completa (2009–2026, ~2,5 milhões de registros) passou de 500 MB do plano gratuito. Custou cerca de 5 dias entre identificar e resolver. Ação: recorte temporal configurável (`INTERVALO_MAXIMO_ANOS=6`) aplicado apenas à série histórica. Custo do replanejamento: a API não oferece dados históricos anteriores a esse intervalo, o que está declarado no `README.md`, em `docs/api.md` e em `docs/ingestion.md` (seção 8.1).

**Indicador de Contagem não coletado.** O registro de acessos em `api_request_logs` não foi implementado por falta de tempo hábil para planejar e desenvolver. O indicador "≥ 15 consultas" fica sem comprovação e será declarado como não atingido na socialização de 04/12, junto com a causa (priorização da carga e do armazenamento dos dados). Como encaminhamento, a tabela, o `client_type` e as regras de exclusão de bots e da equipe já estão modelados, de modo que o middleware pode ser acrescentado depois sem mudar o banco.

**Resolvidos antes:** timeout na carga histórica, incompatibilidade entre schemas e colunas do PostgreSQL e inconsistências de data/dia da semana (resposta da SUPESP de 16/11), conforme o Marco 2.

## Campo 5 — Autopontuação

Todas as dimensões se aplicam. Conta: 8 pontos obtidos de 10 aplicáveis, então 10 × 8 / 10 = **8,0**.

| Dimensão | n.a.? | Pts (0–2) | Por quê, em uma linha |
| :---- | :---- | :---- | :---- |
| D1 Qualidade técnica | | 2 | Pipeline com versionamento e execução diária no GitHub Actions, carga dos 26 arquivos sem falhas, paginação por cursor e suíte de testes; a limitação é o recorte da série histórica em 6 anos. |
| D2 Alcance e adequação ao público | | 1 | 3 pessoas externas com feedback (meta ≥ 2) e melhoria parcial incorporada, mas sem nenhuma contagem de acessos (meta ≥ 15). |
| D3 Documentação e reprodutibilidade | | 1 | `README.md`, `api.md`, `database.md` e `ingestion.md` completos, com OpenAPI em `/docs`; o `README.md` não lista `INTERVALO_MAXIMO_ANOS` na tabela de variáveis nem cita o endereço público. |
| D4 Registro do processo | | 2 | Diário com todas as semanas de 18/09 a 27/11, evidências datadas e indexadas em `docs/evidencias.csv`, commits e PRs frequentes. |
| D5 Autoavaliação e reflexão | | 2 | Obstáculos registrados com causa, custo em dias e ação tomada, e indicador não atingido declarado de forma explícita. |

## Antes de entregar

- [ ] O endereço do produto abre numa máquina que não é a nossa.
- [ ] O que o Campo 1 promete foi testado hoje, não na semana passada.
- [ ] O `README.md` corresponde ao que o produto faz agora.
- [x] O diário tem entrada de todas as semanas desde o último marco.
- [x] Toda evidência do Campo 3 tem data e está em `evidencias/`.
- [ ] O commit informado está publicado.
