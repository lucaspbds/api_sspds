# Entrega de marco 
## Identificação

- **Equipe:** 
	1. David Lucas Pereira Braga dos Santos - 581594
	2. Carlos Abimael Oliveira do Nascimento - 587010
	3. Nikelly Santiago da Silva - 567082
- **Marco e data:** Marco 1 - 02/10/2026
- **Trilha:** A
- **Endereço público do produto:** https://github.com/lucaspbds/api_sspds.git
- **Commit ou tag desta entrega:** `5920b1d`
## Campo 1 — O que funciona hoje
1. Fazer uma requisição `GET http://localhost:8000/crimes/cvli?limit=5` e receber as 5 primeiras linhas da ocorrências de CVLI (Crimes Violentos Letais Intencionais) em formato JSON.
2. Abrir `http://localhost:8000/docs` no navegador para acessar e interagir com a documentação automática da API.
3. Executar o serviço de ingestão via `docker compose up ingestion` para coletar e converter as planilhas da SSPDS/CE em dados processados no arquivo `database/dados.json`.

## Campo 2 — O que mudou desde o marco anterior

- **Passou a existir:** n.a.
- **Foi cortado, e por quê:** n.a.

## Campo 3 — Alcance

| Indicador   | Planejado            | Obtido até hoje | Onde está a evidência                 |
| :---------- | :------------------- | :-------------- | :------------------------------------ |
| Qualitativa | ≥ 2 pessoas externas | 1               | docs\evidencias\teste-aplicacao01.pdf |

**O que o público externo disse.** Conseguiu rodar a aplicação, mas contém alguns bugs na consulta.

## Campo 4 — Obstáculo e replanejamento

**Modelagem do banco:** Indecisão entre tabela única ou tabelas separadas por crime. Seguindo orientação do prof. Ronan Soares, unificamos tudo em uma tabela com chave categórica. Resolução em ~1 dia (tempo de alinhamento com o professor).

**Divulgação do projeto:** Falta de resposta do público e dificuldade de entrar em contato. Esse problema ainda não foi resolvido, contudo, nós temos um plano de resolver isto através do contato entre pessoas físicas e não mais uma pessoa jurídica (Ex.: empresas).

**Licença dos dados do órgão SSPDS:** Aguardando o retorno da nossa solicitação. Até o momento, nós estamos sendo repassados para outros departamentos, mas nada de retorno. 

## Campo 5 — Autopontuação

| Dimensão                            | n.a.? | Pts (0–2) | Por quê, em uma linha                                                                            |
| :---------------------------------- | :---- | :-------- | :----------------------------------------------------------------------------------------------- |
| D1 Qualidade técnica                |       | 2         | Código modular, bem estruturado e eficiente para extração e disponibilização dos dados da SSPDS. |
| D2 Alcance e adequação ao público   | x     |           | Não aplicável para o Marco 1.                                                                    |
| D3 Documentação e reprodutibilidade |       | 2         | README completo com instruções claras de configuração, dependências e exemplos de execução.      |
| D4 Registro do processo             |       | 2         | Histórico de commits estruturado e frequente, demonstrando a evolução lógica do desenvolvimento. |
| D5 Autoavaliação e reflexão         | x     |           | Não aplicável para o Marco 1.                                                                    |

## Antes de entregar

- [x] O endereço do produto abre numa máquina que não é a nossa.
- [x] O que o Campo 1 promete foi testado hoje, não na semana passada.
- [x] O `README.md` corresponde ao que o produto faz agora.
- [x] O diário tem entrada de todas as semanas desde o último marco.
- [x] Toda evidência do Campo 3 tem data e está em `evidencias/`.
- [x] O commit informado está publicado.
