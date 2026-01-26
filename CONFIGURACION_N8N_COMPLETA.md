# 🎯 Configuración Completa n8n - Cliente ID 1702

## 📊 Estructura de Datos Identificada

### Cliente (wp_jet_cct_clientes):
- **ID interno:** `_ID` = 1702
- **Cédula:** `cl_doc_number` = "1116614340"
- **Nombre:** `cl_first_name` + `cl_last_name`
- **Ciudad:** `cl_city`

### Pagos (tabla de pagos):
- Relacionar por: `p_cl_id` = 1702
- Campos: `p_payment_date`, `p_payment_amount`, `p_penalty_payment`

### Préstamos (tabla de préstamos):
- Relacionar por: `l_cl_id` = 1702
- Campos: `l_status`, `l_due_date`, `l_last_payment_date`, `l_balance_principal`

### HCPN (Experian):
- **Archivo S3:** `hcpn_1116614340.json` (por cédula)
- **O tabla MySQL:** `export-historial_credito`
- Relacionar por: `hcpn_id_data_identificacion_numero` = "1116614340"
- **Campos importantes:**
  - `hcpn_score_experian_puntaje` → Score Experian
  - `hcpn_edad` o calcular de birth_date → Edad
  - `hcpn_genero` → Género
  - `hcpn_cuota_total` → Cuota mensual
  - `hcpn_creditos_principal_credito_vigentes` → Créditos vigentes
  - `hcpn_creditos_principal_creditos_actuales_negativos` → Créditos en mora
  - `hcpn_creditos_principal_hist_neg_ult_12_meses` → Historial negativo 12m

---

## 🔄 Flujo Completo en n8n

```
1. Webhook
   ↓
2. Select Cliente (MySQL)
   ↓
3. Select Pagos (MySQL)
   ↓
4. Select Préstamos (MySQL)
   ↓
5. Select HCPN (MySQL) ← NUEVO
   ↓
6. Preparar Datos para Cloud Function
   ↓
7. HTTP Request → Cloud Function
   ↓
8. HTTP Request → WordPress REST API
   ↓
9. Done ✅
```

---

## 📝 Configuración de Nodos n8n

### Nodo 1: Webhook (Ya lo tienes)
**Configuración:**
- Path: `up_scoring`
- HTTP Method: POST
- Response: Immediately

**Input esperado:**
```json
{
  "client_id": "1702",
  "trigger": "late_7"
}
```

---

### Nodo 2: Select Cliente
**Node Type:** MySQL (usando tu conexión existente)

**Query:**
```sql
SELECT
  _ID,
  cl_doc_number,
  cl_first_name,
  cl_last_name,
  cl_city,
  cl_cupo,
  cl_cupo_disponible
FROM wp_jet_cct_clientes
WHERE _ID = {{ $json.client_id }}
LIMIT 1
```

**Output esperado:**
```json
{
  "_ID": 1702,
  "cl_doc_number": "1116614340",
  "cl_first_name": "ANGELA YARITZA",
  "cl_last_name": "DEVIA CIERRA",
  "cl_city": "MANI (C/NARE)",
  ...
}
```

---

### Nodo 3: Select Pagos
**Node Type:** MySQL

**Query:**
```sql
SELECT
  p_payment_date,
  p_payment_amount,
  p_penalty_payment,
  p_status,
  p_type
FROM tu_tabla_pagos
WHERE p_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY p_payment_date DESC
LIMIT 100
```

**⚠️ IMPORTANTE:** Necesitamos calcular `days_past_due`. Dos opciones:

**Opción A: Si tienes `p_due_date` en la tabla:**
```sql
SELECT
  p_payment_date,
  p_due_date,
  DATEDIFF(FROM_UNIXTIME(p_payment_date), FROM_UNIXTIME(p_due_date)) as days_past_due,
  p_payment_amount,
  p_penalty_payment
FROM tu_tabla_pagos
WHERE p_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY p_payment_date DESC
LIMIT 100
```

