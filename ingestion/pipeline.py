from crawler import crawler
from processor import processor
def pipeline():
    lista_url = crawler()
    dados_json = processor(lista_url[0])
    return dados_json

if __name__ == "__main__":
    pipeline()