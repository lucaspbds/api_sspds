class VariavelAmbienteNaoEncontrada(Exception):
    def __init__(self, nome_variavel):
        self.__nome_variavel = nome_variavel
        self.__mensagem = f"Variável de Ambiente não encontrada:\nNome da variável - {self.__nome_variavel}"
        super().__init__(self.__mensagem)

class EstruturaCSSDoSiteAlterado(Exception):
    def __init__(self):
        self.__mensagem = "O container de indicadores detalhados não foi encontrado no HTML (seletor CSS pode ter mudado)."
        super().__init__(self.__mensagem)

class ValorInteiroInvalido(Exception):
    def __init__(self, valor):
        self.__mensagem = f"O valor recebido ({valor}) não é um valor inteiro válido."
        super().__init__(self.__mensagem)

class ColunasAusentesNaPlanilha(Exception):
    def __init__(self, colunasFaltantes):
        self.__mensagem = f"Colunas ausentes na planilha: {colunasFaltantes}"
        super().__init__(self.__mensagem)

class tipoOcorrenciaNaoEncontrado(Exception):
    def __init__(self, tipo_ocorrencia):
        self.__mensagem = f"Tipo de ocorrência não encontrado!({tipo_ocorrencia})"
        super().__init__(self.__mensagem)