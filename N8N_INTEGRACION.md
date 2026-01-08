# 🔗 Integración con n8n - Scoring Completo

## 📋 Resumen

**Input simple:** Solo el `client_id`
**Output completo:**
- ✅ Score interno PLATAM
- ✅ Score Experian
- ✅ Score híbrido (combinación dinámica)
- ✅ Probabilidad de default ML
- ✅ Recomendación final inteligente

---

## 🎯 Ejemplo de Respuesta

**Request:**
```json
{
  "client_id": "12345"
}
```

**Response:**
```json
{
  "client_id": "12345",
  "timestamp": "2026-01-08T01:30:00",
  "scoring": {
    "platam_score": 650,
    "experian_score": 700,
    "hybrid_score": 675,
    "hybrid_category": "Bueno",
    "peso_platam": 0.6,
    "peso_experian": 0.4
  },
  "ml_prediction": {
    "probability_default": 0.642,
    "probability_no_default": 0.358,
    "risk_level": "Muy Alto",
    "ml_decision": "RECHAZAR"
  },
  "recommendation": {
    "final_decision": "RECHAZAR",
    "confidence": "Alta",
    "reason": "Alta probabilidad de default (64.2%) con score bueno",
    "should_review_manually": false,
    "flags": [
      "⚠️ Probabilidad de default muy alta (>70%)"
    ]
  }
}
```

---

## 🚀 Setup Rápido

### 1. Ejecutar la API localmente

```bash
# 1. Instalar dependencias
pip install fastapi uvicorn google-cloud-aiplatform

# 2. Ejecutar la API
python api_scoring_completo.py
```

La API estará disponible en: `http://localhost:8000`

**Docs interactivas:** http://localhost:8000/docs

---

### 2. Configurar n8n

**Flujo básico:**

```
Webhook → HTTP Request → Procesar Response → [Guardar/Notificar]
```

#### Node 1: Webhook (Trigger)

```json
{
  "httpMethod": "POST",
  "path": "scoring-cliente",
  "responseMode": "responseNode"
}
```

**Input esperado:**
```json
{
  "client_id": "12345"
}
```

#### Node 2: HTTP Request (Llamar a la API)

**Configuración:**
- Method: `POST`
- URL: `http://localhost:8000/predict`
- Body Content Type: `JSON`
- Body:
```json
{
  "client_id": "{{ $json.client_id }}"
}
```

#### Node 3: Set (Procesar Response)

Extraer campos importantes:
```javascript
{
  "client_id": "{{ $json.client_id }}",
  "score_hibrido": "{{ $json.scoring.hybrid_score }}",
  "categoria": "{{ $json.scoring.hybrid_category }}",
  "prob_default": "{{ $json.ml_prediction.probability_default }}",
  "decision_final": "{{ $json.recommendation.final_decision }}",
  "confianza": "{{ $json.recommendation.confidence }}",
  "razon": "{{ $json.recommendation.reason }}",
  "requiere_revision": "{{ $json.recommendation.should_review_manually }}"
}
```

#### Node 4a: IF (Enrutar por decisión)

**Condiciones:**
- Si `decision_final` = "APROBAR" → Ruta 1
- Si `decision_final` = "RECHAZAR" → Ruta 2
- Si `decision_final` = "REVISAR MANUALMENTE" → Ruta 3

#### Node 4b: Acciones según decisión

**Ejemplo - Aprobar:**
- Enviar email de aprobación
- Actualizar CRM con status "Aprobado"
- Crear registro en base de datos

**Ejemplo - Rechazar:**
- Enviar notificación al cliente
- Actualizar CRM con status "Rechazado"
- Guardar en log de rechazos

**Ejemplo - Revisar:**
- Crear ticket en sistema de revisión
- Notificar al analista
- Agregar a cola de revisión manual

---

## 📊 Ejemplo Completo de Workflow n8n

```json
{
  "name": "PLATAM - Scoring Completo",
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "httpMethod": "POST",
        "path": "scoring-cliente"
      }
    },
    {
      "name": "Llamar API Scoring",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://localhost:8000/predict",
        "options": {},
        "bodyParametersJson": "={{ { \"client_id\": $json.client_id } }}"
      }
    },
    {
      "name": "Switch por Decisión",
      "type": "n8n-nodes-base.switch",
      "parameters": {
        "mode": "rules",
        "rules": {
          "rules": [
            {
              "value1": "={{ $json.recommendation.final_decision }}",
              "operation": "equal",
              "value2": "APROBAR"
            },
            {
              "value1": "={{ $json.recommendation.final_decision }}",
              "operation": "equal",
              "value2": "RECHAZAR"
            },
            {
              "value1": "={{ $json.recommendation.final_decision }}",
              "operation": "contains",
              "value2": "REVISAR"
            }
          ]
        }
      }
    },
    {
      "name": "Enviar Email Aprobado",
      "type": "n8n-nodes-base.gmail",
      "parameters": {
        "operation": "send",
        "to": "{{ $json.client_email }}",
        "subject": "Tu crédito ha sido aprobado",
        "message": "Felicidades! Tu score híbrido es {{ $json.scoring.hybrid_score }}"
      }
    },
    {
      "name": "Crear Ticket Revisión",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "https://tu-sistema-tickets.com/api/create",
        "bodyParametersJson": "={{ { \"client_id\": $json.client_id, \"reason\": $json.recommendation.reason, \"prob_default\": $json.ml_prediction.probability_default } }}"
      }
    }
  ]
}
```

