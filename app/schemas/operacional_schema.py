from app.schemas.base_schema import CrimeBaseSchema

class OperacionalResponse(CrimeBaseSchema):
    'Schema específico para crimes de Furto, CVP, Armas'
    # Herda tudo da base, sem campos extras necessários por enquanto
    pass