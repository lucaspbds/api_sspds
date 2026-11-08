# Documentação Técnica: Serviço de Ingestão de Dados

## 1. Visão geral

O **Serviço de Ingestão de Dados** é um pipeline ETL desenvolvido em Python. Ele coleta os links das planilhas disponibilizadas no portal da Secretaria da Segurança Pública e Defesa Social (SSPDS), baixa os arquivos Excel, verifica se seus conteúdos já foram ingeridos, classifica os arquivos, normaliza os registros e persiste os dados no banco de dados hospedado.

A persistência é realizada nas tabelas do banco de dados, por meio das funções de inserção e
atualização.
## 2. Estrutura de arquivos

A estrutura abaixo apresenta os módulos relevantes para o serviço. Ela não pretende representar todos os arquivos existentes no pacote.

``` text
ingestion/
├── classifier.py       # Classificação do tipo de ocorrência pelo nome do arquivo
├── cleanup.py          # Limpeza do diretório temporário
├── config.py           # Leitura de variáveis de ambiente
├── crawler.py          # Coleta dos links de planilhas no portal da SSPDS
├── downloader.py       # Download dos arquivos Excel
├── dockerfile          # Construção e configuração da imagem Docker
├── exception.py        # Hierarquia de exceções customizadas
├── helpers.py          # Funções auxiliares
├── insert.py           # Inserção e atualização de registros no banco
├── normalizer.py       # Normalização dos dados das planilhas
├── pipeline.py         # Orquestração do processo de ingestão
└── validator.py        # Validação, cálculo de hash e consulta de duplicidade
```

## 3. Módulos e componentes

### 3.1 `config.py`

Carrega as variáveis de ambiente contidas no arquivo `.env` usando `python-dotenv`.

**`get_variavel_ambiente(nome_variavel: str)`**

-   **Descrição:** obtém o valor de uma variável de ambiente.
-   **Parâmetros:** `nome_variavel`, nome da variável.
-   **Retorno:** valor atribuído à variável.
-   **Exceção:** lança `VariavelAmbienteNaoEncontrada` quando a variável
    não existe ou está vazia.

### 3.2 `crawler.py`

Responsável por acessar a página da SSPDS e coletar os endereços dos arquivos publicados na seção de indicadores detalhados.

**`extrair_links(conteudo_html)`**

- Recebe um elemento HTML processado pelo BeautifulSoup.
- Retorna uma lista com todas as tags `<a>` encontradas.
- Se o conteúdo recebido for nulo ou falso, retorna uma lista vazia.

**`crawler() -> list`**

- Obtém a URL da página por meio da variável de ambiente `url_sspds`.
- Obtém `CRAWLER_TIMEOUT` e tenta convertê-la para inteiro com `recebeInteiro()`.
- Se `CRAWLER_TIMEOUT` estiver ausente ou inválido, registra um aviso e utiliza o padrão de 10 segundos.
- Realiza a requisição HTTP com `requests.get()` e aplica `raise_for_status()` para identificar respostas HTTP de erro.
- Analisa o HTML com `BeautifulSoup`.
- Procura o container dos indicadores detalhados pelo seletor CSS
  `#conteudo > div > div > div > section > section > div > div:nth-child(20)`.
- Se o container não for encontrado, lança `EstruturaCSSDoSiteAlterado`.
- Extrai as tags de link do container e retorna somente os valores `href` não vazios.

**Retorno:** lista de URLs (`list[str]`). 

**Erros e logs:** registra erros de timeout, conexão, HTTP e demais falhas de requisição, propagando as exceções. Também registra e propaga falhas de configuração, alteração da estrutura HTML e erros não mapeados. 

### 3.3 `helpers.py`

Módulo utilitário com funções de apoio.

**`recebeInteiro(valor: str) -> int`**

