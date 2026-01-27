# Guía de Uso: Modelo de Riesgo Crediticio en Vertex AI

## Índice
1. [Resumen del Deployment](#resumen-del-deployment)
2. [Cómo Consumir el Endpoint](#cómo-consumir-el-endpoint)
3. [Actualizar el Modelo con Nueva Data](#actualizar-el-modelo-con-nueva-data)
4. [Gestión de Modelos en Vertex AI](#gestión-de-modelos-en-vertex-ai)
5. [Monitoreo y Troubleshooting](#monitoreo-y-troubleshooting)

---

## Resumen del Deployment

### Configuración Actual
- **Proyecto GCP:** `platam-analytics`
- **Región:** `us-central1`
- **Endpoint ID:** `1160748927884984320`
- **Modelo Activo:** `platam-custom-final`
- **Tipo:** Contenedor Docker personalizado
- **Imagen:** `gcr.io/platam-analytics/platam-scorer-custom:v1`
- **Máquina:** n1-standard-2 (2 vCPUs, 7.5 GB RAM)
- **Réplicas:** 1 mínimo, 1 máximo

### Ventajas del Contenedor Custom
✅ **Escalado automático:** Los datos se envían SIN escalar, el contenedor lo hace internamente
✅ **Compatible:** Control total sobre librerías (XGBoost 2.1, scikit-learn 1.4)
✅ **Todo incluido:** Modelo + Scaler en un solo contenedor
✅ **Producción-ready:** FastAPI optimizado para predicciones rápidas

---

## Cómo Consumir el Endpoint

### Opción 1: Python (Recomendado)

#### Instalación de dependencias:
```bash
pip install google-cloud-aiplatform
```

#### Script completo de ejemplo:
```python
from google.cloud import aiplatform
import os

# Autenticación (asegúrate de tener key.json en tu directorio)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"

# Configuración
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "1160748927884984320"

# Conectar con el endpoint
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

# Preparar datos del cliente (valores ORIGINALES, sin escalar)
datos_cliente = {
    'platam_score': 650,
    'experian_score_normalized': 700,
    'score_payment_performance': 400,
    'score_payment_plan': 150,
    'score_deterioration': 150,
    'payment_count': 18,
    'months_as_client': 14,
    'days_past_due_mean': 8.5,
    'days_past_due_max': 25,
    'pct_early': 0.3,
    'pct_late': 0.25,
    'peso_platam_usado': 0.6,
    'peso_hcpn_usado': 0.4,
    'tiene_plan_activo': 0,
    'tiene_plan_default': 0,
    'tiene_plan_pendiente': 0,
    'num_planes': 0
}

# Convertir a lista (IMPORTANTE: mantener este orden)
feature_order = [
    'platam_score', 'experian_score_normalized',
    'score_payment_performance', 'score_payment_plan', 'score_deterioration',
    'payment_count', 'months_as_client',
    'days_past_due_mean', 'days_past_due_max',
    'pct_early', 'pct_late',
    'peso_platam_usado', 'peso_hcpn_usado',
    'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
]

instance = [[datos_cliente[feature] for feature in feature_order]]

# Hacer predicción
prediction = endpoint.predict(instances=instance)

# Resultado
prob_no_default = prediction.predictions[0][0]  # Probabilidad de NO hacer default
prob_default = prediction.predictions[0][1]      # Probabilidad de hacer default

print(f"Probabilidad de Default: {prob_default*100:.2f}%")
print(f"Probabilidad de No-Default: {prob_no_default*100:.2f}%")

# Aplicar regla de negocio
if prob_default >= 0.60:
    decision = "RECHAZAR"
elif prob_default >= 0.40:
    decision = "REVISAR MANUALMENTE"
else:
    decision = "APROBAR"

print(f"Decisión: {decision}")
```

### Opción 2: Predicciones por Lote (Múltiples Clientes)

```python
# Lista de clientes
clientes = [
    [650, 700, 400, 150, 150, 18, 14, 8.5, 25, 0.3, 0.25, 0.6, 0.4, 0, 0, 0, 0],
    [800, 850, 500, 200, 200, 24, 18, 2.0, 10, 0.7, 0.1, 0.8, 0.2, 0, 0, 0, 0],
    [450, 500, 300, 100, 100, 12, 10, 15.0, 45, 0.2, 0.4, 0.5, 0.5, 1, 0, 0, 1]
]

# Enviar todos a la vez
prediction = endpoint.predict(instances=clientes)

# Procesar resultados
for i, pred in enumerate(prediction.predictions):
    print(f"Cliente {i+1}: {pred[1]*100:.2f}% probabilidad de default")
```

### Opción 3: Desde Excel/VBA (Usando REST API)

**Nota:** Necesitas generar un token de autenticación primero. Desde Python:

```python
from google.auth.transport.requests import Request
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
credentials.refresh(Request())
token = credentials.token
print(f"Token: {token}")
```

Luego en VBA (Excel):
```vb
Sub PredecirRiesgo()
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP")

    ' URL del endpoint
    url = "https://us-central1-aiplatform.googleapis.com/v1/projects/741488896424/locations/us-central1/endpoints/1160748927884984320:predict"

    ' Headers
    http.Open "POST", url, False
    http.setRequestHeader "Content-Type", "application/json"
    http.setRequestHeader "Authorization", "Bearer TU_TOKEN_AQUI"

    ' Body (datos del cliente)
    body = "{""instances"": [[650, 700, 400, 150, 150, 18, 14, 8.5, 25, 0.3, 0.25, 0.6, 0.4, 0, 0, 0, 0]]}"

    ' Enviar
    http.send body

    ' Procesar respuesta
    MsgBox http.responseText
End Sub
```

---

## Actualizar el Modelo con Nueva Data

### Proceso Completo de Actualización

#### **Paso 1: Entrenar el modelo localmente con nueva data**

```bash
# 1. Actualiza tu archivo ml_training_data.csv con los nuevos datos
# 2. Ejecuta el script de entrenamiento
cd "/Users/jpchacon/Scoring Interno"
python save_final_model.py
```

Esto generará:
- `models/xgboost_model_final.pkl` (modelo actualizado)
- `models/scaler_final.pkl` (scaler actualizado)

#### **Paso 2: Actualizar el contenedor**

```bash
# 1. Copiar modelos al directorio del contenedor
cp models/xgboost_model_final.pkl vertex_custom/
cp models/scaler_final.pkl vertex_custom/

# 2. Reconstruir la imagen Docker (incrementa la versión)
cd vertex_custom
export PROJECT_ID="platam-analytics"
export IMAGE_URI="gcr.io/$PROJECT_ID/platam-scorer-custom:v2"  # Nota: v2

gcloud builds submit --tag $IMAGE_URI --project=$PROJECT_ID
```

Esto tomará ~3-5 minutos.

#### **Paso 3: Desplegar la nueva versión**

```python
# Script: redeploy_updated_model.py
from google.cloud import aiplatform
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../key.json"

PROJECT_ID = "platam-analytics"
REGION = "us-central1"
IMAGE_URI = "gcr.io/platam-analytics/platam-scorer-custom:v2"  # Nueva versión
ENDPOINT_ID = "1160748927884984320"

aiplatform.init(project=PROJECT_ID, location=REGION)

# Subir nuevo modelo
model = aiplatform.Model.upload(
    display_name="platam-custom-v2",
    serving_container_image_uri=IMAGE_URI,
    serving_container_predict_route="/predict",
    serving_container_health_route="/health",
    serving_container_ports=[8080]
)

# Desplegar al mismo endpoint (reemplaza el anterior)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

model.deploy(
    endpoint=endpoint,
    deployed_model_display_name="platam-custom-v2",
    machine_type="n1-standard-2",
    min_replica_count=1,
    max_replica_count=1,
    traffic_percentage=100  # 100% del tráfico al nuevo modelo
)

print("✅ Modelo actualizado!")
```

Ejecutar:
```bash
python redeploy_updated_model.py
```

Tomará ~10-15 minutos. **Durante el deployment, el modelo anterior sigue funcionando.**

---

## Gestión de Modelos en Vertex AI

### Ver Modelos Registrados

```bash
gcloud ai models list --region=us-central1 --project=platam-analytics
```

### Eliminar Modelos Antiguos (Recomendado)

**Puedes eliminar los modelos de prueba que NO están desplegados:**

```bash
# Listar modelos
gcloud ai models list --region=us-central1 --project=platam-analytics --format="table(name,displayName,createTime)"

# Eliminar un modelo específico (ejemplo)
gcloud ai models delete MODEL_ID --region=us-central1 --project=platam-analytics
```

**Modelos que puedes eliminar:**
- `platam-riesgo-v1` (intento con XGBoost 1.7)
- `platam-riesgo-v2-xgb21` (intento con XGBoost 2.1)
- `platam-riesgo-v2-compatible` (intento fallido)
- `platam-riesgo-native` (intento fallido)
- `platam-riesgo-sklearn` (intento fallido)

**Modelo que DEBES MANTENER:**
- `platam-custom-final` (el que está actualmente desplegado)

**Verificar qué modelo está desplegado:**
```bash
gcloud ai endpoints describe 1160748927884984320 --region=us-central1 --project=platam-analytics
```

---

## Monitoreo y Troubleshooting

### Consola de Google Cloud

**Endpoints:**
https://console.cloud.google.com/vertex-ai/endpoints?project=platam-analytics

**Modelos registrados:**
https://console.cloud.google.com/vertex-ai/models?project=platam-analytics

**Logs en tiempo real:**
https://console.cloud.google.com/logs/viewer?project=platam-analytics

### Ver Predicciones en Logs

```bash
gcloud logging read "resource.type=aiplatform.googleapis.com/Endpoint AND resource.labels.endpoint_id=1160748927884984320" --limit=10 --project=platam-analytics
```

### Verificar Estado del Endpoint

```bash
gcloud ai endpoints describe 1160748927884984320 --region=us-central1 --project=platam-analytics
```

### Errores Comunes

**Error: "Endpoint not found"**
- Verifica que estés usando el proyecto correcto: `platam-analytics`
- Verifica el ENDPOINT_ID: `1160748927884984320`

**Error: "Permission denied"**
- Asegúrate de que `key.json` esté en el directorio correcto
- Verifica que la service account tenga permisos de Vertex AI User

**Predicciones lentas (>2 segundos)**
- Aumentar el número de réplicas:
```python
# En el script de deploy, cambiar:
min_replica_count=2,  # De 1 a 2
max_replica_count=5   # Escalado automático
```

### Costos

**Configuración actual (1 réplica n1-standard-2):**
- Costo por hora: ~$0.095 USD
- Costo mensual (24/7): ~$70 USD
- Incluye: Predicciones ilimitadas

**Optimización de costos:**
- Si no usas el modelo 24/7, considera detener el endpoint cuando no se use
- Para tráfico bajo (<100 predicciones/día), Cloud Run puede ser más económico

---

## Resumen de Comandos Útiles

```bash
# Ver modelos
gcloud ai models list --region=us-central1 --project=platam-analytics

# Ver endpoints
gcloud ai endpoints list --region=us-central1 --project=platam-analytics

# Eliminar modelo (que NO esté desplegado)
gcloud ai models delete MODEL_ID --region=us-central1 --project=platam-analytics

# Ver logs del endpoint
gcloud logging read "resource.type=aiplatform.googleapis.com/Endpoint" --limit=20 --project=platam-analytics

# Verificar última build de contenedor
gcloud builds list --limit=5 --project=platam-analytics
```

---

## Contacto y Soporte

Para problemas con el modelo o Vertex AI:
- **Documentación Vertex AI:** https://cloud.google.com/vertex-ai/docs
- **Status de GCP:** https://status.cloud.google.com/

**Archivos importantes en el proyecto:**
- `vertex_custom/` - Código del contenedor (modelo + API)
- `test_custom_prediction.py` - Script de prueba
- `key.json` - Credenciales (NO SUBIR A GITHUB)
