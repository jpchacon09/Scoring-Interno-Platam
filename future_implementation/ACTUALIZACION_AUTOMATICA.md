# 🔄 Sistema de Actualización Automática

## Estado Actual vs Propuesto

### ❌ ACTUAL (Manual):
```
┌─────────────────────────────────────────────────────┐
│ 1. Exportas CSV manualmente                         │
│ 2. Calculas scores en Python/Excel                  │
│ 3. Subes CSV a Cloud Run                            │
│ 4. Reconstruyes imagen Docker                       │
│ 5. Redespliegas API                                 │
│                                                      │
│ Frecuencia: Manual, cuando te acuerdes              │
│ Tiempo: ~30 minutos cada vez                        │
└─────────────────────────────────────────────────────┘
```

### ✅ PROPUESTO (Automático):
```
┌─────────────────────────────────────────────────────┐
│ OPCIÓN A: Actualización CSV Semanal                 │
├─────────────────────────────────────────────────────┤
│ 1. Query SQL semanal (Cloud Scheduler)              │
│ 2. Calcula scores híbridos automáticamente          │
│ 3. Guarda en Cloud Storage                          │
│ 4. API carga CSV al iniciar                         │
│ 5. Refresh de instancias de Cloud Run               │
│                                                      │
│ Frecuencia: Automática, cada domingo 2am            │
│ Tiempo: ~0 minutos (desatendido)                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ OPCIÓN B: Conexión Directa a Base de Datos          │
├─────────────────────────────────────────────────────┤
│ 1. API se conecta directo a Cloud SQL               │
│ 2. Cada request hace query fresh                    │
│ 3. Calcula score híbrido on-the-fly                 │
│ 4. Llama a Vertex AI con features actualizadas      │
│                                                      │
│ Frecuencia: Real-time, siempre actualizado          │
│ Latencia: ~800ms (vs 500ms con CSV)                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ OPCIÓN C: Híbrido (Recomendado)                     │
├─────────────────────────────────────────────────────┤
│ 1. API usa CSV en memoria (rápido)                  │
│ 2. Cloud Function actualiza CSV cada semana         │
│ 3. Si cliente no está en CSV → Query a DB           │
│ 4. Mejor de ambos mundos                            │
│                                                      │
│ Frecuencia: Automática semanal + fallback real-time │
│ Latencia: 500ms (caché) / 800ms (DB)               │
└─────────────────────────────────────────────────────┘
```

---

## 🔍 ¿Qué pasa con los datos actualizados y el ML?

### ✅ SÍ afecta las predicciones (incluso sin reentrenar):

```python
# EJEMPLO CONCRETO:

# Hace 3 meses (Octubre 2025):
Cliente "74858339":
  platam_score: 575
  payment_count: 5
  days_past_due_mean: 15
  months_as_client: 6

Modelo predice → 45% default (riesgo medio-alto)
                 ↑ Usa reglas fijas pero con datos viejos

# HOY (Enero 2026) - Datos actualizados:
Cliente "74858339":
  platam_score: 720  ← Mejoró!
  payment_count: 18  ← Más pagos
  days_past_due_mean: 2  ← Menos mora
  months_as_client: 9  ← Más tiempo

Modelo predice → 12% default (riesgo bajo)
                 ↑ MISMAS reglas pero con datos nuevos!
```

**CLAVE:** El modelo usa **reglas fijas** pero **datos frescos**:
- ✅ Predicciones MÁS precisas (refleja situación actual)
- ❌ Modelo NO aprende nuevos patrones (necesita reentrenamiento)

---

## 🛠️ Implementación: Opción C (Recomendada)

### Arquitectura:

```
┌──────────────────┐
│  Base de Datos   │  ← Tu fuente de verdad
│  (Cloud SQL)     │
└────────┬─────────┘
         │
         │ Query SQL semanal
         │ (Cloud Scheduler + Cloud Function)
         ↓
┌──────────────────┐
│ Cloud Storage    │  ← hybrid_scores.csv actualizado
│ Bucket           │
└────────┬─────────┘
         │
         │ API carga al iniciar
         ↓
┌──────────────────┐
│  Cloud Run API   │  ← Responde con datos frescos
│  (En memoria)    │
└────────┬─────────┘
         │
         │ Si cliente no existe en CSV
         │ → Query directo a DB
         ↓
┌──────────────────┐
│  Vertex AI ML    │  ← Predice con features actualizadas
└──────────────────┘
```