-   **Descrição:** converte um valor em número inteiro.
-   **Parâmetros:** `valor`, valor textual a converter.
-   **Retorno:** número inteiro correspondente.
-   **Exceção:** lança `ValorInteiroInvalido` quando a conversão não pode ser realizada.

### 3.4 `downloader.py`

Responsável por baixar as planilhas Excel disponibilizadas pelas URLs coletadas pelo crawler.

**`download_xlsx(url: str, destination_dir: str | Path = DEFAULT_PATH, filename: str | None = None, timeout: int = TIMEOUT_SECONDS) -> Path`**

-   **Descrição:** baixa um arquivo `.xlsx` por HTTP ou HTTPS e o grava no diretório de destino.
-   **Parâmetros:**
    -   `url`: endereço HTTP(S) do arquivo.
    -   `destination_dir`: diretório em que o arquivo será salvo. Por padrão, utiliza a variável de ambiente `TEMP_PATH`.
    -   `filename`: nome alternativo utilizado somente quando a URL não fornece um nome de arquivo no caminho.
    -   `timeout`: tempo limite da requisição, em segundos. Por padrão, utiliza a variável de ambiente `DOWNLOADER_TIMEOUT`.
-   **Retorno:** caminho do arquivo baixado, representado como `Path`.
-   **Validações:** exige URL HTTP(S) com host válido, nome de arquivo sem diretórios e extensão `.xlsx`; o timeout deve ser positivo.
-   **Gravação:** cria o diretório de destino, baixa o conteúdo em
    blocos e grava primeiro em um arquivo temporário `.part`. Após a
    escrita, realiza `flush` e `fsync` e substitui o destino pelo
    arquivo concluído. Isso evita deixar um arquivo final parcialmente
    baixado.
-   **Tratamento de erros:** traduz falhas de timeout, HTTP, conexão,
    requisição e escrita em exceções específicas do serviço. O arquivo
    parcial é removido ao final da operação.

**Configurações utilizadas**
*variáveis de ambiente*
-   `DOWNLOADER_TIMEOUT`: timeout padrão, convertido para inteiro.
-   `CHUNK_SIZE`: tamanho dos blocos usados durante o download.
-   `TEMP_PATH`: diretório temporário padrão.

### 3.5 `validator.py`

Responsável por verificar a integridade básica do arquivo baixado, calcular seu hash e consultar o banco para identificar conteúdo ou nome previamente registrado.

**`calculate_sha256(file_path)`**

-   Calcula o SHA-256 do arquivo lendo-o em blocos de tamanho configurado por `HASH_CHUNK_SIZE`.
-   Falhas de leitura ou configuração inválida são reportadas como `FileValidationError`.

**`check_hash_in_database(file_hash: str) -> bool`**

-   Consulta a tabela `informacoes_arquivo` pelo campo `hash_sha256`.
-   Retorna `True` quando já existe um registro com o hash informado e `False` caso contrário.
-   Hash vazio ou falhas na consulta são tratados como `DatabaseLookupError`.

**`check_filename_in_database(file_name: str) -> list`**

-   Consulta a tabela `informacoes_arquivo` pelo campo `nome_arquivo`.
-   Quando encontra o nome, retorna `[id, True]`, em que `id` é o identificador do registro encontrado.
-   Quando não encontra, retorna `[None, False]`.
-   Nome vazio ou falhas na consulta são tratados como
    `DatabaseLookupError`.

**`validate_xlsx_file(file_path) -> ValidatedFile`**

Verifica se o caminho existe, se aponta para um arquivo regular e se
possui extensão `.xlsx`. Em seguida, calcula o hash e consulta o banco
tanto pelo hash quanto pelo nome.

O resultado contém:

  `path`: Caminho relativo do arquivo.
  `name`: Nome do arquivo.
  `sha256`: Hash SHA-256 do conteúdo.
  `is_new`: `True` quando o conteúdo (hash) ainda não está registrado; `False` quando o hash já existe.
  `size_bytes`: Tamanho do arquivo em bytes.
  `name_exists`: Indica se já existe registro com aquele nome de arquivo.
  `id_registro`: ID do registro encontrado pela consulta do nome; `None` se o nome                        não existir.