**Opción B: Calcular desde préstamo (si cada pago está vinculado a un préstamo):**
```sql
SELECT
  p.p_payment_date,
  l.l_due_date,
  DATEDIFF(FROM_UNIXTIME(p.p_payment_date), FROM_UNIXTIME(l.l_due_date)) as days_past_due,
  p.p_payment_amount,
  p.p_penalty_payment
FROM tu_tabla_pagos p
LEFT JOIN tu_tabla_prestamos l ON p.p_l_id = l._ID
WHERE p.p_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY p.p_payment_date DESC
LIMIT 100
```

**👉 ¿Cuál opción aplica para ti?**

---

### Nodo 4: Select Préstamos
**Node Type:** MySQL

**Query:**
```sql
SELECT
  l_status,
  l_due_date,
  l_last_payment_date,
  l_principal,
  l_balance_principal,
  l_balance_total,
  l_disbursement_date,
  CASE
    WHEN l_status = 'Pagado' THEN 0
    ELSE DATEDIFF(NOW(), FROM_UNIXTIME(l_due_date))
  END as days_past_due
FROM tu_tabla_prestamos
WHERE l_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY l_disbursement_date DESC
```

---

### Nodo 5: Select HCPN (NUEVO)
**Node Type:** MySQL

**⚠️ ¿Tienes la tabla `export-historial_credito` en MySQL?**

**Si SÍ (Opción A - Desde MySQL):**
```sql
SELECT
  hcpn_score_experian_puntaje as experian_score,
  hcpn_cuota_total as cuota_mensual,
  hcpn_creditos_principal_credito_vigentes as creditos_vigentes,
  hcpn_creditos_principal_creditos_actuales_negativos as creditos_mora,
  hcpn_creditos_principal_hist_neg_ult_12_meses as hist_neg_12m,
  hcpn_ingreso as ingreso_mensual,
  -- Si tienes edad/género:
  hcpn_edad as edad,
  hcpn_genero as genero
FROM export_historial_credito
WHERE hcpn_id_data_identificacion_numero = '{{ $("Select Cliente").item.json.cl_doc_number }}'
ORDER BY cct_modified DESC
LIMIT 1
```

**Si NO (Opción B - Desde S3 via HTTP Request):**

Necesitarías un nodo adicional que lea el JSON de S3. **¿Prefieres esta opción?**

---

### Nodo 6: Preparar Datos (Function Node)
**Node Type:** Function

**Code:**
```javascript
// Obtener datos de nodos anteriores
const cliente = $('Select Cliente').item.json;
const pagos = $('Select Pagos').all();
const prestamos = $('Select Préstamos').all();
const hcpn = $('Select HCPN').item.json;

// Calcular months_as_client
const createdDate = new Date(cliente.cct_created);
const now = new Date();
const monthsAsClient = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24 * 30));

// Preparar datos del cliente
const client_data = {
  cedula: cliente.cl_doc_number,
  months_as_client: monthsAsClient,
  experian_score: hcpn.experian_score || 0,
  edad: hcpn.edad || 35, // Default si no existe
  ciudad: cliente.cl_city,
  genero: hcpn.genero || 'M',
  cuota_mensual: hcpn.cuota_mensual || 0,
  creditos_vigentes: hcpn.creditos_vigentes || 0,
  creditos_mora: hcpn.creditos_mora || 0,
  hist_neg_12m: hcpn.hist_neg_12m || 0
};

// Preparar pagos (convertir timestamps a dates y calcular days_past_due)
const payments = pagos.map(p => {
  const paymentDate = new Date(p.json.p_payment_date * 1000); // Unix timestamp a Date

  return {
    payment_date: paymentDate.toISOString().split('T')[0],
    days_past_due: p.json.days_past_due || 0, // Ya calculado en la query
    payment_amount: p.json.p_payment_amount || 0
  };
});

// Preparar préstamos (para planes de pago, por ahora vacío)
const payment_plans = [];
// Más adelante cuando tengas planes de pago reales, mapéalos aquí

return {
  json: {
    client_data: client_data,
    payments: payments,
    payment_plans: payment_plans
  }
};
```

