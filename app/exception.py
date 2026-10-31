from fastapi import Request, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


# Importando as exceções reais do módulo de banco de dados
from database.exceptions import (
    ErroConexaoBanco,
    ErroOperacaoBanco,
)

# ---- Exceções customizadas ----

class VariavelAmbienteNaoEncontrada(Exception):
    def __init__(self, nome_variavel, *args):
        self.__nome_variavel = nome_variavel
        self.__mensagem = "Variável de Ambiente não encontrada"
        super().__init__(*args)

    def print_mensagem_erro(self):
        print(f"{self.__mensagem}:\nNome da variável - {self.__nome_variavel}") 


class RecursoNaoEncontrado(Exception):
    """Exceção customizada para quando um recurso solicitado não existe no banco."""
    def __init__(self, mensagem: str = "Recurso não encontrado.", *args):
        self.mensagem = mensagem
        super().__init__(*args)

# ---- Funções handlers isoladas (manipuladores de erro) ----
# Parâmetro inválido
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Usando os parâmetros para registrar um log, por enquanto só aqui, o trabalho do log será em outra etapa
    print(f"Erro na URL {request.url}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "erro": "Erro de validação nos parâmetros",
            "detalhes": exc.errors()
        }
    )

async def recurso_nao_encontrado_handler(request: Request, exc: RecursoNaoEncontrado):
    # Usando os parâmetros para registrar um log, por enquanto só aqui, o trabalho do log será em outra etapa
    print(f"Erro na URL {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "erro": "Recurso Não Encontrado",
            "mensagem": exc.mensagem
        }
    )

async def erro_conexao_banco_handler(request: Request, exc: ErroConexaoBanco):
    # Usando os parâmetros para registrar um log, por enquanto só aqui, o trabalho do log será em outra etapa
    print(f"Erro na URL {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro de Conexão com o Banco",
            "mensagem": "Não foi possível estabelecer comunicação com o Supabase."
        }
    )


async def erro_operacao_banco_handler(request: Request, exc: ErroOperacaoBanco):
    # Usando os parâmetros para registrar um log, por enquanto só aqui, o trabalho do log será em outra etapa
    print(f"Erro na URL {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro na Operação do Banco",
            "mensagem": "Falha ao executar a operação solicitada no Supabase."
        }
    )

# Erro de infraestrutura/ configuração
async def variavel_ambiente_handler(request: Request, exc: VariavelAmbienteNaoEncontrada):
    # Usando os parâmetros para registrar um log, por enquanto só aqui, o trabalho do log será em outra etapa
    print(f"Erro na URL {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro de Configuração",
            "mensagem": "Uma variável de ambiente obrigatória não foi configurada."
        }
    )

#Erro interno
async def global_exception_handler(request: Request, exc: Exception):
    # Usando os parâmetros para registrar um log, por enquanto só aqui, o trabalho do log será em outra etapa
    print(f"Erro na URL {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "erro": "Erro interno no servidor",
            "mensagem": "Ocorreu um erro inesperado na aplicação."
        }
    )

# ---- Função Centralizadora de Registro ----

def registrar_exception_handlers(app: FastAPI):
    """Registra todos os handlers de exceção na instância principal do FastAPI."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RecursoNaoEncontrado, recurso_nao_encontrado_handler)
    app.add_exception_handler(ErroConexaoBanco, erro_conexao_banco_handler)
    app.add_exception_handler(ErroOperacaoBanco, erro_operacao_banco_handler)
    app.add_exception_handler(VariavelAmbienteNaoEncontrada, variavel_ambiente_handler)
    app.add_exception_handler(Exception, global_exception_handler)