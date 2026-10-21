from .exception import ValorInteiroInvalido

def recebeInteiro(valor: str) -> int:
    """
    Converte um valor fornecido em um número inteiro.

    Args:
        valor (str): O valor a ser convertido para inteiro.

    Returns:
        int: O número inteiro correspondente.

    Raises:
        ValorInteiroInvalido: Se o valor fornecido não puder ser convertido para 
        inteiro (erros de valor ou tipo).
    """
    try:
        numero_int = int(valor)
        return numero_int
    except (ValueError, TypeError):
        raise ValorInteiroInvalido(valor)