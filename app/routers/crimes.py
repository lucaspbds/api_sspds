from datetime import date
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.consulta_schema import CrimeGeralResponse
from app.schemas.operacional_schema import OperacionalResponse
from app.schemas.preconceito_schema import PreconceitoResponse
from app.schemas.vitima_schema import CrimeComVitimaResponse, CvliResponse
from app.services.crime_service import (
    TIPO_CVLI,
    TIPO_PRECONCEITO,
    TIPOS_COM_VITIMA,
    TIPOS_OPERACIONAIS,
    CrimeService,
)

router = APIRouter(prefix="/crimes", tags=["Crimes"])

# ---- Documentação OpenAPI das respostas de erro ----

_EXEMPLO_422_LIMIT: Dict[str, Any] = {
    "erro": "Erro de validação nos parâmetros",
    "detail": [
        {
            "type": "int_parsing",
            "loc": ["query", "limit"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
            "input": "abc",
        }
    ],
}

_EXEMPLO_422_DATA: Dict[str, Any] = {
    "erro": "Erro de validação nos parâmetros",
    "detail": [
        {
            "type": "date_from_datetime_parsing",
            "loc": ["query", "data_inicio"],
            "msg": "Input should be a valid date or datetime, invalid character in year",
            "input": "invalid-date",
        }
    ],
}


def _respostas(detalhe_404: str, exemplo_422: Dict[str, Any] = _EXEMPLO_422_LIMIT) -> Dict[int, Dict[str, Any]]:
    """Monta o bloco `responses` do OpenAPI com os erros possíveis de cada rota."""
    return {
        404: {
            "description": "Nenhum dado encontrado",
            "content": {"application/json": {"example": {"detail": detalhe_404}}},
        },
        422: {
            "description": "Erro de validação nos parâmetros de consulta",
            "content": {"application/json": {"example": exemplo_422}},
        },
        500: {
            "description": "Erro interno (consulta ao banco ou configuração)",
            "content": {
                "application/json": {
                    "example": {
                        "erro": "Erro na Operação do Banco",
                        "mensagem": "Falha ao executar a operação solicitada no Supabase.",
                    }
                }
            },
        },
        503: {
            "description": "Banco de dados indisponível",
            "content": {
                "application/json": {
                    "example": {
                        "erro": "Erro de Conexão com o Banco",
                        "mensagem": "Não foi possível estabelecer comunicação com o Supabase.",
                    }
                }
            },
        },
    }


LimitParam = Annotated[
    Optional[int],
    Query(gt=0, description="Número máximo de registros"),
]


# 1. Rota Geral de Consulta (Busca unificada na tabela do banco com filtros)
@router.get(
    "/",
    response_model=List[CrimeGeralResponse],
    summary="Listar e filtrar ocorrências de crimes",
    description=(
        "Retorna uma lista unificada de crimes cadastrados, permitindo filtrar por município, "
        "tipo de crime, período de datas (`data_fato`, inclusivo) e limitar a quantidade de registros."
    ),
    responses=_respostas("Nenhum crime encontrado com os filtros fornecidos.", _EXEMPLO_422_DATA),
)
def listar_crimes_geral(
    municipio: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Filtrar por nome do município (sem diferenciar maiúsculas/minúsculas)",
    ),
    tipo_crime: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Filtrar pelo tipo de crime (valor exato de `tipo_crime`, ex.: FURTO)",
    ),
    ais: Optional[str] = Query(None, max_length=30, description="Filtrar por AIS (ex.: AIS 01)"),
    natureza: Optional[str] = Query(None, max_length=150, description="Filtrar por tipificação detalhada"),
    meio_empregado: Optional[str] = Query(None, max_length=100, description="Filtrar por meio empregado"),
    vitima_genero: Optional[str] = Query(None, max_length=50, description="Filtrar por gênero da vítima"),
    vitima_raca: Optional[str] = Query(None, max_length=50, description="Filtrar por raça/cor da vítima"),
    dia_semana: Optional[str] = Query(None, max_length=30, description="Filtrar por dia da semana"),
    tipo_entorpecente: Optional[str] = Query(None, max_length=100, description="Filtrar por tipo de entorpecente"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (inclusiva) no formato AAAA-MM-DD"),
    data_fim: Optional[date] = Query(None, description="Data final (inclusiva) no formato AAAA-MM-DD"),
    limit: LimitParam = None,
):
    """
    Endpoint flexível de consulta unificada de crimes com suporte a múltiplos filtros opcionais.
    """
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=422,
            detail="data_inicio não pode ser posterior a data_fim.",
        )

    dados = CrimeService.listar_com_filtros(
        municipio=municipio,
        tipo_crime=tipo_crime,
        ais=ais,
        natureza=natureza,
        meio_empregado=meio_empregado,
        vitima_genero=vitima_genero,
        vitima_raca=vitima_raca,
        dia_semana=dia_semana,
        tipo_entorpecente=tipo_entorpecente,
        data_inicio=data_inicio,
        data_fim=data_fim,
        limit=limit,
    )
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhum crime encontrado com os filtros fornecidos.",
        )
    return dados


