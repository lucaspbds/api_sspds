from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, time, datetime

class CrimeResponse(BaseModel):
    id: int
    tipo_crime: str
    municipio: str
    ais: Optional[str] = None
    data_fato: date
    hora_fato: Optional[time] = None
    natureza: Optional[str] = None
    vitima_genero: Optional[str] = None
    vitima_idade: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)