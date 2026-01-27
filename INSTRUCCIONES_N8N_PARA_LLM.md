# 🤖 INSTRUCCIONES PARA CONFIGURAR N8N - SCORING EN TIEMPO REAL

**INSTRUCCIONES PARA ASISTENTE IA (Gemini/Claude):**

Estas son instrucciones completas para ayudarme a configurar un workflow de n8n paso a paso.
Necesito que me guíes nodo por nodo, validando cada paso antes de continuar al siguiente.

---

## 📋 CONTEXTO DEL PROYECTO

**Sistema:** Scoring en tiempo real para PLATAM Analytics

**Objetivo:** Cuando ocurre un evento (pago tardío, nuevo préstamo), el sistema debe:
1. Recibir trigger con client_id
2. Consultar MySQL (cliente, pagos, préstamos)
3. Enviar datos a Cloud Function
4. Cloud Function calcula scores + ML prediction
5. Actualizar WordPress con nuevos scores

**Flujo completo:**
```
Trigger → n8n Workflow (7 nodos) → Cloud Function → WordPress
```

---

## 🎯 INFORMACIÓN TÉCNICA

### Base de Datos MySQL

**Tablas:**
- `wp_jet_cct_clientes` (clientes)
- `wp_jet_cct_pagos` (pagos)
- `wp_jet_cct_prestamos` (préstamos)

**Cliente de prueba:**
- ID: 1702
- Cédula: 1116614340
- Nombre: ANGELA YARITZA DEVIA CIERRA

### Cloud Function

**URL:** (Usuario debe proporcionarla después del deployment)
```
https://calculate-scores-XXXXXXXXX-uc.a.run.app
```

**Método:** POST
**Content-Type:** application/json

**Input esperado:**
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
    }
  ],
  "payment_plans": []
}
```

**Output esperado:**
```json
{
  "status": "success",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_probability_no_default": 0.88,
  "ml_risk_level": "Bajo",
  "peso_platam": 0.6,
  "peso_hcpn": 0.4
}
```

### WordPress REST API

**Endpoint:** `https://platampay.com/wp-json/jet-cct/clientes/{ID}`
**Método:** POST
**Auth:** (Usuario ya tiene configurada)

---

## 🔧 CONFIGURACIÓN PASO A PASO

### PASO 0: Preparación

**Antes de empezar, necesito que me pidas:**

1. ✅ **URL de Cloud Function** (después de deployment)
   - Ejemplo: `https://calculate-scores-abc123-uc.a.run.app`

2. ✅ **Credenciales MySQL** (si no están configuradas)
   - Host
   - Database
   - User
   - Password
   - Port (usualmente 3306)

3. ✅ **Credenciales WordPress REST API** (si no están configuradas)
   - Username
   - Application Password

**Pregúntame:** "¿Ya tienes configurada la conexión MySQL en n8n? ¿Y la autenticación de WordPress?"

---

### NODO 1: Webhook

**Tipo de nodo:** `Webhook`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ Webhook                                     │
├─────────────────────────────────────────────┤
│                                             │
│ HTTP Method:  POST                          │
│ Path:         scoring-trigger               │
│ Authentication: None                        │
│ Response Mode: Immediately                  │
│ Response Code: 200                          │
│                                             │
└─────────────────────────────────────────────┘
```

**Valores exactos:**
- **HTTP Method:** `POST`
- **Path:** `scoring-trigger`
- **Authentication:** `None` (sin autenticación)
- **Response Mode:** `Immediately`
- **Response Code:** `200`

**Validación:**
Después de configurar, n8n te dará una URL webhook. Debe verse así:
```
https://TU_INSTANCIA_N8N.com/webhook/scoring-trigger
```

**Test:**
```bash
curl -X POST https://TU_INSTANCIA_N8N.com/webhook/scoring-trigger \
  -H "Content-Type: application/json" \
  -d '{"client_id": "1702", "trigger": "test"}'
```

**Pregúntame:** "¿Ya creaste el nodo Webhook? ¿Cuál es la URL que te dio n8n?"

---

### NODO 2: Select Cliente

**Tipo de nodo:** `MySQL`

**Nombre del nodo:** `Select Cliente`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ MySQL - Select Cliente                      │
├─────────────────────────────────────────────┤
│                                             │
│ Operation: Execute Query                    │
│ Query:     [VER ABAJO]                      │
│                                             │
└─────────────────────────────────────────────┘
```

**Query EXACTA:**

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

**⚠️ IMPORTANTE:**
- Usa **EXACTAMENTE** `{{ $json.client_id }}` (con doble llave)
- NO uses comillas alrededor de `{{ $json.client_id }}`
- El nombre de la tabla es `wp_jet_cct_clientes` (con triple c y s al final)

**Conexión:**
- Conectar **Webhook → Select Cliente**

**Validación:**
El output debe tener estos campos:
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

**Pregúntame:** "¿El nodo Select Cliente está ejecutando correctamente? ¿Ves el output con _ID y cedula?"

---

### NODO 3: Select Pagos

**Tipo de nodo:** `MySQL`

**Nombre del nodo:** `Select Pagos`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ MySQL - Select Pagos                        │
├─────────────────────────────────────────────┤
│                                             │
│ Operation: Execute Query                    │
│ Query:     [VER ABAJO]                      │
│                                             │
└─────────────────────────────────────────────┘
```

**Query EXACTA:**

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

**⚠️ IMPORTANTE:**
- Usa **EXACTAMENTE** `{{ $('Select Cliente').item.json._ID }}`
- El LEFT JOIN es con `wp_jet_cct_prestamos`
- La tabla de pagos es `wp_jet_cct_pagos` (pagos con "s")
- NO olvides el `ORDER BY p.p_payment_date DESC` (más recientes primero)

**Conexión:**
- Conectar **Select Cliente → Select Pagos**

**Validación:**
El output debe ser un ARRAY con múltiples pagos:
```json
[
  {
    "p_payment_date": 1699506000,
    "payment_date_formatted": "2023-11-09 10:20:00",
    "p_payment_amount": "2000000",
    "p_penalty_payment": "25355",
    "p_status": "Registrado",
    "days_past_due": 7
  },
  {
    "p_payment_date": 1697000000,
    "payment_date_formatted": "2023-10-11 08:13:20",
    "p_payment_amount": "1500000",
    "p_penalty_payment": "0",
    "p_status": "Registrado",
    "days_past_due": 2
  }
]
```

**Pregúntame:** "¿El nodo Select Pagos devuelve un array? ¿Cuántos pagos te muestra?"

---

### NODO 4: Select Préstamos

**Tipo de nodo:** `MySQL`

**Nombre del nodo:** `Select Préstamos`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ MySQL - Select Préstamos                    │
├─────────────────────────────────────────────┤
│                                             │
│ Operation: Execute Query                    │
│ Query:     [VER ABAJO]                      │
│                                             │
└─────────────────────────────────────────────┘
```

**Query EXACTA:**

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

**⚠️ IMPORTANTE:**
- Usa **EXACTAMENTE** `{{ $('Select Cliente').item.json._ID }}`
- La tabla es `wp_jet_cct_prestamos` (préstamos con acento)
- Incluye los 3 CASE statements para calcular: days_past_due, is_active, is_in_default

**Conexión:**
- Conectar **Select Cliente → Select Préstamos**

**Validación:**
El output debe ser un ARRAY con préstamos:
```json
[
  {
    "loan_id": 1702,
    "l_status": "Pagado",
    "disbursement_date": "2023-11-15 00:00:00",
    "due_date": "2023-12-18 00:00:00",
    "l_principal": "430704",
    "l_balance_principal": "0",
    "l_balance_total": "0",
    "days_past_due": 0,
    "is_active": 0,
    "is_in_default": 0
  }
]
```

**Pregúntame:** "¿El nodo Select Préstamos devuelve datos? ¿Cuántos préstamos te muestra?"

---

### NODO 5: Preparar Datos (Function Node)

**Tipo de nodo:** `Function`

**Nombre del nodo:** `Preparar Datos`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ Function - Preparar Datos                   │
├─────────────────────────────────────────────┤
│                                             │
│ Language: JavaScript                        │
│ Function:  [VER ABAJO]                      │
│                                             │
└─────────────────────────────────────────────┘
```

**Código JavaScript EXACTO:**

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

// Preparar payments (convertir timestamps a fechas ISO)
const payments = pagos.map(p => {
  const paymentTimestamp = p.json.p_payment_date;
  const paymentDate = new Date(paymentTimestamp * 1000);

  return {
    payment_date: paymentDate.toISOString().split('T')[0],
    days_past_due: p.json.days_past_due || 0,
    payment_amount: parseFloat(p.json.p_payment_amount) || 0
  };
});

// Preparar payment_plans (vacío por ahora - futuro uso)
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

**⚠️ IMPORTANTE:**
- Copia el código EXACTAMENTE como está
- Verifica que los nombres de nodos coincidan: `'Select Cliente'`, `'Select Pagos'`, `'Select Préstamos'`
- NO cambies la lógica de conversión de fechas

**Conexión:**
- Conectar **Select Pagos → Preparar Datos**
- Conectar **Select Préstamos → Preparar Datos**

**Validación:**
El output debe verse así:
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
    {
      "payment_date": "2023-10-11",
      "days_past_due": 2,
      "payment_amount": 1500000
    }
  ],
  "payment_plans": []
}
```

**Verificaciones:**
- ✅ `cedula` es string con número de documento
- ✅ `client_data` tiene `months_as_client` y `ciudad`
- ✅ `payments` es un array con objetos que tienen `payment_date` (formato YYYY-MM-DD), `days_past_due`, `payment_amount`
- ✅ `payment_plans` es array vacío

**Pregúntame:** "¿El nodo Preparar Datos muestra un output con cedula, client_data y payments? ¿Cuántos pagos hay en el array?"

---

### NODO 6: HTTP Request - Cloud Function

**Tipo de nodo:** `HTTP Request`

**Nombre del nodo:** `Calcular Scores (Cloud Function)`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ HTTP Request - Cloud Function               │
├─────────────────────────────────────────────┤
│                                             │
│ Method: POST                                │
│ URL: {{ $env.CLOUD_FUNCTION_URL }}          │
│ Authentication: None                        │
│ Body Content Type: JSON                     │
│ Specify Body: Using JSON                    │
│ JSON Body: {{ $json }}                      │
│                                             │
└─────────────────────────────────────────────┘
```

**Valores exactos:**

1. **Method:** `POST`

2. **URL:** `{{ $env.CLOUD_FUNCTION_URL }}`
   - **⚠️ IMPORTANTE:** Usa la variable de entorno, NO la URL directa

3. **Authentication:** `None`

4. **Send Headers:** No (por defecto)

5. **Send Query Parameters:** No (por defecto)

6. **Send Body:** Yes

7. **Body Content Type:** `JSON`

8. **Specify Body:** `Using JSON`

9. **JSON Body:** `{{ $json }}`
   - **⚠️ IMPORTANTE:** Esto envía TODO el output del nodo anterior

**Conexión:**
- Conectar **Preparar Datos → Calcular Scores (Cloud Function)**

**ANTES DE EJECUTAR:**

Debes configurar la variable de entorno `CLOUD_FUNCTION_URL`:

1. Ir a n8n Settings (icono de rueda dentada)
2. Ir a "Environments" o "Variables"
3. Agregar nueva variable:
   - **Nombre:** `CLOUD_FUNCTION_URL`
   - **Valor:** `https://calculate-scores-XXXXXXXXX-uc.a.run.app` (la URL real después del deployment)
4. Guardar

**Validación:**

El output debe verse así:
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

**Si hay error:**

Error común: `"error": "Request body must be JSON"`
- **Solución:** Verifica que "Body Content Type" sea "JSON" y "Specify Body" sea "Using JSON"

Error común: `"error": "cedula is required"`
- **Solución:** Verifica que el nodo "Preparar Datos" esté enviando correctamente el campo "cedula"

**Pregúntame:** "¿El nodo Cloud Function devuelve status: success? ¿Qué valor tiene platam_score?"

---

### NODO 7: HTTP Request - WordPress

**Tipo de nodo:** `HTTP Request`

**Nombre del nodo:** `Actualizar Cliente (WordPress)`

**Configuración:**

