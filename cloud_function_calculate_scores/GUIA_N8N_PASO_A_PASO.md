# 🎯 Guía n8n: Integración Paso a Paso

## 📋 Flujo Completo en n8n

```
1️⃣ Webhook
   Recibe: {"client_id": "1120", "trigger": "late_7"}
   ↓
2️⃣ Select rows from MySQL (ya lo tienes)
   Consulta cliente + pagos + planes
   ↓
3️⃣ HTTP Request → Cloud Function
   Envía datos, recibe scores calculados
   ↓
4️⃣ HTTP Request → WordPress REST API
   Actualiza cliente con los scores
   ↓
5️⃣ Done ✅
```

---

## Paso 1: Webhook (Ya lo tienes)

Tu webhook ya está configurado para recibir:
```json
{
  "client_id": "1068",
  "trigger": "late_7"
}
```

✅ **No cambiar nada aquí**

---

## Paso 2: Consultar MySQL (Necesito entender tu estructura)

### ❓ Pregunta para ti:

**¿Cómo tienes configurada la consulta de MySQL actualmente?**

Necesito saber:

1. **Tabla de clientes:**
   - Nombre: `wp_jet_cct_clientes` ✅
   - Columnas que usas: `_ID`, `cl_cedula`, `cl_nombre`, `cl_ciudad`, `cl_edad`, `cl_genero`, ...?

2. **Tabla de pagos:**
   - Nombre: ¿?
   - Columnas: `payment_date`, `days_past_due` (¿o calculas esto?), ...?

3. **Tabla de planes de pago:**
   - Nombre: ¿?
   - Columnas: `plan_status`, `plan_start_date`, ...?

### Ejemplo de lo que necesitamos obtener:

**Consulta 1: Datos del cliente**
```sql
SELECT
  _ID,
  cl_cedula,
  cl_nombre,
  cl_edad,
  cl_ciudad,
  cl_genero,
  cl_months_as_client,
  cl_experian_score,
  cl_cuota_mensual,
  cl_creditos_vigentes,
  cl_creditos_mora,
  cl_hist_neg_12m
FROM wp_jet_cct_clientes
WHERE _ID = {{ $json.client_id }}
```

**Consulta 2: Historial de pagos (últimos 100)**
```sql
SELECT
  payment_date,
  due_date,
  DATEDIFF(payment_date, due_date) as days_past_due
FROM tu_tabla_pagos
WHERE client_id = {{ $('Select rows from a table').item.json._ID }}
ORDER BY payment_date DESC
LIMIT 100
```

**Consulta 3: Planes de pago**
```sql
SELECT
  plan_status,
  plan_start_date,
  plan_end_date
FROM tu_tabla_planes
WHERE client_id = {{ $('Select rows from a table').item.json._ID }}
ORDER BY plan_start_date DESC
```

**👉 ¿Puedes compartir los nombres de tus tablas y columnas principales?**

---

## Paso 3: HTTP Request a Cloud Function

### Configuración del nodo HTTP Request:

**Name:** `Calcular Scores (Cloud Function)`

**Method:** `POST`

**URL:**
```
TU_URL_CLOUD_FUNCTION_AQUI
```
(La obtienes después del deployment)

**Authentication:** None

**Body Content Type:** `JSON`

**Specify Body:** `Using JSON`

**JSON Body:**
```json
{
  "client_data": {
    "cedula": "{{ $('Select rows from a table').item.json.cl_cedula }}",
    "months_as_client": "{{ $('Select rows from a table').item.json.cl_months_as_client }}",
    "experian_score": "{{ $('Select rows from a table').item.json.cl_experian_score }}",
    "edad": "{{ $('Select rows from a table').item.json.cl_edad }}",
    "ciudad": "{{ $('Select rows from a table').item.json.cl_ciudad }}",
    "genero": "{{ $('Select rows from a table').item.json.cl_genero }}",
    "cuota_mensual": "{{ $('Select rows from a table').item.json.cl_cuota_mensual }}",
    "creditos_vigentes": "{{ $('Select rows from a table').item.json.cl_creditos_vigentes }}",
    "creditos_mora": "{{ $('Select rows from a table').item.json.cl_creditos_mora }}",
    "hist_neg_12m": "{{ $('Select rows from a table').item.json.cl_hist_neg_12m }}"
  },
  "payments": "{{ $('Select payments').json }}",
  "payment_plans": "{{ $('Select plans').json }}"
}
```

**👉 Ajusta los nombres de columnas según tu base de datos**

**Response esperado:**
```json
{
  "status": "success",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_probability_no_default": 0.88,
  "ml_risk_level": "Bajo",
  "peso_platam": 0.6,
  "peso_hcpn": 0.4,
  "score_payment_performance": 450.0,
  "score_payment_plan": 150.0,
  "score_deterioration": 130.5,
  "processing_time_ms": 1847
}
```

---

## Paso 4: HTTP Request a WordPress REST API (Ya lo tienes)

### Configuración del nodo HTTP Request:

**Name:** `Actualizar Cliente (WordPress)`

**Method:** `POST`

**URL:**
```
https://platampay.com/wp-json/jet-cct/clientes/{{ $('Select rows from a table').item.json._ID }}
```

**Authentication:** (la que ya tienes configurada)

**Body Content Type:** `JSON`

**Specify Body:** `Using JSON`

