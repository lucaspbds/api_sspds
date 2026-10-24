from fastapi import FastAPI
from app.exception import registrar_exception_handlers
from app.routers import crimes

app = FastAPI(
    title="API Pública de Dados de Segurança - SSPDS/CE",
    description="API para consulta de dados públicos de segurança do Ceará.",
    version="1.0.0",
)

# Registra os tratamentos de erro 
registrar_exception_handlers(app)

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