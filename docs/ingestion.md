# Documentação Técnica: Serviço de Ingestão de Dados

## 1. Visão Geral do Serviço

O **Serviço de Ingestão de Dados** é um pipeline de extração e processamento de dados (ETL) desenvolvido em Python. Ele é responsável por realizar a raspagem de dados (_web scraping_) no portal da **Secretaria da Segurança Pública e Defesa Social (SSPDS)**, extrair os links das planilhas de estatísticas/indicadores detalhados, converter esses dados estruturados do formato Excel para JSON e salvá-los localmente em um volume específico.

## 2. Estrutura de Arquivos

```
ingestion/
├── config.py          # Gerenciamento de variáveis de ambiente (.env)
├── crawler.py         # Módulo de Web Scraping da página da SSPDS
├── dockerfile         # Configuração para conteinerização da aplicação
├── exception.py       # Exceções customizadas do sistema
├── helpers.py         # Funções auxiliares e utilitários
├── normalizer.py      # Normalização e validação dos dados por tipo de ocorrência
├── pipeline.py        # Orquestrador principal do serviço
└── processor.py       # Processamento das planilhas e gravação em JSON
```

## 3. Módulos e Componentes

### 3.1 `config.py`

Carrega as variáveis de ambiente contidas no arquivo `.env` usando a biblioteca `python-dotenv`.

**`get_variavel_ambiente(nome_variavel: str)`**

    - **Descrição:** Captura o valor de uma variável de ambiente informada.
        
    - **Parâmetros:** `nome_variavel` (string) — Nome da chave no arquivo `.env`.
        
    - **Retorno:** Valor atribuído à variável de ambiente.
        
    - **Exceção:** Lança `VariavelAmbienteNaoEncontrada` caso a variável não exista ou esteja vazia.
        

### 3.2 `crawler.py`

Responsável por realizar a requisição HTTP na página da SSPDS, lidar com configurações de timeout, tratamento avançado de exceções de rede, logs estruturados e mapeamento de seletores HTML.

**`extrair_links(conteudo_html)`**
    
    - **Descrição:** Função auxiliar para capturar todas as tags `<a>` dentro de um elemento HTML delimitado. Retorna uma lista vazia se o conteúdo for nulo.
        
    - **Retorno:** Lista de objetos contendo as tags de link encontradas.
        
**`crawler() -> list`**
    
    - **Descrição:** Acessa a URL da SSPDS obtida via variável de ambiente (`url_sspds`), define o tempo limite da requisição utilizando a variável `CRAWLER_TIMEOUT` (com validação via `recebeInteiro` e fallback para 10 segundos), realiza o parse do HTML com `BeautifulSoup` e extrai os links das planilhas e os nomes dos indicadores.
        
    - **Retorno:** Uma lista composta por dois elementos `[links_arquivos, tipos_ocorrencias]`:
        
        - `links_arquivos`: Lista de URLs (atributos `href`) apontando para os arquivos de indicadores.
            
        - `tipos_ocorrencias`: Lista com os textos descritivos de cada indicador criminal.
            
    - **Tratamento de Exceções e Erros:**
        
        - Captura e trata erros de requisição do `requests` (`Timeout`, `ConnectionError`, `HTTPError`, `RequestException`), registrando logs específicos de erro.
            
        - Verifica se o container CSS esperado (`container_indicadores_detalhados`) existe na página; caso contrário, dispara a exceção `EstruturaCSSDoSiteAlterado`.
            
        - Captura falhas críticas de inicialização, problemas estruturais e erros genéricos, registrando-os via sistema de logs.
            

### 3.3 `helpers.py`

Módulo utilitário contendo funções de apoio para conversão e manipulação de tipos de dados.

**`recebeInteiro(valor: str) -> int`**
    
    - **Descrição:** Converte um valor fornecido em número inteiro.
        
    - **Parâmetros:** `valor` (str) — O valor a ser convertido.
        
    - **Retorno:** O número inteiro correspondente.
        
    - **Exceção:** Lança `ValorInteiroInvalido` se o valor não puder ser convertido (erros de tipo ou valor).
        

### 3.4 `processor.py`

Módulo encarregado do download, transformação e persistência dos dados.

**`processor(url: str, tiposOcorrencias: list) -> None`**
    
    - **Descrição:** Faz a leitura direta da planilha Excel via URL utilizando o `pandas`, converte a estrutura do DataFrame para um array de objetos JSON e salva os arquivos no diretório `/database`.
        
    - **Arquivos Gerados:**
        
        - `/database/dados.json`: Contém os registros da planilha Excel convertidos para formato `records`.
            
        - `/database/tiposOcorrencias.json`: Contém a lista de categorias e tipos de ocorrências extraídos do crawler.
            

### 3.5 `normalizer.py`

Responsável por transformar os dados brutos de cada planilha em registros normalizados, estruturados conforme o schema esperado pelo banco de dados. O módulo recebe um `pandas.DataFrame`, o identificador do arquivo de origem e o nome do tipo de ocorrência; em seguida, seleciona as regras de normalização apropriadas e retorna uma lista de dicionários.

**`normalizer(df: pd.DataFrame, arquivo_id: int, tipo_ocorrencia: str) -> list[dict]`**

- **Descrição:** Função de entrada do módulo. Configura o sistema de logs, registra o início da normalização e encaminha o DataFrame para o normalizador específico conforme `tipo_ocorrencia`.
- **Parâmetros:**
  - `df`: DataFrame com os dados brutos da planilha.
  - `arquivo_id`: identificador positivo do arquivo de origem, usado no campo `arquivo_id` dos registros.
  - `tipo_ocorrencia`: nome da categoria que determina as regras de normalização.
- **Retorno:** Lista de dicionários prontos para a etapa de persistência, com campos padronizados como `arquivo_id`, `tipo_crime`, `municipio`, `ais`, `data_fato`, `hora_fato` e atributos específicos da categoria.
- **Erros:** Registra e propaga falhas de conversão, colunas obrigatórias ausentes e tipos de ocorrência não mapeados.

**Funções auxiliares de normalização**

- `normalizar_texto(valor)`: trata valores ausentes como `None`, remove espaços excedentes e aplica capitalização de título.
- `normalizar_data(valor)`: converte o valor para `datetime.date`; falhas de conversão são propagadas.
- `normalizar_hora(valor)`: converte valores válidos para `datetime.time`; valores ausentes ou `"não informada"` resultam em `None`.
- `normalizar_idade(valor)`: converte idade para inteiro. Valores ausentes/não informados, fracionários ou fora do intervalo de 0 a 130 resultam em `None`; idades inválidas são registradas em log.
- `normalizar_quantidadeArmas(valor)`: converte a quantidade para inteiro, retornando `None` quando ausente/não informada e rejeitando quantidades fracionárias.
- `normalizar_quantidadeEntorpecente(valor)`: converte a quantidade/peso numérico para `float`, aceitando vírgula como separador decimal.

**Normalizadores por tipo de ocorrência**

| Função | Tipos de ocorrência atendidos |
|---|---|
| `normalizar_cvli(...)` | Crimes Violentos Letais e Intencionais (CVLI) |
| `normalizar_animais_CVP_Furto_Incendio_Salvamento(...)` | Maus-tratos a animais, CVP, Furto, Incêndio e Busca e Salvamento |
| `normalizar_armaDeFogo(...)` | Apreensão de armas de fogo |
| `normalizar_preconceitoRacaOuCor_crimesSexuais_indigenas_leiMariaDaPenha(...)` | Preconceito de raça ou cor, Crimes Sexuais, Indígenas vítimas de crimes e Lei Maria da Penha |
| `normalizar_entorpecentes(...)` | Apreensão de entorpecentes |
| `normalizar_homofobiaETransfobia(...)` | Homofobia e Transfobia |

Cada normalizador verifica se as colunas obrigatórias da planilha estão presentes e exige um `arquivo_id` positivo. Os registros resultantes usam nomes de campos padronizados para o banco, preenchendo com `None` os atributos que não se aplicam à categoria. A data é convertida e comparada ao dia da semana informado; quando há divergência, o módulo registra um aviso e marca `st_dia_semana_divergente` como `True`, sem corrigir silenciosamente o valor informado pela fonte.

**Tratamento de erros:** o módulo utiliza as exceções `ColunasAusentesNaPlanilha` e `tipoOcorrenciaNaoEncontrado`, definidas em `exception.py`. Erros de conversão (`ValueError`, `TypeError` e `OverflowError`) são registrados nos logs e propagados para a camada chamadora. Um tipo de ocorrência sem mapeamento não é processado automaticamente: gera `tipoOcorrenciaNaoEncontrado`.

> **Integração:** esta documentação descreve a funcionalidade disponível em `normalizer.py`. A chamada desse módulo pelo `processor.py`/`pipeline.py` e a persistência dos registros normalizados devem ser confirmadas na implementação desses componentes; a existência do normalizador, por si só, não significa que o fluxo atual já o execute.

### 3.6 `pipeline.py`

Arquivo principal (_entrypoint_) do projeto. Executa a orquestração do fluxo de ingestão sequencialmente.

**`pipeline() -> None`**
    
    - Executa o `crawler()` para obter a lista de URLs de planilhas e tipos de ocorrências.
        
    - Pega o primeiro link da lista (`lista_url[0]`).
        
    - Passa o link e as ocorrências para a função `processor()`.

    - A documentação atual não confirma que `processor()` chama `normalizer()`; essa integração deve ser verificada no código antes de considerar os dados normalizados parte do fluxo executado.
        

