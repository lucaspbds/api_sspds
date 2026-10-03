from fastapi import APIRouter, Query
from app.services.crime_service import CrimeService

router = APIRouter(prefix="/crimes", tags=["Crimes"])

@router.get("/", summary="Listar ocorrências criminais")
def obter_crimes(
    limit: int = Query(10, description="Número máximo de registros a retornar")
):
    """
    Endpoint inicial para listagem de ocorrências de segurança pública.
    """
    dados = CrimeService.listar_ocorrencias(limit=limit)
    return {
        "quantidade": len(dados),
        "resultados": dados
    }