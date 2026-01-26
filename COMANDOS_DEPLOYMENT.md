# ⚡ Comandos Rápidos - Deployment & Monitoreo

**Guía de referencia rápida para deployment y troubleshooting**

---

## 🚀 DEPLOYMENT

### 1. Deploy Cloud Function

```bash
# Navegar al directorio
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"

# Hacer ejecutable
chmod +x deploy.sh

# Ejecutar deployment
./deploy.sh
```

**Credenciales que te pedirá:**
- AWS Access Key ID
- AWS Secret Access Key
- S3 Bucket (ej: `fft-analytics-data-lake`)
- S3 Prefix (ej: `ppay/prod/`)

**Tiempo:** ~5 minutos

---

## 🧪 TESTING

### Test Cloud Function (cURL)

```bash
curl -X POST https://TU_URL_CLOUD_FUNCTION_AQUI \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {
      "months_as_client": 3,
      "ciudad": "MANI (C/NARE)"
    },
    "payments": [
      {
        "payment_date": "2023-11-09",
        "days_past_due": 7,
        "payment_amount": 2000000
      },
      {
        "payment_date": "2023-10-15",
        "days_past_due": 2,
        "payment_amount": 1500000
      }
    ],
    "payment_plans": []
  }'
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_risk_level": "Bajo"
}
```

### Test con Python

```bash
python3 << 'EOF'
import requests
import json

url = "https://TU_URL_CLOUD_FUNCTION_AQUI"
data = {
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI (C/NARE)"},
    "payments": [
        {"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}
    ],
    "payment_plans": []
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2))
EOF
```

---

## 📊 MONITOREO

### Ver logs en tiempo real

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=50
```

### Ver logs con streaming (tail -f)

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=50 \
  --format="table(severity,timestamp,textPayload)" \
  --tail
```

### Ver solo errores

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=50 \
  --filter="severity=ERROR"
```

### Ver logs de última hora

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=100 \
  --filter="timestamp>\"$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S')Z\""
```

---

## 🔍 INFORMACIÓN Y ESTADO

### Ver detalles de Cloud Function

```bash
gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2
```

### Ver URL de Cloud Function

```bash
gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2 \
  --format='value(serviceConfig.uri)'
```

### Ver variables de entorno

```bash
gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2 \
  --format="yaml(serviceConfig.environmentVariables)"
```

### Ver estado de Vertex AI endpoint

```bash
gcloud ai endpoints describe 7891061911641391104 \
  --region=us-central1 \
  --project=platam-analytics
```

### Listar modelos deployados en endpoint

```bash
gcloud ai endpoints describe 7891061911641391104 \
  --region=us-central1 \
  --project=platam-analytics \
  --format="yaml(deployedModels)"
```

---

## 🗄️ AWS S3

### Verificar archivo HCPN existe

```bash
aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ | grep hcpn_1116614340
```

### Descargar archivo HCPN para inspección

```bash
aws s3 cp s3://fft-analytics-data-lake/ppay/prod/hcpn_1116614340.json ./test_hcpn.json
cat test_hcpn.json | python3 -m json.tool
```

### Listar archivos HCPN

```bash
aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ | grep hcpn | head -20
```

---

## 🔧 TROUBLESHOOTING

### Test local de Cloud Function (antes de deploy)

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"

# Instalar dependencias localmente
pip3 install -r requirements.txt

# Ejecutar localmente con functions-framework
export AWS_ACCESS_KEY_ID="tu_access_key"
export AWS_SECRET_ACCESS_KEY="tu_secret_key"
export S3_HCPN_BUCKET="fft-analytics-data-lake"
export S3_PREFIX="ppay/prod/"