**Atenção: `is_new` e `name_exists` não representam a mesma verificação.**

-   `is_new` verifica a novidade do **conteúdo**, por meio do hash.
-   `name_exists` verifica a existência do **nome do arquivo**.
-   Portanto, é possível que `is_new=True` e `name_exists=True`: o nome já está cadastrado, mas o conteúdo do arquivo é diferente.
-   `id_registro` é obtido pela consulta do nome, não pela consulta do hash.

### 3.6 `classifier.py`

Responsável por identificar a categoria do arquivo com base em seu nome.

**`normalizar_nome(texto)`**

Normaliza o texto para comparação: remove acentos, aplica normalização Unicode, converte para minúsculas de forma compatível com Unicode, substitui caracteres não alfanuméricos por espaços e elimina espaços excedentes.

**`classificar_tipo_ocorrencia(nome_arquivo: str | Path) -> str`**

-   Utiliza somente o nome-base do caminho para classificar o arquivo.
-   Compara o nome normalizado com as palavras-chave definidas em `REGRAS_TIPO_OCORRENCIA`.
-   Remove correspondências duplicadas, preservando a ordem das regras.
-   Retorna o nome canônico da categoria quando há exatamente uma categoria correspondente.
-   Lança `ValueError` para nome vazio.
-   Retorna `TipoOcorrenciaNaoIdentificado` quando nenhuma categoria é identificada ou quando há correspondência com mais de uma categoria.

**`classificar_arquivo(metadado: MetadadoArquivo) -> MetadadoArquivo`**

-   **Parâmetro:** dicionário de metadados que deve conter `path` não vazio.
-   **Retorno:** uma nova cópia dos metadados, acrescida da chave `tipo_ocorrencia`.
-   **Comportamento:** preserva os demais campos recebidos e não modifica o dicionário original.

O classificador é chamado pelo pipeline somente para arquivos cujo conteúdo foi considerado novo (`is_new=True`).

### 3.7 `normalizer.py`

Responsável por converter as linhas do DataFrame de cada planilha em dicionários com os campos esperados pela tabela `ocorrencias_crimes`. A escolha da rotina de normalização depende do valor canônico de `tipo_ocorrencia`.

**`normalizer(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia: str) -> list[dict]`**

- Recebe o DataFrame, o ID do arquivo em `informacoes_arquivo` e a categoria identificada pelo classificador.
- Encaminha o DataFrame para a função específica da categoria.
- Os normalizadores específicos exigem `arquivo_id > 0` e verificam as colunas obrigatórias da planilha.
- Os registros incluem `arquivo_id`, `tipo_crime`, `municipio`, `ais`, `data_fato`, `hora_fato`, `dia_semana` e campos específicos da categoria. Campos não aplicáveis são preenchidos com `None`.

**Funções auxiliares**

- `normalizar_texto(valor)`: retorna `None` para valores ausentes; nos demais casos, converte para texto, remove espaços nas extremidades, substitui sequências de espaços por um único espaço e aplica capitalização de título (`title()`).
- `normalizar_data(valor)`: converte o valor para `datetime.date` usando `pandas.to_datetime(..., errors="raise")`.
- `normalizar_hora(valor)`: retorna `None` para valores ausentes ou `"não informada"`; preserva valores que já sejam `datetime.time`; nos demais casos, converte para `datetime.time`.
- `normalizar_idade(valor)`: retorna `None` para valores ausentes ou `"não informada"`/`"não informado"`; nos demais casos, converte para `float`. A validação do intervalo e da integralidade é feita nos normalizadores que utilizam idade.
- `normalizar_quantidadeArmas(valor)`: converte para número inteiro. Retorna `None` quando ausente, não informada ou fracionária; valores fracionários são registrados como aviso.
- `normalizar_quantidadeEntorpecente(valor)`: converte a quantidade para `float`, aceitando vírgula como separador decimal. Em caso de falha de conversão, registra aviso e retorna `None`.
- `normalizar_ais(valor)`: normaliza o texto e retorna `None` quando o resultado contém `"Ais Não Identificada"`; caso contrário, retorna o texto normalizado.

