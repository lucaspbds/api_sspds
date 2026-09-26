class VariavelAmbienteNaoEncontrada(Exception):
    def __init__(self, nome_variavel, *args):
        self.__nome_variavel = nome_variavel
        self.__mensagem = "Variável de Ambiente não encontrada"
        super().__init__(*args)
        
    def print_mensagem_erro(self):
        print(f"{self.__mensagem}:\nNome da variável - {self.__nome_variavel}")