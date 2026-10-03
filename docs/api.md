# Documentação da API Pública de Segurança - SSPDS/CE

Esta documentação descreve a arquitetura, a estrutura de diretórios modular e os endpoints disponíveis na API de dados de segurança pública do Ceará.

## 📁 Estrutura de Diretórios da API

A API segue uma arquitetura orientada a serviços e separação de responsabilidades (Clean Architecture / Modular) dentro da pasta `app/`:

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
```

## 🚀 Endpoints Disponíveis

### 1. Raiz da Aplicação
* **Método:** `GET`
* **Rota:** `/`
* **Descrição:** Retorna uma mensagem de boas-vindas e o atalho para a documentação interativa.
* **Resposta (Exemplo):**
  ```json
  {
    "message": "API SSPDS funcionando com sucesso!",
    "docs_url": "/docs"
  }
  ```

### 2. Verificação de Saúde (Health Check)
* **Método:** `GET`
* **Rota:** `/health`
* **Descrição:** Endpoint destinado a monitorização e validação do estado operacional do contentor/servidor.
* **Resposta (Exemplo):**
  ```json
  {
    "status": "ok"
  }
  ```

### 3. Listagem de Crimes (CVLI)
* **Método:** `GET`
* **Rota:** `/crimes/cvli`
* **Parâmetros de Query:**
  * `limit` (opcional, `integer`): Limita o número de registos retornados. Caso não seja informado, retorna a base completa.
* **Response Model:** `List[CvliResponse]`
* **Descrição:** Consulta o ficheiro `database/dados.json` gerado pelo pipeline de ingestão e valida a estrutura dos dados utilizando os schemas definidos.
* **Códigos de Resposta:**
  * `200 OK`: Dados encontrados e retornados com sucesso.
  * `404 Not Found`: Nenhum registo de CVLI localizado na base de dados.
