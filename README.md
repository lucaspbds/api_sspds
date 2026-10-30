# API pública de dados de segurança

Uma API pública que organiza e disponibiliza, em JSON, dados de segurança publicados pela Secretaria da Segurança Pública e Defesa Social do Ceará (SSPDS/CE) em planilhas eletrônicas, permitindo consultas com filtros por tipo de crime, ano, período e município.

## Para quem é

O produto é destinado a **estudantes, pesquisadores, jornalistas e outras pessoas que precisam consultar ou analisar dados públicos de segurança do Ceará**.

A proposta é facilitar o acesso a informações que, na fonte original, estão distribuídas em planilhas e exigem localização, download e interpretação manual para obter uma informação específica.

## De onde vêm os dados

Os dados utilizados pela API são provenientes das estatísticas da **Secretaria da Segurança Pública e Defesa Social do Ceará (SSPDS/CE)**, disponibilizadas em planilhas eletrônicas.

| Fonte                    | Órgão                                                               | Endereço                                  | Data do dado                                                              |
| :----------------------- | :------------------------------------------------------------------ | :---------------------------------------- | :------------------------------------------------------------------------ |
| Estatísticas da SSPDS/CE | Secretaria da Segurança Pública e Defesa Social do Ceará (SSPDS/CE) | https://www.ce.gov.br/sspds/estatisticas/ | Atualização mensal; o dado mais recente depende da publicação da SSPDS/CE |

Os dados são atualizados mensalmente e se referem ao mês que terminou. Por exemplo, os dados de setembro são publicados no mês de outubro.

A ingestão dos dados depende da disponibilidade das páginas e planilhas públicas da SSPDS/CE e de eventuais alterações no formato dessas planilhas. Se a fonte estiver indisponível, o sistema deve manter os dados já ingeridos e registrar a falha. Caso o formato das planilhas seja alterado, o parser deverá ser ajustado e o replanejamento documentado.

## Licença

- **Dados:** Dados públicos abertos sob o **Decreto Estadual nº 36.746/2025** e a **Lei Federal nº 12.527/2011 (LAI)**, com livre utilização, consumo, cruzamento e redistribuição mediante atribuição da fonte oficial à **Secretaria da Segurança Pública e Defesa Social (SSPDS/CE)** e à **Superintendência de Pesquisa e Estratégia de Segurança Pública (SUPESP)** (conforme manifestação via e-SIC em `docs/evidencias/licenca.pdf`).
- **Código e material desta equipe:** Licença MIT.

## O que este produto não faz

- Não inclui um painel visual completo.
- Não realiza previsão de crimes.
- Não realiza análise causal.
- Não coleta dados pessoais.
- Não permite consulta direta do usuário ao site da SSPDS/CE.

## Contato
- davidlucas2610@gmail.com | nikellysantiago@alu.ufc.br | Abimael.oliveira@alu.ufc.br

---

## Rotas
### `GET /crimes/cvli`

- **O que faz:** Lista as ocorrências de CVLI (Crimes Violentos Letais Intencionais) lidas a partir do ficheiro de dados processados pelo serviço de ingestão.
- **Parâmetros:** `limit` (opcional, `integer`) - Limita a quantidade de registos retornados. Caso omitido, retorna a base completa.
- **Exemplo de chamada:** `GET http://localhost:8000/crimes/cvli?limit=5`

- **Exemplo de Resposta (Sucesso - `200 OK`)**
  ```json
  [
    {
      "AIS": "AIS 04",
      "Município": "Canindé",
      "Data": "2026-01-01",
      "Hora": "02:40:00",
      "Dia da Semana": "Quinta",
      "Gênero": "Masculino",
      "Idade da Vítima": 50,
      "Escolaridade da Vítima": "Alfabetizado",
      "Raça da Vítima": "Não Informada",
      "Natureza": "HOMICIDIO DOLOSO",
      "Meio Empregado": "Arma branca"
    }
  ]
  ```

- **Exemplo de Resposta (Erro - `422 Unprocessable Content`)**
  ```json
    {
    "detail": [
      {
        "type": "int_parsing",
        "loc": [
          "query",
          "limit"
        ],
        "msg": "Input should be a valid integer, unable to parse string as an integer",
        "input": "d"
      }
    ]
  }
  ```