**Normalizadores por categoria**

| Função | Tipos de ocorrência atendidos |
|---|---|
| `normalizar_cvli(...)` | Crimes Violentos Letais e Intencionais (CVLI) |
| `normalizar_animais_CVP_Furto_Incendio_Salvamento(...)` | Maus-tratos a animais, CVP, Furto, Incêndio e Busca e Salvamento |
| `normalizar_armaDeFogo(...)` | Apreensão de armas de fogo |
| `normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha(...)` | Preconceito de raça ou cor, Crimes Sexuais, Indígenas vítimas de crimes e Lei Maria da Penha |
| `normalizar_entorpecentes(...)` | Apreensão de entorpecentes |
| `normalizar_homofobiaETransfobia(...)` | Homofobia e Transfobia |

**Colunas obrigatórias por grupo**

| Normalizador | Colunas exigidas |
|---|---|
| CVLI | Município, AIS, Natureza, Data, Hora, Dia da Semana, Meio Empregado, Gênero, Idade da Vítima, Escolaridade da Vítima, Raça da Vítima |
| Animais/CVP/Furto/Incêndio/Salvamento | Município, AIS, Data, Hora, Dia da Semana |
| Armas de fogo | Município, AIS, Data, Hora, Dia da Semana, Quantidade |
| Preconceito/Crimes Sexuais/Indígenas/Lei Maria da Penha | Município, AIS, Data, Hora, Dia da Semana, Gênero, Idade da Vítima, Escolaridade da Vítima, Raça da Vítima |
| Entorpecentes | Município, AIS, Data, Hora, Dia da Semana, Quantidade (Kg), Tipo de Entorpecente |
| Homofobia e Transfobia | Município, AIS, Data, Hora, Dia da Semana, Idade da Vítima, Escolaridade da Vítima, Raça da Vítima, Natureza, Identidade de Gênero, Orientação Sexual, Local |

**Regras de qualidade e sinalização**

1. **Idade (`st_idade_invalida`)**
   - Nos normalizadores CVLI, preconceito/crimes sexuais/indígenas/Lei Maria da Penha e homofobia/transfobia, a idade é convertida para `float` e sinalizada quando não é inteira ou está fora do intervalo de 0 a 130.
   - `st_idade_invalida=True` indica idade fracionária, menor que zero ou maior que 130; `False` indica que a verificação não identificou essas condições.
   - O valor numérico considerado inválido não é substituído por `None`: permanece em `vitima_idade` (como `float`), acompanhado da flag. Idades inteiras válidas são convertidas para `int`.
   - Valores ausentes ou "não informados" tornam-se `None` e mantêm a flag como `False`.

2. **Dia da semana (`st_dia_semana_divergente`)**
   - Compara `Dia da Semana` com o dia calculado a partir de `Data`.
   - A comparação ignora diferenças entre maiúsculas/minúsculas e remove o sufixo `-feira` antes de comparar.
   - `True` indica divergência; `False` indica que a comparação não encontrou divergência.
   - O valor informado é preservado em `dia_semana`; não é corrigido para coincidir com a data.
   - Se o dia informado estiver ausente (`None`), a flag permanece `False`, pois a comparação só ocorre quando há um valor informado.
   - A flag é gerada pelos seis grupos de normalização.

3. **AIS não identificada**
   - `normalizar_ais()` normaliza o texto e retorna `None` quando ele contém `"Ais Não Identificada"`.
   - Assim, valores como `AIS Não Identificada (<nome_do_município>)` são convertidos para `None`, pois o município já está registrado separadamente.
   - A regra é implementada por busca de substring, não por validação de um formato textual exato.