---

### Nodo 7: HTTP Request → Cloud Function
**Node Type:** HTTP Request

**Name:** `Calcular Scores (Cloud Function)`

**Method:** POST

**URL:**
```
{{ $env.CLOUD_FUNCTION_URL }}
```
*(Guardarás la URL como variable de entorno después del deployment)*

**Body Content Type:** JSON

**Body:**
```json
{{ $json }}
```

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

### Nodo 8: HTTP Request → WordPress REST API
**Node Type:** HTTP Request

**Name:** `Actualizar Cliente (WordPress)`

**Method:** POST

**URL:**
```
https://platampay.com/wp-json/jet-cct/clientes/{{ $('Select Cliente').item.json._ID }}
```

**Authentication:** (la que ya tienes configurada)

**Body Content Type:** JSON

**Body:**
```json
{
  "cl_platam_score": "{{ $('Calcular Scores (Cloud Function)').json.platam_score }}",
  "cl_hybrid_score": "{{ $('Calcular Scores (Cloud Function)').json.hybrid_score }}",
  "cl_ml_probability_default": "{{ $('Calcular Scores (Cloud Function)').json.ml_probability_default }}",
  "cl_ml_probability_no_default": "{{ $('Calcular Scores (Cloud Function)').json.ml_probability_no_default }}",
  "cl_ml_risk_level": "{{ $('Calcular Scores (Cloud Function)').json.ml_risk_level }}",
  "cl_hybrid_weight_platam": "{{ $('Calcular Scores (Cloud Function)').json.peso_platam }}",
  "cl_hybrid_weight_experian": "{{ $('Calcular Scores (Cloud Function)').json.peso_hcpn }}",
  "cl_ml_modified": "{{ Math.floor(Date.now() / 1000) }}"
}
```

---

## 🧪 Testing

### Test 1: Verificar queries SQL manualmente

**Cliente:**
```sql
SELECT * FROM wp_jet_cct_clientes WHERE _ID = 1702;
```

**Pagos:**
```sql
SELECT * FROM tu_tabla_pagos WHERE p_cl_id = 1702 LIMIT 5;
```

**HCPN:**
```sql
SELECT * FROM export_historial_credito
WHERE hcpn_id_data_identificacion_numero = '1116614340'
LIMIT 1;
```

### Test 2: Probar flujo completo en n8n

1. Click "Execute Workflow"
2. Enviar test trigger:
   ```json
   {
     "client_id": "1702",
     "trigger": "test"
   }
   ```
3. Ver que cada nodo ejecuta correctamente
4. Verificar output final

---

## ❓ Preguntas Finales para Completar Config

### 1. Nombres exactos de tus tablas:
- Pagos: `_____?` (ej: `wp_pagos`, `wp_jet_cct_pagos`)
- Préstamos: `_____?` (ej: `wp_prestamos`, `wp_jet_cct_prestamos`)
- HCPN: ¿Está en MySQL? ✅ / ❌

### 2. Cálculo de `days_past_due`:
- ¿Tienes `p_due_date` en la tabla de pagos? ✅ / ❌
- Si no, ¿cada pago está vinculado a un préstamo (`p_l_id`)? ✅ / ❌

### 3. HCPN:
- ¿Prefieres leer desde MySQL o desde S3?
  - MySQL: Más rápido, requiere importar CSV
  - S3: Requiere credenciales AWS, más lento

---

## 🚀 Siguientes Pasos

Una vez que me respondas las 3 preguntas:

1. ✅ Ajusto las queries SQL con tus nombres de tablas
2. ✅ Despliegas Cloud Function: `./deploy.sh`
3. ✅ Copias URL de Cloud Function
4. ✅ Configuras nodos en n8n (5 minutos)
5. ✅ Probamos con cliente 1702
6. ✅ Verificamos que se actualizó en WordPress
7. ✅ ¡Listo! Sistema funcionando en tiempo real

**¿Me pasas los nombres de las tablas y preferencia para HCPN?**
