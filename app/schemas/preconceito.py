from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional

class PreconceitoResponse(CrimeBaseSchema):
    """
    Schema específico para ocorrências de crimes de preconceito 
    (Homofobia e Transfobia).
    """
    natureza: Optional[str] = None
    local: Optional[str] = None
    identidade_genero: Optional[str] = None
    orientacao_sexual: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None