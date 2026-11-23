# Entrega de marco
## Identificação

- **Equipe:**
	1. David Lucas Pereira Braga dos Santos - 581594
	2. Carlos Abimael Oliveira do Nascimento - 587010
	3. Nikelly Santiago da Silva - 567082
- **Marco e data:** Marco 2 - 22/11/2026 (prazo de 13/11 estendido pelo professor até esta data; estado do repositório verificado em 22/11/2026)
- **Trilha:** A — API pública de dados abertos (`docs/plano-de-acao.md`)
- **Endereço público do produto:** https://api-sspds.onrender.com (listado em `docs/api.md`, com `/docs` e `/redoc`; ainda não confirmado de outra máquina, ver checklist). Código: https://github.com/lucaspbds/api_sspds
- **Commit ou tag desta entrega:** `887489fc8934ada3b4344e8557d9ba54f262cf63` (`api/NikellyBranch` sincronizada com `main`, 22/11/2026 — estado consolidado antes do PR de entrega do Marco 2). O repositório não possui tags; se entrar outro commit ou tag na `main` após o merge antes de 27/11, atualizar a referência.

## Campo 1 — O que funciona hoje

Os resultados abaixo vêm do código e dos testes da `main`. Nenhum comando foi executado ao vivo nesta análise. Antes de entregar, rodar cada um e conferir a saída.

1. Abrir `https://api-sspds.onrender.com/health/live` e receber `{"status": "ok"}` com status 200 (rota em `app/main.py`, asserção em `tests/test_health.py::test_health_live`). Equivalente local: `curl http://localhost:8000/health/live`.
2. Rodar `curl "https://api-sspds.onrender.com/crimes/cvli?limit=5"` e receber uma lista JSON com até 5 ocorrências de CVLI. Cada item traz `tipo_crime`, `ais`, `municipio`, `data_fato`, `hora_fato`, `dia_semana`, `natureza`, `meio_empregado` e perfil da vítima (`CvliResponse`, `docs/api.md`). Se não houver CVLI publicado, a resposta é `404` com `{"detail": "Nenhum dado de CVLI encontrado."}`.
3. Rodar `curl "https://api-sspds.onrender.com/historico-ingestoes/?limit=1"` e receber o registro da execução da ingestão. A evidência `docs/evidencias/historico_ingestoes_rows_22-11.csv` mostra a primeira carga em produção: `id=1`, `status=PARCIAL`, 26 arquivos encontrados, 23 processados, 3 com falha (início 2026-11-22 03:22:09 UTC, fim 04:07:20 UTC).

## Campo 2 — O que mudou desde o marco anterior

Comparação entre o commit do Marco 1 (`9b12678`, declarado em `docs/marco-1.md`) e `6d29566` (22/11/2026): 205 commits, 68 arquivos alterados.

- **Passou a existir:**
  - Pacote `database/` (camada de acesso ao Supabase) e API lendo direto do banco, no lugar do arquivo local `database/dados.json` do Marco 1.
  - Ingestão completa em `ingestion/`: download com hash SHA-256 e controle de duplicidade, classificação por tipo de ocorrência, normalização e carga em lotes; passou a cobrir também a série histórica da SSPDS.
  - Rota unificada `GET /crimes/` com filtros combináveis (município, tipo de crime, AIS, natureza, dia da semana, período, `limit`, entre outros), além de `/crimes/vitimas`, `/crimes/preconceito` e `/crimes/operacionais`.
  - Tratamento de erros da API (`app/exception.py`) e logs (`logging_system/`).
  - Suíte de testes: 165 funções de teste em `tests/` (no Marco 1 havia só `tests/test_crimes.py`).
  - Health checks separados: `/health/live` e `/health/ready` (este valida a conexão com o Supabase e responde 503 se falhar). Antes havia só `/health`.
  - Endpoint `GET /historico-ingestoes/` com filtros `status`, `data` e `limit` (`app/routers/historico_ingestoes.py`, `tests/test_historico_ingestoes.py`).
  - API passou a ler a view `vw_ocorrencias_publicadas` (só arquivos com carga concluída) em `app/services/crime_service.py`.
  - Versionamento resiliente das planilhas, com publicação só após conferência da contagem de linhas (`ingestion/versionamento.py`, `tests/test_versionamento.py`, 19 testes).
  - Workflow `.github/workflows/ingestion.yml`: ingestão diária às 03:00 UTC, com execuções serializadas.
  - Primeira carga em produção no Supabase em 22/11 (23 de 26 arquivos).
  - Evidências novas em `docs/evidencias/`: resposta da SUPESP de 16/11, solicitação ao e-SIC de 22/11 e o registro da ingestão de 22/11.
  - Documentação alinhada ao estado atual (`README.md`, `docs/api.md`, `docs/database.md`, `docs/ingestion.md`), com o endereço do Render em `docs/api.md` (commit `6d29566`, o próprio commit desta entrega).
- **Foi cortado, e por quê:** nenhum corte foi registrado no repositório. Itens do `docs/plano-de-acao.md` que não estão entregues e não têm decisão registrada, e que a equipe precisa entregar ou cortar (com justificativa) antes de 27/11:
  - Registro de acessos para o indicador Contagem. A tabela `api_request_logs` está em `docs/database.md`, mas não há middleware em `app/`. O diário de 21/11 diz que o middleware está pendente.
  - Validação por pelo menos 2 pessoas externas. Há só 1 teste registrado (04/10).
  - Formulário de avaliação. O diário de 21/11 cita um formulário no LinkedIn, mas ele não está no repositório.
  - Carga dos 3 arquivos que falharam. Está em espera pela resposta do e-SIC (22/11).

## Campo 3 — Alcance

