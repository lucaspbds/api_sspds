from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.consulta_schema import PaginationMeta


class HistoricoIngestaoResponse(BaseModel):
    id: int
    data_inicio: datetime
    data_fim: Optional[datetime] = None
    status: str
    qtd_arquivos_encontrados: int
    qtd_arquivos_processados: int
    qtd_arquivos_falhas: int
    mensagem_erro: Optional[str] = None
    criado_em: datetime


class HistoricoIngestaoPaginadoResponse(BaseModel):
    items: List[HistoricoIngestaoResponse]
    pagination: PaginationMeta