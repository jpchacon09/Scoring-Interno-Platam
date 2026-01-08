# 🚀 API de Scoring en Cloud Run

## 📍 URL de la API

**Producción:** `https://scoring-api-741488896424.us-central1.run.app`

**Acceso:** Público (sin autenticación)

---

## 🎯 Cómo Usar desde n8n

### Configuración rápida (3 pasos):

#### 1. Webhook Node (Trigger)
```json
{
  "httpMethod": "POST",
  "path": "consultar-scoring"
}
```

#### 2. HTTP Request Node
**Configuración:**
- Method: `POST`
- URL: `https://scoring-api-741488896424.us-central1.run.app/predict`
- Body Content Type: `JSON`
- Body:
```json
{
  "cedula": "{{ $json.cedula }}"
}
```

#### 3. Resultado
Obtienes automáticamente:
```json
{
  "client_info": {
    "cedula": "1006157869",
    "months_as_client": 0,
    "payment_count": 0
  },
  "scoring": {
    "platam_score": 575,
    "experian_score": 715,
    "hybrid_score": 687,
    "hybrid_category": "Bueno"
  },
  "ml_prediction": {
    "probability_default": 0.392,
    "risk_level": "Medio",
    "attention_level": "Atención moderada"
  },
  "recommendation": {
    "action_plan": "Recordatorio preventivo - Seguimiento mensual",
    "priority": "Media",
    "reason": "Riesgo moderado (39.2%) con score bueno",
    "requires_follow_up": true,
    "flags": ["🆕 Cliente muy nuevo (<3 meses)"]
  }
}
```

---

## 📊 Endpoints Disponibles

### 1. **POST /predict** (Principal)
Retorna evaluación completa del cliente

**Request:**
```bash
curl -X POST https://scoring-api-741488896424.us-central1.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"cedula":"1006157869"}'
```

**Response:** Ver arriba

---

### 2. **GET /health**
Verificar estado de la API

**Request:**
```bash
curl https://scoring-api-741488896424.us-central1.run.app/health
```

**Response:**
```json
{
  "status": "healthy",
  "data_loaded": true,
  "vertex_ai": "connected",
  "model": "platam-custom-final",
  "clientes": 1835
}
```

---

### 3. **GET /stats**
Estadísticas de los datos cargados

**Request:**
```bash
curl https://scoring-api-741488896424.us-central1.run.app/stats
```

**Response:**
```json
{
  "total_clientes": 1835,
  "score_promedio": 687.3,
  "score_min": 300,
  "score_max": 950,
  "clientes_con_historial": 1243
}
```

---

### 4. **GET /docs**
Documentación interactiva (Swagger)

URL: https://scoring-api-741488896424.us-central1.run.app/docs

---

## 🔍 Datos Incluidos

La API tiene **1,835 clientes** con:
- ✅ Cédula/NIT
- ✅ Score híbrido calculado
- ✅ Score PLATAM
- ✅ Score Experian normalizado
- ✅ Todas las features de ML

**Fuente:** `data/processed/hybrid_scores.csv`

---

## 📊 Niveles de Atención y Planes de Acción

El modelo predice **riesgo de incumplimiento** para clientes existentes (no aprueba/rechaza nuevos clientes).

### Niveles de Atención (attention_level):

| Prob. Default | Nivel | Descripción |
|--------------|-------|-------------|
| < 20% | **Monitoreo normal** | Cliente confiable, bajo riesgo |
| 20-40% | **Atención moderada** | Seguimiento preventivo |
| 40-60% | **Seguimiento cercano** | Riesgo significativo, contacto prioritario |
| > 60% | **Alerta crítica** | Riesgo muy alto, acción inmediata |

### Planes de Acción (action_plan):

Ejemplos según riesgo y score:

**Riesgo Bajo:**
- "Sin acción - Cliente confiable"
- "Monitoreo rutinario - Buen desempeño"

**Riesgo Moderado:**
- "Recordatorio preventivo - Seguimiento mensual"
- "Contacto preventivo - Evaluar refinanciación"

**Riesgo Alto:**
- "Seguimiento cercano - Limitar exposición"
- "Cobranza inmediata - Restringir nuevos créditos"

### Prioridad (priority):

- **Ninguna**: Sin acción requerida
- **Baja**: Monitoreo rutinario
- **Media**: Seguimiento preventivo
- **Alta**: Contacto prioritario
- **Crítica**: Acción inmediata

---

## 🎨 Ejemplo de Workflow en n8n

