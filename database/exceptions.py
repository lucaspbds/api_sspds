class VariavelAmbienteNaoEncontrada(Exception):
    """Exceção lançada quando uma variável de ambiente obrigatória não está definida."""

    def __init__(self, nome_variavel: str):
        self.nome_variavel = nome_variavel
        mensagem = f"A variável de ambiente obrigatória '{nome_variavel}' não foi encontrada."
        super().__init__(mensagem)


class ErroConexaoBanco(Exception):
    """Exceção lançada quando não é possível estabelecer conexão com o Supabase."""

    def __init__(self, mensagem: str = "Falha ao conectar ao banco de dados Supabase."):
        super().__init__(mensagem)


class ErroOperacaoBanco(Exception):
    """Exceção lançada quando uma operação de leitura, inserção ou atualização falha."""

    def __init__(self, operacao: str, tabela: str, detalhe: str = ""):
        self.operacao = operacao
        self.tabela = tabela
        mensagem = f"Falha na operação '{operacao}' na tabela '{tabela}'."
        if detalhe:
            mensagem = f"{mensagem} Detalhe: {detalhe}"
        super().__init__(mensagem)