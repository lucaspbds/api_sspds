from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional

class CrimeComVitimaResponse(CrimeBaseSchema):
    'Schema específico para crimes de Maria da Penha, Sexuais, Indígenas'
    vitima_genero: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None

class CvliResponse(CrimeComVitimaResponse):
    natureza: Optional[str] = None
    meio_empregado: Optional[str] = None