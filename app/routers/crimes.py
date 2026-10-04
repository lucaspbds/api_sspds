from typing import Optional, List
from fastapi import APIRouter, HTTPException
from app.services.crime_service import CrimeService
from app.schemas.vitima_schema import CvliResponse

router = APIRouter(prefix="/crimes", tags=["Crimes"])

@router.get("/cvli", response_model=List[CvliResponse])
def listar_cvli(limit: Optional[int] = None):
    """
    Lista ocorrências de CVLI. 
    Se o parâmetro 'limit' não for informado, retorna todos os registos.
    """
    dados = CrimeService.listar_ocorrencias(limit=limit)
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum dado de CVLI encontrado."
        )
    return dados