**Campos normalizados**

Os normalizadores montam um schema comum, com campos como `arquivo_id`, `tipo_crime`, `municipio`, `ais`, `data_fato`, `hora_fato`, `local_fato`, `dia_semana`, `natureza`, `meio_empregado`, `vitima_genero`, `vitima_idade`, `vitima_escolaridade`, `vitima_raca`, `vitima_orientacao_sexual`, `quantidade_armas`, `tipo_entorpecente`, `peso_entorpecente_kg` e as flags de qualidade
aplicáveis.

O roteamento utiliza os nomes canônicos exatos definidos no código. Uma categoria não mapeada gera `tipoOcorrenciaNaoEncontrado`, que é capturada pelo `normalizer()`.

### 3.8 `insert.py`

Centraliza as operações de inserção e atualização nas tabelas utilizadas pelo serviço de ingestão.

**Histórico de ingestões**

-   `inserir_historico_ingestoes(dados: dict) -> int`: insere um registro em `historico_ingestoes` e retorna o ID do registro retornado pelo banco.
-   `atualizar_historico_ingestoes(id: int, dados: dict) -> list[dict]`: atualiza o registro de `historico_ingestoes` identificado pela coluna `id` e retorna o ID retornado pela operação.

**Metadados dos arquivos**

-   `inserir_informacoes_arquivo(dados: dict) -> int`: insere um registro em
    `informacoes_arquivo` e retorna seu ID.
-   `atualizar_informacoes_arquivo(id, dados) -> int`: atualiza um registro de `informacoes_arquivo` e retorna o ID retornado pela operação.

**Registros de ocorrências**

-   `inserir_ocorrencias_crimes(dados: list[dict], tamanho_lote=tamanho_lote)`: divide a lista de ocorrências em lotes e insere cada lote na tabela `ocorrencias_crimes`.
-   O tamanho padrão do lote é obtido da variável de ambiente `INSERT_CHUNK_SIZE`.

### 3.9 `cleanup.py`

Responsável por remover o diretório temporário utilizado durante a ingestão.

**`limpar_pasta_temporaria(caminho: str | Path = TEMP_PATH) -> None`**

-   Se o caminho não existir, registra a situação e retorna sem erro.
-   Se o caminho existir, mas não for um diretório, lança `NotADirectoryError`.
-   Se for um diretório, remove-o recursivamente com `shutil.rmtree`.
-   Falhas de remoção são registradas e propagadas como `OSError`.

### 3.10 `pipeline.py`

É o orquestrador do serviço. Executa a coleta, o processamento dos arquivos e a persistência dos dados.

**`pipeline() -> None`**

A função não recebe parâmetros e não retorna valor. Seu fluxo é:

1.  Executa `crawler()` e obtém a lista de URLs das planilhas.
2.  Cria um registro em `historico_ingestoes` com status `EM_ANDAMENTO` e a quantidade de arquivos encontrados.
3.  Para cada URL:
    1.  Baixa a planilha com `download_xlsx()`.
    2.  Registra a data de coleta em UTC.
    3.  Valida o arquivo com `validate_xlsx_file()`, calculando seu hash e consultando o banco pelo hash e pelo nome.
    4.  Se `is_new` for `False`, não executa a classificação, normalização nem inserção das ocorrências para aquele arquivo.
    5.  Se `is_new` for `True`, classifica o arquivo com `classificar_arquivo()`.
    6.  Se `name_exists` for `True`, atualiza o registro de `informacoes_arquivo` identificado por `id_registro`. Nesse caminho, os campos atualizados incluem URL de download, hash,
        período de dados, tamanho, data de coleta, data de atualização e ID da ingestão. O pipeline utiliza o ID retornado pela atualização como `arquivo_id`.
    7.  Se `name_exists` for `False`, insere um novo registro em `informacoes_arquivo`, incluindo nome do arquivo, URL, hash, tipo de ocorrência, período de dados, tamanho, data de coleta e ID da ingestão. O ID retornado pela inserção passa a ser o `arquivo_id`.
    8.  Lê a planilha com `pandas.read_excel()`.
    9.  Chama `normalizer(df=..., arquivo_id=..., tipo_ocorrencia=...)`.
    10. Insere os registros normalizados em `ocorrencias_crimes`, em lotes.
    11. Extrai os anos presentes em `data_fato` e atualiza `periodo_dados` nos metadados do arquivo. Quando há um único ano, registra esse ano; quando há mais de um, registra o
        intervalo entre o menor e o maior ano.
