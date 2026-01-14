# Custom Container para Vertex AI - Python 3.11 + XGBoost 2.0.3
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV AIP_HTTP_PORT=8080
ENV AIP_HEALTH_ROUTE=/health
ENV AIP_PREDICT_ROUTE=/predict

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
RUN pip install --no-cache-dir \
    xgboost==2.0.3 \
    scikit-learn==1.3.0 \
    pandas==2.0.3 \
    numpy==1.24.3 \
    joblib==1.3.0 \
    flask==2.3.0 \
    gunicorn==21.2.0

# Copiar predictor y modelo
COPY predictor.py /app/predictor.py
COPY model.pkl /app/model.pkl
COPY scaler.pkl /app/scaler.pkl
COPY feature_names.json /app/feature_names.json

# Exponer puerto
EXPOSE 8080

# Ejecutar predictor con gunicorn
CMD exec gunicorn --bind :$AIP_HTTP_PORT --workers 1 --threads 8 --timeout 0 predictor:app
