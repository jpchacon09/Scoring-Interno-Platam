# 📝 Queries SQL Finales para n8n - Cliente ID 1702

## ✅ Tablas Confirmadas:
- **Clientes:** `wp_jet_cct_clientes`
- **Pagos:** `wp_jet_cct_pagos`
- **Préstamos:** `wp_jet_cct_prestamos`
- **Planes de pago:** `wp_jet_cct_planes_de_pago` (futuro)

---

## 🔄 Flujo Completo n8n

```
1. Webhook → Recibe {"client_id": "1702", "trigger": "late_7"}
2. Select Cliente
3. Select Pagos
4. Select Préstamos (para calcular créditos vigentes/mora)
5. Preparar Datos (Function Node)
6. HTTP Request → Cloud Function
7. HTTP Request → WordPress REST API
```

---

## 📊 Query 1: Select Cliente

**Node:** MySQL Select

**Query:**
```sql
SELECT
  _ID,
  cl_doc_number as cedula,
  cl_first_name,
  cl_last_name,
  cl_city as ciudad,
  cl_cupo,
  cl_cupo_disponible,
  cct_created,
  TIMESTAMPDIFF(MONTH, cct_created, NOW()) as months_as_client
FROM wp_jet_cct_clientes
WHERE _ID = {{ $json.client_id }}
LIMIT 1
```

**Output esperado:**
```json
{
  "_ID": 1702,
  "cedula": "1116614340",
  "cl_first_name": "ANGELA YARITZA",
  "cl_last_name": "DEVIA CIERRA",
  "ciudad": "MANI (C/NARE)",
  "months_as_client": 3
}
```

---

## 💳 Query 2: Select Pagos

**Node:** MySQL Select

**Query:**
```sql
SELECT
  p_payment_date,
  FROM_UNIXTIME(p_payment_date) as payment_date_formatted,
  p_payment_amount,
  p_penalty_payment,
  p_status,
  -- Calcular days_past_due desde préstamo
  COALESCE(
    DATEDIFF(
      FROM_UNIXTIME(p.p_payment_date),
      FROM_UNIXTIME(l.l_due_date)
    ),
    0
  ) as days_past_due
FROM wp_jet_cct_pagos p
LEFT JOIN wp_jet_cct_prestamos l ON p.p_l_id = l._ID
WHERE p.p_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY p.p_payment_date DESC
LIMIT 100
```

**⚠️ NOTA:** Esta query asume que cada pago está vinculado a un préstamo (`p_l_id`).

**Si NO tienes `p_l_id` o `p_due_date`:**
```sql
SELECT
  p_payment_date,
  FROM_UNIXTIME(p_payment_date) as payment_date_formatted,
  p_payment_amount,
  p_penalty_payment,
  p_status,
  -- Si hay penalty, asumimos que pagó tarde
  CASE
    WHEN p_penalty_payment > 0 THEN 10  -- Aproximado
    ELSE 0
  END as days_past_due
FROM wp_jet_cct_pagos
WHERE p_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY p_payment_date DESC
LIMIT 100
```

**Output esperado:**
```json
[
  {
    "p_payment_date": 1699506000,
    "payment_date_formatted": "2023-11-09",
    "p_payment_amount": "2000000",
    "p_penalty_payment": "25355",
    "p_status": "Registrado",
    "days_past_due": 7
  },
  ...
]
```

---

## 🏦 Query 3: Select Préstamos

**Node:** MySQL Select

**Query:**
```sql
SELECT
  _ID as loan_id,
  l_status,
  FROM_UNIXTIME(l_disbursement_date) as disbursement_date,
  FROM_UNIXTIME(l_due_date) as due_date,
  l_principal,
  l_balance_principal,
  l_balance_total,
  -- Días de mora si está activo
  CASE
    WHEN l_status != 'Pagado' AND l_due_date < UNIX_TIMESTAMP()
    THEN DATEDIFF(NOW(), FROM_UNIXTIME(l_due_date))
    ELSE 0
  END as days_past_due,
  -- Está vigente si no está pagado
  CASE WHEN l_status != 'Pagado' THEN 1 ELSE 0 END as is_active,
  -- Está en mora si tiene saldo y pasó fecha de vencimiento
  CASE
    WHEN l_status != 'Pagado' AND l_balance_total > 0 AND l_due_date < UNIX_TIMESTAMP()
    THEN 1
    ELSE 0
  END as is_in_default
FROM wp_jet_cct_prestamos
WHERE l_cl_id = {{ $('Select Cliente').item.json._ID }}
ORDER BY l_disbursement_date DESC
LIMIT 50
```

**Output esperado:**
```json
[
  {
    "loan_id": 1702,
    "l_status": "Pagado",
    "disbursement_date": "2023-11-15",
    "due_date": "2023-12-18",
    "l_principal": 430704,
    "l_balance_principal": 0,
    "l_balance_total": 0,
    "days_past_due": 0,
    "is_active": 0,
    "is_in_default": 0
  },
  ...
]
```

