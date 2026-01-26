# 🏗️ Arquitectura Completa - Sistema de Scoring en Tiempo Real

---

## 📐 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EQUIPO DE TECH                                   │
│                                                                          │
│  Envía triggers cuando ocurren eventos:                                 │
│  • late_1, late_7, late_14, late_25, late_34, late_55...                │
│  • new_loan                                                             │
│  • payment                                                              │
│                                                                          │
│  Formato: {"client_id": "1702", "trigger": "late_7"}                   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                                │ HTTP POST
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          N8N WORKFLOW                                    │
│  Webhook: /scoring-trigger                                              │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   NODO 1: Select Cliente │    │  NODO 2: Select Pagos    │
│                          │    │                          │
│  SELECT _ID, cedula,     │    │  SELECT p_payment_date,  │
│    cl_city, ...          │    │    days_past_due,        │
│  FROM wp_jet_cct_clientes│    │    p_payment_amount      │
│  WHERE _ID = 1702        │    │  FROM wp_jet_cct_pagos   │
└─────────────┬────────────┘    │  LEFT JOIN prestamos     │
              │                 │  WHERE p_cl_id = 1702    │
              │                 └─────────────┬────────────┘
              │                               │
              │                ┌──────────────┘
              │                │
              │                ▼
              │   ┌──────────────────────────┐
              │   │ NODO 3: Select Préstamos │
              │   │                          │
              │   │  SELECT loan_id,         │
              │   │    l_status,             │
              │   │    days_past_due,        │
              │   │    is_active,            │
              │   │    is_in_default         │
              │   │  FROM wp_jet_cct_prestamos│
              │   │  WHERE l_cl_id = 1702    │
              │   └─────────────┬────────────┘
              │                 │
              └─────────────────┴─────────────┐
                                              │
                                              ▼
                          ┌──────────────────────────────┐
                          │  NODO 4: Function Node       │
                          │  (Preparar Datos)            │
                          │                              │
                          │  const cliente = ...         │
                          │  const pagos = ...           │
                          │                              │
                          │  return {                    │
                          │    cedula: "1116614340",     │
                          │    client_data: {...},       │
                          │    payments: [...],          │
                          │    payment_plans: []         │
                          │  }                           │
                          └──────────────┬───────────────┘
                                         │
                                         │ HTTP POST
                                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOOGLE CLOUD FUNCTION                                 │
│                    calculate-scores                                      │
│                                                                          │
│  Region: us-central1                                                    │
│  Runtime: Python 3.11                                                   │
│  Memory: 1GB, Timeout: 60s                                              │
│                                                                          │
│  Recibe:                                                                │
│  {                                                                      │
│    "cedula": "1116614340",                                              │
│    "client_data": {"months_as_client": 3, "ciudad": "MANI"},           │
│    "payments": [{...}, {...}],                                          │
│    "payment_plans": []                                                  │
│  }                                                                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│      AWS S3              │    │   CÁLCULO PLATAM         │
│  fft-analytics-data-lake │    │                          │
│                          │    │  1. Payment Performance  │
│  Descarga:               │    │     (600 pts)            │
│  hcpn_1116614340.json    │    │                          │
│                          │    │  2. Payment Plan         │
│  Extrae:                 │    │     (150 pts)            │
│  • experian_score: 750   │    │                          │
│  • edad: 32              │    │  3. Deterioration        │
│  • genero: M             │    │     (250 pts)            │
│  • cuota_mensual: 450K   │    │                          │
│  • creditos_vigentes: 5  │    │  PLATAM Score = 730.5    │
│  • creditos_mora: 1      │    │                          │
│  • hist_neg_12m: 0       │    │                          │
└─────────────┬────────────┘    └─────────────┬────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │    CÁLCULO HÍBRIDO           │
                │                              │
                │  Pesos dinámicos por:        │
                │  • Antigüedad del cliente    │
                │  • Cantidad de pagos         │
                │                              │
                │  Hybrid Score =              │
                │    (PLATAM × 0.6) +          │
                │    (Experian × 0.4)          │
                │                              │
                │  = 745.2                     │
                └──────────────┬───────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      VERTEX AI ENDPOINT                                  │
