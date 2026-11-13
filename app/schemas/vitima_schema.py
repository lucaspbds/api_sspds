from app.schemas.base_schema import CrimeBaseSchema
from typing import Optional
from pydantic import Field, ConfigDict, model_validator

class CrimeComVitimaResponse(CrimeBaseSchema):
    """Schema específico para crimes de Maria da Penha, Sexuais, Indígenas."""
    vitima_genero: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CvliResponse(CrimeComVitimaResponse):
    """Schema para Crimes Violentos Letais Intencionais (CVLI)."""
    natureza: Optional[str] = None
    meio_empregado: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def limpar_dados_brutos(cls, values: dict) -> dict:
        """
        Trata idades que vêm como texto ("Não Informada") no banco.
        O Pydantic espera int em `vitima_idade`; se vier texto, vira None.
        """
        if isinstance(values, dict):
            idade = values.get("vitima_idade")
            if isinstance(idade, str) and idade.strip().lower() in (
                "não informada", "nao informada", "nao informado",
                "não informado", "", "none", "null"
            ):
                values["vitima_idade"] = None
        return values