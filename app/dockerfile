FROM python:3.13.4

# Define o diretório de trabalho na raiz do workspace do contentor
WORKDIR /workspace

# Copia e instala as dependências a partir da raiz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia a pasta app inteira para dentro de /workspace/app
COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]