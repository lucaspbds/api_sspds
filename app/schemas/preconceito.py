from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional
from pydantic import Field, ConfigDict

class PreconceitoResponse(CrimeBaseSchema):
    """
    Schema específico para ocorrências de crimes de preconceito 
    (Homofobia e Transfobia).
    """
    natureza: Optional[str] = Field(None, alias="Natureza")
    local: Optional[str] = Field(None, alias="Local")
    identidade_genero: Optional[str] = None
    orientacao_sexual: Optional[str] = None
    vitima_idade: Optional[int] = Field(None, alias="Idade da Vítima")       
    vitima_escolaridade: Optional[str] = Field(None, alias="Escolaridade da Vítima")  
    vitima_raca: Optional[str] = Field(None, alias="Raça da Vítima")        

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)