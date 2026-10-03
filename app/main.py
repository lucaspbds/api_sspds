from fastapi import FastAPI
from app.routers import crimes

app = FastAPI(
    title="API Pública de Dados de Segurança - SSPDS/CE",
    description="API para consulta de dados públicos de segurança do Ceará.",
    version="1.0.0",
)

# Incluindo o roteador de crimes
app.include_router(crimes.router)

@app.get("/")
def root():
    return {
        "message": "API SSPDS funcionando com sucesso!",
        "docs_url": "/docs"
    }

@app.get("/health")
def health():
    return {
        "status": "ok"
    }