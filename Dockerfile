# Dockerfile para Cloud Run - API de Scoring PLATAM
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements-api.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements-api.txt

# Copiar código y datos
COPY api_scoring_cedula.py .
COPY key.json .
COPY data/processed/hybrid_scores.csv data/processed/hybrid_scores.csv

# Exponer puerto
EXPOSE 8080

# Ejecutar API
CMD exec uvicorn api_scoring_cedula:app --host 0.0.0.0 --port $PORT
