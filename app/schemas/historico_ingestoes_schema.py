from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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