│                      ID: 7891061911641391104                             │
│                                                                          │
│  Modelo: XGBoost 2.0.3 (v2.2)                                           │
│  Features: 22 (PLATAM + Experian + Demografía + Payment History)        │
│                                                                          │
│  Input:                                                                 │
│  [730.5, 750, 450, 150, 130.5, 25, 3, 0.8, 0.2, 0.6, 0.4,             │
│   False, False, False, 0, 1, 32, 0, 450000, 5, 1, 0]                   │
│                                                                          │
│  Output:                                                                │
│  • Probability Default: 0.12 (12%)                                      │
│  • Probability No Default: 0.88 (88%)                                   │
│  • Risk Level: "Bajo"                                                   │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ Respuesta
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLOUD FUNCTION RESPONSE                               │
│                                                                          │
│  {                                                                      │
│    "status": "success",                                                 │
│    "cedula": "1116614340",                                              │
│    "platam_score": 730.5,                                               │
│    "hybrid_score": 745.2,                                               │
│    "ml_probability_default": 0.12,                                      │
│    "ml_probability_no_default": 0.88,                                   │
│    "ml_risk_level": "Bajo",                                             │
│    "peso_platam": 0.6,                                                  │
│    "peso_hcpn": 0.4,                                                    │
│    "score_payment_performance": 450.0,                                  │
│    "score_payment_plan": 150.0,                                         │
│    "score_deterioration": 130.5,                                        │
│    "payment_count": 25,                                                 │
│    "pct_early": 0.8,                                                    │
│    "pct_late": 0.2,                                                     │
│    "processing_time_ms": 2847,                                          │
│    "hcpn_found": true                                                   │
│  }                                                                      │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ Regresa a n8n
                                ▼
                ┌──────────────────────────────┐
                │  NODO 6: HTTP Request        │
                │  (Actualizar WordPress)      │
                │                              │
                │  POST https://platampay.com/ │
                │    wp-json/jet-cct/          │
                │    clientes/1702             │
                │                              │
                │  Body: {                     │
                │    "cl_platam_score": 730.5, │
                │    "cl_hybrid_score": 745.2, │
                │    "cl_ml_risk_level": "Bajo"│
                │    ...                       │
                │  }                           │
                └──────────────┬───────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    WORDPRESS / MYSQL                                     │
│                                                                          │
│  UPDATE wp_jet_cct_clientes                                             │
│  SET                                                                    │
│    cl_platam_score = 730.5,                                             │
│    cl_hybrid_score = 745.2,                                             │
│    cl_ml_probability_default = 0.12,                                    │
│    cl_ml_probability_no_default = 0.88,                                 │
│    cl_ml_risk_level = 'Bajo',                                           │
│    cl_hybrid_weight_platam = 0.6,                                       │
│    cl_hybrid_weight_experian = 0.4,                                     │
│    cl_ml_modified = UNIX_TIMESTAMP()                                    │
│  WHERE _ID = 1702                                                       │
│                                                                          │
│  ✅ Cliente actualizado en tiempo real                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Datos Detallado

### 1. TRIGGER (Equipo de Tech → n8n)

```json
POST https://n8n.platam.com/webhook/scoring-trigger
{
  "client_id": "1702",
  "trigger": "late_7"
}
```

### 2. CONSULTA MySQL (n8n → MySQL)

**Query 1: Cliente**
```sql
SELECT _ID, cl_doc_number as cedula, cl_city,
       TIMESTAMPDIFF(MONTH, cct_created, NOW()) as months_as_client
FROM wp_jet_cct_clientes
WHERE _ID = 1702
```

**Resultado:**
```json
{
  "_ID": 1702,
  "cedula": "1116614340",
  "ciudad": "MANI (C/NARE)",
  "months_as_client": 3
}
```

**Query 2: Pagos**
```sql
SELECT p_payment_date, p_payment_amount,
       COALESCE(DATEDIFF(FROM_UNIXTIME(p.p_payment_date),
                         FROM_UNIXTIME(l.l_due_date)), 0) as days_past_due
FROM wp_jet_cct_pagos p
LEFT JOIN wp_jet_cct_prestamos l ON p.p_l_id = l._ID
WHERE p.p_cl_id = 1702
```

**Resultado:**
```json
[
  {"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000},
  {"payment_date": "2023-10-15", "days_past_due": 2, "payment_amount": 1500000},
  ...
]
```

### 3. PREPARAR DATOS (n8n Function Node)

```javascript
return {
  json: {
    cedula: "1116614340",
    client_data: {
      months_as_client: 3,
      ciudad: "MANI (C/NARE)"
    },
    payments: [
      {"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000},
      ...
    ],
    payment_plans: []
  }
}
```

### 4. CLOUD FUNCTION (n8n → GCP)

**Request:**
```json
POST https://calculate-scores-XXXX.run.app
{
  "cedula": "1116614340",
  "client_data": {...},
  "payments": [...],
  "payment_plans": []
}
```

