from pydantic import BaseModel, ConfigDict, Field
from datetime import date, time
from typing import Optional

class CrimeBaseSchema(BaseModel):
    """Atributos que todo crime tem e servirá de herança para os outros tipos de crime"""
    ais: Optional[str] = Field(None, alias="AIS")  
    municipio: str = Field(alias="Município")      
    data_fato: date = Field(alias="Data")          
    hora_fato: Optional[time] = Field(None, alias="Hora")  
    dia_semana: Optional[str] = Field(None, alias="Dia da Semana")  

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)