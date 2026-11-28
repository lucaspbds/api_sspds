# Documentação da API Pública de Segurança - SSPDS/CE

Esta documentação descreve a arquitetura, a estrutura de diretórios modular e os endpoints disponíveis na API de dados de segurança pública do Ceará.

A API é construída com **FastAPI** e lê os dados publicados pela view `vw_ocorrencias_publicadas` (ocorrências cujos arquivos já tiveram carga concluída) e pela tabela `historico_ingestoes` no **Supabase**. A documentação interativa gerada automaticamente fica em `/docs` (Swagger UI) e `/redoc`.

## 🌐 Ambiente Hospedado e Status

A API ainda está **em desenvolvimento**, mas já possui uma instância publicada e acessível para consultas e testes pela documentação interativa (Swagger UI):

- **URL Base:** [https://api-sspds.onrender.com](https://api-sspds.onrender.com)
- **Swagger UI (`/docs`):** [https://api-sspds.onrender.com/docs](https://api-sspds.onrender.com/docs)
- **ReDoc (`/redoc`):** [https://api-sspds.onrender.com/redoc](https://api-sspds.onrender.com/redoc)

## 📁 Estrutura de Diretórios da API

A API segue uma arquitetura orientada a serviços e separação de responsabilidades (Clean Architecture / Modular) dentro da pasta `app/`:

```text
api_sspds/
├── app/
│   ├── __init__.py
│   ├── config.py                          # get_variavel_ambiente (leitura do .env, independente de database/)
│   ├── dockerfile
│   ├── exception.py                       # Exceções da API (RecursoNaoEncontrado, VariavelAmbienteNaoEncontrada) e handlers
│   ├── main.py                            # Instância FastAPI, /, /health/live, /health/ready
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── crimes.py                      # Rotas /crimes/*
│   │   └── historico_ingestoes.py         # Rota /historico-ingestoes/
│   ├── schemas/                           # Serialização, validação de saída e doc. automática
│   │   ├── __init__.py
│   │   ├── base_schema.py                 # CrimeBaseSchema (campos comuns)
│   │   ├── consulta_schema.py             # CrimeGeralResponse, PaginationMeta e respostas paginadas
│   │   ├── historico_ingestoes_schema.py  # HistoricoIngestaoResponse e HistoricoIngestaoPaginadoResponse
│   │   ├── operacional_schema.py          # OperacionalResponse e OperacionalPaginadoResponse
│   │   ├── preconceito_schema.py          # PreconceitoResponse e PreconceitoPaginadoResponse
│   │   └── vitima_schema.py               # CrimeComVitimaResponse, CvliResponse e respostas paginadas
│   └── services/
│       ├── __init__.py
│       ├── crime_service.py               # Consultas à view vw_ocorrencias_publicadas
│       └── historico_ingestoes_service.py # Consultas à tabela historico_ingestoes
```

### Fluxo de uma requisição

`Router` (valida parâmetros) → `Service` (`CrimeService` sobre `vw_ocorrencias_publicadas` ou `HistoricoIngestoesService` sobre `historico_ingestoes`) → `Schema` (valida e serializa a resposta) → JSON.

Os dois serviços leem o banco por `database.repository.consultar_registros_paginados`, que aplica filtros de igualdade, filtro `IN` (usado em `tipo_crime` por `/crimes/vitimas` e `/crimes/operacionais`), intervalo de datas e paginação por cursor.

Erros de banco (`ErroOperacaoBanco`), de conexão (`ErroConexaoBanco`) e de configuração (`VariavelAmbienteNaoEncontrada`) são propagados como estão e tratados por `app/exception.py`. A API tem a própria `get_variavel_ambiente` (`app/config.py`) e a própria `VariavelAmbienteNaoEncontrada`; o handler de configuração cobre também a exceção homônima de `database/`, de modo que `app` e `database` só compartilham as exceções de banco.

## 📄 Paginação

As rotas `/crimes/*` e `/historico-ingestoes/` usam **paginação por cursor (keyset)**, em ordem **decrescente de `id`** (os registros mais recentes primeiro). Parâmetros comuns:

| Parâmetro | Tipo | Descrição |
| :--- | :--- | :--- |
| `limit` | `integer`, `> 0` | Registros por página. Padrão **100**, máximo **500** (`LIMITE_PADRAO_PAGINACAO` e `LIMITE_MAXIMO_PAGINACAO` em `database.repository`); acima do máximo a resposta é `422`. |
| `cursor` | `integer`, `> 0` | `id` do último item da página anterior (use o `next_cursor` recebido). Omitido, retorna a primeira página. |

Formato da resposta:

```json
{
  "items": [ { "id": 1520, "...": "..." } ],
  "pagination": { "limit": 100, "next_cursor": 1421, "has_next": true }
}
```

Para percorrer tudo, repita a chamada passando `cursor=<next_cursor>` enquanto `has_next` for `true`. Quando `has_next` é `false`, `next_cursor` é `null`.

## 🚀 Endpoints Disponíveis

### 1. Raiz da Aplicação
- **Método:** `GET`
- **Rota:** `/`
- **Descrição:** Retorna uma mensagem de boas-vindas e o atalho para a documentação interativa.
- **Resposta (Exemplo - `200 OK`):**
  ```json
  {
    "message": "API SSPDS funcionando com sucesso!",
    "docs_url": "/docs"
  }
  ```

---

### 2. Verificação de Saúde (Health Checks)

#### 2.1 Liveness Check
- **Método:** `GET`
- **Rota:** `/health/live`
- **Descrição:** Verifica apenas se o processo da API está ativo e respondendo; **não** testa a conexão com o banco. Substitui a antiga rota `/health`, que não existe mais.
- **Resposta (`200 OK`):** `{"status": "ok"}`

#### 2.2 Readiness Check
- **Método:** `GET`
- **Rota:** `/health/ready`
- **Descrição:** Verifica se a API está pronta para atender requisições, executando `validar_conexao()` contra o Supabase.
- **Códigos de Resposta:**
  - `200 OK`: `{"status": "ready", "database": "ok"}`
  - `503 Service Unavailable`: `{"detail": "Banco de dados indisponível ou configuração ausente."}` (ou `"Banco de dados indisponível."`)

---

### 3. Consulta Geral Unificada de Crimes
- **Método:** `GET`
- **Rota:** `/crimes/`
- **Parâmetros de Query (todos opcionais e combináveis):**
  - `municipio` (`string`, 1–100 caracteres): Filtra por nome do município.
  - `tipo_crime` (`string`, 1–100 caracteres): Filtra pelo valor **exato** de `tipo_crime` (ex.: `FURTO`; veja a [tabela de tipos](#tipos-de-crime-tipo_crime)). Maiúsculas/minúsculas e espaços extras são normalizados.
  - `ais` (`string`, até 30 caracteres): Filtra por Área Integrada de Segurança (ex.: `AIS 01`).
  - `natureza` (`string`, até 150): Filtra pela tipificação detalhada do delito.
  - `meio_empregado` (`string`, até 100): Filtra pelo instrumento utilizado (ex.: `Arma de fogo`).
  - `vitima_genero` (`string`, até 50): Filtra pelo gênero da vítima.
  - `vitima_raca` (`string`, até 50): Filtra pela raça/cor da vítima.
  - `dia_semana` (`string`, até 30): Filtra pelo dia da semana (ex.: `Segunda-feira`).
  - `tipo_entorpecente` (`string`, até 100): Filtra pelo tipo de droga apreendida.
  - `data_inicio` (`date`, `AAAA-MM-DD`): Data inicial **inclusiva** sobre `data_fato`.
  - `data_fim` (`date`, `AAAA-MM-DD`): Data final **inclusiva** sobre `data_fato`.
  - `cursor` (`integer`, `> 0`): Cursor da página anterior (veja [Paginação](#paginação)).
  - `limit` (`integer`, `> 0`): Registros por página (veja [Paginação](#paginação)).
- **Response Model:** `CrimeGeralPaginadoResponse` (`items`: lista de `CrimeGeralResponse`; `pagination`)
- **Descrição:** Consulta a base unificada de dados permitindo o uso combinado de filtros de pesquisa.
- **Normalização dos filtros de texto:** `municipio`, `ais`, `natureza`, `meio_empregado`, `vitima_genero`, `vitima_raca`, `dia_semana` e `tipo_entorpecente` são comparados por igualdade exata, mas a entrada é normalizada para o padrão gravado pela ingestão (espaços extras removidos e Title Case), então `fortaleza` encontra `Fortaleza` e `masculino` encontra `Masculino`. `tipo_crime` é normalizado para caixa alta.
- **Exemplo:** `GET /crimes/?municipio=Fortaleza&tipo_crime=FURTO&vitima_genero=Masculino&data_inicio=2025-01-01&data_fim=2025-03-31&limit=10`
- **Códigos de Resposta:**
  - `200 OK`: Registos encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum crime encontrado com os filtros fornecidos (inclui um `cursor` além da última página).
  - `422 Unprocessable Content`: Parâmetro de consulta inválido (ex.: data fora do formato, `limit` não numérico, `<= 0` ou acima do máximo, `cursor <= 0`) **ou** `data_inicio` posterior a `data_fim`.
  - `500` / `503`: Falha no banco de dados ou na configuração (veja [Formato dos erros](#formato-dos-erros)).

**Campos retornados (`CrimeGeralResponse`):**

| Campo | Tipo | Observação |
| :--- | :--- | :--- |
| `id` | `integer` | Identificador da ocorrência. |
| `arquivo_id` | `integer \| null` | Arquivo de origem na tabela `informacoes_arquivo`. |
| `tipo_crime` | `string \| null` | Categoria da ocorrência. |
| `municipio`, `ais`, `local_fato` | `string \| null` | Localização do fato. |
| `data_fato` | `date \| null` | `AAAA-MM-DD`. |
| `hora_fato` | `time \| null` | `HH:MM:SS`. |
| `dia_semana` | `string \| null` | |
| `st_dia_semana_divergente`, `st_idade_invalida` | `boolean` | Indicadores de qualidade do dado. |
| `natureza`, `meio_empregado` | `string \| null` | |
| `vitima_genero`, `vitima_escolaridade`, `vitima_raca`, `vitima_orientacao_sexual` | `string \| null` | |
| `vitima_idade` | `integer \| null` | |
| `quantidade_armas` | `integer \| null` | |
| `tipo_entorpecente` | `string \| null` | |
| `peso_entorpecente_kg` | `number \| null` | |
| `criado_em` | `datetime \| null` | |

---

### 4. Listagem de Crimes Violentos Letais Intencionais (CVLI)
- **Método:** `GET`
- **Rota:** `/crimes/cvli`
- **Parâmetros de Query (todos opcionais e combináveis):**
  - `municipio` (`string`, 1–100 caracteres): Filtra por nome do município.
  - `ais` (`string`, até 30 caracteres): Filtra por Área Integrada de Segurança (ex.: `AIS 01`).
  - `dia_semana` (`string`, até 30): Filtra pelo dia da semana (ex.: `Segunda-feira`).
  - `natureza` (`string`, até 150): Filtra pela tipificação detalhada do delito.
  - `meio_empregado` (`string`, até 100): Filtra pelo instrumento utilizado (ex.: `Arma de fogo`).
  - `vitima_genero` (`string`, até 50): Filtra pelo gênero da vítima.
  - `vitima_raca` (`string`, até 50): Filtra pela raça/cor da vítima.
  - `vitima_idade` (`integer`, `>= 0`): Filtra pela idade da vítima.
  - `vitima_escolaridade` (`string`, até 100): Filtra pela escolaridade da vítima.
  - `data_inicio` (`date`, `AAAA-MM-DD`): Data inicial **inclusiva** sobre `data_fato`.
  - `data_fim` (`date`, `AAAA-MM-DD`): Data final **inclusiva** sobre `data_fato`.
  - `cursor` (`integer`, `> 0`): Cursor da página anterior (veja [Paginação](#paginação)).
  - `limit` (`integer`, `> 0`): Registros por página (veja [Paginação](#paginação)).
- **Tipo(s) de crime:** `CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI`
- **Response Model:** `CvliPaginadoResponse` (`items`: lista de `CvliResponse`; `pagination`)
- **Descrição:** Lista ocorrências específicas de CVLI com detalhamento de perfil de vítima e natureza.
- **Exemplo:** `GET /crimes/cvli?municipio=Fortaleza&meio_empregado=Arma%20de%20fogo&data_inicio=2025-01-01&data_fim=2025-03-31&limit=10`
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum dado de CVLI encontrado na base.
  - `422 Unprocessable Content`: Parâmetro de consulta inválido (ex.: `limit` fora do intervalo permitido, `cursor <= 0`, `vitima_idade < 0` ou data fora do formato) **ou** `data_inicio` posterior a `data_fim`.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 5. Listagem de Crimes com Perfil de Vítima
- **Método:** `GET`
- **Rota:** `/crimes/vitimas`
- **Parâmetros de Query (todos opcionais e combináveis):**
  - `municipio` (`string`, 1–100 caracteres): Filtra por nome do município.
  - `ais` (`string`, até 30 caracteres): Filtra por Área Integrada de Segurança (ex.: `AIS 01`).
  - `dia_semana` (`string`, até 30): Filtra pelo dia da semana (ex.: `Segunda-feira`).
  - `vitima_genero` (`string`, até 50): Filtra pelo gênero da vítima.
  - `vitima_raca` (`string`, até 50): Filtra pela raça/cor da vítima.
  - `vitima_idade` (`integer`, `>= 0`): Filtra pela idade da vítima.
  - `vitima_escolaridade` (`string`, até 100): Filtra pela escolaridade da vítima.
  - `data_inicio` (`date`, `AAAA-MM-DD`): Data inicial **inclusiva** sobre `data_fato`.
  - `data_fim` (`date`, `AAAA-MM-DD`): Data final **inclusiva** sobre `data_fato`.
  - `cursor` (`integer`, `> 0`): Cursor da página anterior (veja [Paginação](#paginação)).
  - `limit` (`integer`, `> 0`): Registros por página (veja [Paginação](#paginação)).
- **Tipo(s) de crime:** `LEI 11.340/06 (LEI MARIA DA PENHA)`, `CRIMES SEXUAIS` e `INDÍGENAS VÍTIMAS DE CRIMES` (os três, na mesma lista; use `tipo_crime` em cada registro para distingui-los).
- **Response Model:** `CrimeComVitimaPaginadoResponse` (`items`: lista de `CrimeComVitimaResponse`; `pagination`)
- **Descrição:** Retorna ocorrências específicas de crimes com detalhamento de perfil da vítima (Lei Maria da Penha, Crimes Sexuais e Indígenas).
- **Exemplo:** `GET /crimes/vitimas?municipio=Fortaleza&vitima_genero=Feminino&data_inicio=2025-01-01&data_fim=2025-03-31&limit=10`
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro de crime com vítima encontrado.
  - `422 Unprocessable Content`: Parâmetro de consulta inválido (ex.: `limit` fora do intervalo permitido, `cursor <= 0`, `vitima_idade < 0` ou data fora do formato) **ou** `data_inicio` posterior a `data_fim`.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 6. Listagem de Crimes de Preconceito
- **Método:** `GET`
- **Rota:** `/crimes/preconceito`
- **Parâmetros de Query (todos opcionais e combináveis):**
  - `municipio` (`string`, 1–100 caracteres): Filtra por nome do município.
  - `ais` (`string`, até 30 caracteres): Filtra por Área Integrada de Segurança (ex.: `AIS 01`).
  - `dia_semana` (`string`, até 30): Filtra pelo dia da semana (ex.: `Segunda-feira`).
  - `natureza` (`string`, até 150): Filtra pela tipificação detalhada do delito.
  - `local_fato` (`string`, até 150): Filtra pelo local de ocorrência do fato.
  - `vitima_genero` (`string`, até 50): Filtra pelo gênero da vítima.
  - `vitima_orientacao_sexual` (`string`, até 50): Filtra pela orientação sexual da vítima.
  - `vitima_raca` (`string`, até 50): Filtra pela raça/cor da vítima.
  - `vitima_idade` (`integer`, `>= 0`): Filtra pela idade da vítima.
  - `vitima_escolaridade` (`string`, até 100): Filtra pela escolaridade da vítima.
  - `data_inicio` (`date`, `AAAA-MM-DD`): Data inicial **inclusiva** sobre `data_fato`.
  - `data_fim` (`date`, `AAAA-MM-DD`): Data final **inclusiva** sobre `data_fato`.
  - `cursor` (`integer`, `> 0`): Cursor da página anterior (veja [Paginação](#paginação)).
  - `limit` (`integer`, `> 0`): Registros por página (veja [Paginação](#paginação)).
- **Tipo(s) de crime:** `HOMOFOBIA E TRANSFOBIA`
- **Response Model:** `PreconceitoPaginadoResponse` (`items`: lista de `PreconceitoResponse`; `pagination`)
- **Descrição:** Retorna ocorrências específicas de crimes motivados por preconceito (homofobia e transfobia).
- **Exemplo:** `GET /crimes/preconceito?municipio=Fortaleza&vitima_orientacao_sexual=Homossexual&limit=10`
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum crime de preconceito encontrado.
  - `422 Unprocessable Content`: Parâmetro de consulta inválido (ex.: `limit` fora do intervalo permitido, `cursor <= 0`, `vitima_idade < 0` ou data fora do formato) **ou** `data_inicio` posterior a `data_fim`.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 7. Listagem de Crimes Operacionais
- **Método:** `GET`
- **Rota:** `/crimes/operacionais`
- **Parâmetros de Query (todos opcionais e combináveis):**
  - `municipio` (`string`, 1–100 caracteres): Filtra por nome do município.
  - `ais` (`string`, até 30 caracteres): Filtra por Área Integrada de Segurança (ex.: `AIS 01`).
  - `dia_semana` (`string`, até 30): Filtra pelo dia da semana (ex.: `Segunda-feira`).
  - `data_inicio` (`date`, `AAAA-MM-DD`): Data inicial **inclusiva** sobre `data_fato`.
  - `data_fim` (`date`, `AAAA-MM-DD`): Data final **inclusiva** sobre `data_fato`.
  - `cursor` (`integer`, `> 0`): Cursor da página anterior (veja [Paginação](#paginação)).
  - `limit` (`integer`, `> 0`): Registros por página (veja [Paginação](#paginação)).
- **Tipo(s) de crime:** `FURTO` e `CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP` (os dois, na mesma lista; use `tipo_crime` em cada registro para distingui-los).
- **Response Model:** `OperacionalPaginadoResponse` (`items`: lista de `OperacionalResponse`; `pagination`)
- **Descrição:** Retorna ocorrências de crimes operacionais de menor complexidade estrutural (Furtos e CVP).
- **Exemplo:** `GET /crimes/operacionais?municipio=Fortaleza&ais=AIS%2001&data_inicio=2025-01-01&data_fim=2025-03-31&limit=10`
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro operacional encontrado.
  - `422 Unprocessable Content`: Parâmetro de consulta inválido (ex.: `limit` fora do intervalo permitido, `cursor <= 0` ou data fora do formato) **ou** `data_inicio` posterior a `data_fim`.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 8. Histórico de Ingestões
- **Método:** `GET`
- **Rota:** `/historico-ingestoes/`
- **Parâmetros de Query (todos opcionais e combináveis):**
  - `status` (`string`): Filtra pelo status da execução (`EM_ANDAMENTO`, `SUCESSO`, `PARCIAL` ou `FALHA`; normalizado para caixa alta).
  - `data` (`date`, `AAAA-MM-DD`): Filtra os registros criados naquele dia (`criado_em`, em **UTC**, de `00:00:00` a `23:59:59.999999`). Em horário de Brasília (UTC-3), o dia UTC começa às 21:00 do dia anterior.
  - `cursor` (`integer`, `> 0`): Cursor da página anterior (veja [Paginação](#paginação)).
  - `limit` (`integer`, `> 0`): Registros por página (veja [Paginação](#paginação)).
- **Response Model:** `HistoricoIngestaoPaginadoResponse` (`items`: lista de `HistoricoIngestaoResponse`; `pagination`)
- **Descrição:** Consulta paginada (do mais recente para o mais antigo) dos registros de execução da tabela `historico_ingestoes`, permitindo acompanhar o status, contadores de arquivos e eventuais mensagens de erro/aviso da ingestão.
- **Exemplo:** `GET /historico-ingestoes/?status=SUCESSO&data=2026-11-21&limit=5`
- **Códigos de Resposta:**
  - `200 OK`: Registros encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos.
  - `422 Unprocessable Content`: `status` fora dos valores permitidos, `data` fora do formato `AAAA-MM-DD`, `limit` fora do intervalo permitido ou `cursor <= 0`.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

## 📦 Schemas de Resposta

Os schemas das rotas específicas herdam de `CrimeBaseSchema`.

| Schema | Campos | Usado em |
| :--- | :--- | :--- |
| `CrimeBaseSchema` | `id`, `tipo_crime`, `ais`, `municipio` (obrigatório), `data_fato` (obrigatório), `hora_fato`, `dia_semana`, `st_dia_semana_divergente`, `st_idade_invalida` | Base dos demais |
| `OperacionalResponse` | Somente os campos da base | `/crimes/operacionais` |
| `CrimeComVitimaResponse` | Base + `vitima_genero`, `vitima_idade`, `vitima_escolaridade`, `vitima_raca` | `/crimes/vitimas` |
| `CvliResponse` | `CrimeComVitimaResponse` + `natureza`, `meio_empregado` | `/crimes/cvli` |
| `PreconceitoResponse` | Base + `natureza`, `local_fato`, `vitima_genero`, `vitima_orientacao_sexual`, `vitima_idade`, `vitima_escolaridade`, `vitima_raca` | `/crimes/preconceito` |
| `CrimeGeralResponse` | Todos os 22 campos da view `vw_ocorrencias_publicadas` (lista acima) | `/crimes/` |
| `HistoricoIngestaoResponse` | `id`, `data_inicio`, `data_fim`, `status`, `qtd_arquivos_encontrados`, `qtd_arquivos_processados`, `qtd_arquivos_falhas`, `mensagem_erro`, `criado_em` | `/historico-ingestoes/` |
| `PaginationMeta` | `limit` (`integer`), `next_cursor` (`integer \| null`), `has_next` (`boolean`) | Campo `pagination` de todas as respostas paginadas |
| `*PaginadoResponse` | `items` (lista do schema da rota) + `pagination` (`PaginationMeta`) | Resposta de cada rota listada acima |

Em `CrimeComVitimaResponse` (e, por herança, `CvliResponse`), um `vitima_idade` textual como `"Não Informada"` é convertido em `null` em vez de provocar erro de validação.

## 🏷️ Tipos de crime (`tipo_crime`)

Valores exatos gravados pela ingestão (`ingestion/classifier.py`) e aceitos pelo filtro `tipo_crime` de `/crimes/`:

- `CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI`
- `CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP`
- `FURTO`
- `CRIMES SEXUAIS`
- `LEI 11.340/06 (LEI MARIA DA PENHA)`
- `INDÍGENAS VÍTIMAS DE CRIMES`
- `HOMOFOBIA E TRANSFOBIA`
- `APREENSÃO DE ARMAS DE FOGO`
- `APREENSÃO DE ENTORPECENTES`
- `BUSCA E SALVAMENTO`
- `CRIME DE MAUS-TRATOS A ANIMAIS`
- `CRIME OU PRECONCEITO DE RAÇA OU DE COR`
- `INCÊNDIO`

Para listar os valores presentes no banco: `SELECT DISTINCT tipo_crime FROM ocorrencias_crimes ORDER BY tipo_crime;`

## ⚠️ Formato dos erros

| Origem | Status | Corpo |
| :--- | :--- | :--- |
| Rotas sem resultado (`HTTPException`) | `404` | `{"detail": "Nenhum dado de CVLI encontrado."}` |
| `data_inicio` posterior a `data_fim` | `422` | `{"detail": "data_inicio não pode ser posterior a data_fim."}` |
| `status` inválido em `/historico-ingestoes/` | `422` | `{"detail": "Status inválido 'INVALIDO'. Valores permitidos: EM_ANDAMENTO, FALHA, PARCIAL, SUCESSO."}` |
| Parâmetro inválido (validação) | `422` | `{"erro": "Erro de validação nos parâmetros", "detail": [ { "type": "int_parsing", "loc": ["query", "limit"], "msg": "...", "input": "abc" } ]}` |
| Banco indisponível (`ErroConexaoBanco`) | `503` | `{"erro": "Erro de Conexão com o Banco", "mensagem": "Não foi possível estabelecer comunicação com o Supabase."}` |
| Banco indisponível em `/health/ready` (`HTTPException`) | `503` | `{"detail": "Banco de dados indisponível ou configuração ausente."}` |
| Falha na consulta (`ErroOperacaoBanco`) | `500` | `{"erro": "Erro na Operação do Banco", "mensagem": "Falha ao executar a operação solicitada no Supabase."}` |
| Variável de ambiente ausente | `500` | `{"erro": "Erro de Configuração", "mensagem": "Uma variável de ambiente obrigatória não foi configurada."}` |
| Erro inesperado | `500` | `{"erro": "Erro interno no servidor", "mensagem": "Ocorreu um erro inesperado na aplicação."}` |

Os detalhes técnicos (nome da variável de ambiente, stack trace) são registrados apenas nos logs (`app.exception`), nunca na resposta.

## 📝 Observações e limitações

- Uma consulta (ou página) sem registros responde `404` (e não `200` com `items` vazio).
- A ordem é sempre `id` decrescente; ainda não há parâmetro de ordenação nem paginação por `offset` (só por cursor).
- A rota `/health` foi substituída por `/health/live` e `/health/ready`; monitores externos que usavam `/health` precisam ser atualizados.
- As variáveis `SUPABASE_URL`, `SUPABASE_KEY` e `LOG_LEVEL` precisam estar definidas no `.env` (o módulo de banco configura os logs ao ser importado).
- Os testes de `tests/test_crimes.py` e `tests/test_historico_ingestoes.py` consultam o Supabase real, enquanto `tests/test_health.py` usa `monkeypatch` sem acessar o banco; veja o [README](../README.md#66-executar-os-testes).
- A cobertura histórica dos dados em produção é limitada: a série histórica da SSPDS/CE foi recortada para os anos mais recentes de cada planilha (hoje, `INTERVALO_MAXIMO_ANOS=6`) por causa do limite de armazenamento do plano gratuito do Supabase. Ocorrências anteriores a esse período não estão disponíveis na API. Detalhes em [`docs/ingestion.md`](ingestion.md#81-cobertura-atual-dos-dados-em-produção).
