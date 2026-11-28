from datetime import date
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.historico_ingestoes_schema import HistoricoIngestaoPaginadoResponse
from app.services.historico_ingestoes_service import HistoricoIngestoesService
from database.repository import LIMITE_MAXIMO_PAGINACAO, LIMITE_PADRAO_PAGINACAO

router = APIRouter(prefix="/historico-ingestoes", tags=["Histórico de Ingestões"])

# ---- Documentação OpenAPI das respostas de erro ----
_EXEMPLO_422_STATUS: Dict[str, Any] = {
    "detail": "Status inválido 'INVALIDO'. Valores permitidos: EM_ANDAMENTO, FALHA, PARCIAL, SUCESSO."
}


def _respostas(detalhe_404: str, exemplo_422: Dict[str, Any] = _EXEMPLO_422_STATUS) -> Dict[int, Dict[str, Any]]:
    """Monta o bloco `responses` do OpenAPI com os erros possíveis da rota."""
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


# Tipos anotados reutilizáveis (mesmo padrão de app/routers/crimes.py)
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


@router.get(
    "/",
    response_model=HistoricoIngestaoPaginadoResponse,
    summary="Listar histórico de ingestões",
    description=(
        "Consulta os registros de execuções da tabela `historico_ingestoes` com paginação keyset. "
        "Permite filtrar por status e por data de criação (`criado_em`)."
    ),
    responses=_respostas("Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos."),
)
def listar_historico_ingestoes(
    status: Optional[str] = Query(
        None,
        description="Filtrar por status da ingestão: EM_ANDAMENTO, SUCESSO, PARCIAL ou FALHA",
    ),
    data: Optional[date] = Query(
        None,
        description="Filtrar pela data de criação (`criado_em`, dia inteiro em UTC) no formato AAAA-MM-DD",
    ),
    cursor: CursorParam = None,
    limit: LimitParam = LIMITE_PADRAO_PAGINACAO,
):
    """Lista as execuções da ingestão, da mais recente para a mais antiga (`id DESC`)."""
    try:
        pagina = HistoricoIngestoesService.listar_historico(
            status=status,
            data=data,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not pagina["items"]:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos.",
        )
    return pagina
