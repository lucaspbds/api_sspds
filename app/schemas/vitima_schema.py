from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional
from pydantic import Field, ConfigDict

class CrimeComVitimaResponse(CrimeBaseSchema):
    """Schema específico para crimes de Maria da Penha, Sexuais, Indígenas (CVLI)"""
    vitima_genero: Optional[str] = Field(None, alias="Gênero")               # Informa o gênero da vítima
    vitima_idade: Optional[int] = Field(None, alias="Idade da Vítima")       # Regista a idade da vítima
    vitima_escolaridade: Optional[str] = Field(None, alias="Escolaridade da Vítima")  # Detalha a escolaridade
    vitima_raca: Optional[str] = Field(None, alias="Raça da Vítima")         # Indica a raça informada

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CvliResponse(CrimeComVitimaResponse):
    """Schema para Crimes Violentos Letais Intencionais (CVLI)"""
    natureza: Optional[str] = Field(None, alias="Natureza")
    meio_empregado: Optional[str] = Field(None, alias="Meio Empregado")     # Informa o meio empregado no crime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)