# 🚀 Integración: Cloud Function + n8n para Actualización de Scores

## 📋 ¿Qué hace esta Cloud Function?

Recibe triggers de eventos de negocio (nuevo préstamo, mora, pagos) y **recalcula el score de UN cliente específico** en tiempo real, actualizando directamente MySQL.

**Ventajas:**
- ⚡ Actualización en <5 segundos
- 💰 Costo bajo (~$5/mes para 10,000 eventos)
- 🎯 Recalcula solo el cliente afectado (no todo el dataset)
- 🔄 Sincronización automática con MySQL

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│  Sistema PLATAM (MySQL)                         │
│  - Nuevo préstamo                               │
│  - Pago recibido                                │
│  - Mora detectada (late_1, late_7, late_90...)  │
└────────────────┬────────────────────────────────┘
                 │
                 │ Trigger con {"client_id": "1120", "trigger": "late_7"}
                 ▼
       ┌─────────────────────┐
       │  n8n Webhook        │
       │  "ActualizarML"     │
       └──────────┬──────────┘
                  │
                  │ HTTP POST
                  ▼
       ┌──────────────────────────────────┐
       │  Cloud Function                  │
       │  "update-client-score"           │
       │  - Python 3.11                   │
       │  - Timeout: 60s                  │
       │  - Memory: 1GB                   │
       └──────────┬───────────────────────┘
                  │
                  ├─ 1. Consulta MySQL
                  │     SELECT FROM wp_jet_cct_clientes WHERE _ID = 1120
                  │
                  ├─ 2. Obtiene historial completo
                  │     - Pagos (wp_pagos)
                  │     - Planes de pago (wp_payment_plans)
                  │
                  ├─ 3. Recalcula scores
                  │     • Score PLATAM (600+150+250 pts)
                  │     • Score híbrido (PLATAM + Experian)
                  │
                  ├─ 4. Llama Vertex AI
                  │     • Predicción ML con 22 features
                  │     • Endpoint: 7891061911641391104
                  │
                  └─ 5. Actualiza MySQL
                        UPDATE wp_jet_cct_clientes SET
                          cl_platam_score = 730.5,
                          cl_hybrid_score = 745.2,
                          cl_ml_probability_default = 0.12,
                          cl_ml_risk_level = "Bajo",
                          cl_last_update_trigger = "late_7",
                          cl_modified = NOW()
                        WHERE _ID = 1120
                  │
                  ▼
       ┌──────────────────────────────────┐
       │  MySQL Database                  │
       │  (wp_jet_cct_clientes)           │
       │  ← Score actualizado             │
       └──────────┬───────────────────────┘
                  │
                  ▼
       ┌──────────────────────────────────┐
       │  Frontend PLATAM                 │
       │  (Lee de MySQL)                  │
       │  ✅ Score en tiempo real         │
       └──────────────────────────────────┘
```

---

## 📦 Deployment

### Paso 1: Configurar Cloud Function

```bash
cd cloud_function_update_score

# Hacer ejecutable el script
chmod +x deploy.sh

# Ejecutar deployment
./deploy.sh
```

**El script te pedirá:**
- MySQL Host (ej: `34.123.45.67`)
- MySQL User (ej: `platam_user`)
- MySQL Password
- MySQL Database (ej: `platam_db`)

**Output esperado:**
```
✅ DEPLOYMENT COMPLETADO
📍 URL de la Cloud Function:
   https://us-central1-platam-analytics.cloudfunctions.net/update-client-score
```

---

## 🔧 Integración con n8n

### Paso 2: Configurar Webhook en n8n

Tu flujo **ActualizarML** ya está casi listo. Solo necesitas agregar un paso:

```
┌─────────────────────┐
│  Webhook            │  ← Ya lo tienes
│  Recibe trigger     │
└──────────┬──────────┘
           │ {"client_id": "1120", "trigger": "late_7"}
           ▼
┌─────────────────────┐
│  HTTP Request       │  ← AGREGAR ESTE NODO
│  POST a Cloud Fn    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Actualizar MySQL   │  ← (Opcional, Cloud Function ya lo hace)
└─────────────────────┘
```

**Configuración del HTTP Request Node:**

```json
{
  "method": "POST",
  "url": "https://us-central1-platam-analytics.cloudfunctions.net/update-client-score",
  "options": {
    "headers": {
      "Content-Type": "application/json"
    }
  },
  "body": {
    "client_id": "{{ $json.client_id }}",
    "trigger": "{{ $json.trigger }}"
  }
}
```

---

## 🧪 Probar la Integración

### Opción 1: Probar Cloud Function directamente (desde terminal)

```bash
# Test con client_id real
curl -X POST https://us-central1-platam-analytics.cloudfunctions.net/update-client-score \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "1068",
    "trigger": "test"
  }'
