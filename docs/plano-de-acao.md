# Plano de ação — API pública de dados de segurança
## Identificação

- **Equipe:** 
	1. David Lucas Pereira Braga dos Santos - 581594
	2. Carlos Abimael Oliveira do Nascimento - 587010
	3. Nikelly Santiago da Silva - 567082
- **Trilha:** (A) API pública de dados abertos 
- **Área temática da PREX:** Tecnologia e Produção
- **Por que essa área,** em uma linha: Desejamos utilizar a tecnologia em prol da coletivização de informações através de um serviço web que amplia o acesso e a transparência sobre informações públicas de segurança para facilitar seu uso por pessoas que precisam compreender ou analisar esses dados.
- **Repositório:** [repositório GitHub do projeto](https://github.com/lucaspbds/api_sspds)
## Campo 1 — O problema

Uma pessoa que precisa consultar ou analisar dados públicos de segurança do Ceará encontra as informações distribuídas em planilhas da SSPDS/CE e precisa localizar, baixar e interpretar esses arquivos manualmente para obter uma informação específica.

## Campo 2 — O público externo

- **Quem é:** estudantes, pesquisadores, jornalistas e outras pessoas que precisam consultar ou analisar dados públicos de segurança do Ceará.
- **Duas ou três pessoas reais desse grupo:** Opovo, Fortaleza ordinária e entre outros portais de notícias.
- **Já falamos com alguma? Quando falaremos?** Já enviamos mensagens para alguns portais pelo Instagram, mas não obtivemos nenhum retorno.
- **Como essa pessoa vai descobrir que o produto existe:** por meio do repositório público, README/documentação da API e divulgação através do linkedIn de cada integrante da equipe.

## Campo 3 — Trilha e produto

- **O que é, em uma frase que caiba num tuíte, e onde ficará publicado:** Uma API pública que organiza e disponibiliza, em JSON, dados de segurança publicados pela SSPDS/CE em planilhas, com filtros por tipo de crime, ano, período e município, publicada no repositório do projeto e em um endereço público da API.
- **O que NÃO faz parte:** não inclui um painel visual completo, previsão de crimes, análise causal, coleta de dados pessoais, nem consulta direta do usuário ao site da SSPDS.

## Campo 4 — Fontes de dados

|                                                                       |                                                                                                                                                                                                                                                                                     |
| :-------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nome e órgão**                                                      | Estatísticas da Secretaria da Segurança Pública e Defesa Social do Ceará (SSPDS/CE), disponibilizadas em planilhas eletrônicas.                                                                                                                                                     |
| **Endereço**                                                          | https://www.ce.gov.br/sspds/estatisticas/                                                                                                                                                                                                                                           |
| **Licença — e o que ela permite ao nosso produto**                    | Não há licença de uso explicitamente informada na fonte. Os dados serão utilizados como fonte pública para processamento e disponibilização por meio da API, com atribuição à SSPDS/CE e indicação da fonte original. As planilhas originais não serão redistribuídas pelo projeto. |
| **Atualização — periodicidade declarada e data do dado mais recente** | Os dados são atualizados mensalmente e se referem ao mês que terminou, ou seja, os dados de setembro só serão postados no mês de outubro, e assim por diante.                                                                                                                       |
| **Dado pessoal? — se sim, granularidade e o que será agregado**       | Não há.                                                                                                                                                                                                                                                                             |

## Campo 5 — Papéis

| Integrante                            | Papel                               | O que fica sob sua responsabilidade                                                                                                                                                                                                     |
| :------------------------------------ | :---------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| David Lucas Pereira Braga dos Santos  | **Ingestão / Crawler/Scrum Master** | Descobrir os links XLS/XLSX da SSPDS/CE, baixar arquivos, calcular hash, detectar novidades/republicações, normalizar os dados para o banco, organizar a equipe para concluir o projeto com êxito e configurar o ambiente da aplicação. |
| Carlos Abimael Oliveira do Nascimento | **Banco**                           | Criar o banco de dados e hospedar em um serviço de nuvem, fazer a integração do banco de dados com a aplicação e criar os modelos das entidades na aplicação.                                                                           |
| Nikelly Santiago da Silva             | **API/Divulgação do projeto**       | Implementar FastAPI, schemas, endpoints, filtros, tratamento de erros e criação de posts/documentos de divulgação do projeto.                                                                                                           |
| TODOS                                 |                                     | Documentação, testes e logs.                                                                                                                                                                                                            |

## Campo 6 — Cronograma

| Data                     | O que estará pronto                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| :----------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **02/10 (Marco 1)**      | Foco na estruturação inicial do projeto por meio do repositório organizado, ambiente configurado e modelagem básica do banco PostgreSQL. Inclui o desenvolvimento do crawler base para a SSPDS/CE, captura de um conjunto mínimo de dados para disponibilização em uma rota funcional inicial na API. O banco de dados não estará conectado com a aplicação nesse marco.                                                                                              |
| **13/11 (Marco 2)**      | Consolidação do fluxo de dados ponta a ponta em ambiente de desenvolvimento, implementação da lógica de detecção por hash integrada ao crawler, normalização dos dados e conexão do banco de dados com a aplicação. A solução contará com os principais filtros de busca na API, tratamento de erros e testes automatizados. Será disponibilizada uma versão utilizável da API para validação por ao menos dois usuários externos, com coleta e registro de feedback. |
| **27/11 (Marco 3)**      | Implantação da API em ambiente de produção na nuvem, acompanhada da disponibilização do histórico visível de ingestões. O marco inclui o detalhamento técnico via OpenAPI/Swagger, com exemplos reproduzíveis, indicação das fontes e limitações, além da consolidação dos ajustes identificados durante a validação com usuários externos.                                                                                                                           |
| **04/12 (Socialização)** | Apresentação do produto, demonstração de uso, evidências coletadas, comparação entre indicadores planejados e obtidos e registro das principais decisões, dificuldades e replanejamentos.                                                                                                                                                                                                                                                                             |

**Dependências externas.** O projeto depende da disponibilidade das páginas e planilhas públicas da SSPDS/CE e de eventuais alterações no formato dessas planilhas. Se a fonte estiver indisponível, o sistema manterá os dados já ingeridos e registrará a falha; se o formato mudar, a equipe ajustará o parser e documentará o replanejamento. 

## Campo 7 — Indicadores

|                 | Medida                                                                                                             | Como será coletada                                                                                                                                                                                          | Valor que seria bom                                                                                |
| :-------------- | :----------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **Contagem**    | Número de acessos/consultas à API pública.                                                                         | Logs do servidor da API, contabilizados entre o Marco 2 e o Marco 3. Será excluído os bots através de uma indicação de origem no link da api e as consultas da equipe através de um token de identificação. | **≥ 15 consultas**                                                                                 |
| **Qualitativa** | Pessoas externas conseguem realizar uma consulta e avaliar se os dados e filtros atendem à necessidade apresentada | Formulário ou registro escrito após o uso, associado às evidências do projeto                                                                                                                               | **≥ 2 pessoas externas**, com feedback registrado e pelo menos uma melhoria incorporada ao produto |
## Antes de entregar: a prova dos nove

- [x] Riscamos tudo o que não conseguiríamos terminar até 13/11.
- [x] O que sobrou ainda ajuda alguém.
- [x] Uma pessoa de fora entende o Campo 1 e o Campo 3 sem explicação oral.
- [x] A data da primeira conversa com o público está marcada.
- [x] Os indicadores podem ser coletados sem depender de terceiro.