**JSON Body:**
```json
{
  "cl_platam_score": "{{ $('Calcular Scores (Cloud Function)').json.platam_score }}",
  "cl_hybrid_score": "{{ $('Calcular Scores (Cloud Function)').json.hybrid_score }}",
  "cl_ml_probability_default": "{{ $('Calcular Scores (Cloud Function)').json.ml_probability_default }}",
  "cl_ml_risk_level": "{{ $('Calcular Scores (Cloud Function)').json.ml_risk_level }}",
  "cl_score_payment_performance": "{{ $('Calcular Scores (Cloud Function)').json.score_payment_performance }}",
  "cl_score_payment_plan": "{{ $('Calcular Scores (Cloud Function)').json.score_payment_plan }}",
  "cl_score_deterioration": "{{ $('Calcular Scores (Cloud Function)').json.score_deterioration }}",
  "cl_peso_platam": "{{ $('Calcular Scores (Cloud Function)').json.peso_platam }}",
  "cl_peso_hcpn": "{{ $('Calcular Scores (Cloud Function)').json.peso_hcpn }}",
  "cl_last_update_trigger": "{{ $json.trigger }}",
  "cl_payment_count": "{{ $('Calcular Scores (Cloud Function)').json.payment_count }}",
  "cl_pct_early": "{{ $('Calcular Scores (Cloud Function)').json.pct_early }}",
  "cl_pct_late": "{{ $('Calcular Scores (Cloud Function)').json.pct_late }}"
}
```

**👉 Asegúrate que tu REST API de WordPress acepta estos campos**

---

## 🧪 Testing

### Test 1: Cloud Function aislada

```bash
curl -X POST TU_URL_CLOUD_FUNCTION \
  -H "Content-Type: application/json" \
  -d '{
    "client_data": {
      "cedula": "128282",
      "months_as_client": 8,
      "experian_score": 715,
      "edad": 32,
      "ciudad": "Barranquilla",
      "genero": "M",
      "cuota_mensual": 450000,
      "creditos_vigentes": 5,
      "creditos_mora": 1,
      "hist_neg_12m": 0
    },
    "payments": [
      {"payment_date": "2026-01-20", "days_past_due": 7},
      {"payment_date": "2025-12-15", "days_past_due": 2},
      {"payment_date": "2025-11-20", "days_past_due": 0}
    ],
    "payment_plans": [
      {"plan_status": "active", "plan_start_date": "2025-11-01"}
    ]
  }'
```

**Verificar que retorna:**
```json
{
  "status": "success",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  ...
}
```

### Test 2: Flujo completo en n8n

1. Click "Execute Workflow" en n8n
2. Enviar test trigger:
   ```json
   {
     "client_id": "1068",
     "trigger": "test"
   }
   ```
3. Ver que cada nodo ejecuta correctamente
4. Verificar en WordPress/MySQL que se actualizó

---

## 📊 Diagrama Visual del Flujo n8n

```
┌─────────────────────────────────────────────────────────────┐
│ Webhook                                                     │
│ Input: {"client_id": "1068", "trigger": "late_7"}          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Select rows from MySQL (Cliente)                           │
│ Query: SELECT * FROM wp_jet_cct_clientes WHERE _ID = 1068  │
│ Output: {_ID: 1068, cl_cedula: "...", cl_edad: 32, ...}    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Select rows from MySQL (Pagos)                             │
│ Query: SELECT * FROM pagos WHERE client_id = 1068          │
│ Output: [{payment_date: "...", days_past_due: 7}, ...]     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ Select rows from MySQL (Planes)                            │
│ Query: SELECT * FROM planes WHERE client_id = 1068         │
│ Output: [{plan_status: "active", ...}, ...]                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP Request → Cloud Function                              │
│ POST https://.../calculate-scores                          │
│ Body: {client_data: {...}, payments: [...], plans: [...]}  │
│ Output: {platam_score: 730.5, hybrid_score: 745.2, ...}    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP Request → WordPress REST API                          │
│ POST https://platampay.com/wp-json/jet-cct/clientes/1068   │
│ Body: {cl_platam_score: 730.5, cl_hybrid_score: 745.2, ...}│
│ Output: {success: true, updated: {...}}                    │
└─────────────────────────────────────────────────────────────┘
```

---

## ❓ Preguntas para Configurar Correctamente

**Para poder ayudarte mejor, necesito saber:**

### 1. Estructura de tu base de datos:

**Tabla de pagos:**
- Nombre de la tabla: `_____`
- Columna de fecha de pago: `_____`
- Columna de fecha de vencimiento: `_____`
- ¿Tienes `days_past_due` calculado? Sí / No
- Si no, ¿cómo se calcula?: `_____`

**Tabla de planes de pago:**
- Nombre de la tabla: `_____`
- Columna de estado del plan: `_____ `
- Posibles valores de estado: `active`, `completed`, `defaulted`, ...?

**Tabla de clientes:**
- ¿Tienes columnas para guardar los scores? Sí / No
- Si no, ¿las creamos? Sí / No
- Nombres de columnas: `cl_platam_score`, `cl_hybrid_score`, ...?

### 2. Tu REST API de WordPress:

**¿Acepta cualquier campo custom en el POST?**
- Ejemplo: Si envío `{"cl_platam_score": 730.5}`, ¿actualiza esa columna? Sí / No

**¿Requiere autenticación?**
- Tipo: Basic Auth / Bearer Token / API Key / Ninguna

**¿Tienes la URL exacta?**
- URL: `https://platampay.com/wp-json/jet-cct/clientes/{ID}`

### 3. Conexión MySQL en n8n:

**¿Ya tienes guardada una conexión MySQL en n8n?**
- Sí / No
- Nombre de la conexión: `_____`

---

## 🎯 Próximos Pasos

**Una vez que me respondas las preguntas, yo:**

1. Ajusto el JSON body del HTTP Request con tus columnas exactas
2. Te doy las queries SQL específicas para tus tablas
3. Verificamos que tu REST API acepta los campos
4. Desplegamos la Cloud Function
5. Probamos todo el flujo end-to-end

**¿Listo para continuar?** 🚀

Dame los nombres de tus tablas y columnas, y configuramos todo en 10 minutos!
