from typing import List
from pydantic import BaseModel
from app.schemas.base_schema import CrimeBaseSchema
from app.schemas.consulta_schema import PaginationMeta


class OperacionalResponse(CrimeBaseSchema):
    """Schema específico para crimes operacionais: Furto e CVP."""
    # Herda tudo da base, sem campos extras necessários por enquanto
    pass


class OperacionalPaginadoResponse(BaseModel):
    items: List[OperacionalResponse]
    pagination: PaginationMeta