from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional
from pydantic import Field, ConfigDict

class PreconceitoResponse(CrimeBaseSchema):
    """
    Schema específico para ocorrências de crimes de preconceito 
    (Homofobia e Transfobia).
    """
    ais: Optional[str] = None
    municipio: Optional[str] = None
    data_fato: Optional[str] = None
    hora_fato: Optional[str] = None
    dia_semana: Optional[str] = None
    natureza: Optional[str] = None
    local_fato: Optional[str] = None
    vitima_genero: Optional[str] = None
    vitima_orientacao_sexual: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)