```
┌─────────────────────────────────────────────┐
│ HTTP Request - WordPress REST API           │
├─────────────────────────────────────────────┤
│                                             │
│ Method: POST                                │
│ URL: [VER ABAJO]                            │
│ Authentication: [TU AUTH CONFIGURADA]       │
│ Body Content Type: JSON                     │
│ JSON Body: [VER ABAJO]                      │
│                                             │
└─────────────────────────────────────────────┘
```

**Valores exactos:**

1. **Method:** `POST`

2. **URL:**
```
https://platampay.com/wp-json/jet-cct/clientes/{{ $('Select Cliente').item.json._ID }}
```

**⚠️ IMPORTANTE:**
- Usa **EXACTAMENTE** `{{ $('Select Cliente').item.json._ID }}`
- La URL termina con el ID del cliente (1702 en este caso)

3. **Authentication:**
   - Usa la autenticación que ya tienes configurada para WordPress
   - Usualmente: Basic Auth o Header Auth

4. **Body Content Type:** `JSON`

5. **Specify Body:** `Using JSON`

6. **JSON Body:**

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

**⚠️ IMPORTANTE:**
- Copia el JSON EXACTAMENTE como está
- Todos los valores vienen del nodo `'Calcular Scores (Cloud Function)'`
- `cl_ml_modified` usa timestamp actual en UNIX format

**Conexión:**
- Conectar **Calcular Scores (Cloud Function) → Actualizar Cliente (WordPress)**

**Validación:**

El output debe verse así:
```json
{
  "success": true,
  "data": {
    "_ID": 1702,
    "cl_platam_score": "730.5",
    "cl_hybrid_score": "745.2",
    "cl_ml_probability_default": "0.12",
    "cl_ml_probability_no_default": "0.88",
    "cl_ml_risk_level": "Bajo",
    "cl_hybrid_weight_platam": "0.6",
    "cl_hybrid_weight_experian": "0.4"
  }
}
```

**Si hay error:**

Error común: `401 Unauthorized`
- **Solución:** Verifica las credenciales de WordPress

Error común: `404 Not Found`
- **Solución:** Verifica que la URL tenga el ID correcto

**Pregúntame:** "¿El nodo WordPress devuelve success: true? ¿Se actualizaron los scores?"

---

## 🔗 CONEXIONES ENTRE NODOS

**Diagrama visual:**

```
┌──────────────┐
│   Webhook    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│Select Cliente│
└──┬───────┬───┘
   │       │
   │       └─────────────────┐
   │                         │
   ▼                         ▼
┌──────────────┐    ┌───────────────┐
│Select Pagos  │    │Select Préstamos│
└──────┬───────┘    └───────┬────────┘
       │                    │
       └────────┬───────────┘
                │
                ▼
        ┌───────────────┐
        │Preparar Datos │
        └───────┬───────┘
                │
                ▼
    ┌─────────────────────────┐
    │ Cloud Function          │
    │ (Calcular Scores)       │
    └─────────┬───────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │ WordPress REST API      │
    │ (Actualizar Cliente)    │
    └─────────────────────────┘
```

**Verificación de conexiones:**

1. ✅ Webhook → Select Cliente
2. ✅ Select Cliente → Select Pagos
3. ✅ Select Cliente → Select Préstamos
4. ✅ Select Pagos → Preparar Datos
5. ✅ Select Préstamos → Preparar Datos
6. ✅ Preparar Datos → Cloud Function
7. ✅ Cloud Function → WordPress

**Total de nodos:** 7
**Total de conexiones:** 7

---

## ✅ VALIDACIÓN COMPLETA

Después de configurar todos los nodos, ejecuta el workflow completo:

### Test 1: Ejecución Manual

1. Click en "Execute Workflow"
2. El webhook recibirá un test trigger automático
3. Verifica que TODOS los nodos se ejecuten en verde

### Test 2: Trigger Real

Envía un POST al webhook:

```bash
curl -X POST https://TU_INSTANCIA_N8N.com/webhook/scoring-trigger \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "1702",
    "trigger": "test"
  }'
```

### Verificaciones:

