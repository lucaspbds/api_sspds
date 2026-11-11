from typing import Optional, List
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from app.services.crime_service import CrimeService
# Importando os esquemas necessários
from app.schemas.consulta_schema import CrimeGeralResponse
from app.schemas.operacional_schema import OperacionalResponse
from app.schemas.preconceito_schema import PreconceitoResponse
from app.schemas.vitima_schema import CvliResponse, CrimeComVitimaResponse

router = APIRouter(prefix="/crimes", tags=["Crimes"])

# 1. Rota Geral de Consulta (Busca unificada na tabela do banco com filtros)
@router.get(
    "/", 
    response_model=List[CrimeGeralResponse],
    summary="Listar e filtrar ocorrências de crimes",
    description="Retorna uma lista unificada de crimes cadastrados, permitindo filtrar por município, tipo de crime, período de datas e limitar a quantidade de registros.",
    responses={
        404: {
            "description": "Nenhum dado encontrado com os filtros informados",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nenhum crime encontrado com os filtros fornecidos."
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
                                "type": "date_parsing",
                                "loc": ["query", "data_inicio"],
                                "msg": "Input should be a valid valid date, format YYYY-MM-DD",
                                "input": "invalid-date"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def listar_crimes_geral(
    municipio: Optional[str] = Query(None, description="Filtrar por nome do município"),
    tipo_crime: Optional[str] = Query(None, description="Filtrar pelo tipo de crime"),
    data_inicio: Optional[date] = Query(None, description="Data inicial no formato AAAA-MM-DD"),
    data_fim: Optional[date] = Query(None, description="Data final no formato AAAA-MM-DD"),
    limit: Optional[int] = Query(None, gt=0, description="Número máximo de registros")
):
    """
    Endpoint flexível de consulta unificada de crimes com suporte a múltiplos filtros opcionais.
    """
    dados = CrimeService.listar_com_filtros(
        municipio=municipio, 
        tipo_crime=tipo_crime, 
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit
    )
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum crime encontrado com os filtros fornecidos."
        )
    return dados

# 2. Rota Específica para CVLI
@router.get(
    "/cvli", 
    response_model=List[CvliResponse],
    summary="Listar Crimes Violentos Letais Intencionais (CVLI)",
    description="Retorna ocorrências específicas de CVLI formatadas com o schema de vítimas e meios empregados.",
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
                                "loc": ["query", "limit"],
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
def listar_cvli(limit: Optional[int] = Query(None, gt=0, description="Número máximo de registros")):
    """
    Lista ocorrências de CVLI. 
    Se o parâmetro 'limit' não for informado, retorna todos os registros.
    """
    dados = CrimeService.listar_por_tipo(
        tipo="CRIMES VIOLENTOS LETAIS E INTENCIONAIS - CVLI", 
        limit=limit
    )
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum dado de CVLI encontrado."
        )
    return dados

# 3. Rota Específica para Preconceito
@router.get(
    "/preconceito", 
    response_model=List[PreconceitoResponse],
    summary="Listar crimes de preconceito (Homofobia e Transfobia)",
    description="Retorna ocorrências detalhadas de crimes motivados por preconceito com foco em identidade de gênero e orientação sexual.",
    responses={
        404: {
            "description": "Nenhum dado encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nenhum crime de preconceito encontrado."
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
                                "loc": ["query", "limit"],
                                "msg": "Input should be a valid integer, unable to parse string as an integer",
                                "input": "abc"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def listar_preconceito(limit: Optional[int] = Query(None, gt=0, description="Número máximo de registros")):
    """
    Lista ocorrências de crimes de preconceito.
    """
    dados = CrimeService.listar_por_tipo(
        tipo="HOMOFOBIA E TRANSFOBIA", 
        limit=limit
    )
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum crime de preconceito encontrado."
        )
    return dados

# 4. Rota Específica para Operacionais (Furto, CVP, etc.)
@router.get(
    "/operacionais", 
    response_model=List[OperacionalResponse],
    summary="Listar crimes operacionais (Furto, CVP...)",
    description="Retorna ocorrências de crimes operacionais de menor complexidade estrutural (como Furto ou CVP).",
    responses={
        404: {
            "description": "Nenhum dado encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nenhum registro operacional encontrado."
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
                                "loc": ["query", "limit"],
                                "msg": "Input should be a valid integer, unable to parse string as an integer",
                                "input": "xyz"
                            }
                        ]
                    }
                }
            }
        }
    }
)
def listar_operacionais(limit: Optional[int] = Query(None, gt=0, description="Número máximo de registros")):
    """
    Lista ocorrências de crimes operacionais.
    """
    dados = CrimeService.listar_por_tipo(
        tipo="FURTO", 
        limit=limit
    ) 
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum registro operacional encontrado."
        )
    return dados

# 5. Rota Específica para Crimes com Vítima (Maria da Penha, Sexuais, Indígenas)
@router.get(
    "/vitimas", 
    response_model=List[CrimeComVitimaResponse],
    summary="Listar crimes com perfil de vítima (Maria da Penha, Sexuais, Indígenas)",
    description="Retorna ocorrências específicas de crimes com detalhamento de perfil da vítima (como Lei Maria da Penha, Crimes Sexuais e Indígenas).",
    responses={
        404: {
            "description": "Nenhum dado encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Nenhum registro de crime com vítima encontrado."
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
                                "loc": ["query", "limit"],
                                "msg": "Input should be a valid integer, unable to parse string as an integer",
                                "input": "xyz"
                            }
                        ]
                    }
                }
            }
        }
    }
)

def listar_crimes_com_vitima(limit: Optional[int] = Query(None, gt=0, description="Número máximo de registros")):
    """
    Lista ocorrências de crimes com perfil de vítima (ex: Lei Maria da Penha).
    """
    dados = CrimeService.listar_por_tipo(
        tipo="LEI 11.340/06 (LEI MARIA DA PENHA)", 
        limit=limit
    ) 
    if not dados:
        raise HTTPException(
            status_code=404, 
            detail="Nenhum registro de crime com vítima encontrado."
        )
    return dados