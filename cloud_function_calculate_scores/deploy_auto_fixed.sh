#!/bin/bash
# ============================================================================
# PLATAM - Deployment Automático Cloud Function (Con credenciales del .env)
# ============================================================================

set -e

echo ""
echo "========================================================================="
echo "  PLATAM - Deployment AUTOMÁTICO Cloud Function: Calculate Scores"
echo "========================================================================="
echo ""

PROJECT_ID="platam-analytics"
REGION="us-central1"
FUNCTION_NAME="calculate-scores"
RUNTIME="python311"
ENTRY_POINT="calculate_scores"
MEMORY="1GB"
TIMEOUT="60s"

# Cargar credenciales del archivo .env
ENV_FILE="../config/.env"

if [ -f "$ENV_FILE" ]; then
    echo "✅ Cargando credenciales desde $ENV_FILE"
    echo ""

    # Leer solo las variables AWS necesarias (ignorar las que tienen espacios)
    AWS_ACCESS_KEY_ID=$(grep "^AWS_ACCESS_KEY_ID=" "$ENV_FILE" | cut -d '=' -f2)
    AWS_SECRET_ACCESS_KEY=$(grep "^AWS_SECRET_ACCESS_KEY=" "$ENV_FILE" | cut -d '=' -f2)
    S3_HCPN_BUCKET=$(grep "^S3_HCPN_BUCKET=" "$ENV_FILE" | cut -d '=' -f2)
    S3_PREFIX=$(grep "^S3_PREFIX=" "$ENV_FILE" | cut -d '=' -f2)

    echo "📋 Credenciales cargadas:"
    echo "  • AWS Access Key: ${AWS_ACCESS_KEY_ID:0:10}..."
    echo "  • S3 Bucket: $S3_HCPN_BUCKET"
    echo "  • S3 Prefix: $S3_PREFIX"
    echo ""
else
    echo "❌ ERROR: No se encontró el archivo $ENV_FILE"
    echo ""
    echo "Por favor, asegúrate de que existe el archivo:"
    echo "  /Users/jpchacon/Scoring Interno/config/.env"
    echo ""
    echo "Con el contenido:"
    echo "  AWS_ACCESS_KEY_ID=tu_access_key"
    echo "  AWS_SECRET_ACCESS_KEY=tu_secret_key"
    echo "  S3_HCPN_BUCKET=fft-analytics-data-lake"
    echo "  S3_PREFIX=ppay/prod/"
    echo ""
    exit 1
fi

# Validar que las variables existan
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "❌ ERROR: Credenciales AWS no encontradas en $ENV_FILE"
    exit 1
fi

if [ -z "$S3_HCPN_BUCKET" ]; then
    echo "❌ ERROR: S3_HCPN_BUCKET no encontrado en $ENV_FILE"
    exit 1
fi

echo ""
echo "📋 Resumen del Deployment:"
echo "  • Proyecto:     $PROJECT_ID"
echo "  • Región:       $REGION"
echo "  • Función:      $FUNCTION_NAME"
echo "  • Runtime:      $RUNTIME"
echo "  • S3 Bucket:    $S3_HCPN_BUCKET"
echo "  • S3 Prefix:    $S3_PREFIX"
echo ""

read -p "¿Continuar con el deployment? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Deployment cancelado"
    exit 1
fi

echo ""
echo "🚀 Desplegando Cloud Function..."
echo ""

gcloud functions deploy "$FUNCTION_NAME" \
  --gen2 \
  --runtime="$RUNTIME" \
  --region="$REGION" \
  --source=. \
  --entry-point="$ENTRY_POINT" \
  --trigger-http \
  --allow-unauthenticated \
  --memory="$MEMORY" \
  --timeout="$TIMEOUT" \
  --set-env-vars="AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY,S3_HCPN_BUCKET=$S3_HCPN_BUCKET,S3_PREFIX=$S3_PREFIX" \
  --project="$PROJECT_ID"

FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --gen2 \
  --format='value(serviceConfig.uri)')

echo ""
echo "========================================================================="
echo "✅ DEPLOYMENT COMPLETADO"
echo "========================================================================="
echo ""
echo "📍 URL de la Cloud Function:"
echo "   $FUNCTION_URL"
echo ""
echo "🔐 Credenciales AWS configuradas desde config/.env"
echo ""
echo "📝 IMPORTANTE: Copia esta URL y configúrala en n8n"
echo ""
echo "   Variable de entorno en n8n:"
echo "   Nombre: CLOUD_FUNCTION_URL"
echo "   Valor:  $FUNCTION_URL"
echo ""
echo "🧪 Probar la función:"
echo ""
echo "curl -X POST $FUNCTION_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '    "cedula": "1116614340",'
echo '    "client_data": {"months_as_client": 3, "ciudad": "MANI"},'
echo '    "payments": [{"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}],'
echo '    "payment_plans": []'
echo "  }'"
echo ""
echo "========================================================================="
echo ""