**Procesamiento interno:**

1. **Descarga HCPN de S3:**
   ```python
   hcpn_data = download_hcpn_from_s3("1116614340")
   # Descarga: s3://fft-analytics-data-lake/ppay/prod/hcpn_1116614340.json
   ```

2. **Extrae demografía:**
   ```python
   {
     'experian_score': 750,
     'edad': 32,
     'genero': 'M',
     'cuota_mensual': 450000,
     'creditos_vigentes': 5,
     'creditos_mora': 1,
     'hist_neg_12m': 0
   }
   ```

3. **Calcula PLATAM Score:**
   ```python
   payment_performance = 450.0  # De 600 pts
   payment_plan = 150.0         # De 150 pts
   deterioration = 130.5        # De 250 pts
   platam_score = 730.5         # Total
   ```

4. **Calcula Hybrid Score:**
   ```python
   # Cliente con 3 meses → categoría "muy_nuevo"
   # peso_platam = 0.30 base + ajustes
   # peso_hcpn = 0.70

   hybrid = (730.5 × 0.6) + (750 × 0.4) = 745.2
   ```

5. **Predicción ML (Vertex AI):**
   ```python
   # Preparar 22 features
   instance = [
     730.5,    # platam_score
     750,      # experian_score
     450.0,    # score_payment_performance
     150.0,    # score_payment_plan
     130.5,    # score_deterioration
     25,       # payment_count
     3,        # months_as_client
     0.8,      # pct_early
     0.2,      # pct_late
     0.6,      # peso_platam
     0.4,      # peso_hcpn
     False,    # tiene_plan_activo
     False,    # tiene_plan_default
     False,    # tiene_plan_pendiente
     0,        # num_planes
     1,        # genero_encoded (M=1)
     32,       # edad
     0,        # ciudad_encoded
     450000,   # cuota_mensual
     5,        # creditos_vigentes
     1,        # creditos_mora
     0         # hist_neg_12m
   ]

   prediction = endpoint.predict(instances=[instance])
   # → probability_default: 0.12 (12%)
   # → risk_level: "Bajo"
   ```

**Response:**
```json
{
  "status": "success",
  "cedula": "1116614340",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_probability_no_default": 0.88,
  "ml_risk_level": "Bajo",
  "peso_platam": 0.6,
  "peso_hcpn": 0.4,
  "processing_time_ms": 2847,
  "hcpn_found": true
}
```

### 5. ACTUALIZAR WordPress (n8n → WordPress REST API)

```json
POST https://platampay.com/wp-json/jet-cct/clientes/1702
{
  "cl_platam_score": "730.5",
  "cl_hybrid_score": "745.2",
  "cl_ml_probability_default": "0.12",
  "cl_ml_probability_no_default": "0.88",
  "cl_ml_risk_level": "Bajo",
  "cl_hybrid_weight_platam": "0.6",
  "cl_hybrid_weight_experian": "0.4",
  "cl_ml_modified": "1738006845"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "_ID": 1702,
    "cl_platam_score": "730.5",
    "cl_hybrid_score": "745.2",
    ...
  }
}
```

---

## 📊 Componentes del Sistema

### Google Cloud Platform

| Componente | Detalles |
|------------|----------|
| **Project** | platam-analytics |
| **Cloud Function** | calculate-scores (Gen2, Python 3.11) |
| **Vertex AI Endpoint** | 7891061911641391104 |
| **Región** | us-central1 |
| **Modelo ML** | XGBoost 2.0.3 (v2.2) |

### AWS S3

| Componente | Detalles |
|------------|----------|
| **Bucket** | fft-analytics-data-lake |
| **Prefix** | ppay/prod/ |
| **Archivos** | hcpn_{cedula}.json |
| **Acceso** | IAM credentials (env vars) |

### MySQL / WordPress

| Componente | Detalles |
|------------|----------|
| **Tabla Clientes** | wp_jet_cct_clientes |
| **Tabla Pagos** | wp_jet_cct_pagos |
| **Tabla Préstamos** | wp_jet_cct_prestamos |
| **REST API** | https://platampay.com/wp-json/jet-cct/clientes/{ID} |

### n8n

| Componente | Detalles |
|------------|----------|
| **Workflow** | ActualizarML - Scoring en Tiempo Real |
| **Nodos totales** | 7 |
| **Webhook** | /scoring-trigger |
| **MySQL Connection** | Ya configurado |

---

## ⚡ Performance

### Tiempos Estimados

