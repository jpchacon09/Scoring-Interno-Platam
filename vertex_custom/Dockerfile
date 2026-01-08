# Usar Python 3.11 (misma versión que el entorno local)
FROM python:3.11-slim

WORKDIR /app

# Instalar librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código y los modelos DENTRO de la imagen
COPY . .

# Comando para arrancar el servidor compatible con Vertex
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
