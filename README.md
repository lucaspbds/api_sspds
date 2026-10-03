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

- **Dados:** Aguardando o retorno do e-SIC.
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
- **Exemplo de resposta:**
  ```json
  [
    {
      "id": "1",
      "municipio": "Fortaleza",
      "data": "2026-09-01",
      "tipo": "CVLI"
    }
  ]
  ```
- **Erros possíveis:** `404 Not Found` (quando nenhum dado de CVLI é encontrado na base).

## Como rodar localmente

### 📋 Pré-requisitos

Certifique-se de ter instalado em sua máquina:

* **Python 3.10+**
* **Git**
* **Docker** 

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

### 🚀 1. Execução Individual dos Serviços

#### A. Serviço de API

A API é responsável por disponibilizar os dados processados via endpoints.
##### Execução via Docker (Individual)
```bash
# Construir a imagem Docker
docker compose build api

# Rodar o container da API 
docker compose up api
```

---
#### B. Serviço de Ingestão (Ingestion)

O serviço de ingestão executa a coleta, transforma os dados em json e salva na pasta `database`.
##### Execução via Docker (Individual)
```bash
# Criar a imagem do serviço de Ingestion
docker compose build ingestion

#Rodar o container
docker compose up ingestion
```

---

### 🔗 2. Execução Conjunta (API + Ingestion)

####  Via Docker Compose

1. **Subir todos os serviços:**
   ```bash
   docker compose up 
   ```
Observação: Caso queira subir os serviços em segundo plano, apenas coloque a flag `-d` no final do código acima.

---

### 🛠️ Parar e Limpar Serviços

* **Parar serviços via Docker Compose:**
  ```bash
  docker compose down
  ```
Ou, caso você não tenha colocado para rodar em segundo plano, pode utilizar o atalho `Ctrl + C` no terminal correspondente.

---

### Estrutura do Projeto

```text
api_sspds/
├── app/
│   ├── __init__.py
│   ├── main.py                 
│   ├── config.py               
│   ├── exception.py            
│   ├── routers/
│   │   ├── __init__.py
│   │   └── crimes.py           
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── base_schema.py      
│   │   ├── operacional_schema.py 
│   │   ├── vitima_schema.py    
│   │   └── preconceito_schema.py 
│   └── services/
│       ├── __init__.py
│       └── crime_service.py    
├── database/
├── docs/
│   ├── evidencias/
│   │   ├── divulgacao-api-seguranca-ce.pdf
│   │   ├── pedido-de-licenca.pdf
│   │   └── prints_mensagens_17-09.pdf
│   ├── api.md
│   ├── architecture.md
│   ├── database.md
│   ├── diario-de-bordo.md
│   ├── evidencias.csv
│   ├── ingestion.md
│   ├── logging.md
│   └── plano-de-acao.md
├── ingestion/
│   ├── config.py
│   ├── crawler.py
│   ├── dockerfile
│   ├── exception.py
│   ├── pipeline.py
│   └── processor.py
├── .env.example
├── .gitignore
├── compose.yml
├── dockerfile
├── LICENSE
├── README.md
└── requirements.txt
```

---

### 🧪 Verificação da Aplicação

* **Documentação interativa da API:** Acesse `http://localhost:8000/docs`.
* **Status da Ingestão:** Retornará um print contendo a quantidade de URLs coletadas e o link dos dados que foram salvos no arquivo `database/dados.json`.