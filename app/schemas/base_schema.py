from pydantic import BaseModel, ConfigDict
from datetime import date, time
from typing import Optional

class CrimeBaseSchema(BaseModel):
    'Atributos que todo crime tem e servirá de herança para os\
    outros tipos de crime'
    ais: Optional[str] = None
    municipio: str
    data_fato: date
    hora_fato: Optional[time] = None
    dia_semana: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)