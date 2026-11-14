# Documentação da API Pública de Segurança - SSPDS/CE

Esta documentação descreve a arquitetura, a estrutura de diretórios modular e os endpoints disponíveis na API de dados de segurança pública do Ceará.

A API é construída com **FastAPI** e lê os dados da tabela `ocorrencias_crimes` do **Supabase** (alimentada pelo serviço de ingestão). A documentação interativa gerada automaticamente fica em `/docs` (Swagger UI) e `/redoc`.

## 📁 Estrutura de Diretórios da API

A API segue uma arquitetura orientada a serviços e separação de responsabilidades (Clean Architecture / Modular) dentro da pasta `app/`:

```text
api_sspds/
├── app/
│   ├── __init__.py
│   ├── config.py                 # get_variavel_ambiente (leitura do .env, independente de database/)
│   ├── dockerfile
│   ├── exception.py              # Exceções da API (RecursoNaoEncontrado, VariavelAmbienteNaoEncontrada) e handlers
│   ├── main.py                   # Instância FastAPI, /, /health
│   ├── routers/
│   │   ├── __init__.py
│   │   └── crimes.py             # Rotas /crimes/*
│   ├── schemas/ # Serve para serialização, val. de saída e doc. aut.
│   │   ├── __init__.py
│   │   ├── base_schema.py        # CrimeBaseSchema (campos comuns)
│   │   ├── consulta_schema.py    # CrimeGeralResponse (rota geral)
│   │   ├── operacional_schema.py # OperacionalResponse
│   │   ├── preconceito_schema.py # PreconceitoResponse
│   │   └── vitima_schema.py      # CrimeComVitimaResponse, CvliResponse
│   └── services/
│       ├── __init__.py
│       └── crime_service.py      # Consultas ao Supabase (filtros, tipos, período)
```

### Fluxo de uma requisição

`Router` (valida parâmetros) → `CrimeService` (monta a consulta e acessa o Supabase) → `Schema` (valida e serializa a resposta) → JSON.

O `CrimeService` acessa o banco de duas formas:

- **Zero ou um tipo de crime** (rota geral, `/cvli`, `/preconceito`): usa `database.repository.consultar_registros`, com filtros de igualdade, período sobre `data_fato` (`coluna_data`, `data_inicio`, `data_fim`) e `limit`.
- **Vários tipos** (`/vitimas` e `/operacionais`): o repository só suporta igualdade, então o serviço cria um cliente com `criar_cliente_supabase()` e monta a consulta com filtro `IN` em `tipo_crime`.

Erros de banco (`ErroOperacaoBanco`), de conexão (`ErroConexaoBanco`) e de configuração (`VariavelAmbienteNaoEncontrada`) são propagados como estão e tratados por `app/exception.py`. A API tem a própria `get_variavel_ambiente` (`app/config.py`) e a própria `VariavelAmbienteNaoEncontrada`; o handler de configuração cobre também a exceção homônima de `database/`, de modo que `app` e `database` só compartilham as exceções de banco.

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

### 2. Verificação de Saúde (Health Check)
- **Método:** `GET`
- **Rota:** `/health`
- **Descrição:** Endpoint destinado a monitorização e validação do estado operacional do contentor/servidor. Indica apenas que o processo da API está no ar; **não** testa a conexão com o banco.
- **Resposta (Exemplo - `200 OK`):**
  ```json
  {
    "status": "ok"
  }
  ```

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
  - `limit` (`integer`, `> 0`): Limita o número de registos retornados.
- **Response Model:** `List[CrimeGeralResponse]`
- **Descrição:** Consulta a base unificada de dados permitindo o uso combinado de filtros de pesquisa.
- **Normalização dos filtros de texto:** `municipio`, `ais`, `natureza`, `meio_empregado`, `vitima_genero`, `vitima_raca`, `dia_semana` e `tipo_entorpecente` são comparados por igualdade exata, mas a entrada é normalizada para o padrão gravado pela ingestão (espaços extras removidos e Title Case), então `fortaleza` encontra `Fortaleza` e `masculino` encontra `Masculino`. `tipo_crime` é normalizado para caixa alta.
- **Exemplo:** `GET /crimes/?municipio=Fortaleza&tipo_crime=FURTO&vitima_genero=Masculino&data_inicio=2025-01-01&data_fim=2025-03-31&limit=10`
- **Códigos de Resposta:**
  - `200 OK`: Registos encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum crime encontrado com os filtros fornecidos.
  - `422 Unprocessable Content`: Parâmetro de consulta inválido (ex.: data fora do formato, `limit` não numérico ou `<= 0`) **ou** `data_inicio` posterior a `data_fim`.
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
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados. Caso omitido, retorna a base completa.
- **Tipo(s) de crime:** `CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI`
- **Response Model:** `List[CvliResponse]`
- **Descrição:** Lista ocorrências específicas de CVLI com detalhamento de perfil de vítima e natureza.
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum dado de CVLI encontrado na base.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido (não numérico ou menor/igual a zero).
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 5. Listagem de Crimes com Perfil de Vítima
- **Método:** `GET`
- **Rota:** `/crimes/vitimas`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Tipo(s) de crime:** `LEI 11.340/06 (LEI MARIA DA PENHA)`, `CRIMES SEXUAIS` e `INDÍGENAS VÍTIMAS DE CRIMES` (os três, na mesma lista; use `tipo_crime` em cada registo para distingui-los).
- **Response Model:** `List[CrimeComVitimaResponse]`
- **Descrição:** Retorna ocorrências específicas de crimes com detalhamento de perfil da vítima (Lei Maria da Penha, Crimes Sexuais e Indígenas).
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro de crime com vítima encontrado.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 6. Listagem de Crimes de Preconceito
- **Método:** `GET`
- **Rota:** `/crimes/preconceito`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Tipo(s) de crime:** `HOMOFOBIA E TRANSFOBIA`
- **Response Model:** `List[PreconceitoResponse]`
- **Descrição:** Retorna ocorrências específicas de crimes motivados por preconceito (homofobia e transfobia).
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum crime de preconceito encontrado.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