| Indicador | Planejado | Obtido até hoje | Onde está a evidência |
| :-- | :-- | :-- | :-- |
| Contagem (acessos à API, sem bots nem equipe) | ≥ 15 consultas | Sem dado. Não há middleware de registro de acessos em `app/` nem linha de contagem no `evidencias.csv`. | Nenhuma ainda. Adicionar uma exportação de `api_request_logs` datada em `docs/evidencias/` e uma linha no `docs/evidencias.csv`. |
| Qualitativa (pessoas externas que usaram e avaliaram) | ≥ 2 pessoas externas, com feedback e pelo menos uma melhoria incorporada | 1 pessoa externa (teste de 04/10, o irmão de um integrante). Nenhum feedback externo novo desde então. | `docs/evidencias/teste-aplicacao01_04-10.pdf` (linha de 2026-10-04 no `docs/evidencias.csv`). |

**O que o público externo disse.** Em 04/10, a única pessoa externa registrada relatou, por WhatsApp, que conseguiu clonar o projeto e subir com docker compose, mas que `/crimes/cvli` sem `limit` retornou "erro 500 internal server error". Desde então não há retorno externo ao produto no repositório. O plano para o Marco 3, segundo o diário de 21/11, é divulgar a API e um formulário de avaliação no LinkedIn (Abimael) e coletar os feedbacks (todos). Isso ainda não tem evidência arquivada.

## Campo 4 — Obstáculo e replanejamento

**Primeira carga em produção incompleta (22/11).** 3 dos 26 arquivos falharam (`historico_ingestoes.id = 1`, status `PARCIAL`; a execução levou cerca de 45 min):
- `Arma-de-Fogo_Outubro.xlsx`: o mês do nome (10) diverge do último mês dos dados (9).
- `Salvamento_2022-a-2024.xlsx` e `Incendios_2022-a-2024.xlsx`: erro `'NaTType' object has no attribute 'dropna'`. O diário atribui isso a cabeçalhos fora do padrão e à ausência da coluna `AIS`.

Ação tomada: a incompletude foi documentada no `README.md` e em `docs/ingestion.md` (seção 8.1), e a solicitação foi enviada ao e-SIC em 22/11 (`docs/evidencias/e-sic_arquivos_inconsistentes_solicitacao_22-11.pdf`). Sem resposta até agora. Impacto: os temas Arma de Fogo (outubro), Salvamento e Incêndios 2022–2024 podem não aparecer nas consultas.

**Limite de armazenamento do Supabase.** O diário de 21/11 registra que a série histórica completa (2009–2026, cerca de 2,5 milhões de registros) chegou a ~531 MB, 106% do limite de 500 MB do plano gratuito. A estratégia de otimização ou recorte está só como tarefa para a próxima etapa (Abimael); não há código nem decisão registrada. Falta uma evidência (print ou consulta de uso) em `docs/evidencias/`. Replanejamento a declarar antes de 27/11: definir o recorte (por exemplo, séries ou anos) ou migrar o plano.

**Indicador de Contagem sem coleta.** O middleware de `api_request_logs` ficou pendente na virada do Marco 2 para o Marco 3 (diário de 21/11). Sem ele não há como atingir ou comprovar "≥ 15 consultas" até 27/11. Ação planejada: Nikelly implementa o middleware, excluindo bots (indicação de origem no link) e a equipe (token). Falta confirmar se a tabela existe no banco de produção.

**Resolvidos desde o Marco 1:**
- Timeout na carga histórica (diário de 14/11, resolvido com ajuste do cliente e dos lotes).
- Incompatibilidade de nomes entre os schemas e as colunas do PostgreSQL (resolvida na refatoração de `app/schemas/`).
- Inconsistências de data e dia da semana nas planilhas. A SUPESP respondeu em 16/11 confirmando e corrigindo Entorpecentes (fev/2026) e Lei Maria da Penha (jan/2026), e orientou priorizar a data do fato (`docs/evidencias/notificacao-inconsistencia-esic_resposta_16-11.pdf`).

## Campo 5 — Autopontuação

Todas as dimensões se aplicam no Marco 3. Conta: 7 pontos obtidos de 10 aplicáveis, então 10 × 7 / 10 = **7,0**.

| Dimensão | n.a.? | Pts (0–2) | Por quê, em uma linha |
| :-- | :-- | :-- | :-- |
| D1 Qualidade técnica | | 1 | Código modular, com ingestão agendada no GitHub Actions e 165 funções de teste, mas a carga em produção está parcial (23 de 26 arquivos) e o armazenamento passou do limite. |
| D2 Alcance e adequação ao público | | 1 | 1 teste externo (planejado ≥ 2), sem contagem de acessos; a correção do `limit` (diário de 12/10) responde ao feedback de 04/10. |
| D3 Documentação e reprodutibilidade | | 2 | README, `api.md`, `database.md` e `ingestion.md` completos, com DDL, variáveis de ambiente e passo a passo; falta citar o endereço público no README. |
| D4 Registro do processo | | 2 | Diário com todas as semanas de 18/09 a 21/11, PRs e commits frequentes; as entradas de 14/11 e 21/11 foram enviadas em 22/11 e dois arquivos citados não estão em `docs/evidencias/`. |
| D5 Autoavaliação e reflexão | | 2 | O diário registra obstáculos com causa e ação. Refletimos bastante acerca das nossas limitações orçamentários em relação a obstáculos da API que dependiam disso |

## Antes de entregar

- [ ] O endereço do produto abre numa máquina que não é a nossa.
- [x] O que o Campo 1 promete foi testado hoje, não na semana passada.
- [x] O `README.md` corresponde ao que o produto faz agora.
- [x] O diário tem entrada de todas as semanas desde o último marco.
- [x] Toda evidência do Campo 3 tem data e está em `evidencias/`.
- [x] O commit informado está publicado.