```

**Response esperado:**
```json
{
  "status": "success",
  "client_id": "1068",
  "cedula": "1006157869",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_probability_no_default": 0.88,
  "ml_risk_level": "Bajo",
  "peso_platam": 0.6,
  "peso_hcpn": 0.4,
  "trigger": "test",
  "processing_time_ms": 2847,
  "timestamp": "2026-01-26T15:30:45.123456"
}
```

### Opción 2: Probar desde n8n

1. Ir al flujo **ActualizarML**
2. Hacer clic en "Execute Workflow" (botón rojo)
3. Enviar manualmente un test payload:
   ```json
   {
     "client_id": "1068",
     "trigger": "test"
   }
   ```
4. Ver la respuesta en el output del HTTP Request node

---

## 🔍 Verificar que Funcionó

### 1. Ver logs de la Cloud Function

```bash
# Ver últimos 50 logs
gcloud functions logs read update-client-score \
  --region=us-central1 \
  --gen2 \
  --limit=50
```

**Buscar en los logs:**
```
🔄 RECALCULANDO SCORE PARA CLIENT_ID: 1068
📌 Trigger: late_7
...
✅ ACTUALIZACIÓN COMPLETADA EN 2847ms
```

### 2. Verificar en MySQL

```sql
-- Ver si el score se actualizó
SELECT
  _ID,
  cl_cedula,
  cl_platam_score,
  cl_hybrid_score,
  cl_ml_probability_default,
  cl_ml_risk_level,
  cl_last_update_trigger,
  cl_modified
FROM wp_jet_cct_clientes
WHERE _ID = 1068;
```

**Verificar:**
- `cl_platam_score` tiene un valor nuevo
- `cl_hybrid_score` se actualizó
- `cl_ml_probability_default` tiene una probabilidad (ej: 0.12)
- `cl_ml_risk_level` muestra el nivel (ej: "Bajo")
- `cl_last_update_trigger` dice "late_7"
- `cl_modified` tiene la fecha/hora reciente

### 3. Ver en el frontend

1. Ir a tu aplicación PLATAM
2. Buscar el cliente con cédula correspondiente
3. Verificar que el score mostrado coincide con MySQL

---

## 🎯 Triggers Soportados

| Trigger | Descripción | Cuándo usar |
|---------|-------------|-------------|
| `new_loan` | Nuevo préstamo | Cliente saca un nuevo crédito |
| `payment` | Pago recibido | Cliente realiza un pago |
| `late_1` | Mora 1 día | Primer día de retraso |
| `late_7` | Mora 7 días | 7 días de retraso |
| `late_14` | Mora 14 días | 2 semanas de retraso |
| `late_25` | Mora 25 días | ~1 mes de retraso |
| `late_34` | Mora 34 días | 34 días de retraso |
| `late_55` | Mora 55 días | ~2 meses de retraso |
| `late_64` | Mora 64 días | 64 días de retraso |
| `late_90` | Mora 90 días | 3 meses de retraso (crítico) |
| `late_120` | Mora 120 días | 4 meses de retraso |
| `late_150` | Mora 150 días | 5 meses de retraso |
| `payment_plan_created` | Plan de pago creado | Cliente entra a plan de pago |
| `payment_plan_completed` | Plan completado | Cliente completa plan exitosamente |
| `payment_plan_defaulted` | Plan en default | Cliente no cumple plan de pago |

---

## 🔄 Flujo Completo de Actualización

### Ejemplo: Cliente entra en mora de 7 días

```
1. Sistema PLATAM detecta mora de 7 días
   → Envía webhook a n8n

2. n8n recibe trigger
   Body: {"client_id": "1120", "trigger": "late_7"}

3. n8n llama a Cloud Function
   POST https://..../update-client-score
   Body: {"client_id": "1120", "trigger": "late_7"}

4. Cloud Function ejecuta (en ~3 segundos):
   ├─ Consulta MySQL (cliente 1120 = cédula 128282)
   ├─ Obtiene historial de pagos del cliente
   ├─ Obtiene planes de pago del cliente
   ├─ Recalcula Score PLATAM:
   │  • Payment Performance: 450/600 (bajó por mora)
   │  • Payment Plan: 150/150 (sin cambios)
   │  • Deterioration: 175/250 (empeoró)
   │  • TOTAL: 775 → 625 (bajó 150 puntos)
   ├─ Recalcula Score Híbrido:
   │  • PLATAM: 625
   │  • Experian: 715
   │  • Híbrido: 670 (ponderado)
   ├─ Llama Vertex AI:
   │  • Probabilidad default: 32% (antes era 15%)
   │  • Nivel de riesgo: Medio (antes era Bajo)
   └─ Actualiza MySQL:
      • cl_platam_score = 625
      • cl_hybrid_score = 670
      • cl_ml_probability_default = 0.32
      • cl_ml_risk_level = "Medio"
      • cl_last_update_trigger = "late_7"
      • cl_modified = NOW()

