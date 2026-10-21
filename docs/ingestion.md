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
            

### 3.5 `pipeline.py`

Arquivo principal (_entrypoint_) do projeto. Executa a orquestração do fluxo de ingestão sequencialmente.

**`pipeline() -> None`**
    
    - Executa o `crawler()` para obter a lista de URLs de planilhas e tipos de ocorrências.
        
    - Pega o primeiro link da lista (`lista_url[0]`).
        
    - Passa o link e as ocorrências para a função `processor()`.
        

### 3.6 `exception.py`

Define as exceções personalizadas utilizadas para o tratamento de erros do sistema:

- **`VariavelAmbienteNaoEncontrada(Exception)`**: Disparada quando uma variável de ambiente obrigatória não é encontrada. Retorna uma mensagem detalhando o nome da variável ausente.
    
- **`EstruturaCSSDoSiteAlterado(Exception)`**: Disparada quando o container CSS esperado de indicadores detalhados não é localizado no HTML da página alvo (indicando possível alteração no layout do site).
    
- **`ValorInteiroInvalido(Exception)`**: Disparada quando a conversão de um parâmetro (como o timeout) falha por não ser um número inteiro válido.
    

### 3.7 `dockerfile`

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

Contém as linhas da planilha convertidas em uma lista de objetos JSON:

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