```
┌─────────────────────────────────────────────────────────┐
│ 1. Webhook recibe                                       │
│    {"cedula": "1006157869"}                             │
│                                                         │
│ 2. HTTP Request a Cloud Run                            │
│    POST /predict                                        │
│                                                         │
│ 3. Response completa                                    │
│    • Score híbrido: 687                                 │
│    • Prob default: 39.2%                                │
│    • Nivel atención: Atención moderada                  │
│    • Plan: Recordatorio preventivo                      │
│                                                         │
│ 4. Switch por prioridad                                 │
│    IF priority = "Crítica" OR "Alta"                    │
│       → Crear tarea de cobranza urgente                 │
│       → Notificar al equipo                             │
│    ELSE IF priority = "Media"                           │
│       → Programar seguimiento en 7 días                 │
│       → Enviar recordatorio automático                  │
│    ELSE                                                 │
│       → Monitoreo rutinario (sin acción)                │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ Características

### Ventajas
- ✅ **No requiere autenticación** - Listo para usar
- ✅ **Sin límite de requests** - Hasta 1000 requests simultáneos
- ✅ **Escalado automático** - De 0 a 10 instancias
- ✅ **Latencia baja** - ~500ms por request
- ✅ **Disponibilidad 24/7** - Always on
- ✅ **HTTPS incluido** - Seguro por defecto

### Datos
- 📊 **1,835 clientes** precargados
- 🔄 **Se puede actualizar** subiendo nuevo CSV
- 🎯 **17 features ML** + scores híbridos

---

## 💰 Costos

**Cloud Run (pago por uso):**
- Primeros 2M requests/mes: **GRATIS**
- Después: $0.40 USD por millón de requests
- Memoria 1GB, 1 vCPU

**Vertex AI (ya desplegado):**
- n1-standard-2: ~$70 USD/mes (24/7)

**Total para 1,000 requests/día:**
- Cloud Run: ~$0/mes (dentro del free tier)
- Vertex AI: ~$70/mes
- **Total: ~$70/mes**

---

## 🔧 Actualizar Datos

Para actualizar el CSV con nuevos clientes:

```bash
# 1. Actualizar CSV local
# Editar: data/processed/hybrid_scores.csv

# 2. Reconstruir imagen
cd "/Users/jpchacon/Scoring Interno"
gcloud builds submit --tag gcr.io/platam-analytics/scoring-api:v2

# 3. Redesplegar
gcloud run deploy scoring-api \
  --image gcr.io/platam-analytics/scoring-api:v2 \
  --region us-central1 \
  --project platam-analytics

# Tarda ~2-3 minutos
```

---

## 📱 Prueba Rápida

### Desde terminal:
```bash
curl -X POST https://scoring-api-741488896424.us-central1.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"cedula":"74858339"}'
```

### Desde Postman:
```
POST https://scoring-api-741488896424.us-central1.run.app/predict
Headers: Content-Type: application/json
Body: {"cedula": "74858339"}
```

### Desde Python:
```python
import requests

response = requests.post(
    "https://scoring-api-741488896424.us-central1.run.app/predict",
    json={"cedula": "1006157869"}
)

result = response.json()
print(f"Score: {result['scoring']['hybrid_score']}")
print(f"Riesgo default: {result['ml_prediction']['probability_default']*100:.1f}%")
print(f"Nivel atención: {result['ml_prediction']['attention_level']}")
print(f"Plan de acción: {result['recommendation']['action_plan']}")
print(f"Prioridad: {result['recommendation']['priority']}")
```

---

## 🆘 Troubleshooting

**Error: "Cliente no encontrado"**
- Verifica que la cédula esté en el CSV
- Hay 1,835 clientes disponibles
- Consulta /stats para ver estadísticas

**Error: 500 Internal Server Error**
- Revisa logs: https://console.cloud.google.com/run?project=platam-analytics
- Verifica que Vertex AI endpoint esté activo

**Latencia alta (>3s)**
- Primera request es lenta (cold start)
- Requests subsecuentes son rápidas (~500ms)

---

## 📊 Monitoreo

### Cloud Run Dashboard:
https://console.cloud.google.com/run/detail/us-central1/scoring-api?project=platam-analytics

### Métricas disponibles:
- Request count
- Latency (p50, p95, p99)
- Error rate
- Instance count
- Memory usage

---

## ✅ Checklist de Integración n8n

- [ ] Crear workflow en n8n
- [ ] Agregar Webhook trigger
- [ ] Configurar HTTP Request con URL de Cloud Run
- [ ] Probar con cédula real
- [ ] Agregar lógica de enrutamiento (Switch node)
- [ ] Configurar acciones según decisión
- [ ] Probar flujo completo end-to-end

---

**¡Listo para usar!** 🚀

La API está disponible 24/7 en:
`https://scoring-api-741488896424.us-central1.run.app`