functions-framework --target=calculate_scores --port=8080
```

Luego en otra terminal:

```bash
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI"},
    "payments": [{"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}],
    "payment_plans": []
  }'
```

### Verificar acceso a Vertex AI

```bash
gcloud ai endpoints list \
  --region=us-central1 \
  --project=platam-analytics
```

### Ver últimos deployments

```bash
gcloud functions list \
  --project=platam-analytics \
  --region=us-central1
```

### Ver métricas de Cloud Function

```bash
gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2 \
  --format="yaml(serviceConfig.availableMemory,serviceConfig.timeoutSeconds)"
```

---

## 🔄 RE-DEPLOYMENT

### Re-deploy después de cambios en código

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"

# Si NO cambiaste variables de entorno, puedes usar comando directo:
gcloud functions deploy calculate-scores \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=calculate_scores \
  --trigger-http \
  --allow-unauthenticated \
  --memory=1GB \
  --timeout=60s \
  --project=platam-analytics
```

**Nota:** Esto mantiene las variables de entorno existentes.

### Re-deploy con nuevas variables de entorno

```bash
# Usa el script deploy.sh que te pedirá las credenciales de nuevo
./deploy.sh
```

---

## 🗑️ ELIMINACIÓN (si necesitas empezar de cero)

### Eliminar Cloud Function

```bash
gcloud functions delete calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2
```

**⚠️ CUIDADO:** Esto eliminará la función completamente. Solo usa si necesitas empezar de cero.

---

## 📊 MySQL (Testing)

### Test queries SQL directamente

```sql
-- Cliente
SELECT
  _ID,
  cl_doc_number as cedula,
  cl_city as ciudad,
  TIMESTAMPDIFF(MONTH, cct_created, NOW()) as months_as_client
FROM wp_jet_cct_clientes
WHERE _ID = 1702;

-- Pagos
SELECT
  p_payment_date,
  FROM_UNIXTIME(p_payment_date) as payment_date_formatted,
  p_payment_amount,
  p_penalty_payment,
  COALESCE(
    DATEDIFF(
      FROM_UNIXTIME(p.p_payment_date),
      FROM_UNIXTIME(l.l_due_date)
    ),
    0
  ) as days_past_due
FROM wp_jet_cct_pagos p
LEFT JOIN wp_jet_cct_prestamos l ON p.p_l_id = l._ID
WHERE p.p_cl_id = 1702
LIMIT 10;

-- Préstamos
SELECT
  _ID as loan_id,
  l_status,
  FROM_UNIXTIME(l_disbursement_date) as disbursement_date,
  FROM_UNIXTIME(l_due_date) as due_date,
  l_principal,
  l_balance_total
FROM wp_jet_cct_prestamos
WHERE l_cl_id = 1702
LIMIT 10;
```

---

## 🌐 WordPress REST API (Testing)

### Ver cliente actual

```bash
curl -X GET "https://platampay.com/wp-json/jet-cct/clientes/1702" \
  -u "username:application_password"
```

### Actualizar scores manualmente

```bash
curl -X POST "https://platampay.com/wp-json/jet-cct/clientes/1702" \
  -H "Content-Type: application/json" \
  -u "username:application_password" \
  -d '{
    "cl_platam_score": "730.5",
    "cl_hybrid_score": "745.2",
    "cl_ml_probability_default": "0.12",
    "cl_ml_probability_no_default": "0.88",
    "cl_ml_risk_level": "Bajo",
    "cl_hybrid_weight_platam": "0.6",
    "cl_hybrid_weight_experian": "0.4",
    "cl_ml_modified": "'$(date +%s)'"
  }'
```

---

## 📋 CHECKLIST DE DEPLOYMENT

```bash
# 1. Verificar proyecto GCP
gcloud config get-value project
# Debe mostrar: platam-analytics

# 2. Verificar autenticación
gcloud auth list

# 3. Deploy Cloud Function
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
./deploy.sh

# 4. Guardar URL
URL=$(gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2 \
  --format='value(serviceConfig.uri)')
echo "Cloud Function URL: $URL"

# 5. Test Cloud Function
curl -X POST $URL \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI"},
    "payments": [{"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}],
    "payment_plans": []
  }'

# 6. Verificar logs
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=10

# 7. Configurar n8n con la URL
echo "Configurar en n8n:"
echo "  Variable: CLOUD_FUNCTION_URL"
echo "  Valor: $URL"
```

---

## 🆘 COMANDOS DE EMERGENCIA

### Si Cloud Function no responde

```bash
# Ver logs de errores
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --limit=50 \
  --filter="severity>=ERROR"

# Re-deploy rápido
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
gcloud functions deploy calculate-scores \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=calculate_scores \
  --trigger-http \
  --allow-unauthenticated \
  --memory=1GB \
  --timeout=60s \
  --project=platam-analytics
```

### Si Vertex AI no responde

```bash
# Verificar endpoint
gcloud ai endpoints describe 7891061911641391104 \
  --region=us-central1 \
  --project=platam-analytics

# Listar endpoints disponibles
gcloud ai endpoints list \
  --region=us-central1 \
  --project=platam-analytics
```

### Si S3 no responde

```bash
# Verificar credenciales AWS
aws sts get-caller-identity

# Verificar acceso al bucket
aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ | head -5
```

---

## 📈 MÉTRICAS Y PERFORMANCE

### Ver invocaciones de Cloud Function

```bash
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=calculate-scores" \
  --limit=50 \
  --format="table(timestamp,severity,jsonPayload.message)" \
  --project=platam-analytics
```

### Ver tiempos de respuesta

```bash
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=calculate-scores AND jsonPayload.processing_time_ms" \
  --limit=20 \
  --format="table(timestamp,jsonPayload.processing_time_ms)" \
  --project=platam-analytics
```

### Estadísticas de uso

```bash
gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2 \
  --format="yaml(serviceConfig.maxInstanceCount,serviceConfig.availableCpu)"
```

---

## 🔐 SEGURIDAD

### Ver IAM de Cloud Function

```bash
gcloud functions get-iam-policy calculate-scores \
  --region=us-central1 \
  --project=platam-analytics
```

### Verificar que variables de entorno están configuradas

```bash
gcloud functions describe calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --gen2 \
  --format="yaml(serviceConfig.environmentVariables)" | \
  grep -E "(AWS_ACCESS|S3_)"
```

**Salida esperada:**
```yaml
AWS_ACCESS_KEY_ID: AKI...
AWS_SECRET_ACCESS_KEY: ***
S3_HCPN_BUCKET: fft-analytics-data-lake
S3_PREFIX: ppay/prod/
```

---

## 💾 BACKUP

### Backup del código actual

```bash
# Crear backup antes de cambios
cd "/Users/jpchacon/Scoring Interno"
tar -czf "backup_cloud_function_$(date +%Y%m%d_%H%M%S).tar.gz" \
  cloud_function_calculate_scores/
```

### Ver backups

```bash
cd "/Users/jpchacon/Scoring Interno"
ls -lh backup_cloud_function_*.tar.gz
```

### Restaurar backup

```bash
cd "/Users/jpchacon/Scoring Interno"
tar -xzf backup_cloud_function_YYYYMMDD_HHMMSS.tar.gz
```

---

## 📝 VARIABLES DE ENTORNO

Para configurar localmente (testing):

```bash
export AWS_ACCESS_KEY_ID="tu_access_key_aqui"
export AWS_SECRET_ACCESS_KEY="tu_secret_key_aqui"
export S3_HCPN_BUCKET="fft-analytics-data-lake"
export S3_PREFIX="ppay/prod/"
export GOOGLE_CLOUD_PROJECT="platam-analytics"
```

Para verificar:

```bash
echo "AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:0:10}..."
echo "S3_HCPN_BUCKET: $S3_HCPN_BUCKET"
echo "S3_PREFIX: $S3_PREFIX"
```

---

## 🎯 CASOS DE USO COMUNES

### Test con cliente específico

```bash
CEDULA="1116614340"

# Test Cloud Function
curl -X POST $CLOUD_FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d "{
    \"cedula\": \"$CEDULA\",
    \"client_data\": {\"months_as_client\": 3, \"ciudad\": \"MANI\"},
    \"payments\": [{\"payment_date\": \"2023-11-09\", \"days_past_due\": 7, \"payment_amount\": 2000000}],
    \"payment_plans\": []
  }"

# Ver si HCPN existe en S3
aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ | grep "hcpn_$CEDULA"
```

### Batch testing (múltiples clientes)

```bash
for CEDULA in 1116614340 128282 1234567890; do
  echo "Testing cedula: $CEDULA"
  curl -X POST $CLOUD_FUNCTION_URL \
    -H "Content-Type: application/json" \
    -d "{
      \"cedula\": \"$CEDULA\",
      \"client_data\": {\"months_as_client\": 3, \"ciudad\": \"MANI\"},
      \"payments\": [{\"payment_date\": \"2023-11-09\", \"days_past_due\": 7, \"payment_amount\": 2000000}],
      \"payment_plans\": []
    }" | python3 -m json.tool
  echo "---"
done
```

---

**Última actualización:** 2026-01-26
**Versión:** 1.0 Final

**Guías relacionadas:**
- `GUIA_DEPLOYMENT_FINAL.md` - Guía completa paso a paso
- `N8N_QUERIES_FINALES.md` - Queries SQL para n8n
- `ARQUITECTURA_COMPLETA.md` - Arquitectura detallada del sistema
