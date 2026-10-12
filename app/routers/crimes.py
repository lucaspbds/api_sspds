from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from app.services.crime_service import CrimeService
from app.schemas.vitima_schema import CvliResponse

router = APIRouter(prefix="/crimes", tags=["Crimes"])

@router.get(
    "/cvli", 
    response_model=List[CvliResponse],
    responses={
        404: {
            "description": "Nenhum dado encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nenhum dado de CVLI encontrado."
                    }
                }
            }
        },
        422: {
            "description": "Erro de validação nos parâmetros de consulta",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "int_parsing",
                                "loc": [
                                    "query",
                                    "limit"
                                ],
                                "msg": "Input should be a valid integer, unable to parse string as an integer",
                                "input": "d"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def listar_cvli(
    limit: Optional[int] = Query(
        None, 
        gt=0
    )
):
    """
    Lista ocorrências de CVLI. 
    Se o parâmetro 'limit' não for informado, retorna todos os registros.
    """
    dados = CrimeService.listar_ocorrencias(limit=limit)
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum dado de CVLI encontrado."
        )
    return dados