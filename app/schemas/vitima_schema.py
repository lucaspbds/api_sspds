from typing import Any, Optional

from pydantic import model_validator

from app.schemas.base_schema import CrimeBaseSchema

_IDADE_NAO_INFORMADA = {
    "não informada", "nao informada", "nao informado",
    "não informado", "", "none", "null",
}


class CrimeComVitimaResponse(CrimeBaseSchema):
    """Schema específico para crimes de Maria da Penha, Sexuais, Indígenas."""
    vitima_genero: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def limpar_dados_brutos(cls, values: Any) -> Any:
        """
        Trata idades que vêm como texto ("Não Informada") no banco.
        O Pydantic espera int em `vitima_idade`; se vier texto, vira None.
        Sem isso, uma única linha com texto derrubaria a resposta inteira (500).
        """
        if isinstance(values, dict):
            idade = values.get("vitima_idade")
            if isinstance(idade, str) and idade.strip().lower() in _IDADE_NAO_INFORMADA:
                # Copia o dicionário para não alterar o registro original recebido.
                values = {**values, "vitima_idade": None}
        return values


class CvliResponse(CrimeComVitimaResponse):
    """Schema para Crimes Violentos Letais Intencionais (CVLI)."""
    natureza: Optional[str] = None
    meio_empregado: Optional[str] = None