---

## ⚙️ Nodo 4: Preparar Datos (Function Node)

**Node Type:** Function

**Code:**
```javascript
// Obtener datos de nodos anteriores
const cliente = $('Select Cliente').item.json;
const pagos = $('Select Pagos').all();
const prestamos = $('Select Préstamos').all();

// Preparar client_data
const client_data = {
  months_as_client: cliente.months_as_client || 0,
  ciudad: cliente.ciudad || ''
};

// Preparar payments (convertir timestamps a fechas)
const payments = pagos.map(p => {
  const paymentTimestamp = p.json.p_payment_date;
  const paymentDate = new Date(paymentTimestamp * 1000);

  return {
    payment_date: paymentDate.toISOString().split('T')[0],
    days_past_due: p.json.days_past_due || 0,
    payment_amount: parseFloat(p.json.p_payment_amount) || 0
  };
});

// Preparar payment_plans (vacío por ahora)
const payment_plans = [];

// Preparar request para Cloud Function
return {
  json: {
    cedula: cliente.cedula,
    client_data: client_data,
    payments: payments,
    payment_plans: payment_plans
  }
};
```

**Output:**
```json
{
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
    ...
  ],
  "payment_plans": []
}
```

---

## ☁️ Nodo 5: HTTP Request → Cloud Function

**Node Type:** HTTP Request

**Name:** `Calcular Scores (Cloud Function)`

**Method:** POST

**URL:**
```
{{ $env.CLOUD_FUNCTION_URL }}
```
*(Configura esta variable de entorno en n8n después del deployment)*

**Authentication:** None

**Body Content Type:** JSON

**Body:**
```json
{{ $json }}
```

**Response esperado:**
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
  "score_payment_performance": 450.0,
  "score_payment_plan": 150.0,
  "score_deterioration": 130.5,
  "payment_count": 25,
  "pct_early": 0.8,
  "pct_late": 0.2,
  "tiene_plan_activo": false,
  "tiene_plan_default": false,
  "tiene_plan_pendiente": false,
  "num_planes": 0,
  "processing_time_ms": 2847,
  "timestamp": "2026-01-26T15:30:45.123456",
  "hcpn_found": true
}
```

---

## 🌐 Nodo 6: HTTP Request → WordPress REST API

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

**Response esperado:**
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

## 🧪 Testing

### Test 1: Probar queries SQL directamente

```sql
-- Cliente
SELECT * FROM wp_jet_cct_clientes WHERE _ID = 1702;

-- Pagos
SELECT * FROM wp_jet_cct_pagos WHERE p_cl_id = 1702 LIMIT 5;

-- Préstamos
SELECT * FROM wp_jet_cct_prestamos WHERE l_cl_id = 1702 LIMIT 5;
```

### Test 2: Probar Cloud Function (después del deployment)

```bash
curl -X POST https://TU_URL_CLOUD_FUNCTION \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {
      "months_as_client": 3,
      "ciudad": "MANI (C/NARE)"
    },
    "payments": [
      {"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000},
      {"payment_date": "2023-10-15", "days_past_due": 2, "payment_amount": 1500000}
    ],
    "payment_plans": []
  }'
```

### Test 3: Probar flujo completo en n8n

1. Click "Execute Workflow"
2. Enviar test trigger:
   ```json
   {
     "client_id": "1702",
     "trigger": "test"
   }
   ```
3. Verificar que cada nodo ejecuta correctamente
4. Verificar en WordPress que se actualizó

---

## 📌 Notas Importantes

### 1. Days Past Due
Si la query de pagos no retorna `days_past_due` correctamente, **avísame** y ajustamos la lógica.

### 2. Timestamp vs Date
Tus fechas están en **UNIX timestamp** (ej: `1699506000`). La Cloud Function espera fechas en formato **`YYYY-MM-DD`**, así que el Function Node hace la conversión.

### 3. Payment Plans
Por ahora enviamos array vacío `[]`. Cuando tengas datos en `wp_jet_cct_planes_de_pago`, agregaremos otro nodo SELECT.

### 4. Variables de Entorno en n8n
Después del deployment, configura en n8n:
- Click en "Settings" (rueda dentada)
- "Environments"
- Agregar variable: `CLOUD_FUNCTION_URL` = `https://tu-url...`

---

## ✅ Checklist

- [ ] Probar queries SQL en MySQL (cliente, pagos, préstamos)
- [ ] Desplegar Cloud Function (`./deploy.sh`)
- [ ] Guardar URL de Cloud Function
- [ ] Configurar 6 nodos en n8n (copiar/pegar queries)
- [ ] Configurar variable de entorno `CLOUD_FUNCTION_URL`
- [ ] Probar flujo con cliente 1702
- [ ] Verificar que se actualizó en WordPress
- [ ] ¡Listo! Sistema en tiempo real funcionando

---

**¿Listo para desplegar?** 🚀
