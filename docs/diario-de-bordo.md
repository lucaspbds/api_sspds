## Entradas
---
### Semana de 18/09

**Quem trabalhou e quanto:**
- David Lucas Pereira Braga dos Santos - 5h30
- Nikelly Santiago da Silva - 2h15
- Carlos Abimael Oliveira do Nascimento - 4h30
**O que foi feito:**
- Arquitetura do software; plano de ação; criação das pastas do projeto no repositório (Lucas)
- Comunicação com o público alvo; criação de um documento de divulgação do projeto (Nikelly)
- Estudo da documentação do Supabase; criação da conta; configuração do ambiente no Supabase e a criação das tabelas iniciais: histórico de ingestão e informações das planilhas (Abimael)
- Reformulação do plano de ação e o envio para o professor. (TODOS)

**Obstáculo:**
- **Modelagem do banco:** Indecisão entre tabela única ou tabelas separadas por crime. Seguindo orientação do prof. Ronan Soares, unificamos tudo em uma tabela com chave categórica. Resolução em ~1 dia (tempo de alinhamento com o professor).
- **Divulgação do projeto:** Falta de resposta do público e dificuldade de entrar em contato. Esse problema ainda não foi resolvido e ainda estamos buscando resolver. 

**Contato com o público:**
- Ceará Notícias (Instagram) - sem retorno 
- Notícias do Ceará (Instagram) - sem retorno
- Fortaleza Ordinária (Instagram) - sem retorno
- Notícias 24 horas Ceará (Instagram) - sem retorno
- Opovo Online (Instagram) - sem retorno

**Evidência coletada:**
- `docs\evidencias\divulgacao-api-seguranca-ce.pdf` - Documento utilizado para divulgar o nosso projeto para os portais de notícias que entramos em contato;
- `docs\evidencias\prints_mensagens_17-09.pdf` - Print das mensagens enviadas para os portais de notícias;
- `docs\evidencias\Arquitetura da API.canvas` - Arquitetura do projeto.

**Próxima semana:**
- Enviar um e-mail pedindo a licença para o SSPDS pelo e-SIC (Abimael);
- Configurar o Trello para organizar as tarefas do projeto (Lucas);
- Início do desenvolvimento da aplicação de ingestão de dados (Lucas);
- Infraestrutura inicial da API (Nikelly);
- Criação da tabela de crimes (Abimael);
- Descobrir uma maneira de contabilizar os acessos da API, desconsiderando as requisições dos integrantes do grupo (Nikelly);
- Criação do post de divulgação para o linkedIn (Nikelly). 

---
### Semana de 25/09

**Quem trabalhou e quanto:**
- David Lucas Pereira Braga dos Santos - 7h30 
- Nikelly Santiago da Silva - 1h
- Carlos Abimael Oliveira do Nascimento - 2h30
  
**O que foi feito:**
- Configuração do ambiente de desenvolvimento da aplicação; configuração do Trello (Lucas).
- Criação da postagem sobre o projeto no LinkedIn (Nikelly).
- Modelagem do Banco de Dados; contato com o SSPDS para obtenção da licença; contato com o professor sobre o indicador de contagem e a tabela de logs; documentação do banco de dados (Abimael); criação do banco de dados com as principais tabelas.
- Reformulação do plano de ação e o envio para o professor (TODOS).

**Obstáculo:**
- Não obtivemos retorno em relação à licença dos dados;
- Falta de conhecimento técnico para configurar o ambiente docker. Custou 3h de estudo e 2h de implementação, mas foi resolvido;

**Contato com o público:**
- Público do LinkedIn

**Evidência coletada:**
- Protocolo da solicitação da licença dos dados:`https://github.com/lucaspbds/api_sspds/blob/main/docs/evidencias/pedido-de-licenca.pdf`
- Postagem do linkedIn: `https://lnkd.in/p/euYN4Yyx`

**Próxima semana:**
- Conversar com o professor sobre a nova ideia de indicador de contagem (Lucas);
- Início do desenvolvimento da aplicação de ingestão de dados (Lucas);
- Infraestrutura inicial da API (Nikelly);
- Criar a primeira rota funcional da API (Nikelly);
- Melhorar a segurança do banco de dados (Abimael);
- Criar a tabela de logs (Abimael).

---
### Semana de 04/10

**Quem trabalhou e quanto:**
- David Lucas Pereira Braga dos Santos -  8h17
- Nikelly Santiago da Silva - 9h
- Carlos Abimael Oliveira do Nascimento - 1h15
  
**O que foi feito:**
- **Segurança do banco de dados:** Conexão com banco de dados através de um token. (Abimael)
- **Serviço de ingestão de dados (base):** Captura urls, baixa arquivos e salva os dados em JSON. (Lucas)
- **Reajuste no plano de ação:** Teste do público externo está no marco 2. (Lucas)
- **Organizar a pasta docs do projeto:** Pasta organizada de acordo com os critérios do professor. (Lucas)
- **Readme criado** (Lucas e Nikelly)
- **Problema da coleta do indicador de contagem resolvido:** nós decidimos utilizar um indicador de origem no link da api para excluir os bots da contagem e um token de identificação para a equipe, desta forma, as consultas da equipe não será contabilizado. (TODOS)
- **Estrutura inicial da API e uma rota funcional** (Nikelly) 

**Obstáculo:**
- **Funcionalidade de cada arquivo:** Tivemos uma dificuldade para entender como funcionava o `diário de bordo` e o arquivo `evidencias.xlsx`, pois antes estávamos criando um arquivo por diário de bordo e não estávamos entendendo o que podia ser evidências ou não. Custou ~1h30 para organizar os arquivos e preencher corretamente. 

**Contato com o público:**
- Irmão do David Lucas

**Evidência coletada:**
- Teste da aplicação pelo público externo: `docs\evidencias\teste-aplicacao01.pdf`

**Próxima semana:**
- Divulgação de como está o projeto no linkedIn(Nikelly);
- Organizar o Trello para o próximo marco (Lucas);