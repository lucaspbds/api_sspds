from fastapi import FastAPI

app = FastAPI(
    title="API Pública de Dados de Segurança",
    description="API para consulta de dados públicos de segurança do Ceará.",
    version="0.0.1",
)


@app.get("/")
def root():
    return {
        "message": "API SSPDS funcionando!"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }