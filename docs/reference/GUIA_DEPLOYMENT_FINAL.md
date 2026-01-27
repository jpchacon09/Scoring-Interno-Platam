# 🚀 Guía de Deployment Final - Sistema de Scoring en Tiempo Real

**Proyecto:** PLATAM Analytics - Sistema de Actualización Automática de Scores
**Fecha:** Enero 2026
**Status:** ✅ **LISTO PARA DEPLOYMENT**

---

## 📋 Resumen del Sistema

Este sistema permite calcular y actualizar scores automáticamente en tiempo real cuando ocurren eventos de negocio (pagos tardíos, nuevos préstamos, etc.).

### Arquitectura Implementada:

```
Trigger (n8n)
    ↓
    {"client_id": "1702", "trigger": "late_7"}
    ↓
1. n8n Query MySQL → Extrae datos del cliente
2. n8n Function Node → Prepara JSON
3. Cloud Function → Descarga HCPN de S3 + Calcula Scores + Llama Vertex AI
4. n8n recibe scores
5. n8n actualiza vía WordPress REST API
```

### Componentes:

- **Cloud Function**: `calculate-scores` (Python 3.11, Gen2)
- **Vertex AI Endpoint**: 7891061911641391104 (Modelo v2.2 con 22 features)
- **S3 Bucket**: Datos HCPN (formato: `hcpn_{cedula}.json`)
- **MySQL Tables**:
  - `wp_jet_cct_clientes`
  - `wp_jet_cct_pagos`
  - `wp_jet_cct_prestamos`
- **WordPress REST API**: `https://platampay.com/wp-json/jet-cct/clientes/{ID}`

---

## ✅ Checklist Pre-Deployment

### 1. Archivos Verificados

- [x] **cloud_function_calculate_scores/main.py** - Cloud Function con S3 ✅
- [x] **cloud_function_calculate_scores/requirements.txt** - Incluye boto3 ✅
- [x] **cloud_function_calculate_scores/deploy.sh** - Script de deployment ✅
- [x] **N8N_QUERIES_FINALES.md** - Queries SQL para n8n ✅

### 2. Credenciales Necesarias

Antes de empezar, asegúrate de tener:

- [ ] **AWS Access Key ID** (para S3)
- [ ] **AWS Secret Access Key** (para S3)
- [ ] **S3 Bucket Name** (ej: `fft-analytics-data-lake`)
- [ ] **S3 Prefix** (ej: `ppay/prod/`)
- [ ] **Credenciales MySQL** (ya configuradas en n8n)
- [ ] **Credenciales WordPress REST API** (ya configuradas en n8n)

### 3. Permisos GCP

Verifica que tienes permisos en Google Cloud:

```bash
gcloud auth list
gcloud config get-value project
```

Debe mostrar: `platam-analytics`

---

## 🚀 PASO 1: Desplegar Cloud Function

### 1.1 Navegar al directorio

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
```

### 1.2 Hacer ejecutable el script

```bash
chmod +x deploy.sh
```

### 1.3 Ejecutar deployment

```bash
./deploy.sh
```

### 1.4 Proporcionar credenciales cuando se soliciten

El script te pedirá:

```
AWS Access Key ID: [ingresar tu access key]
AWS Secret Access Key: [ingresar tu secret key]
S3 Bucket (ej: fft-analytics-data-lake): [ingresar bucket]
S3 Prefix (ej: ppay/prod/): [ingresar prefix]
```

### 1.5 Confirmar deployment

```
¿Continuar con el deployment? (y/n): y
```

### 1.6 Esperar resultado

El deployment tomará ~3-5 minutos. Al finalizar verás:

```
========================================================================
✅ DEPLOYMENT COMPLETADO
========================================================================

📍 URL de la Cloud Function:
   https://calculate-scores-XXXXXXXXX-uc.a.run.app

🔐 Credenciales AWS configuradas como variables de entorno

📝 Guarda esta URL para configurar n8n
```

**⚠️ IMPORTANTE:** Copia y guarda la URL de la Cloud Function

---

## 🧪 PASO 2: Probar la Cloud Function

Antes de configurar n8n, prueba que la Cloud Function funciona correctamente:

```bash
curl -X POST https://TU_URL_AQUI \
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

**Resultado esperado:**

```json
{
  "status": "success",
  "cedula": "1116614340",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_probability_no_default": 0.88,
  "ml_risk_level": "Bajo",
  ...
}
```

Si ves este resultado, ✅ **la Cloud Function funciona correctamente**.

---

## 🔧 PASO 3: Configurar n8n

### 3.1 Abrir n8n y crear nuevo workflow

1. Ir a n8n
2. Crear nuevo workflow
3. Nombrar: **"ActualizarML - Scoring en Tiempo Real"**

### 3.2 Configurar 6 nodos

Usa el archivo `N8N_QUERIES_FINALES.md` como referencia completa. Aquí el resumen:

#### Nodo 1: Webhook
- **Tipo:** Webhook
- **Path:** `/scoring-trigger`
- **Method:** POST
- **Responde:** Immediately
- **Payload esperado:**
  ```json
  {
    "client_id": "1702",
    "trigger": "late_7"
  }
  ```

#### Nodo 2: Select Cliente
- **Tipo:** MySQL
- **Operation:** Select
- **Query:** (ver N8N_QUERIES_FINALES.md línea 30-44)

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

#### Nodo 3: Select Pagos
- **Tipo:** MySQL
- **Operation:** Select
- **Query:** (ver N8N_QUERIES_FINALES.md línea 65-85)

```sql
SELECT
  p_payment_date,
  FROM_UNIXTIME(p_payment_date) as payment_date_formatted,
  p_payment_amount,
  p_penalty_payment,
  p_status,
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

#### Nodo 4: Select Préstamos
- **Tipo:** MySQL
- **Operation:** Select
- **Query:** (ver N8N_QUERIES_FINALES.md línea 130-157)

```sql
SELECT
  _ID as loan_id,
  l_status,
  FROM_UNIXTIME(l_disbursement_date) as disbursement_date,
  FROM_UNIXTIME(l_due_date) as due_date,
  l_principal,
  l_balance_principal,
  l_balance_total,
  CASE
    WHEN l_status != 'Pagado' AND l_due_date < UNIX_TIMESTAMP()
    THEN DATEDIFF(NOW(), FROM_UNIXTIME(l_due_date))
    ELSE 0
  END as days_past_due,
  CASE WHEN l_status != 'Pagado' THEN 1 ELSE 0 END as is_active,
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

#### Nodo 5: Preparar Datos (Function)
- **Tipo:** Function
- **Code:** (ver N8N_QUERIES_FINALES.md línea 185-221)

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

#### Nodo 6: HTTP Request - Cloud Function
- **Tipo:** HTTP Request
- **Name:** `Calcular Scores (Cloud Function)`
- **Method:** POST
- **URL:** `{{ $env.CLOUD_FUNCTION_URL }}`
- **Authentication:** None
- **Body Content Type:** JSON
- **Body:** `{{ $json }}`

#### Nodo 7: HTTP Request - WordPress
- **Tipo:** HTTP Request
- **Name:** `Actualizar Cliente (WordPress)`
- **Method:** POST
- **URL:** `https://platampay.com/wp-json/jet-cct/clientes/{{ $('Select Cliente').item.json._ID }}`
- **Authentication:** (la que ya tienes configurada)
- **Body Content Type:** JSON
- **Body:**

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

### 3.3 Configurar variable de entorno

1. En n8n, ir a **Settings** (rueda dentada)
2. Ir a **Environments**
3. Agregar variable:
   - **Nombre:** `CLOUD_FUNCTION_URL`
   - **Valor:** `https://TU_URL_DE_CLOUD_FUNCTION_AQUI`
4. Guardar

### 3.4 Conectar nodos

```
Webhook
  → Select Cliente
    → Select Pagos
    → Select Préstamos
      → Preparar Datos
        → HTTP Request (Cloud Function)
          → HTTP Request (WordPress)
```

---

## 🧪 PASO 4: Probar Flujo Completo

### 4.1 Test manual en n8n

1. Click en **"Execute Workflow"** en n8n
2. Enviar test trigger:
   ```json
   {
     "client_id": "1702",
     "trigger": "test"
   }
   ```
3. Verificar que cada nodo ejecuta correctamente
4. Verificar output de cada nodo

### 4.2 Verificar resultado en WordPress

1. Ir a WordPress admin
2. Buscar cliente ID 1702 (cédula: 1116614340)
3. Verificar que los campos fueron actualizados:
   - `cl_platam_score`
   - `cl_hybrid_score`
   - `cl_ml_probability_default`
   - `cl_ml_probability_no_default`
   - `cl_ml_risk_level`
   - `cl_hybrid_weight_platam`
   - `cl_hybrid_weight_experian`
   - `cl_ml_modified`

### 4.3 Test con trigger real

Pide a tu equipo de tech que envíe un trigger real:

```json
{
  "client_id": "1702",
  "trigger": "late_7"
}
```

Verificar que el sistema actualiza correctamente.

---

## 📊 Logs y Monitoreo

### Ver logs de Cloud Function

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=50
```

### Ver logs en tiempo real

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=50 \
  --format="table(severity,timestamp,textPayload)"
```

### Verificar endpoint Vertex AI

```bash
gcloud ai endpoints describe 7891061911641391104 \
  --region=us-central1 \
  --project=platam-analytics
```

---

## 🔧 Troubleshooting

### Error: "HCPN not found"

**Causa:** El archivo `hcpn_{cedula}.json` no existe en S3

**Solución:**
1. Verificar que el archivo existe en S3:
   ```bash
   aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ | grep hcpn_1116614340
   ```
2. Verificar formato del nombre del archivo
3. Si no existe, la Cloud Function usará valores por defecto

### Error: "MySQL connection failed"

**Causa:** Credenciales incorrectas o timeout

**Solución:**
1. Verificar credenciales MySQL en n8n
2. Verificar que la base de datos está accesible
3. Verificar nombres de tablas correctos

### Error: "Vertex AI prediction failed"

**Causa:** Endpoint no disponible o input inválido

**Solución:**
1. Verificar que el endpoint está activo:
   ```bash
   gcloud ai endpoints list --region=us-central1
   ```
2. Verificar logs de Cloud Function
3. Verificar que todas las 22 features están presentes

### Error: "WordPress API update failed"

**Causa:** Autenticación o permisos

**Solución:**
1. Verificar credenciales WordPress REST API
2. Verificar que el endpoint está accesible
3. Verificar que los campos existen en la base de datos

---

## 📈 Métricas de Éxito

Después del deployment, verifica:

- [ ] Cloud Function responde en < 5 segundos
- [ ] Logs muestran descarga exitosa de HCPN
- [ ] Scores calculados correctamente
- [ ] WordPress actualizado correctamente
- [ ] n8n workflow ejecuta sin errores
- [ ] Triggers desde tech team funcionan correctamente

---

## 🎯 Próximos Pasos (Opcional)

### 1. Agregar tabla de Planes de Pago

Cuando `wp_jet_cct_planes_de_pago` esté en producción:

1. Agregar nodo MySQL en n8n para planes de pago
2. Modificar Function Node para incluir payment_plans
3. Cloud Function ya está preparada para recibir payment_plans

### 2. Implementar más triggers

Actualmente soportados:
- `late_1`, `late_7`, `late_14`, `late_25`, `late_34`, `late_55`, `late_64`, `late_90`, `late_120`, `late_150`
- `new_loan`
- `payment`

Puedes agregar más según necesidades del negocio.

### 3. Dashboard de Monitoreo

Considera crear dashboard en Metabase/Looker para:
- Scores promedio por ciudad
- Distribución de riesgo
- Tiempo de respuesta de Cloud Function
- Tasa de actualización de scores

---

## 📞 Soporte

Si encuentras problemas durante el deployment:

1. **Logs de Cloud Function:**
   ```bash
   gcloud functions logs read calculate-scores --region=us-central1 --limit=100
   ```

2. **Verificar deployment:**
   ```bash
   gcloud functions describe calculate-scores --region=us-central1 --gen2
   ```

3. **Verificar variables de entorno:**
   ```bash
   gcloud functions describe calculate-scores --region=us-central1 --gen2 --format="yaml(serviceConfig.environmentVariables)"
   ```

---

## ✅ Deployment Completado

Una vez que hayas completado todos los pasos y verificado que funciona:

- [x] Cloud Function deployada ✅
- [x] Test unitario exitoso ✅
- [x] n8n configurado ✅
- [x] Test de flujo completo ✅
- [x] Verificación en WordPress ✅
- [x] Test con trigger real ✅

**🎉 ¡Sistema en producción y funcionando!**

---

**Notas Finales:**

- La Cloud Function descarga SOLO el archivo HCPN específico del cliente (no batch)
- Los datos demográficos vienen de S3, no de MySQL
- El modelo v2.2 usa 22 features incluyendo demografía
- La actualización es en tiempo real vía WordPress REST API
- Los triggers son enviados por el equipo de tech

**Tiempo estimado de deployment completo:** 30-45 minutos

---

**Creado por:** Claude Code
**Fecha:** 2026-01-26
**Versión:** 1.0 Final