- **Exemplo de Resposta (Erro - `404 Not Found`)**
```json
    {
  "detail": "Nenhum dado de CVLI encontrado."
    }
```

- **Erros possíveis:**
  * `404 Not Found`: Retornado quando nenhum dado de CVLI é encontrado na base.
  * `422 Validation Error / Unprocessable Content`: Retornado quando o parâmetro informado é inválido (por exemplo: um número negativo, zero ou um valor não numérico).

## 🚀 Como rodar localmente

### 📋 Pré-requisitos

Certifique-se de ter instalado em sua máquina:

* **Python 3.13+**
* **Git**
* **Docker** 
* **WSL** (obrigatório para o uso do Docker; exige a ativação prévia da virtualização no computador)

---

### ⚙️ Configuração Inicial do Ambiente

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/lucaspbds/api_sspds.git
   cd api_sspds
   ```

2. **Configuração de Variáveis de Ambiente (`.env`):**
Crie um arquivo `.env` na raiz do projeto com as configurações gerais do serviço:
```env
# Configurações do serviço de ingestão de dados
url_sspds="https://www.ce.gov.br/sspds/estatisticas/"
```
Observação: Utilize o arquivo `.env.example`.

---
### Via Docker
####  Execução Individual dos Serviços

##### A. Serviço de API

A API é responsável por disponibilizar os dados processados via endpoints.
###### Execução via Docker (Individual)
```bash
# Construir a imagem Docker
docker compose build api

# Rodar o container da API 
docker compose up api
```

---
##### B. Serviço de Ingestão (Ingestion)

O serviço de ingestão executa a coleta, transforma os dados em json e salva na pasta `database`.
###### Execução via Docker (Individual)
```bash
# Criar a imagem do serviço de Ingestion
docker compose build ingestion

#Rodar o container
docker compose up ingestion
```

---
#### 🔗 Execução Conjunta via Docker Compose

1. **Subir todos os serviços:**
   ```bash
   docker compose up --build
   ```

---
#### 🛠️ Parar Serviços Docker

1. Aperte `Ctrl + C` para finalizar os processos docker
2. Verifique se ainda tem algum serviço rodando:
	- Rode o comando `docker compose ps` para listar todos os serviços que estão rodando no momento. Caso tenha, rode `docker compose down` para finalizar. 

---
### 💻 Execução Local (Sem Docker)

Caso prefira rodar a aplicação diretamente no seu ambiente Python:

1. **Criar e ativar o ambiente virtual:**
```bash
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
```

2. **Instalar as dependências:**
```bash
pip install -r requirements.txt
```

3. **Executar a Ingestão de Dados:**
```bash
python ingestion/pipeline.py
```
   *(Os dados processados serão salvos na pasta database/dados.json).*

4. **Executar a API:**
```bash
uvicorn app.main:app --reload
```

---
### 🧪 Verificação da Aplicação

* **Documentação interativa da API:** Acesse `http://localhost:8000/docs`.
* **Status da Ingestão:** Retornará no terminal a quantidade de URLs coletadas e os dados salvos em `database/dados.json`.

---

### 🔎 Executar os Testes

O projeto utiliza o **pytest** em conjunto com o `TestClient` do FastAPI para garantir a integridade das rotas, validações de parâmetros e os códigos de resposta HTTP (`200`, `404` e `422`).

1. **Ativar o Ambiente Virtual**
Certifique-se de que o seu ambiente virtual está ativado no terminal:

- **Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

2. **Instalar as Dependências**
```bash
pip install -r requirements.txt
```

3. **Rodar Testes**
	
	*Você precisa rodar o serviço de ingestão de dados antes de rodar os testes*
```bash
python -m pytest -v
```

---

## 📁 Estrutura do Projeto
```text
api_sspds/
├── app/
│   ├── routers/
│   ├── schemas/
│   └── services/
├── database/
├── docs/
│   └── evidencias/
├── ingestion/
├── tests/
├── .env.example
├── .gitignore
├── compose.yml
├── LICENSE
├── pytest.ini
├── README.md
└── requirements.txt
```
--- 
## 📊 Status do Projeto
**Em desenvolvimento.**
