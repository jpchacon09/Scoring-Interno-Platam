#!/bin/bash
# ============================================================================
# PLATAM - Deployment Cloud Function (Simplificada)
# ============================================================================

set -e

echo ""
echo "========================================================================="
echo "  PLATAM - Deployment Cloud Function: Calculate Scores"
echo "========================================================================="
echo ""

PROJECT_ID="platam-analytics"
REGION="us-central1"
FUNCTION_NAME="calculate-scores"
RUNTIME="python311"
ENTRY_POINT="calculate_scores"
MEMORY="1GB"
TIMEOUT="60s"

echo "📋 Configuración:"
echo "  • Proyecto:  $PROJECT_ID"
echo "  • Región:    $REGION"
echo "  • Función:   $FUNCTION_NAME"
echo "  • Runtime:   $RUNTIME"
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
echo "📝 Guarda esta URL para configurar n8n"
echo ""
echo "========================================================================="
echo ""