### 3.7 `exception.py`

Define as exceções personalizadas utilizadas para o tratamento de erros do sistema:

- **`VariavelAmbienteNaoEncontrada(Exception)`**: Disparada quando uma variável de ambiente obrigatória não é encontrada. Retorna uma mensagem detalhando o nome da variável ausente.
    
- **`EstruturaCSSDoSiteAlterado(Exception)`**: Disparada quando o container CSS esperado de indicadores detalhados não é localizado no HTML da página alvo (indicando possível alteração no layout do site).
    
- **`ValorInteiroInvalido(Exception)`**: Disparada quando a conversão de um parâmetro (como o timeout) falha por não ser um número inteiro válido.
    

### 3.8 `dockerfile`

Configuração de imagem Docker baseada em Python 3.13.4.

- Define o diretório de trabalho `/workspace`.
    
- Copia e instala as dependências via `requirements.txt` sem cache (`--no-cache-dir`).
    
- Copia o pacote `./ingestion` para o contêiner.
    
- Define o comando padrão de execução como módulo (`CMD ["python", "-m", "ingestion.pipeline"]`).
    

## 4. Fluxo de Ingestão de Dados

```
 ┌──────────────┐      1. Busca URL      ┌──────────────┐
 │   .env       │ ────────────────────>  │  config.py   │
 └──────────────┘                        └──────────────┘
                                                │
                                                │ 2. Retorna URL
                                                ▼
 ┌──────────────┐    3. Scraping HTML    ┌──────────────┐
 │ Site SSPDS   │ <────────────────────> │  crawler.py  │
 └──────────────┘                        └──────────────┘
                                                │
                                                │ 4. Retorna [links, categorias]
                                                ▼
                                         ┌──────────────┐
                                         │ pipeline.py  │
                                         └──────────────┘
                                                │
                                                │ 5. Envia URL da planilha
                                                ▼
 ┌──────────────┐   6. Download Excel    ┌──────────────┐
 │ Servidor de  │ <────────────────────> │ processor.py │
 │  Arquivos    │                        └──────────────┘
 └──────────────┘                               │
                                                │ 7. Salva arquivos .json
                                                ▼
                                      ┌───────────────────┐
                                      │ /database/*.json  │
                                      └───────────────────┘
```

## 5. Estrutura dos Arquivos de Saída

### `/database/dados.json`

Contém as linhas da planilha convertidas em uma lista de objetos JSON no fluxo descrito originalmente. Quando a normalização for integrada ao processamento, os registros terão a estrutura padronizada descrita na seção `normalizer.py`:

JSON

```
[
    {
        "Município": "Canindé",
        "AIS": "AIS 04",
        "Natureza": "HOMICIDIO DOLOSO",
        "Data": 1767225600000,
        "Hora": "02:40:00",
        "Dia da Semana": "Quinta",
        "Meio Empregado": "Arma branca",
        "Gênero": "Masculino",
        "Idade da Vítima": 50,
        "Escolaridade da Vítima": "Alfabetizado",
        "Raça da Vítima": "Não Informada"
    }
]
```

### `/database/tiposOcorrencias.json`

Contém a lista de categorias/nomes de indicadores raspados da página:

JSON

```
[
	"CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI", 
	"APREENSÃO DE ENTORPECENTES", 
	"FURTO", 
	"LEI 11.340/06 (LEI MARIA DA PENHA)", 
	"BUSCA E SALVAMENTO", 
	"INDÍGENAS VÍTIMAS DE CRIMES", 
	"CRIME DE MAUS-TRATOS A ANIMAIS", 
	"CRIMES VIOLENTOS CONTRA O PATRIMÔNIO - CVP", 
	"APREENSÃO DE ARMAS DE FOGO", 
	"CRIMES SEXUAIS", 
	"INCÊNDIO", 
	"HOMOFOBIA E TRANSFOBIA", 
	"CRIME OU PRECONCEITO DE RAÇA OU DE COR"
]
```
## 6. Observações sobre a normalização

- A função de entrada do módulo é `normalizer(df, arquivo_id, tipo_ocorrencia)`.
- O `arquivo_id` precisa ser positivo; os normalizadores também validam a presença das colunas necessárias para cada categoria.
- O campo `dia_semana` preserva o valor informado na planilha. A divergência em relação à data calculada é sinalizada separadamente em `st_dia_semana_divergente`.
- Campos não aplicáveis à categoria são representados por `None`.
- Para que a normalização faça parte da execução real da ingestão, o `processor.py` deve carregar a planilha em um DataFrame, identificar o `arquivo_id` e o `tipo_ocorrencia`, chamar `normalizer(...)` e encaminhar os registros retornados para a persistência. Essa sequência é uma condição de integração, não uma garantia descrita pelo módulo isolado.
