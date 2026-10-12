from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional
from pydantic import Field, ConfigDict, model_validator

class CrimeComVitimaResponse(CrimeBaseSchema):
    """Schema específico para crimes de Maria da Penha, Sexuais, Indígenas"""
    vitima_genero: Optional[str] = Field(None, alias="Gênero")               
    vitima_idade: Optional[int] = Field(None, alias="Idade da Vítima")       
    vitima_escolaridade: Optional[str] = Field(None, alias="Escolaridade da Vítima")  
    vitima_raca: Optional[str] = Field(None, alias="Raça da Vítima")        

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CvliResponse(CrimeComVitimaResponse):
    """Schema para Crimes Violentos Letais Intencionais (CVLI)"""
    natureza: Optional[str] = Field(None, alias="Natureza")
    meio_empregado: Optional[str] = Field(None, alias="Meio Empregado")   

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

# Validador para tratar idades que vêm como texto ("Não Informada")
# Razão: o Pydantic espera um inteiro na idade mas alguma colunas estão com str
# Em específico essa de idade
    @model_validator(mode='before')
    @classmethod
    def limpar_dados_brutos(cls, values: dict) -> dict:
        if isinstance(values, dict):
            # Se a idade vier como texto inválido, transformamos em None de forma segura
            idade = values.get("Idade da Vítima")
            if idade in ["Não Informada", "Não informada", "nao informada", "NAO INFORMADA", "", None]:
                values["Idade da Vítima"] = None
                
            # Se houver outros campos que venham com lixo de texto, pode limpá-los aqui também!
            
        return values