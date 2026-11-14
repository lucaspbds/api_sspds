import logging
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Exceções da camada de banco de dados, que a API também precisa traduzir em respostas HTTP.
# A `VariavelAmbienteNaoEncontrada` do banco é importada com outro nome para não colidir
# com a da própria API (definida abaixo): as duas têm handler.
from database.exceptions import (
    ErroConexaoBanco,
    ErroOperacaoBanco,
)
from database.exceptions import (
    VariavelAmbienteNaoEncontrada as VariavelAmbienteNaoEncontradaBanco,
)

logger = logging.getLogger("app.exception")

# ---- Exceções customizadas ----


class VariavelAmbienteNaoEncontrada(Exception):
    """Lançada por `app.config` quando uma variável de ambiente obrigatória não está definida."""

    def __init__(self, nome_variavel: str):
        self.nome_variavel = nome_variavel
        super().__init__(
            f"A variável de ambiente obrigatória '{nome_variavel}' não foi encontrada."
        )


class RecursoNaoEncontrado(Exception):
    """Exceção customizada para quando um recurso solicitado não existe no banco."""

    def __init__(self, mensagem: str = "Recurso não encontrado."):
        self.mensagem = mensagem
        super().__init__(mensagem)


# ---- Funções handlers isoladas (manipuladores de erro) ----
# Corpo padrão das respostas de erro tratadas aqui:
#   {"erro": "<título>", "mensagem": "<texto>"}
# Exceção: o erro de validação (422) mantém a chave "detail" do FastAPI, com a
# lista de erros por parâmetro. As respostas `HTTPException` (ex.: 404 das rotas)
# usam o formato padrão do FastAPI: {"detail": "<texto>"}.


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Parâmetro inválido (422)."""
    logger.warning("Parâmetros inválidos em %s %s: %s", request.method, request.url.path, exc.errors())

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "erro": "Erro de validação nos parâmetros",
            # `jsonable_encoder` evita falha de serialização quando `ctx` traz objetos
            # de exceção (ex.: ValueError) dentro dos erros do Pydantic.
            "detail": jsonable_encoder(exc.errors()),
        },
    )


async def recurso_nao_encontrado_handler(
    request: Request, exc: RecursoNaoEncontrado
) -> JSONResponse:
    """Recurso inexistente (404)."""
    logger.info("Recurso não encontrado em %s %s: %s", request.method, request.url.path, exc.mensagem)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "erro": "Recurso Não Encontrado",
            "mensagem": exc.mensagem,
        },
    )


async def erro_conexao_banco_handler(
    request: Request, exc: ErroConexaoBanco
) -> JSONResponse:
    """Banco indisponível (503)."""
    logger.error(
        "Erro de conexão com o banco em %s %s: %s", request.method, request.url.path, exc,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "erro": "Erro de Conexão com o Banco",
            "mensagem": "Não foi possível estabelecer comunicação com o Supabase.",
        },
    )


async def erro_operacao_banco_handler(
    request: Request, exc: ErroOperacaoBanco
) -> JSONResponse:
    """Falha ao executar a consulta no banco (500)."""
    logger.error(
        "Erro de operação no banco em %s %s: %s", request.method, request.url.path, exc,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro na Operação do Banco",
            "mensagem": "Falha ao executar a operação solicitada no Supabase.",
        },
    )


async def variavel_ambiente_handler(
    request: Request,
    exc: Union[VariavelAmbienteNaoEncontrada, VariavelAmbienteNaoEncontradaBanco],
) -> JSONResponse:
    """
    Erro de infraestrutura/configuração (500). O nome da variável só vai para o log.
    Cobre a exceção da API (`app.config`) e a da camada de banco (`database.config`).
    """
    logger.error(
        "Variável de ambiente ausente em %s %s: %s", request.method, request.url.path, exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro de Configuração",
            "mensagem": "Uma variável de ambiente obrigatória não foi configurada.",
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Erro interno inesperado (500). Detalhes só no log, nunca na resposta."""
    logger.error(
        "Erro inesperado em %s %s: %s", request.method, request.url.path, type(exc).__name__,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro interno no servidor",
            "mensagem": "Ocorreu um erro inesperado na aplicação.",
        },
    )


# ---- Função Centralizadora de Registro ----


def registrar_exception_handlers(app: FastAPI) -> None:
    """Registra todos os handlers de exceção na instância principal do FastAPI."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RecursoNaoEncontrado, recurso_nao_encontrado_handler)
    app.add_exception_handler(ErroConexaoBanco, erro_conexao_banco_handler)
    app.add_exception_handler(ErroOperacaoBanco, erro_operacao_banco_handler)
    app.add_exception_handler(VariavelAmbienteNaoEncontrada, variavel_ambiente_handler)
    app.add_exception_handler(VariavelAmbienteNaoEncontradaBanco, variavel_ambiente_handler)
    app.add_exception_handler(Exception, global_exception_handler)
