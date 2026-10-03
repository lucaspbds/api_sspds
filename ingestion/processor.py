import pandas as pd
import json 

def processor(url: str, tiposOcorrencias:list) -> None:
    """
    Função responsável por baixar uma planilha, convertê-la para
    o formato JSON e salvar em um arquivo .json.

    Args:
        string url: endereço da planilha que será baixada.
        list tiposOcorrencias: lista dos tipos de ocorrências criminais.

    Return:
        None
    """
    #Download do arquivo
    df = pd.read_excel(url)

    # O parâmetro orient='records' transforma cada linha da planilha
    # em um dicionário, formando uma lista de registros em JSON.
    json_dados = df.to_json(
        orient='records',
        force_ascii=False,
        indent=4
    )

    # Salva os dados em um arquivo JSON
    with open('/database/dados.json', 'w', encoding='utf-8') as f:
        f.write(json_dados)

    tiposOcorrenciasJson = json.dumps(tiposOcorrencias)
    with open('/database/tiposOcorrencias.json', 'w', encoding='utf-8') as f:
            f.write(tiposOcorrenciasJson)