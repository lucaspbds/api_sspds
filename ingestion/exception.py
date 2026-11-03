class IngestionError(Exception):
    """Exceção-base para erros esperados no pipeline de ingestão."""

class VariavelAmbienteNaoEncontrada(IngestionError):
    def __init__(self, nome_variavel):
        self.__nome_variavel = nome_variavel
        self.__mensagem = f"Variável de Ambiente não encontrada:\nNome da variável - {self.__nome_variavel}"
        super().__init__(self.__mensagem)

class EstruturaCSSDoSiteAlterado(IngestionError):
    def __init__(self):
        self.__mensagem = "O container de indicadores detalhados não foi encontrado no HTML (seletor CSS pode ter mudado)."
        super().__init__(self.__mensagem)

class ValorInteiroInvalido(IngestionError):
    def __init__(self, valor):
        self.__mensagem = f"O valor recebido ({valor}) não é um valor inteiro válido."
        super().__init__(self.__mensagem)

class NormalizerError(IngestionError):
    """Exceção-base para erros esperados na normalização."""

class ColunasAusentesNaPlanilha(NormalizerError):
    def __init__(self, colunasFaltantes):
        self.__mensagem = f"Colunas ausentes na planilha: {colunasFaltantes}"
        super().__init__(self.__mensagem)

class tipoOcorrenciaNaoEncontrado(NormalizerError):
    def __init__(self, tipo_ocorrencia):
        self.__mensagem = f"Tipo de ocorrência não encontrado!({tipo_ocorrencia})"
        super().__init__(self.__mensagem)

class DownloadError(IngestionError):
    """Falha ao baixar ou salvar um arquivo remoto."""


class DownloadHTTPError(DownloadError):
    """O servidor respondeu com um status HTTP de erro."""


class DownloadTimeoutError(DownloadError):
    """A requisição excedeu o tempo limite configurado."""


class DownloadConnectionError(DownloadError):
    """Não foi possível estabelecer ou manter a conexão HTTP."""


class FileWriteError(DownloadError):
    """Falha ao gravar o arquivo baixado em disco."""


class FileValidationError(IngestionError):
    """Falha ao localizar, ler ou calcular o hash de um arquivo."""


class DatabaseLookupError(IngestionError):
    """Falha ao consultar se um hash já existe no banco de dados."""
