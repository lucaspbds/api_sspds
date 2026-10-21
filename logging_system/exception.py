class VariavelAmbienteNaoEncontrada(Exception):
    def __init__(self, nome_variavel):
        self.__nome_variavel = nome_variavel
        self.__mensagem = f"Variável de Ambiente não encontrada:\nNome da variável - {self.__nome_variavel}"
        super().__init__(self.__mensagem)