### 7. Listagem de Crimes Operacionais
- **Método:** `GET`
- **Rota:** `/crimes/operacionais`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Tipo(s) de crime:** `FURTO` e `CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP` (os dois, na mesma lista; use `tipo_crime` em cada registo para distingui-los).
- **Response Model:** `List[OperacionalResponse]`
- **Descrição:** Retorna ocorrências de crimes operacionais de menor complexidade estrutural (Furtos e CVP).
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro operacional encontrado.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido.
  - `500` / `503`: Falha no banco de dados ou na configuração.

---

## 📦 Schemas de Resposta

Os schemas das rotas específicas herdam de `CrimeBaseSchema`.

| Schema | Campos | Usado em |
| :--- | :--- | :--- |
| `CrimeBaseSchema` | `tipo_crime`, `ais`, `municipio` (obrigatório), `data_fato` (obrigatório), `hora_fato`, `dia_semana`, `st_dia_semana_divergente`, `st_idade_invalida` | Base dos demais |
| `OperacionalResponse` | Somente os campos da base | `/crimes/operacionais` |
| `CrimeComVitimaResponse` | Base + `vitima_genero`, `vitima_idade`, `vitima_escolaridade`, `vitima_raca` | `/crimes/vitimas` |
| `CvliResponse` | `CrimeComVitimaResponse` + `natureza`, `meio_empregado` | `/crimes/cvli` |
| `PreconceitoResponse` | Base + `natureza`, `local_fato`, `vitima_genero`, `vitima_orientacao_sexual`, `vitima_idade`, `vitima_escolaridade`, `vitima_raca` | `/crimes/preconceito` |
| `CrimeGeralResponse` | Todos os campos da tabela `ocorrencias_crimes` (lista acima) | `/crimes/` |

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
| Parâmetro inválido (validação) | `422` | `{"erro": "Erro de validação nos parâmetros", "detail": [ { "type": "int_parsing", "loc": ["query", "limit"], "msg": "...", "input": "abc" } ]}` |
| Banco indisponível (`ErroConexaoBanco`) | `503` | `{"erro": "Erro de Conexão com o Banco", "mensagem": "Não foi possível estabelecer comunicação com o Supabase."}` |
| Falha na consulta (`ErroOperacaoBanco`) | `500` | `{"erro": "Erro na Operação do Banco", "mensagem": "Falha ao executar a operação solicitada no Supabase."}` |
| Variável de ambiente ausente | `500` | `{"erro": "Erro de Configuração", "mensagem": "Uma variável de ambiente obrigatória não foi configurada."}` |
| Erro inesperado | `500` | `{"erro": "Erro interno no servidor", "mensagem": "Ocorreu um erro inesperado na aplicação."}` |

Os detalhes técnicos (nome da variável de ambiente, stack trace) são registrados apenas nos logs (`app.exception`), nunca na resposta.

## 📝 Observações e limitações

- Uma consulta que não encontra registros responde `404` (e não `200` com lista vazia).
- A ordem dos registros não é garantida; combinada com `limit`, a seleção pode variar entre chamadas. Ainda não há parâmetro de ordenação.
- O Supabase/PostgREST pode impor um teto de linhas por requisição (padrão de 1000 no Supabase hospedado, configurável no projeto). Use `limit` e os filtros de período para consultas grandes; ainda não há paginação por `offset`.
- As variáveis `SUPABASE_URL`, `SUPABASE_KEY` e `LOG_LEVEL` precisam estar definidas no `.env` (o módulo de banco configura os logs ao ser importado).
- Os testes de `tests/test_crimes.py` consultam o Supabase real; veja o [README](../README.md#65-executar-os-testes).
