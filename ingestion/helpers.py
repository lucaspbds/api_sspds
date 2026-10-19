from .exception import ValorInteiroInvalido

def recebeInteiro(valor) -> int:
    try:
        numero_int = int(valor)
        return numero_int
    except (ValueError, TypeError):
        raise ValorInteiroInvalido(valor)