#!/bin/bash
# Script de Despliegue de API v2.2 a Cloud Run

set -e

PROJECT_ID="platam-analytics"
REGION="us-central1"
SERVICE_NAME="scoring-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/scoring-api:v2.2"

echo "=========================================="
echo "DESPLIEGUE API v2.2 A CLOUD RUN"
echo "=========================================="
echo ""

# 1. Verificar prerequisitos
echo "[1/4] Verificando prerequisitos..."

if [ ! -f "SCORES_V2_ANALISIS_COMPLETO.csv" ]; then
    echo "❌ Error: SCORES_V2_ANALISIS_COMPLETO.csv no encontrado"
    exit 1
fi

if [ ! -f "key.json" ]; then
    echo "❌ Error: key.json no encontrado"
    exit 1
fi

if [ ! -f "api_scoring_cedula.py" ]; then
    echo "❌ Error: api_scoring_cedula.py no encontrado"
    exit 1
fi

echo "✓ Archivos necesarios encontrados"

# 2. Build de Docker
echo ""
echo "[2/4] Construyendo imagen Docker..."
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID}
echo "✓ Imagen construida: ${IMAGE_NAME}"

# 3. Desplegar a Cloud Run
echo ""
echo "[3/4] Desplegando a Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --project ${PROJECT_ID}

echo "✓ Servicio desplegado"

# 4. Obtener URL
echo ""
echo "[4/4] Obteniendo URL del servicio..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo ""
echo "=========================================="
echo "✅ DESPLIEGUE COMPLETADO"
echo "=========================================="
echo ""
echo "📊 Información:"
echo "   • Servicio: ${SERVICE_NAME}"
echo "   • Región: ${REGION}"
echo "   • URL: ${SERVICE_URL}"
echo "   • Versión: v2.2 (22 features)"
echo ""
echo "🧪 Probar servicio:"
echo "   curl ${SERVICE_URL}/health"
echo ""
echo "   curl -X POST ${SERVICE_URL}/predict \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"cedula\":\"1006157869\"}'"
echo ""
echo "📚 Docs interactivas:"
echo "   ${SERVICE_URL}/docs"
echo ""
echo "=========================================="
