from database.repository import inserir_registros
from database.repository import atualizar_registro
from .config import get_variavel_ambiente
from .helpers import recebeInteiro

tamanho_lote = recebeInteiro(get_variavel_ambiente("INSERT_CHUNK_SIZE"))
def inserir_historico_ingestoes(dados: dict[str, any]) -> int:
    resposta = inserir_registros(tabela="historico_ingestoes", dados=dados)
    return resposta[0]['id']

def atualizar_historico_ingestoes(id:int, dados: dict[str, any]) -> list[dict[str, any]]:
    resposta = atualizar_registro(tabela="historico_ingestoes", id_registro=id, coluna_id="id", novos_dados=dados)
    return resposta

def inserir_informacoes_arquivo(dados: dict[str, any]) -> int:
    resposta = inserir_registros(tabela="informacoes_arquivo", dados=dados)
    return resposta[0]['id']

def atualizar_informacoes_arquivo(id:int, dados: dict[str, any]) -> int:
    resposta = atualizar_registro(tabela="informacoes_arquivo", id_registro=id, coluna_id="id", novos_dados=dados)
    return resposta[0]['id']

def inserir_ocorrencias_crimes(dados: list[dict[str, any]], tamanho_lote=tamanho_lote):
    for i in range(0, len(dados), tamanho_lote):
        lote = dados[i:i + tamanho_lote]
        inserir_registros(tabela="ocorrencias_crimes", dados=lote)
   

