#!/bin/bash
# ============================================================================
# PLATAM - Deployment Cloud Function (Con S3 para HCPN)
# ============================================================================

set -e

echo ""
echo "========================================================================="
echo "  PLATAM - Deployment Cloud Function: Calculate Scores (con S3)"
echo "========================================================================="
echo ""

PROJECT_ID="platam-analytics"
REGION="us-central1"
FUNCTION_NAME="calculate-scores"
RUNTIME="python311"
ENTRY_POINT="calculate_scores"
MEMORY="1GB"
TIMEOUT="60s"

echo "📋 Esta función descargará HCPN de S3 automáticamente"
echo ""
echo "🔐 Necesito credenciales AWS para S3:"
echo ""

read -p "AWS Access Key ID: " AWS_ACCESS_KEY
read -sp "AWS Secret Access Key: " AWS_SECRET_KEY
echo ""
read -p "S3 Bucket (ej: fft-analytics-data-lake): " S3_BUCKET
read -p "S3 Prefix (ej: ppay/prod/): " S3_PREFIX
echo ""

echo ""
echo "📋 Resumen:"
echo "  • Proyecto:     $PROJECT_ID"
echo "  • Región:       $REGION"
echo "  • Función:      $FUNCTION_NAME"
echo "  • S3 Bucket:    $S3_BUCKET"
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
  --set-env-vars="AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY,AWS_SECRET_ACCESS_KEY=$AWS_SECRET_KEY,S3_HCPN_BUCKET=$S3_BUCKET,S3_PREFIX=$S3_PREFIX" \
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
echo "🔐 Credenciales AWS configuradas como variables de entorno"
echo ""
echo "📝 Guarda esta URL para configurar n8n"
echo ""
echo "🧪 Probar la función:"
echo ""
echo "curl -X POST $FUNCTION_URL \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{"
echo '    "cedula": "1116614340",'
echo '    "client_data": {"months_as_client": 8, "ciudad": "Barranquilla"},'
echo '    "payments": [{"days_past_due": 7}, {"days_past_due": 2}],'
echo '    "payment_plans": []'
echo "  }'"
echo ""
echo "========================================================================="
echo ""
