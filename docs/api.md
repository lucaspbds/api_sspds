# Documentação da API Pública de Segurança - SSPDS/CE

Esta documentação descreve a arquitetura, a estrutura de diretórios modular e os endpoints disponíveis na API de dados de segurança pública do Ceará.

## 📁 Estrutura de Diretórios da API

A API segue uma arquitetura orientada a serviços e separação de responsabilidades (Clean Architecture / Modular) dentro da pasta `app/`:

```text
api_sspds/
├── app/
│   ├── __init__.py
│   ├── config.py                 
│   ├── dockerfile
│   ├── exception.py               
│   ├── main.py            
│   ├── routers/
│   │   ├── __init__.py
│   │   └── crimes.py           
│   ├── schemas/ # Serve para serialização, val. de saída e doc. aut.
│   │   ├── __init__.py
│   │   ├── base_schema.py  
│   │   ├── consulta_schema.py         
│   │   ├── operacional_schema.py 
│   │   ├── preconceito_schema.py    
│   │   └── vitima_schema.py 
│   └── services/
│       ├── __init__.py
│       └── crime_service.py    
```

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
- **Descrição:** Endpoint destinado a monitorização e validação do estado operacional do contentor/servidor.
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
- **Parâmetros de Query:**
  - `municipio` (opcional, `string`): Filtra por nome do município.
  - `tipo_crime` (opcional, `string`): Filtra por tipo específico de crime.
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Response Model:** `List[CrimeResponse]`
- **Descrição:** Consulta a base unificada de dados permitindo o uso combinado de filtros de pesquisa.
- **Códigos de Resposta:**
  - `200 OK`: Registos encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum crime encontrado com os filtros fornecidos.
  - `422 Unprocessable Content`: Parâmetro de consulta inválido.

---

### 4. Listagem de Crimes Violentos Letais Intencionais (CVLI)
- **Método:** `GET`
- **Rota:** `/crimes/cvli`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados. Caso omitido, retorna a base completa.
- **Response Model:** `List[CvliResponse]`
- **Descrição:** Lista ocorrências específicas de CVLI com detalhamento de perfil de vítima e natureza.
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum dado de CVLI encontrado na base.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido (não numérico ou menor/igual a zero).

---

### 5. Listagem de Crimes com Perfil de Vítima
- **Método:** `GET`
- **Rota:** `/crimes/vitimas`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Response Model:** `List[CrimeComVitimaResponse]`
- **Descrição:** Retorna ocorrências específicas de crimes com detalhamento de perfil da vítima (como Lei Maria da Penha, Crimes Sexuais e Indígenas).
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro de crime com vítima encontrado.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido.

---

### 6. Listagem de Crimes de Preconceito
- **Método:** `GET`
- **Rota:** `/crimes/preconceito`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Response Model:** `List[PreconceitoResponse]`
- **Descrição:** Retorna ocorrências específicas de crimes motivados por preconceito (homofobia e transfobia).
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum crime de preconceito encontrado.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido.

---

### 7. Listagem de Crimes Operacionais
- **Método:** `GET`
- **Rota:** `/crimes/operacionais`
- **Parâmetros de Query:**
  - `limit` (opcional, `integer`): Limita o número de registos retornados.
- **Response Model:** `List[OperacionalResponse]`
- **Descrição:** Retorna ocorrências de crimes operacionais de menor complexidade estrutural (como Furtos e CVP).
- **Códigos de Resposta:**
  - `200 OK`: Dados encontrados e retornados com sucesso.
  - `404 Not Found`: Nenhum registro operacional encontrado.
  - `422 Unprocessable Content`: Parâmetro `limit` inválido.