# 2. Rota Específica para CVLI
@router.get(
    "/cvli",
    response_model=List[CvliResponse],
    summary="Listar Crimes Violentos Letais Intencionais (CVLI)",
    description="Retorna ocorrências específicas de CVLI formatadas com o schema de vítimas e meios empregados.",
    responses=_respostas("Nenhum dado de CVLI encontrado."),
)
def listar_cvli(limit: LimitParam = None):
    """
    Lista ocorrências de CVLI.
    Se o parâmetro 'limit' não for informado, retorna todos os registros.
    """
    dados = CrimeService.listar_por_tipo(tipo=TIPO_CVLI, limit=limit)
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhum dado de CVLI encontrado.",
        )
    return dados


# 3. Rota Específica para Preconceito
@router.get(
    "/preconceito",
    response_model=List[PreconceitoResponse],
    summary="Listar crimes de preconceito (Homofobia e Transfobia)",
    description="Retorna ocorrências detalhadas de crimes motivados por preconceito com foco em identidade de gênero e orientação sexual.",
    responses=_respostas("Nenhum crime de preconceito encontrado."),
)
def listar_preconceito(limit: LimitParam = None):
    """
    Lista ocorrências de crimes de preconceito.
    """
    dados = CrimeService.listar_por_tipo(tipo=TIPO_PRECONCEITO, limit=limit)
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhum crime de preconceito encontrado.",
        )
    return dados


# 4. Rota Específica para Operacionais (Furto e CVP)
@router.get(
    "/operacionais",
    response_model=List[OperacionalResponse],
    summary="Listar crimes operacionais (Furto e CVP)",
    description=(
        "Retorna ocorrências de crimes operacionais de menor complexidade estrutural "
        "(Furto e Crimes Violentos contra o Patrimônio - CVP). "
        "O campo `tipo_crime` identifica a categoria de cada registro."
    ),
    responses=_respostas("Nenhum registro operacional encontrado."),
)
def listar_operacionais(limit: LimitParam = None):
    """
    Lista ocorrências de crimes operacionais (Furto e CVP).
    """
    dados = CrimeService.listar_por_tipos(tipos=TIPOS_OPERACIONAIS, limit=limit)
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro operacional encontrado.",
        )
    return dados


# 5. Rota Específica para Crimes com Vítima (Maria da Penha, Sexuais, Indígenas)
@router.get(
    "/vitimas",
    response_model=List[CrimeComVitimaResponse],
    summary="Listar crimes com perfil de vítima (Maria da Penha, Sexuais, Indígenas)",
    description=(
        "Retorna ocorrências específicas de crimes com detalhamento de perfil da vítima "
        "(Lei Maria da Penha, Crimes Sexuais e Indígenas Vítimas de Crimes). "
        "O campo `tipo_crime` identifica a categoria de cada registro."
    ),
    responses=_respostas("Nenhum registro de crime com vítima encontrado."),
)
def listar_crimes_com_vitima(limit: LimitParam = None):
    """
    Lista ocorrências de crimes com perfil de vítima (Maria da Penha, Sexuais e Indígenas).
    """
    dados = CrimeService.listar_por_tipos(tipos=TIPOS_COM_VITIMA, limit=limit)
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro de crime com vítima encontrado.",
        )
    return dados
