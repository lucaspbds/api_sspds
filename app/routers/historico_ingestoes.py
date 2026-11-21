from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.historico_ingestoes_schema import HistoricoIngestaoResponse
from app.services.historico_ingestoes_service import HistoricoIngestoesService

router = APIRouter(prefix="/historico-ingestoes", tags=["Histórico de Ingestões"])


@router.get(
    "/",
    response_model=List[HistoricoIngestaoResponse],
    summary="Listar histórico de ingestões",
    description="Consulta os registros de execuções da tabela `historico_ingestoes`, com filtros opcionais por `status` e `data` (`criado_em`).",
)
def listar_historico_ingestoes(
    status: Optional[str] = Query(
        None,
        description="Filtrar por status da ingestão: EM_ANDAMENTO, SUCESSO, PARCIAL ou FALHA",
    ),
    data: Optional[date] = Query(
        None,
        description="Filtrar pela data de criação (`criado_em`) no formato AAAA-MM-DD",
    ),
    limit: Optional[int] = Query(
        None,
        gt=0,
        description="Número máximo de registros",
    ),
):
    try:
        dados = HistoricoIngestoesService.listar_historico(
            status=status,
            data=data,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Nenhum registro de histórico de ingestão encontrado com os filtros fornecidos.",
        )
    return dados