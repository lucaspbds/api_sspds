from datetime import date
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.consulta_schema import CrimeGeralPaginadoResponse
from app.schemas.operacional_schema import OperacionalPaginadoResponse
from app.schemas.preconceito_schema import PreconceitoPaginadoResponse
from app.schemas.vitima_schema import (
    CrimeComVitimaPaginadoResponse,
    CvliPaginadoResponse,
)
from app.services.crime_service import (
    TIPO_CVLI,
    TIPO_PRECONCEITO,
    TIPOS_COM_VITIMA,
    TIPOS_OPERACIONAIS,
    CrimeService,
)
from database.repository import LIMITE_MAXIMO_PAGINACAO, LIMITE_PADRAO_PAGINACAO

router = APIRouter(prefix="/crimes", tags=["Crimes"])

# ---- Documentação OpenAPI das respostas de erro ----

_EXEMPLO_422_LIMIT: Dict[str, Any] = {
    "erro": "Erro de validação nos parâmetros",
    "detail": [
        {
            "type": "int_parsing",
            "loc": ["query", "limit"],
            "msg": "A entrada deve ser um número inteiro válido; não foi possível analisar a string como um número inteiro.",
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
            "msg": "A entrada deve ser uma data ou hora válida; caracteres inválidos no ano podem ser considerados inválidos.",
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
    int,
    Query(
        gt=0,
        le=LIMITE_MAXIMO_PAGINACAO,
        description=(
            f"Número máximo de registros por página "
            f"(padrão: {LIMITE_PADRAO_PAGINACAO}, máx.: {LIMITE_MAXIMO_PAGINACAO})"
        ),
    ),
]

CursorParam = Annotated[
    Optional[int],
    Query(
        gt=0,
        description="Cursor keyset (id do último item da página anterior em ordem decrescente)",
    ),
]


def _validar_periodo(data_inicio: Optional[date], data_fim: Optional[date]) -> None:
    """Rejeita com 422 um período em que `data_inicio` é posterior a `data_fim`."""
    if data_inicio and data_fim and data_inicio > data_fim:
        raise HTTPException(
            status_code=422,
            detail="data_inicio não pode ser posterior a data_fim.",
        )


# 1. Rota Geral de Consulta (Busca unificada na tabela do banco com filtros)
@router.get(
    "/",
    response_model=CrimeGeralPaginadoResponse,
    summary="Listar e filtrar ocorrências de crimes",
    description=(
        "Retorna uma resposta paginada por cursor (`id DESC`) com `items` e `pagination` "
        "(`limit`, `next_cursor`, `has_next`), permitindo filtrar por município, tipo de crime, "
        "AIS, natureza, meio empregado, perfil da vítima (gênero e raça), dia da semana, "
        "tipo de entorpecente e período de datas (`data_fato`, inclusivo)."
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
    cursor: CursorParam = None,
    limit: LimitParam = LIMITE_PADRAO_PAGINACAO,
):
    """
    Endpoint flexível de consulta unificada de crimes com suporte a múltiplos filtros opcionais.
    """
    _validar_periodo(data_inicio, data_fim)

    pagina = CrimeService.listar_com_filtros(
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
        cursor=cursor,
        limit=limit,
    )
    if not pagina["items"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum crime encontrado com os filtros fornecidos.",
        )
    return pagina


# 2. Rota Específica para CVLI
@router.get(
    "/cvli",
    response_model=CvliPaginadoResponse,
    summary="Listar Crimes Violentos Letais Intencionais (CVLI)",
    description="Retorna ocorrências específicas de CVLI formatadas com o schema de vítimas e meios empregados.",
    responses=_respostas("Nenhum dado de CVLI encontrado.", _EXEMPLO_422_DATA),
)
def listar_cvli(
    municipio: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Filtrar por nome do município (sem diferenciar maiúsculas/minúsculas)",
    ),
    ais: Optional[str] = Query(None, max_length=30, description="Filtrar por AIS (ex.: AIS 01)"),
    dia_semana: Optional[str] = Query(None, max_length=30, description="Filtrar por dia da semana"),
    natureza: Optional[str] = Query(None, max_length=150, description="Filtrar por tipificação detalhada"),
    meio_empregado: Optional[str] = Query(None, max_length=100, description="Filtrar por meio empregado"),
    vitima_genero: Optional[str] = Query(None, max_length=50, description="Filtrar por gênero da vítima"),
    vitima_raca: Optional[str] = Query(None, max_length=50, description="Filtrar por raça/cor da vítima"),
    vitima_idade: Optional[int] = Query(None, ge=0, description="Filtrar pela idade da vítima"),
    vitima_escolaridade: Optional[str] = Query(None, max_length=100, description="Filtrar pela escolaridade da vítima"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (inclusiva) no formato AAAA-MM-DD"),
    data_fim: Optional[date] = Query(None, description="Data final (inclusiva) no formato AAAA-MM-DD"),
    cursor: CursorParam = None,
    limit: LimitParam = LIMITE_PADRAO_PAGINACAO,
):
    """
    Lista ocorrências de CVLI.
    Se o parâmetro 'limit' não for informado, usa o limite padrão de paginação.
    """
    _validar_periodo(data_inicio, data_fim)

    pagina = CrimeService.listar_por_tipo(
        tipo=TIPO_CVLI,
        municipio=municipio,
        ais=ais,
        dia_semana=dia_semana,
        natureza=natureza,
        meio_empregado=meio_empregado,
        vitima_genero=vitima_genero,
        vitima_raca=vitima_raca,
        vitima_idade=vitima_idade,
        vitima_escolaridade=vitima_escolaridade,
        data_inicio=data_inicio,
        data_fim=data_fim,
        cursor=cursor,
        limit=limit,
    )
    if not pagina["items"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum dado de CVLI encontrado.",
        )
    return pagina


# 3. Rota Específica para Preconceito
@router.get(
    "/preconceito",
    response_model=PreconceitoPaginadoResponse,
    summary="Listar crimes de preconceito (Homofobia e Transfobia)",
    description="Retorna ocorrências detalhadas de crimes motivados por preconceito com foco em identidade de gênero e orientação sexual.",
    responses=_respostas("Nenhum crime de preconceito encontrado.", _EXEMPLO_422_DATA),
)
def listar_preconceito(
    municipio: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Filtrar por nome do município (sem diferenciar maiúsculas/minúsculas)",
    ),
    ais: Optional[str] = Query(None, max_length=30, description="Filtrar por AIS (ex.: AIS 01)"),
    dia_semana: Optional[str] = Query(None, max_length=30, description="Filtrar por dia da semana"),
    natureza: Optional[str] = Query(None, max_length=150, description="Filtrar por tipificação detalhada"),
    local_fato: Optional[str] = Query(None, max_length=150, description="Filtrar pelo local do fato"),
    vitima_genero: Optional[str] = Query(None, max_length=50, description="Filtrar por gênero da vítima"),
    vitima_orientacao_sexual: Optional[str] = Query(
        None, max_length=50, description="Filtrar pela orientação sexual da vítima"
    ),
    vitima_raca: Optional[str] = Query(None, max_length=50, description="Filtrar por raça/cor da vítima"),
    vitima_idade: Optional[int] = Query(None, ge=0, description="Filtrar pela idade da vítima"),
    vitima_escolaridade: Optional[str] = Query(None, max_length=100, description="Filtrar pela escolaridade da vítima"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (inclusiva) no formato AAAA-MM-DD"),
    data_fim: Optional[date] = Query(None, description="Data final (inclusiva) no formato AAAA-MM-DD"),
    cursor: CursorParam = None,
    limit: LimitParam = LIMITE_PADRAO_PAGINACAO,
):
    """
    Lista ocorrências de crimes de preconceito.
    """
    _validar_periodo(data_inicio, data_fim)

    pagina = CrimeService.listar_por_tipo(
        tipo=TIPO_PRECONCEITO,
        municipio=municipio,
        ais=ais,
        dia_semana=dia_semana,
        natureza=natureza,
        local_fato=local_fato,
        vitima_genero=vitima_genero,
        vitima_orientacao_sexual=vitima_orientacao_sexual,
        vitima_raca=vitima_raca,
        vitima_idade=vitima_idade,
        vitima_escolaridade=vitima_escolaridade,
        data_inicio=data_inicio,
        data_fim=data_fim,
        cursor=cursor,
        limit=limit,
    )
    if not pagina["items"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum crime de preconceito encontrado.",
        )
    return pagina


# 4. Rota Específica para Operacionais (Furto e CVP)
@router.get(
    "/operacionais",
    response_model=OperacionalPaginadoResponse,
    summary="Listar crimes operacionais (Furto e CVP)",
    description=(
        "Retorna ocorrências de crimes operacionais de menor complexidade estrutural "
        "(Furto e Crimes Violentos contra o Patrimônio - CVP). "
        "O campo `tipo_crime` identifica a categoria de cada registro."
    ),
    responses=_respostas("Nenhum registro operacional encontrado.", _EXEMPLO_422_DATA),
)
def listar_operacionais(
    municipio: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Filtrar por nome do município (sem diferenciar maiúsculas/minúsculas)",
    ),
    ais: Optional[str] = Query(None, max_length=30, description="Filtrar por AIS (ex.: AIS 01)"),
    dia_semana: Optional[str] = Query(None, max_length=30, description="Filtrar por dia da semana"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (inclusiva) no formato AAAA-MM-DD"),
    data_fim: Optional[date] = Query(None, description="Data final (inclusiva) no formato AAAA-MM-DD"),
    cursor: CursorParam = None,
    limit: LimitParam = LIMITE_PADRAO_PAGINACAO,
):
    """
    Lista ocorrências de crimes operacionais (Furto e CVP).
    """
    _validar_periodo(data_inicio, data_fim)

    pagina = CrimeService.listar_por_tipos(
        tipos=TIPOS_OPERACIONAIS,
        municipio=municipio,
        ais=ais,
        dia_semana=dia_semana,
        data_inicio=data_inicio,
        data_fim=data_fim,
        cursor=cursor,
        limit=limit,
    )
    if not pagina["items"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro operacional encontrado.",
        )
    return pagina


# 5. Rota Específica para Crimes com Vítima (Maria da Penha, Sexuais, Indígenas)
@router.get(
    "/vitimas",
    response_model=CrimeComVitimaPaginadoResponse,
    summary="Listar crimes com perfil de vítima (Maria da Penha, Sexuais, Indígenas)",
    description=(
        "Retorna ocorrências específicas de crimes com detalhamento de perfil da vítima "
        "(Lei Maria da Penha, Crimes Sexuais e Indígenas Vítimas de Crimes). "
        "O campo `tipo_crime` identifica a categoria de cada registro."
    ),
    responses=_respostas("Nenhum registro de crime com vítima encontrado.", _EXEMPLO_422_DATA),
)
def listar_crimes_com_vitima(
    municipio: Optional[str] = Query(
        None, min_length=1, max_length=100,
        description="Filtrar por nome do município (sem diferenciar maiúsculas/minúsculas)",
    ),
    ais: Optional[str] = Query(None, max_length=30, description="Filtrar por AIS (ex.: AIS 01)"),
    dia_semana: Optional[str] = Query(None, max_length=30, description="Filtrar por dia da semana"),
    vitima_genero: Optional[str] = Query(None, max_length=50, description="Filtrar por gênero da vítima"),
    vitima_raca: Optional[str] = Query(None, max_length=50, description="Filtrar por raça/cor da vítima"),
    vitima_idade: Optional[int] = Query(None, ge=0, description="Filtrar pela idade da vítima"),
    vitima_escolaridade: Optional[str] = Query(None, max_length=100, description="Filtrar pela escolaridade da vítima"),
    data_inicio: Optional[date] = Query(None, description="Data inicial (inclusiva) no formato AAAA-MM-DD"),
    data_fim: Optional[date] = Query(None, description="Data final (inclusiva) no formato AAAA-MM-DD"),
    cursor: CursorParam = None,
    limit: LimitParam = LIMITE_PADRAO_PAGINACAO,
):
    """
    Lista ocorrências de crimes com perfil de vítima (Maria da Penha, Sexuais, Indígenas).
    """
    _validar_periodo(data_inicio, data_fim)

    pagina = CrimeService.listar_por_tipos(
        tipos=TIPOS_COM_VITIMA,
        municipio=municipio,
        ais=ais,
        dia_semana=dia_semana,
        vitima_genero=vitima_genero,
        vitima_raca=vitima_raca,
        vitima_idade=vitima_idade,
        vitima_escolaridade=vitima_escolaridade,
        data_inicio=data_inicio,
        data_fim=data_fim,
        cursor=cursor,
        limit=limit,
    )
    if not pagina["items"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro de crime com vítima encontrado.",
        )
    return pagina