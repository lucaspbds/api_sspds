from app.schemas.base_schema import CrimeBaseSchema

class OperacionalResponse(CrimeBaseSchema):
    """Schema específico para crimes operacionais: Furto e CVP."""
    # Herda tudo da base, sem campos extras necessários por enquanto
    pass