1. ✅ **Nodo 1 (Webhook):** Recibe `client_id: 1702`
2. ✅ **Nodo 2 (Select Cliente):** Devuelve datos de ANGELA YARITZA
3. ✅ **Nodo 3 (Select Pagos):** Devuelve array con múltiples pagos
4. ✅ **Nodo 4 (Select Préstamos):** Devuelve array con préstamos
5. ✅ **Nodo 5 (Preparar Datos):** JSON con cedula + client_data + payments
6. ✅ **Nodo 6 (Cloud Function):** Devuelve status: success + scores
7. ✅ **Nodo 7 (WordPress):** Devuelve success: true

### Verificación en WordPress:

1. Ir a WordPress admin
2. Buscar cliente ID 1702 o cédula 1116614340
3. Verificar que estos campos tienen valores NUEVOS:
   - `cl_platam_score`
   - `cl_hybrid_score`
   - `cl_ml_risk_level`

---

## 🆘 TROUBLESHOOTING COMÚN

### Error: "No items to send"

**Causa:** Un nodo anterior no devolvió datos
**Solución:**
1. Ir al nodo que falló
2. Click en "Execute Node" para ver el error específico
3. Revisar la query SQL o la lógica

### Error: "Unknown expression"

**Causa:** Error de sintaxis en expresión `{{ }}`
**Solución:**
1. Verificar que uses EXACTAMENTE la sintaxis indicada
2. Las comillas dentro de `{{ }}` deben ser simples: `$('Select Cliente')`
3. NO uses comillas dobles: ❌ `$("Select Cliente")`

### Error: "Cannot read property of undefined"

**Causa:** Referencia incorrecta a nodo anterior
**Solución:**
1. Verifica el NOMBRE EXACTO del nodo anterior
2. Usa `$('Nombre Exacto')` con comillas simples
3. Para obtener el item actual: `.item.json`
4. Para obtener todos los items: `.all()`

### Error: "Request failed with status code 500"

**Causa:** Error en Cloud Function
**Solución:**
1. Ver logs de Cloud Function:
   ```bash
   gcloud functions logs read calculate-scores --region=us-central1 --limit=20
   ```
2. Verificar que el JSON enviado tiene la estructura correcta

---

## 📝 CHECKLIST FINAL

Antes de dar por terminado, verifica:

- [ ] Los 7 nodos están creados
- [ ] Todas las conexiones están hechas (7 conexiones)
- [ ] Variable de entorno `CLOUD_FUNCTION_URL` está configurada
- [ ] Test manual ejecuta todos los nodos correctamente
- [ ] Test con cURL funciona
- [ ] WordPress muestra scores actualizados
- [ ] NO hay errores en ningún nodo

---

## 🎯 SIGUIENTE PASO

**Una vez configurado n8n:**

El equipo de tech enviará triggers reales:

```json
{"client_id": "1702", "trigger": "late_7"}
{"client_id": "128282", "trigger": "new_loan"}
{"client_id": "1234567", "trigger": "payment"}
```

El sistema calculará y actualizará scores automáticamente en tiempo real.

---

## 💡 TIPS PARA EL ASISTENTE IA

**Cuando me ayudes:**

1. **Pídeme confirmación en cada nodo** antes de pasar al siguiente
2. **Muéstrame la configuración específica** de cada campo
3. **Valida el output** de cada nodo conmigo
4. **Si hay error, ayúdame a debuggear** con preguntas específicas
5. **Usa capturas de pantalla** si puedo proporcionarlas
6. **No asumas** que algo está bien, valida cada paso

**Preguntas útiles:**

- "¿Puedes mostrarme el output del nodo X?"
- "¿El campo Y tiene valor o está vacío?"
- "¿Cuántos items devuelve el nodo Z?"
- "¿Qué error específico muestra n8n?"

---

**FIN DE INSTRUCCIONES**

---

**INSTRUCCIONES ADICIONALES PARA USUARIO:**

Copia ESTE ARCHIVO COMPLETO y pégalo en tu conversación con Gemini o Claude.

Diles algo como:

```
"Necesito tu ayuda para configurar un workflow de n8n siguiendo estas
instrucciones paso a paso. Por favor guíame nodo por nodo y valida
cada paso antes de continuar."
```

Luego pega todo este documento.

El asistente te guiará paso a paso, nodo por nodo, validando cada configuración.

---

**Creado:** 2026-01-26
**Versión:** 1.0