4.  Se ocorrer uma exceção durante o processamento de um arquivo, o pipeline registra a falha, incrementa o contador de falhas e continua para o próximo arquivo.
5.  Ao final do processamento, atualiza o histórico com a data de fim, os totais de arquivos processados e de falhas, e status `SUCESSO`, caso não tenha falhas no processo.
6.  Executa `limpar_pasta_temporaria()` ao final do fluxo normal.

**Observações importantes sobre o comportamento atual**

-   A contagem de `arquivos_processados` é incrementada fora da condição `is_new`. Assim, um arquivo cujo hash já existe também pode ser contabilizado como processado, embora não seja normalizado nem tenha ocorrências inseridas novamente.
-   Limitação do código atual: as exceções ocorridas durante o processamento individual dos arquivos são capturadas pelo `try/except` do laço, permitindo que o pipeline continue. Entretanto, falhas ocorridas fora desse bloco, como durante o crawler ou a atualização do histórico, podem interromper a execução antes da limpeza do diretório temporário. A limpeza não está protegida por um bloco `finally`.
-   O caminho de atualização por nome existente não atualiza `nome_arquivo` nem `tipo_crime`; ele atualiza os demais metadados indicados no código.
-   O `arquivo_id` associa os registros normalizados ao registro correspondente em `informacoes_arquivo`.

### 3.11 `exception.py`

Define a hierarquia de exceções do serviço.

- `IngestionError`: classe-base para erros esperados no pipeline.
- `VariavelAmbienteNaoEncontrada`: variável de ambiente obrigatória
  ausente.
- `EstruturaCSSDoSiteAlterado`: container esperado dos indicadores
  detalhados não encontrado no HTML.
- `ValorInteiroInvalido`: valor que não pôde ser convertido para
  inteiro.
- `NormalizerError`: classe-base para exceções relacionadas à
  normalização.
- `ColunasAusentesNaPlanilha`: uma ou mais colunas obrigatórias não
  estão presentes no DataFrame.
- `tipoOcorrenciaNaoEncontrado`: tipo de ocorrência não mapeado pelo
  normalizador.
- `DownloadError`: classe-base para falhas de download ou gravação.
- `DownloadHTTPError`: resposta HTTP de erro.
- `DownloadTimeoutError`: timeout na requisição.
- `DownloadConnectionError`: falha de conexão.
- `FileWriteError`: falha ao gravar o arquivo baixado.
- `FileValidationError`: falha ao localizar, ler ou calcular o hash
  de um arquivo.
- `DatabaseLookupError`: falha ao consultar dados no banco.
- `TipoOcorrenciaNaoIdentificado`: nome de arquivo sem correspondência
  única com as regras de classificação; herda diretamente de
  `ValueError`, não de `IngestionError`.

As exceções de download, validação, consulta e classificação são
utilizadas pelos módulos analisados. A exceção de normalização
`tipoOcorrenciaNaoEncontrado` é capturada dentro de `normalizer()`;
conforme descrito na seção anterior, não é propagada ao chamador por
essa função.

### 3.12 `dockerfile`

Define a imagem e o ambiente de execução do serviço de ingestão.

