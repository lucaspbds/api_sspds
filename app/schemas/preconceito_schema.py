from typing import Optional

from app.schemas.base_schema import CrimeBaseSchema


class PreconceitoResponse(CrimeBaseSchema):
    """
    Schema específico para ocorrências de crimes de preconceito
    (Homofobia e Transfobia).

    Os campos comuns (município, data, hora, AIS, dia da semana...) são herdados de
    `CrimeBaseSchema`, mantendo os tipos corretos (`date`/`time`) e a obrigatoriedade
    de `municipio` e `data_fato`.
    """
    natureza: Optional[str] = None
    local_fato: Optional[str] = None
    vitima_genero: Optional[str] = None
    vitima_orientacao_sexual: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None
