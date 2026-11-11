# app/schemas/crime_response.py
from datetime import date, time, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CrimeResponse(BaseModel):
    """Schema unificado para resposta das rotas de consulta de crimes."""
    id: int
    arquivo_id: Optional[int] = None
    tipo_crime: Optional[str] = None
    municipio: Optional[str] = None
    ais: Optional[str] = None
    local_fato: Optional[str] = None
    data_fato: Optional[date] = None
    hora_fato: Optional[time] = None
    dia_semana: Optional[str] = None
    natureza: Optional[str] = None
    meio_empregado: Optional[str] = None
    vitima_genero: Optional[str] = None
    vitima_idade: Optional[int] = None
    vitima_escolaridade: Optional[str] = None
    vitima_raca: Optional[str] = None
    vitima_orientacao_sexual: Optional[str] = None
    quantidade_armas: Optional[int] = None
    tipo_entorpecente: Optional[str] = None
    peso_entorpecente_kg: Optional[float] = None
    criado_em: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)