- Utiliza a imagem base `python:3.13.4`.
- Define `/workspace` como diretório de trabalho.
- Copia `requirements.txt` e instala as dependências com
  `pip install --no-cache-dir -r requirements.txt`.
- Instala o pacote `ca-certificates` e atualiza o repositório de
  certificados do sistema.
- Copia `certs/amazon-rsa-2048-m01.crt` para
  `/usr/local/share/ca-certificates/` e executa `update-ca-certificates`.
- Define `REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt`,
  para que as requisições feitas com `requests` utilizem o conjunto de
  certificados configurado no container.
- Copia os diretórios `ingestion/`, `database/` e
  `logging_system/` para `/workspace`.
- Define como comando padrão
  `python -m ingestion.pipeline`.

O Dockerfile, portanto, inclui no container não apenas o pacote de
ingestão, mas também os módulos de acesso ao banco e de configuração de
logs, além do certificado CA adicional.

## 4. Fluxo de ingestão de dados

``` text
                 ┌─────────────────────┐
                 │       crawler       │
                 │ Coleta URLs SSPDS   │
                 └──────────┬──────────┘
                            │ lista_url
                            ▼
                 ┌─────────────────────┐
                 │      pipeline       │
                 │ Cria histórico      │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │     downloader      │
                 │ Baixa arquivo XLSX  │
                 └──────────┬──────────┘
                            │ arquivo local
                            ▼
                 ┌─────────────────────┐
                 │      validator      │
                 │ SHA-256 + consultas │
                 │ por hash e nome     │
                 └──────────┬──────────┘
                            │
                 ┌──────────┴──────────┐
                 │ is_new?             │
                 └──────────┬──────────┘
                     Não    │    Sim
                ┌───────────┘     └───────────────┐
                ▼                                 ▼
        Não reprocessa                    ┌─────────────────┐
        ocorrências                       │    classifier   │
                                          │ Identifica tipo  │
                                          └────────┬────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │ insert / update │
                                          │ informacoes_    │
                                          │ arquivo         │
                                          └────────┬────────┘
                                                   │ arquivo_id
                                                   ▼
                                          ┌─────────────────┐
                                          │   normalizer    │
                                          │ DataFrame + ID  │
                                          │ + tipo          │
                                          └────────┬────────┘
                                                   │ registros
                                                   ▼
                                          ┌─────────────────┐
                                          │     insert      │
                                          │ ocorrencias_    │
                                          │ crimes (lotes)  │
                                          └────────┬────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │ Atualiza período│
                                          │ e histórico     │
                                          └────────┬────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │     cleanup     │
                                          │ Remove temporário│
                                          └─────────────────┘
```

## 5. Persistência no banco de dados

O pipeline utiliza as seguintes tabelas:
  `historico_ingestoes`: Registra o início e o encerramento de cada execução, incluindo status e contadores.

  `informacoes_arquivo`: Armazena os metadados dos arquivos, como nome, URL, hash, categoria,   tamanho, período e datas de coleta.

  `ocorrencias_crimes`: Armazena os registros normalizados extraídos das planilhas.

A associação entre o arquivo de origem e suas ocorrências é realizada pelo campo `arquivo_id`, encaminhado ao normalizador e incluído nos registros normalizados.

## 6. Variáveis de ambiente identificadas

  `TEMP_PATH`: Diretório temporário utilizado para armazenar os arquivos baixados e posteriormente removido pela limpeza.

  `DOWNLOADER_TIMEOUT`: Timeout padrão das requisições de download.

  `CHUNK_SIZE`: Tamanho dos blocos de leitura durante o download.

  `HASH_CHUNK_SIZE`: Tamanho dos blocos utilizados no cálculo do SHA-256.

  `INSERT_CHUNK_SIZE`: Quantidade de registros enviados por lote para inserção em `ocorrencias_crimes`.

As variáveis são obtidas por `get_variavel_ambiente()` e convertidas para inteiro com `recebeInteiro()` ou com a conversão utilizada diretamente no módulo correspondente.