---

## 📋 Requerimientos del SQL Query

Para que esto funcione, tu query SQL semanal debe traer:

### Tabla: `clientes_scoring_v2` (ejemplo)

```sql
SELECT
    -- Identificación
    c.cedula,
    c.client_id,
    c.client_name,

    -- Score Experian (externo)
    e.experian_score,
    e.experian_score / 950.0 * 1000 AS experian_score_normalized,

    -- Features de historial de pagos
    CASE WHEN COUNT(p.payment_id) > 0 THEN TRUE ELSE FALSE END AS has_payment_history,
    COUNT(DISTINCT DATE_TRUNC('month', p.payment_date)) AS payment_history_months,
    COUNT(p.payment_id) AS payment_id_count,
    AVG(p.days_past_due) AS days_past_due_mean,
    MAX(p.days_past_due) AS days_past_due_max,

    -- Porcentajes early/late
    SUM(CASE WHEN p.days_past_due < 0 THEN 1 ELSE 0 END)::FLOAT /
        NULLIF(COUNT(p.payment_id), 0) AS pct_early,
    SUM(CASE WHEN p.days_past_due > 0 THEN 1 ELSE 0 END)::FLOAT /
        NULLIF(COUNT(p.payment_id), 0) AS pct_late,

    -- Días desde último pago
    CURRENT_DATE - MAX(p.payment_date) AS days_since_last_payment,

    -- Crédito y utilización
    c.cupo_total,
    c.saldo_actual::FLOAT / NULLIF(c.cupo_total, 0) AS pct_utilization,

    -- Plan de pagos actual
    pl.status AS status_plan,

    -- Perfil de riesgo
    c.risk_profile,

    -- Antigüedad
    EXTRACT(EPOCH FROM (CURRENT_DATE - c.created_date))/2592000 AS months_as_client,
    COUNT(p.payment_id) AS payment_count,

    -- Features de planes de pago
    CASE WHEN pl.status = 'activo' THEN TRUE ELSE FALSE END AS tiene_plan_activo,
    CASE WHEN pl.status = 'default' THEN TRUE ELSE FALSE END AS tiene_plan_default,
    CASE WHEN pl.status = 'pendiente' THEN TRUE ELSE FALSE END AS tiene_plan_pendiente,
    COUNT(DISTINCT pl.plan_id) AS num_planes,

    -- Metadata
    CURRENT_DATE AS calculation_date

FROM clientes c
LEFT JOIN pagos p ON c.client_id = p.client_id
LEFT JOIN experian_scores e ON c.cedula = e.cedula
LEFT JOIN planes_pago pl ON c.client_id = pl.client_id

WHERE c.status = 'activo'  -- Solo clientes activos

GROUP BY
    c.cedula, c.client_id, c.client_name,
    e.experian_score, c.cupo_total, c.saldo_actual,
    c.risk_profile, c.created_date, pl.status

ORDER BY c.cedula;
```

### Columnas mínimas requeridas:

**Identificación:**
- `cedula` (o `client_id`)
- `client_name` (opcional)

**Scores base:**
- `experian_score` (0-950)
- `experian_score_normalized` (0-1000)

**17 Features de ML:**
1. `platam_score` (se calcula después)
2. `experian_score_normalized`
3. `score_payment_performance` (se calcula)
4. `score_payment_plan` (se calcula)
5. `score_deterioration` (se calcula)
6. `payment_count`
7. `months_as_client`
8. `days_past_due_mean`
9. `days_past_due_max`
10. `pct_early`
11. `pct_late`
12. `peso_platam_usado` (se calcula)
13. `peso_hcpn_usado` (se calcula)
14. `tiene_plan_activo`
15. `tiene_plan_default`
16. `tiene_plan_pendiente`
17. `num_planes`

---

## 🚀 Plan de Implementación

### Fase 1: Script de Actualización Semanal (2-3 horas)

1. **Cloud Function** que:
   - Ejecuta tu query SQL
   - Calcula scores PLATAM
   - Calcula score híbrido
   - Guarda CSV en Cloud Storage

2. **Cloud Scheduler**:
   - Trigger: Cada domingo a las 2am
   - Llama a la Cloud Function

3. **API actualizada**:
   - Al iniciar, descarga CSV de Cloud Storage
   - Fallback: Query directo a DB si cliente no existe

### Fase 2: Conexión Directa (opcional, futuro)

Si quieres real-time total:
- API se conecta a Cloud SQL
- Calcula scores on-the-fly
- Sin necesidad de CSV

---

## 💰 Costos Estimados

### Opción A (CSV semanal):
- Cloud Function: ~$0 (2M invocaciones gratis/mes)
- Cloud Scheduler: ~$0.10/mes
- Cloud Storage: ~$0.02/mes (1 CSV de ~500KB)
- **Total: ~$0.12/mes** 💰

### Opción B (DB directa):
- Cloud SQL (db-f1-micro): ~$8/mes
- Conexiones: ~$0
- **Total: ~$8/mes**

### Opción C (Híbrido - Recomendado):
- Cloud Function + Storage: ~$0.12/mes
- Cloud SQL (solo fallback): ~$8/mes
- **Total: ~$8.12/mes**

---

## 🔄 Diferencia: Actualizar Datos vs Reentrenar Modelo

### ✅ Actualizar datos semanalmente:

```
Semana 1: Cliente tiene score 600 → ML predice 35% default
Semana 2: Cliente pagó, score sube a 700 → ML predice 15% default
         ↑ MISMO modelo, NUEVOS datos, NUEVA predicción
```

**Efecto:**
- ✅ Predicciones reflejan situación actual del cliente
- ✅ Más precisión sin reentrenar
- ✅ Automático y rápido

### ✅ Reentrenar modelo (cada 3-6 meses):

```
Octubre 2025: Modelo aprende patrones con datos históricos
Enero 2026: Comportamiento de clientes cambió (nueva economía)
           → Reentrenar con datos nuevos
           → Modelo aprende NUEVOS patrones
```

**Efecto:**
- ✅ Modelo aprende nuevas reglas de negocio
- ✅ Detecta nuevos patrones de riesgo
- ✅ Mejora precisión a largo plazo

---

## 📊 Resumen Visual

```
┌────────────────────────────────────────────────────────┐
│ FLUJO COMPLETO RECOMENDADO                             │
├────────────────────────────────────────────────────────┤
│                                                        │
│ SEMANAL (Automático):                                  │
│ ├─ Query SQL → Datos frescos                          │
│ ├─ Calcula scores híbridos                            │
│ ├─ Actualiza CSV en Cloud Storage                     │
│ └─ API usa datos actualizados                         │
│                                                        │
│ EFECTO: Predicciones con datos actuales               │
│         (reglas del modelo siguen iguales)             │
│                                                        │
├────────────────────────────────────────────────────────┤
│                                                        │
│ TRIMESTRAL (Manual):                                   │
│ ├─ Revisas script check_model_drift.py                │
│ ├─ Si es necesario: Reentrenar modelo                 │
│ ├─ Validar nuevo modelo                               │
│ └─ Desplegar a Vertex AI                              │
│                                                        │
│ EFECTO: Modelo aprende nuevos patrones                │
│         (reglas actualizadas)                          │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## ✅ Próximos Pasos

1. **Define tu SQL query** con las columnas que te especifiqué
2. **Te creo la Cloud Function** que procesa el query y calcula scores
3. **Configuramos Cloud Scheduler** para ejecución semanal
4. **Actualizamos la API** para cargar desde Cloud Storage
5. **Probamos todo el flujo** end-to-end

---

## ❓ Preguntas para ti:

1. **¿Qué base de datos usas?** (PostgreSQL, MySQL, BigQuery, otra?)
2. **¿Ya tienes Cloud SQL configurado** o necesitas ayuda con eso?
3. **¿Prefieres Opción A (CSV), B (DB directa) o C (Híbrido)?**
4. **¿Quieres que empecemos con el SQL query?** (comparte estructura de tus tablas)
5. **¿Qué día/hora prefieres** para la actualización semanal?

Dime y te ayudo a implementarlo! 🚀
