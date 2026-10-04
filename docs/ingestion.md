# Documentação Técnica: Serviço de Ingestão de Dados

## 1. Visão Geral do Serviço

O **Serviço de Ingestão de Dados** é um pipeline de extração e processamento de dados (ETL) desenvolvido em Python. Ele é responsável por realizar a raspagem de dados (*web scraping*) no portal da **Secretaria da Segurança Pública e Defesa Social (SSPDS)**, extrair os links das planilhas de estatísticas/indicadores detalhados, converter esses dados estruturados do formato Excel para JSON e salvá-los localmente em um volume específico.

---

## 2. Estrutura de Arquivos

```text
ingestion/
├── __pycache__/
├── config.py          # Gerenciamento de variáveis de ambiente (.env)
├── crawler.py         # Módulo de Web Scraping da página da SSPDS
├── dockerfile         # Configuração para conteinerização da aplicação
├── exception.py       # Exceções customizadas do sistema
├── pipeline.py        # Orquestrador principal do serviço
└── processor.py       # Processamento das planilhas e gravação em JSON
```

---

## 3. Módulos e Componentes

### 3.1 `config.py`
Carrega as variáveis de ambiente contidas no arquivo `.env` usando a biblioteca `python-dotenv`.

- **`get_variavel_ambiente(nome_variavel: str)`**
  - **Descrição:** Captura o valor de uma variável de ambiente informada.
  - **Parâmetros:** `nome_variavel` (string) — Nome da chave no arquivo `.env`.
  - **Retorno:** Valor atribuído à variável de ambiente.
  - **Exceção:** Lança `VariavelAmbienteNaoEncontrada` caso a variável não exista ou esteja vazia.

### 3.2 `crawler.py`
Responsável por realizar a requisição HTTP na página da SSPDS e mapear os seletores HTML para extração de links e tipos de ocorrências.

- **`extrair_links(conteudo_html)`**
  - **Descrição:** Função auxiliar para capturar todas as tags `<a>` dentro de um elemento HTML delimitado.
  - **Retorno:** Lista de objetos com as tags de link encontradas.

- **`crawler() -> list`**
  - **Descrição:** Acessa a URL da SSPDS configurada nas variáveis de ambiente, realiza o parse do HTML com `BeautifulSoup` e extrai os links das planilhas e os nomes dos indicadores.
  - **Retorno:** Uma lista composta por dois elementos `[links_arquivos, tipos_ocorrencias]`:
    - `links_arquivos`: Lista de URLs (atributos `href`) apontando para as planilhas Excel.
    - `tipos_ocorrencias`: Lista com os textos descritivos de cada indicador criminal.
  - **Tratamento de Exceção:** Captura a exceção `VariavelAmbienteNaoEncontrada` e exibe a mensagem correspondente no terminal.

### 3.3 `processor.py`
Módulo encarregado do download, transformação e persistência dos dados.

- **`processor(url: str, tiposOcorrencias: list) -> None`**
  - **Descrição:** Faz a leitura direta da planilha Excel via URL utilizando o `pandas`, converte a estrutura do DataFrame para um array de objetos JSON e salva os arquivos no diretório `/database`.
  - **Arquivos Gerados:**
    - `/database/dados.json`: Contém os registros da planilha Excel convertidos para formato `records`.
    - `/database/tiposOcorrencias.json`: Contém a lista de categorias e tipos de ocorrências extraídos do crawler.

### 3.4 `pipeline.py`
Arquivo principal (*entrypoint*) do projeto. Executa a orquestração do fluxo de ingestão sequencialmente.

- **`pipeline() -> None`**
  - Executa o `crawler()` para obter a lista de URLs de planilhas e tipos de ocorrências.
  - Pega o primeiro link da lista (`lista_url[0]`).
  - Passa o link e as ocorrências para a função `processor()`.

### 3.5 `exception.py`
Define exceções personalizadas para o sistema.

- **`VariavelAmbienteNaoEncontrada(Exception)`**
  - Exceção disparada quando uma variável solicitada via `config.py` não é encontrada.
  - Método `print_mensagem_erro()`: Formata e imprime a mensagem de erro detalhando o nome da variável ausente.

### 3.6 `dockerfile`
Configuração de imagem Docker baseada em Python 3.13.4.

- Define o diretório de trabalho `/app`.
- Copia e instala as dependências via `requirements.txt`.
- Copia a pasta `./ingestion` para o contêiner.
- Define o comando padrão de execução (`CMD ["python", "pipeline.py"]`).

---

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

---
## 5. Estrutura dos Arquivos de Saída

### `/database/dados.json`
Contém as linhas da planilha convertidas em uma lista de objetos JSON:
```json
[
    {
        "Município":"Canindé",
        "AIS":"AIS 04",
        "Natureza":"HOMICIDIO DOLOSO",
        "Data":1767225600000,
        "Hora":"02:40:00",
        "Dia da Semana":"Quinta",
        "Meio Empregado":"Arma branca",
        "Gênero":"Masculino",
        "Idade da Vítima":50,
        "Escolaridade da Vítima":"Alfabetizado",
        "Raça da Vítima":"Não Informada"
    }
]
```

### `/database/tiposOcorrencias.json`
Contém a lista de categorias/nomes de indicadores raspados da página:
```json
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