| Etapa | Tiempo |
|-------|--------|
| n8n → MySQL queries (3 queries) | ~300ms |
| n8n → Preparar datos | ~50ms |
| Cloud Function → S3 download | ~500ms |
| Cloud Function → Cálculo PLATAM | ~100ms |
| Cloud Function → Vertex AI prediction | ~1500ms |
| Cloud Function → Response | ~50ms |
| n8n → WordPress update | ~300ms |
| **TOTAL** | **~3 segundos** |

### Recursos

| Recurso | Uso |
|---------|-----|
| **Cloud Function Memory** | ~200-300MB (de 1GB asignado) |
| **CPU** | ~15-20% |
| **Network (S3 download)** | ~10-50KB |
| **Network (Vertex AI)** | ~1-2KB |

---

## 🔐 Seguridad

### Credenciales Manejadas

| Credencial | Ubicación | Acceso |
|------------|-----------|--------|
| **AWS S3 Keys** | Cloud Function env vars | Solo Cloud Function |
| **MySQL** | n8n credentials | Solo n8n |
| **WordPress REST API** | n8n credentials | Solo n8n |
| **Vertex AI** | GCP Service Account | Solo Cloud Function |

### Separación de Responsabilidades

```
n8n:
  ✅ Tiene acceso a MySQL (lectura)
  ✅ Tiene acceso a WordPress REST API (escritura)
  ❌ NO tiene acceso a S3
  ❌ NO tiene acceso a Vertex AI

Cloud Function:
  ✅ Tiene acceso a S3 (lectura HCPN)
  ✅ Tiene acceso a Vertex AI (predicción)
  ❌ NO tiene acceso a MySQL
  ❌ NO tiene acceso a WordPress
```

**Beneficio:** Si Cloud Function es comprometida, no puede acceder a la base de datos principal.

---

## 📈 Escalabilidad

### Triggers Soportados

```python
triggers = [
  'late_1', 'late_7', 'late_14', 'late_25', 'late_34',
  'late_55', 'late_64', 'late_90', 'late_120', 'late_150',
  'new_loan',
  'payment'
]
```

### Concurrencia

- **Cloud Function:** Auto-scaling (max 100 instancias concurrentes)
- **Vertex AI:** Endpoint soporta ~10 QPS
- **n8n:** Workflows concurrentes según plan

### Límites

| Recurso | Límite |
|---------|--------|
| **Cloud Function concurrent executions** | 100 |
| **Cloud Function max timeout** | 60s |
| **Vertex AI QPS** | ~10 |
| **S3 requests/second** | ~3500 |
| **WordPress API rate limit** | Variable |

---

## 🎯 Casos de Uso

### 1. Cliente paga tarde

```
Trigger: {"client_id": "1702", "trigger": "late_7"}
→ Sistema calcula nuevo score (probablemente más bajo)
→ Actualiza WordPress
→ Analista ve nuevo score en dashboard
```

### 2. Cliente paga a tiempo

```
Trigger: {"client_id": "1702", "trigger": "payment"}
→ Sistema calcula nuevo score (probablemente más alto)
→ Actualiza WordPress
→ Sistema de aprobación automática evalúa nuevos límites
```

### 3. Nuevo préstamo

```
Trigger: {"client_id": "1702", "trigger": "new_loan"}
→ Sistema calcula score con nuevo préstamo
→ Actualiza WordPress
→ Monitoreo de riesgo actualizado
```

---

## ✅ Ventajas de esta Arquitectura

1. **Separación de Responsabilidades**
   - n8n solo orquesta y consulta
   - Cloud Function solo calcula
   - Cada servicio tiene credenciales mínimas necesarias

2. **Performance**
   - Cálculos en paralelo donde es posible
   - S3 descarga solo archivo necesario (no batch)
   - Vertex AI endpoint pre-calentado

3. **Seguridad**
   - Cloud Function sin acceso a MySQL
   - Credenciales AWS en env vars (no código)
   - WordPress REST API con autenticación

4. **Escalabilidad**
   - Cloud Function auto-scaling
   - Vertex AI endpoint escalable
   - n8n workflows independientes

5. **Mantenibilidad**
   - Código modular
   - Logs centralizados en GCP
   - Fácil debugging (cada nodo de n8n visible)

6. **Costo**
   - Cloud Function solo cobra por uso
   - S3 solo descarga lo necesario
   - Vertex AI solo predice cuando es requerido

---

**Creado:** 2026-01-26
**Versión:** 1.0 Final
**Status:** ✅ READY FOR DEPLOYMENT