---

## 🌐 Desplegar la API en Cloud Run (Producción)

Para que n8n pueda acceder desde cualquier lugar:

### 1. Crear Dockerfile

Ya existe en `api_scoring_completo.py`, solo falta:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api_scoring_completo.py .
COPY key.json .

EXPOSE 8000

CMD ["python", "api_scoring_completo.py"]
```

### 2. Desplegar a Cloud Run

```bash
# 1. Construir y subir imagen
gcloud builds submit --tag gcr.io/platam-analytics/scoring-api

# 2. Desplegar
gcloud run deploy scoring-api \
  --image gcr.io/platam-analytics/scoring-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 1Gi \
  --cpu 1
```

Obtendrás una URL como: `https://scoring-api-xxx.run.app`

### 3. Actualizar n8n

Cambiar URL en el HTTP Request Node:
```
https://scoring-api-xxx.run.app/predict
```

---

## 🎯 Endpoints Disponibles

### 1. Scoring Completo (Recomendado)
**POST** `/predict`

Retorna scoring híbrido + ML + recomendación

### 2. Solo Scoring Híbrido
**POST** `/predict/scoring-only`

Retorna solo scores (sin llamar a Vertex AI)

### 3. Solo Predicción ML
**POST** `/predict/ml-only`

Retorna solo probabilidad de default

---

## 🔧 Configuración Avanzada

### Conectar a tu Base de Datos

En `api_scoring_completo.py`, modifica la función `get_client_data()`:

**Ejemplo con BigQuery:**
```python
from google.cloud import bigquery

def get_client_data(client_id: str) -> Dict:
    client = bigquery.Client()
    query = f"""
        SELECT *
        FROM `platam-analytics.scoring.clientes`
        WHERE client_id = '{client_id}'
    """
    result = client.query(query).to_dataframe()

    if result.empty:
        return None

    return result.iloc[0].to_dict()
```

**Ejemplo con PostgreSQL:**
```python
import psycopg2

def get_client_data(client_id: str) -> Dict:
    conn = psycopg2.connect(
        host="tu-host",
        database="platam",
        user="tu-usuario",
        password="tu-password"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes WHERE client_id = %s", (client_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return None

    # Mapear resultado a dict...
    return {...}
```

---

## 📈 Monitoreo y Logs

### Ver logs de la API (si está en Cloud Run)

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=scoring-api" --limit=50
```

### Métricas importantes para monitorear

1. **Latencia:** Tiempo de respuesta (debería ser <2s)
2. **Tasa de error:** % de requests fallidos
3. **Distribución de decisiones:** % Aprobar/Rechazar/Revisar
4. **Alertas:** Probabilidad de default promedio (si sube mucho, hay problema)

---

## 🎨 Personalizar la Lógica de Recomendación

La función `generate_recommendation()` combina scoring + ML.

**Puedes ajustar:**
- Thresholds de decisión (actualmente 40% y 60%)
- Peso del scoring vs ML
- Reglas de excepción (ej: siempre aprobar si score >800)
- Flags adicionales

**Ejemplo - Agregar flag de cliente nuevo:**
```python
if client_data.get('months_as_client', 0) < 6:
    flags.append("⚠️ Cliente nuevo (<6 meses)")
```

---

## 💰 Costos Estimados

**Cloud Run (API intermedia):**
- Primeros 2 millones de requests/mes: GRATIS
- Después: $0.40 USD por millón de requests
- Costo mínimo: $0

**Vertex AI (ya desplegado):**
- n1-standard-2: ~$70 USD/mes (24/7)
- Predicciones: ilimitadas (incluidas)

**Total estimado para 10,000 consultas/mes:**
- Cloud Run: ~$0
- Vertex AI: ~$70
- **Total: ~$70/mes**

---

## 🆘 Troubleshooting

**Error: "Cliente no encontrado"**
- Verifica que `get_client_data()` esté consultando correctamente
- Revisa que el `client_id` exista en tu base de datos

**Error: "Connection to Vertex AI failed"**
- Verifica que `key.json` esté en el directorio
- Verifica que el endpoint `1160748927884984320` esté activo

**Latencia alta (>5s)**
- La primera request es lenta (cold start de Cloud Run)
- Considera aumentar min_instances a 1 en Cloud Run

**Decisiones inconsistentes**
- Verifica que los pesos (peso_platam, peso_experian) estén correctos
- Revisa los thresholds en `generate_recommendation()`

---

## ✅ Checklist de Implementación

- [ ] Ejecutar `python api_scoring_completo.py` localmente
- [ ] Probar endpoint con Postman/curl
- [ ] Conectar función `get_client_data()` a tu base de datos
- [ ] Configurar workflow en n8n
- [ ] Probar con clientes reales
- [ ] Desplegar a Cloud Run (producción)
- [ ] Actualizar URL en n8n
- [ ] Configurar monitoreo y alertas
- [ ] Documentar para el equipo

---

## 📞 Testing Rápido

**Con curl:**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"client_id": "12345"}'
```

**Con Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/predict",
    json={"client_id": "12345"}
)

print(response.json())
```

**Desde n8n webhook:**
```
POST https://tu-n8n.com/webhook/scoring-cliente
{
  "client_id": "12345"
}
```

---

✅ **Con esta integración, desde n8n solo envías el ID del cliente y obtienes una evaluación crediticia completa en un solo request!**
