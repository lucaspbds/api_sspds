import pandas as pd

def processor(url:str):
    df  = pd.read_excel(url)
    print(df)
    
    # O parâmetro orient='records' cria uma lista de dicionários (formato ideal para JSON)
    json_dados = df.to_json(orient='records', force_ascii=False, indent=4)

    # 3. Salve o resultado em um arquivo .json (opcional)
    with open('/database/dados.json', 'w', encoding='utf-8') as f:
        f.write(json_dados)