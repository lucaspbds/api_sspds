import os
from pathlib import Path
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


    # Define o diretório do banco via variável de ambiente (padrão: "database")
    database_dir = Path(os.getenv("DATABASE_PATH", "database"))
    database_dir.mkdir(parents=True, exist_ok=True)
    # Salva os dados em um arquivo JSON
    with open(database_dir/'dados.json', 'w', encoding='utf-8') as f:
        f.write(json_dados)

    tiposOcorrenciasJson = json.dumps(tiposOcorrencias)
    with open(database_dir/'tiposOcorrencias.json', 'w', encoding='utf-8') as f:
        f.write(tiposOcorrenciasJson)