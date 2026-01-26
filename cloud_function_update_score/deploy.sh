#!/bin/bash
# ============================================================================
# PLATAM - Script de Deployment para Cloud Function
# ============================================================================
#
# Despliega la Cloud Function para actualización de scores individuales
#
# Uso:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# ============================================================================

set -e  # Exit on error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "========================================================================="
echo "  PLATAM - Deployment de Cloud Function: Update Client Score"
echo "========================================================================="
echo ""

# Variables de configuración
PROJECT_ID="platam-analytics"
REGION="us-central1"
FUNCTION_NAME="update-client-score"
RUNTIME="python311"
ENTRY_POINT="update_client_score"
MEMORY="1GB"
TIMEOUT="60s"

# Credenciales MySQL (CONFIGURA ESTAS VARIABLES)
read -p "🔐 MySQL Host (ej: 34.123.45.67): " MYSQL_HOST
read -p "🔐 MySQL User (ej: platam_user): " MYSQL_USER
read -sp "🔐 MySQL Password: " MYSQL_PASSWORD
echo ""
read -p "🔐 MySQL Database (ej: platam_db): " MYSQL_DATABASE
echo ""

# Confirmar deployment
echo ""
echo -e "${YELLOW}📋 RESUMEN DE DEPLOYMENT:${NC}"
echo "  • Proyecto:     $PROJECT_ID"
echo "  • Región:       $REGION"
echo "  • Función:      $FUNCTION_NAME"
echo "  • Runtime:      $RUNTIME"
echo "  • Memoria:      $MEMORY"
echo "  • Timeout:      $TIMEOUT"
echo "  • MySQL Host:   $MYSQL_HOST"
echo "  • MySQL DB:     $MYSQL_DATABASE"
echo ""

read -p "¿Continuar con el deployment? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${RED}❌ Deployment cancelado${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🚀 Iniciando deployment...${NC}"
echo ""

# Deploy Cloud Function
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
  --set-env-vars="MYSQL_HOST=$MYSQL_HOST,MYSQL_USER=$MYSQL_USER,MYSQL_PASSWORD=$MYSQL_PASSWORD,MYSQL_DATABASE=$MYSQL_DATABASE" \
  --project="$PROJECT_ID"

# Obtener URL de la función
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --gen2 \
  --format='value(serviceConfig.uri)')

echo ""
echo "========================================================================="
echo -e "${GREEN}✅ DEPLOYMENT COMPLETADO${NC}"
echo "========================================================================="
echo ""
echo -e "${GREEN}📍 URL de la Cloud Function:${NC}"
echo "   $FUNCTION_URL"
echo ""
echo -e "${YELLOW}📝 SIGUIENTES PASOS:${NC}"
echo ""
echo "1. Probar la función manualmente:"
echo ""
echo "   curl -X POST $FUNCTION_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"client_id\": \"1068\", \"trigger\": \"test\"}'"
echo ""
echo "2. Configurar n8n webhook para llamar a esta URL"
echo ""
echo "3. Ver logs en tiempo real:"
echo ""
echo "   gcloud functions logs read $FUNCTION_NAME --region=$REGION --gen2 --limit=50"
echo ""
echo "========================================================================="
echo ""
