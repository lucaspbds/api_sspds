from typing import Dict

from fastapi import APIRouter, FastAPI, HTTPException, status

from app.exception import registrar_exception_handlers
from app.routers import crimes, historico_ingestoes
from database.exceptions import ErroConexaoBanco
from database.exceptions import (
    VariavelAmbienteNaoEncontrada as VariavelAmbienteNaoEncontradaBanco,
)
from database.repository import validar_conexao

app = FastAPI(
    title="API Pública de Dados de Segurança - SSPDS/CE",
    description="API para consulta de dados públicos de segurança do Ceará.",
    version="1.0.0",
)

# Registra os tratamentos de erro
registrar_exception_handlers(app)

health_router = APIRouter(prefix="/health", tags=["Health"])


@health_router.get(
    "/live",
    summary="Liveness check",
    description="Verifica se o processo da API está ativo e respondendo.",
)
def health_live() -> Dict[str, str]:
    return {"status": "ok"}


@health_router.get(
    "/ready",
    summary="Readiness check",
    description="Verifica se a API está pronta para atender requisições, incluindo acesso ao banco de dados.",
)
def health_ready() -> Dict[str, str]:
    try:
        conectado = validar_conexao()
    except (VariavelAmbienteNaoEncontradaBanco, ErroConexaoBanco) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível ou configuração ausente.",
        ) from exc

    if not conectado:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível.",
        )

    return {"status": "ready", "database": "ok"}


# Incluindo os roteadores
app.include_router(health_router)
app.include_router(crimes.router)
app.include_router(historico_ingestoes.router)


@app.get("/", summary="Raiz da aplicação", tags=["Status"])
def root() -> Dict[str, str]:
    return {
        "message": "API SSPDS funcionando com sucesso!",
        "docs_url": "/docs",
    }