5. Frontend refleja cambios inmediatamente
   ✅ Score actualizado en tiempo real
```

---

## 💰 Costos Estimados

**Escenario típico (10,000 eventos/mes):**

| Servicio | Uso | Costo |
|----------|-----|-------|
| Cloud Functions (Gen 2) | 10,000 invocaciones × 3s × 1GB | $1.50/mes |
| Cloud Functions (requests) | 10,000 requests | $0.40/mes |
| Vertex AI (predicciones) | 10,000 predicciones | $1.50/mes |
| **TOTAL** | | **~$3.50/mes** ✅ |

**Mucho más barato que:**
- ❌ Cloud Run always-on: ~$25/mes
- ❌ Batch recalculo completo diario: ~$10/mes

---

## 🐛 Troubleshooting

### Error: "Client not found"

**Causa:** El `client_id` no existe en `wp_jet_cct_clientes`

**Solución:**
```sql
-- Verificar que el ID existe
SELECT _ID, cl_cedula, cl_nombre FROM wp_jet_cct_clientes WHERE _ID = 1120;
```

### Error: "Connection to MySQL failed"

**Causa:** Credenciales MySQL incorrectas o IP no permitida

**Solución:**
1. Verificar credenciales en Cloud Function:
   ```bash
   gcloud functions describe update-client-score \
     --region=us-central1 \
     --gen2 \
     --format="value(serviceConfig.environmentVariables)"
   ```

2. Permitir IP de Cloud Functions en MySQL:
   - Obtener IPs de Cloud Functions (rango de GCP)
   - Agregar a whitelist de MySQL

### Error: "Vertex AI prediction failed"

**Causa:** Endpoint no disponible o features incorrectas

**Solución:**
```bash
# Verificar que endpoint está activo
gcloud ai endpoints describe 7891061911641391104 \
  --region=us-central1 \
  --project=platam-analytics
```

### Latencia alta (>10 segundos)

**Causa:** Cold start de Cloud Function

**Solución:**
- Configurar "Min instances: 1" (cuesta ~$15/mes pero elimina cold starts)
- O aceptar el cold start en la primera request (solo afecta primera llamada del día)

---

## 📊 Monitoreo

### Métricas importantes a revisar:

1. **Tasa de éxito:**
   ```bash
   gcloud functions describe update-client-score \
     --region=us-central1 \
     --gen2 \
     --format="value(metrics.function/execution_count)"
   ```

2. **Latencia promedio:**
   - Ver en GCP Console → Cloud Functions → Métricas

3. **Errores:**
   ```bash
   gcloud functions logs read update-client-score \
     --region=us-central1 \
     --gen2 \
     --filter="severity=ERROR" \
     --limit=20
   ```

---

## ✅ Checklist de Implementación

- [ ] Deployment de Cloud Function completado
- [ ] Test manual de Cloud Function exitoso
- [ ] Configurado HTTP Request node en n8n (flujo ActualizarML)
- [ ] Probado flujo completo desde n8n
- [ ] Verificado actualización en MySQL
- [ ] Verificado cambios reflejados en frontend
- [ ] Configurado monitoreo de errores (opcional)
- [ ] Documentado triggers específicos de tu negocio

---

## 🚀 Próximos Pasos (Mejoras Futuras)

1. **Alertas Proactivas:**
   - Si prob_default > 60%, enviar alerta a Slack/Email
   - Agregar nodo en n8n que revise el response

2. **Batch Updates Programados:**
   - Cloud Scheduler cada 6 horas para clientes sin eventos
   - Recalcula todos los que no han tenido updates en 24h

3. **Dashboard de Monitoreo:**
   - BigQuery para almacenar histórico de scores
   - Looker Studio para visualizar drift del modelo

---

## 📞 Soporte

**Logs en tiempo real:**
```bash
gcloud functions logs tail update-client-score \
  --region=us-central1 \
  --gen2
```

**¿Problemas?**
1. Revisar logs de Cloud Function
2. Verificar conectividad MySQL
3. Probar query SQL manualmente
4. Verificar credenciales de Vertex AI

---

**¡Listo para producción!** 🎉

Tu sistema ahora actualiza scores en tiempo real cada vez que ocurre un evento de negocio.
