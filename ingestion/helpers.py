import ast
import operator

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


# Operadores permitidos em expressões de configuração (ex.: "1024 * 64").
# Potência (**) fica de fora de propósito: permite gerar números gigantes.
OPERADORES_BINARIOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
}
OPERADORES_UNARIOS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
LIMITE_ABSOLUTO = 10**12


def avaliar_no(no: ast.AST, original: str) -> int:
    """Avalia recursivamente apenas inteiros e operações aritméticas simples."""
    if isinstance(no, ast.Constant) and type(no.value) is int:
        resultado = no.value
    elif isinstance(no, ast.BinOp) and type(no.op) in OPERADORES_BINARIOS:
        resultado = OPERADORES_BINARIOS[type(no.op)](
            avaliar_no(no.left, original), avaliar_no(no.right, original)
        )
    elif isinstance(no, ast.UnaryOp) and type(no.op) in OPERADORES_UNARIOS:
        resultado = OPERADORES_UNARIOS[type(no.op)](avaliar_no(no.operand, original))
    else:
        raise ValorInteiroInvalido(original)

    if abs(resultado) > LIMITE_ABSOLUTO:
        raise ValorInteiroInvalido(original)
    return resultado


def avaliar_expressao_inteira(expressao: str) -> int:
    """
    Converte um texto de configuração em inteiro, aceitando aritmética simples.

    Substitui o uso de ``eval`` nas variáveis de ambiente (``CHUNK_SIZE``,
    ``HASH_CHUNK_SIZE``): nada além de inteiros e dos operadores ``+``, ``-``,
    ``*``, ``//`` e parênteses é aceito, então o conteúdo do ``.env`` nunca é
    executado como código.

    Args:
        expressao (str): Texto como ``"65536"`` ou ``"1024 * 64"``.

    Returns:
        int: Valor calculado.

    Raises:
        ValorInteiroInvalido: Texto vazio, não textual, com sintaxe inválida,
            com elementos não permitidos, divisão por zero ou resultado
            absoluto acima de 10**12.
    """
    if not isinstance(expressao, str) or not expressao.strip():
        raise ValorInteiroInvalido(expressao)
    try:
        arvore = ast.parse(expressao.strip(), mode="eval")
        return avaliar_no(arvore.body, expressao)
    except (SyntaxError, ValueError, ZeroDivisionError, RecursionError) as erro:
        raise ValorInteiroInvalido(expressao) from erro
