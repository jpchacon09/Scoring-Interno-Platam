# PROPUESTA: Sistema de Actualización Automática de Scores

**Versión:** 1.0
**Fecha:** Enero 2026
**Autor:** PLATAM Data Team

---

## 📋 CONTEXTO

### Situación Actual
- **Scores almacenados en CSV estático** (1,870 clientes, 39 columnas)
- **Actualización manual** cuando se necesita recalcular
- **No hay sincronización** entre eventos de negocio y recálculo de scores
- **API consume CSV** → Busca por cédula → Llama Vertex AI

### Problema Identificado
Cuando ocurren eventos críticos (nuevo plan de pagos, default, nuevo préstamo), los scores NO se actualizan automáticamente, lo que genera:
- ❌ Scores desactualizados en la API
- ❌ Decisiones de crédito con información obsoleta
- ❌ Falta de alertas en tiempo real

---

## 🎯 OBJETIVOS DE LA SOLUCIÓN

1. **Actualización selectiva**: Recalcular solo clientes afectados (no todo el dataset)
2. **Minimizar cómputo**: Evitar procesamiento innecesario
3. **Baja latencia**: Scores actualizados en <30 segundos desde el evento
4. **Bajo costo**: Aprovechar infraestructura existente
5. **Escalable**: Soportar crecimiento de clientes sin cambios arquitectónicos

---

## 🔔 TRIGGERS IDENTIFICADOS

Los eventos que deben disparar recálculo de scores son:

| Evento | Score Afectado | Features ML Afectadas | Prioridad |
|--------|----------------|------------------------|-----------|
| **Cliente adquiere plan de pagos** | Payment Plan Score | `num_planes`, `tiene_plan_activo`, `tiene_plan_pendiente` | 🔴 Alta |
| **Cliente saca préstamo nuevo** | Payment Performance | `payment_count`, `months_as_client` | 🟡 Media |
| **Cliente entra en default** | Payment Performance, Deterioration | `tiene_plan_default`, `creditos_mora`, `hist_neg_12m` | 🔴 Alta |
| **Cliente realiza un pago** | Payment Performance | `payment_count`, `pct_early`, `pct_late` | 🟢 Baja |
| **Cliente obtiene aumento de cupo** | No afecta scoring | N/A | ⚪ No aplica |

### Análisis de Triggers

**1. Adquirir plan de pagos**
- **Cálculo requerido:** `calculate_payment_plan_score()`
- **Datos necesarios:** `payment_plans_df` (histórico de planes)
- **Impacto:** Modifica 3 features ML + 1 componente score PLATAM (150 pts)

**2. Préstamo nuevo**
- **Cálculo requerido:** `calculate_payment_performance()`
- **Datos necesarios:** `payments_df` (histórico de pagos)
- **Impacto:** Modifica 2 features ML + recalcula peso híbrido

**3. Default**
- **Cálculo requerido:** `calculate_payment_performance()` + `calculate_deterioration_velocity()`
- **Datos necesarios:** `payments_df` + `payment_plans_df`
- **Impacto:** Modifica múltiples features + alerta crítica

**4. Pago realizado**
- **Cálculo requerido:** `calculate_payment_performance()` + `calculate_deterioration_velocity()`
- **Datos necesarios:** `payments_df`
- **Impacto:** Recalcula timeliness y pattern score

---

## 🏗️ ARQUITECTURAS PROPUESTAS

### **Opción 1: Event-Driven con Cloud Functions** (Recomendada)

#### Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                       SISTEMA DE NEGOCIO                        │
│              (MySQL + n8n workflows / Make.com)                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ├─ Evento: Nuevo plan de pagos
                     ├─ Evento: Nuevo préstamo
                     ├─ Evento: Default detectado
                     ├─ Evento: Pago realizado
                     │
                     ▼
        ┌────────────────────────────┐
        │  Cloud Pub/Sub (Topic)     │
        │  - platam-scoring-events   │
        └────────┬───────────────────┘
                 │
                 ├──► Mensaje: {"event": "new_payment_plan",
                 │              "cedula": "1006157869",
                 │              "plan_id": "P12345",
                 │              "timestamp": "..."}
                 │
                 ▼
        ┌────────────────────────────┐
        │  Cloud Function             │
        │  "process-scoring-event"    │
        │  - Python 3.11              │
        │  - Timeout: 60s             │
        │  - Memory: 512MB            │
        └────────┬───────────────────┘
                 │
                 ├─ 1. Identifica tipo de evento
                 ├─ 2. Lee datos de MySQL (solo el cliente)
                 ├─ 3. Recalcula scores (función específica)
                 ├─ 4. Llama a Vertex AI (predicción ML)
                 └─ 5. Actualiza:
                       ├─ BigQuery (historical storage)
                       ├─ Cloud Storage (CSV actualizado)
                       └─ Firestore (cache rápido para API)
                 │
                 ▼
        ┌────────────────────────────┐
        │  Almacenamiento Multi-capa │
        ├────────────────────────────┤
        │  Firestore (cache)         │  ← Lectura rápida API (<10ms)
        │  - TTL: 7 días             │
        │  - Key: cedula             │
        ├────────────────────────────┤
        │  Cloud Storage (CSV)       │  ← Backup para análisis
        │  - scores_v2_latest.csv    │
        ├────────────────────────────┤
        │  BigQuery (histórico)      │  ← Auditoría y dashboards
        │  - platam_scoring_history  │
        └────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │  API Cloud Run (FastAPI)   │
        │  - Lee de Firestore cache  │
        │  - Fallback a Cloud Storage│
        └────────────────────────────┘
```

#### Flujo Detallado

**1. Envío del Trigger (desde n8n o MySQL)**
```javascript
// Ejemplo: n8n workflow
POST https://pubsub.googleapis.com/v1/projects/platam-analytics/topics/platam-scoring-events:publish
{
  "messages": [{
    "data": base64encode({
      "event_type": "new_payment_plan",
      "cedula": "1006157869",
      "plan_id": "P12345",
      "timestamp": "2026-01-23T10:30:00Z",
      "metadata": {
        "plan_status": "active",
        "plan_amount": 2000000
      }
    })
  }]
}
```

**2. Cloud Function: `process_scoring_event.py`**
```python
import functions_framework
from google.cloud import firestore, storage, bigquery
from google.cloud import aiplatform
import pymysql
import pandas as pd
from internal_credit_score import calculate_credit_score
from hybrid_scoring import calculate_hybrid_score

# Conectar a servicios
db_firestore = firestore.Client()
db_mysql = pymysql.connect(host='...', user='...', password='...', database='platam')

@functions_framework.cloud_event
def process_scoring_event(cloud_event):
    """
    Procesa un evento de scoring y actualiza solo el cliente afectado
    """
    # 1. Parsear evento
    data = cloud_event.data['message']['data']
    event = json.loads(base64.b64decode(data))

    cedula = event['cedula']
    event_type = event['event_type']

    print(f"📨 Evento recibido: {event_type} para cliente {cedula}")

    # 2. Leer datos SOLO del cliente afectado desde MySQL
    client_data = get_client_from_mysql(cedula)
    payments_df = get_payments_from_mysql(cedula)
    payment_plans_df = get_payment_plans_from_mysql(cedula)

    # 3. Recalcular scores según tipo de evento
    if event_type in ['new_payment_plan', 'plan_defaulted']:
        # Solo recalcular payment plan score
        platam_score = calculate_credit_score(
            client_data, payments_df, payment_plans_df
        )

    elif event_type in ['new_payment', 'payment_late']:
        # Recalcular payment performance + deterioration
        platam_score = calculate_credit_score(
            client_data, payments_df, payment_plans_df
        )

    # 4. Calcular hybrid score
    hybrid_result = calculate_hybrid_score(
        platam_score=platam_score['total_score'],
        hcpn_score=client_data['experian_score_normalized'],
        months_as_client=client_data['months_as_client'],
        payment_count=len(payments_df)
    )

    # 5. Obtener predicción ML de Vertex AI
    ml_prediction = get_ml_prediction_from_vertex(client_data, hybrid_result)

    # 6. Guardar en múltiples destinos
    updated_record = {
        'cedula': cedula,
        'platam_score': platam_score['total_score'],
        'hybrid_score': hybrid_result['hybrid_score'],
        'ml_probability_default': ml_prediction['prob_default'],
        'updated_at': datetime.now().isoformat(),
        'triggered_by': event_type
    }

    # 6a. Firestore (cache rápido)
    db_firestore.collection('scores').document(cedula).set(updated_record)

    # 6b. BigQuery (histórico)
    bq_client = bigquery.Client()
    bq_client.insert_rows_json('platam_scoring_history', [updated_record])

    # 6c. Actualizar CSV en Cloud Storage (si se desea mantener)
    update_csv_in_storage(cedula, updated_record)

    print(f"✅ Score actualizado para {cedula}")
    return {'status': 'success', 'cedula': cedula}
```

**3. API Actualizada: `api_scoring_cedula_v3.py`**
```python
from google.cloud import firestore

db = firestore.Client()

@app.post("/predict")
async def predict_by_cedula(request: ClientRequest):
    """
    Endpoint principal: Lee de Firestore cache primero
    """
    cedula = request.cedula

    # 1. Intentar leer de Firestore (cache)
    doc = db.collection('scores').document(cedula).get()

    if doc.exists:
        client_data = doc.to_dict()
        print(f"✅ Cache hit: {cedula}")
    else:
        # 2. Fallback: Leer de Cloud Storage CSV
        client_data = get_from_csv_storage(cedula)

        # 3. Guardar en cache para próximas consultas
        if client_data:
            db.collection('scores').document(cedula).set(client_data)

    # Resto del flujo igual...
    return CompleteResponse(...)
```

#### Ventajas ✅
- **Ultra-rápido**: Actualiza solo 1 cliente (<5 segundos)
- **Bajo costo**: Cloud Functions factura por ejecución (1M invocaciones gratis/mes)
- **Escalable**: Automáticamente escala con carga
- **Desacoplado**: Pub/Sub permite múltiples consumidores
- **Firestore cache**: API responde en <10ms
- **Auditable**: BigQuery guarda historial completo

#### Desventajas ❌
- Requiere configurar Pub/Sub, Firestore, Cloud Functions
- Más componentes = más puntos de fallo
- Requiere configurar triggers en n8n/MySQL

#### Costo Estimado Mensual
| Componente | Uso Estimado | Costo |
|------------|--------------|-------|
| Cloud Functions | 10,000 eventos/mes × 1s × 512MB | $0.50 |
| Pub/Sub | 10,000 mensajes/mes | $0.40 |
| Firestore | 1,870 docs + 50,000 reads | $1.50 |
| BigQuery | 10,000 inserts + storage | $2.00 |
| **TOTAL** | | **$4.40/mes** |

---

### **Opción 2: Microservicio de Actualización (Síncrono)**

#### Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│              SISTEMA DE NEGOCIO (MySQL/n8n)             │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP POST directo
                     │
                     ▼
        ┌────────────────────────────────┐
        │  Cloud Run Service             │
        │  "scoring-updater-service"     │
        │  - Python 3.11                 │
        │  - Min instances: 1            │
        │  - Max instances: 10           │
        │  - Concurrency: 10             │
        └────────┬───────────────────────┘
                 │
                 │ POST /update-score
                 │ {"cedula": "1006157869", "event": "new_plan"}
                 │
                 ├─ 1. Valida request
                 ├─ 2. Lee de MySQL (conexión pool)
                 ├─ 3. Recalcula scores
                 ├─ 4. Llama Vertex AI
                 ├─ 5. Actualiza:
                 │     ├─ MySQL (scores_table)
                 │     ├─ Firestore (cache)
                 │     └─ Cloud Storage (CSV backup)
                 │
                 ▼
        ┌────────────────────────────────┐
        │  MySQL Database                │
        │  - tabla: client_scores        │
        │  - índice: cedula              │
        └────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────┐
        │  API Cloud Run (FastAPI)       │
        │  - Lee de MySQL directo        │
        │  - Cache en memoria (TTL 5min) │
        └────────────────────────────────┘
```

#### Flujo Detallado

**1. n8n Workflow llama directamente al servicio**
```javascript
// n8n HTTP Request node
POST https://scoring-updater-741488896424.us-central1.run.app/update-score
{
  "cedula": "1006157869",
  "event_type": "new_payment_plan",
  "event_data": {
    "plan_id": "P12345",
    "plan_status": "active"
  }
}
```

**2. Servicio: `scoring_updater_service.py`**
```python
from fastapi import FastAPI, BackgroundTasks
import pymysql
from contextlib import contextmanager

app = FastAPI(title="Scoring Updater Service")

# Connection pool para MySQL
db_pool = pymysql.pooling.SimpleConnectionPool(
    pool_size=5,
    host=os.getenv('MYSQL_HOST'),
    user=os.getenv('MYSQL_USER'),
    password=os.getenv('MYSQL_PASSWORD'),
    database='platam'
)

@app.post("/update-score")
async def update_score(request: UpdateRequest, background_tasks: BackgroundTasks):
    """
    Endpoint síncrono que recalcula y actualiza score de UN cliente
    """
    cedula = request.cedula
    event_type = request.event_type

    # 1. Leer datos del cliente desde MySQL
    with get_db_connection() as conn:
        client_data = pd.read_sql(
            f"SELECT * FROM clients WHERE cedula = '{cedula}'",
            conn
        ).iloc[0].to_dict()

        payments_df = pd.read_sql(
            f"SELECT * FROM payments WHERE client_cedula = '{cedula}' ORDER BY payment_date DESC LIMIT 100",
            conn
        )

        payment_plans_df = pd.read_sql(
            f"SELECT * FROM payment_plans WHERE client_cedula = '{cedula}'",
            conn
        )

    # 2. Recalcular scores
    platam_result = calculate_credit_score(
        client_data, payments_df, payment_plans_df
    )

    hybrid_result = calculate_hybrid_score(
        platam_score=platam_result['total_score'],
        hcpn_score=client_data.get('experian_score_normalized'),
        months_as_client=client_data['months_as_client'],
        payment_count=len(payments_df)
    )

    # 3. Predicción ML (Vertex AI)
    ml_pred = get_ml_prediction_vertex(client_data, hybrid_result)

    # 4. Actualizar en MySQL
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE clients
            SET platam_score = {platam_result['total_score']},
                hybrid_score = {hybrid_result['hybrid_score']},
                ml_prob_default = {ml_pred['prob_default']},
                updated_at = NOW(),
                updated_by_event = '{event_type}'
            WHERE cedula = '{cedula}'
        """)
        conn.commit()

    # 5. Background: Actualizar Firestore y CSV (no bloqueante)
    background_tasks.add_task(
        update_cache_async, cedula, {
            'platam_score': platam_result['total_score'],
            'hybrid_score': hybrid_result['hybrid_score'],
            'ml_prob_default': ml_pred['prob_default']
        }
    )

    return {
        'status': 'success',
        'cedula': cedula,
        'platam_score': platam_result['total_score'],
        'hybrid_score': hybrid_result['hybrid_score'],
        'processing_time_ms': 2500
    }

@app.post("/update-batch")
async def update_batch(request: BatchUpdateRequest):
    """
    Endpoint para actualizar múltiples clientes (batch)
    Útil para actualizaciones masivas o reconciliaciones
    """
    cedulas = request.cedulas  # Lista de cédulas

    results = []
    for cedula in cedulas[:50]:  # Límite 50 por request
        result = await update_single_client(cedula, "batch_update")
        results.append(result)

    return {
        'total_processed': len(results),
        'successful': sum(1 for r in results if r['status'] == 'success'),
        'failed': sum(1 for r in results if r['status'] == 'error')
    }
```

**3. API Principal actualizada**
```python
from functools import lru_cache
import pymysql

@lru_cache(maxsize=1000, ttl=300)  # Cache 5 minutos
def get_client_score(cedula: str):
    """Lee score desde MySQL con cache en memoria"""
    with get_db_connection() as conn:
        result = pd.read_sql(
            f"SELECT * FROM clients WHERE cedula = '{cedula}'",
            conn
        )
    return result.iloc[0].to_dict()

@app.post("/predict")
async def predict(request: ClientRequest):
    """Lee de MySQL con cache en memoria"""
    client_data = get_client_score(request.cedula)
    # Resto del flujo...
```

#### Ventajas ✅
- **Simple**: Un solo servicio para actualización
- **Síncrono**: n8n recibe confirmación inmediata
- **Sin dependencias extra**: No requiere Pub/Sub ni Firestore
- **Fácil debugging**: Logs centralizados en Cloud Run
- **Batch support**: Puede actualizar múltiples clientes

#### Desventajas ❌
- Requiere instancia mínima siempre corriendo ($20-30/mes)
- No escala tan bien como Cloud Functions
- Actualizar CSV completo es lento

#### Costo Estimado Mensual
| Componente | Uso Estimado | Costo |
|------------|--------------|-------|
| Cloud Run (min 1 instance) | 730 horas × 512MB | $25.00 |
| Cloud SQL (MySQL) | db-f1-micro | $15.00 |
| Vertex AI calls | 10,000 predicciones | $1.50 |
| **TOTAL** | | **$41.50/mes** |

---

### **Opción 3: Híbrida con Batch Updates Programados**

#### Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                   SISTEMA DE NEGOCIO                         │
│                    (MySQL + n8n)                             │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ├─ Eventos críticos (default, nuevo plan)
                     │  → Cloud Function (actualización inmediata)
                     │
                     └─ Eventos normales (pagos, consultas)
                        → Se acumulan en MySQL
                        → Cloud Scheduler actualiza cada 6 horas
                     │
        ┌────────────┴────────────┬─────────────────────────────┐
        │                         │                             │
        ▼                         ▼                             ▼
  [Cloud Function]    [Cloud Scheduler → Batch Job]    [MySQL DB]
  (eventos críticos)  (cada 6 horas)                   (fuente de verdad)
        │                         │                             │
        └─────────────────────────┴─────────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │  Cloud Storage (CSV backup)  │
                    │  - scores_snapshot.csv       │
                    └──────────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │  API Cloud Run               │
                    │  - Lee de MySQL primero      │
                    │  - Fallback a CSV            │
                    └──────────────────────────────┘
```

#### Flujo Detallado

**1. Para eventos CRÍTICOS (default, nuevo plan default)**
```javascript
// n8n workflow: Trigger inmediato vía Cloud Function
IF evento == "default" OR evento == "plan_default":
    POST https://us-central1-platam-analytics.cloudfunctions.net/update-score-critical
    {
      "cedula": "1006157869",
      "event": "client_default"
    }
```

**2. Para eventos NORMALES (pagos, consultas)**
```javascript
// n8n workflow: Solo insertar en MySQL, batch procesará después
INSERT INTO events_queue (cedula, event_type, created_at)
VALUES ('1006157869', 'payment_made', NOW())
```

**3. Cloud Scheduler: Batch Job cada 6 horas**
```bash
# Cron: 0 */6 * * * (cada 6 horas)
gcloud scheduler jobs create http batch-score-update \
  --schedule="0 */6 * * *" \
  --uri="https://us-central1-platam-analytics.cloudfunctions.net/batch-update-scores" \
  --http-method=POST
```

**4. Batch Function: `batch_update_scores.py`**
```python
@functions_framework.http
def batch_update_scores(request):
    """
    Procesa todos los clientes con eventos pendientes
    Optimizado para procesar en lotes de 100
    """
    # 1. Leer eventos pendientes desde MySQL
    with get_db_connection() as conn:
        pending_events = pd.read_sql("""
            SELECT DISTINCT cedula, MAX(event_type) as last_event
            FROM events_queue
            WHERE processed = FALSE
            GROUP BY cedula
            ORDER BY created_at DESC
            LIMIT 500
        """, conn)

    print(f"📊 Procesando {len(pending_events)} clientes con cambios")

    # 2. Procesar en paralelo (ThreadPoolExecutor)
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(update_single_client, row['cedula']): row['cedula']
            for _, row in pending_events.iterrows()
        }

        for future in as_completed(futures):
            cedula = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"❌ Error procesando {cedula}: {e}")

    # 3. Marcar eventos como procesados
    with get_db_connection() as conn:
        cedulas_str = "','".join([r['cedula'] for r in results if r['status'] == 'success'])
        conn.execute(f"""
            UPDATE events_queue
            SET processed = TRUE, processed_at = NOW()
            WHERE cedula IN ('{cedulas_str}')
        """)

    # 4. Generar CSV snapshot actualizado
    export_scores_to_csv()

    return {
        'status': 'batch_completed',
        'total_processed': len(results),
        'successful': sum(1 for r in results if r['status'] == 'success'),
        'timestamp': datetime.now().isoformat()
    }
```

#### Ventajas ✅
- **Mejor de ambos mundos**: Inmediato para críticos, batch para normales
- **Costo bajo**: Solo paga por ejecuciones (no instancia 24/7)
- **Eficiente**: Procesa en paralelo con ThreadPoolExecutor
- **Simple**: MySQL como única fuente de verdad

#### Desventajas ❌
- Latencia de hasta 6 horas para eventos normales
- Más complejidad en la lógica de "qué es crítico vs normal"
- Requiere tabla `events_queue` en MySQL

#### Costo Estimado Mensual
| Componente | Uso Estimado | Costo |
|------------|--------------|-------|
| Cloud Functions (críticos) | 1,000 eventos/mes × 2s | $0.20 |
| Cloud Functions (batch) | 120 ejecuciones/mes × 60s | $0.30 |
| Cloud Scheduler | 1 job | $0.10 |
| Cloud SQL (MySQL) | db-f1-micro | $15.00 |
| **TOTAL** | | **$15.60/mes** |

---

## 📊 COMPARACIÓN DE OPCIONES

| Criterio | Opción 1: Event-Driven | Opción 2: Microservicio | Opción 3: Híbrida |
|----------|------------------------|-------------------------|-------------------|
| **Costo mensual** | $4.40 | $41.50 | $15.60 |
| **Latencia** | <5s | <3s | <5s críticos, <6h normales |
| **Escalabilidad** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Complejidad setup** | Alta | Media | Media |
| **Mantenibilidad** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Debugging** | Medio | Fácil | Medio |
| **Auditoría** | Excelente (BigQuery) | Buena (MySQL logs) | Buena (MySQL + logs) |
| **Fallback** | Firestore → Cloud Storage | MySQL → Cache memoria | MySQL → CSV |
| **Requiere MySQL siempre-on** | No | Sí | Sí |

---

## 🎯 RECOMENDACIÓN: Opción 3 (Híbrida)

### Por qué Opción 3 es la mejor

1. **Costo-beneficio óptimo**: $15.60/mes vs $41.50 de Opción 2
2. **Prioriza lo crítico**: Defaults y planes malos se actualizan <5s
3. **Eficiente con volumen**: Pagos normales en batch cada 6 horas es suficiente
4. **MySQL como fuente de verdad**: Ya existe, evita Firestore
5. **Fácil de implementar**: 2 Cloud Functions + 1 Cloud Scheduler
6. **Escalable**: ThreadPoolExecutor procesa 500 clientes en ~60s

### Implementación Paso a Paso

#### Fase 1: Setup Infraestructura (Semana 1)

**1. Crear tabla de eventos en MySQL**
```sql
CREATE TABLE events_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(20) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP NULL,
    INDEX idx_cedula (cedula),
    INDEX idx_processed (processed, created_at)
);
```

**2. Actualizar tabla de clientes**
```sql
ALTER TABLE clients ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
ALTER TABLE clients ADD COLUMN updated_by_event VARCHAR(50);
```

**3. Deploy Cloud Function para eventos críticos**
```bash
cd cloud_functions/update_score_critical
gcloud functions deploy update-score-critical \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --memory 512MB \
  --timeout 60s \
  --set-env-vars PROJECT_ID=platam-analytics
```

**4. Deploy Cloud Function para batch**
```bash
cd cloud_functions/batch_update
gcloud functions deploy batch-update-scores \
  --runtime python311 \
  --trigger-http \
  --memory 1024MB \
  --timeout 540s \
  --set-env-vars PROJECT_ID=platam-analytics
```

**5. Configurar Cloud Scheduler**
```bash
gcloud scheduler jobs create http batch-score-update \
  --schedule="0 */6 * * *" \
  --uri="https://us-central1-platam-analytics.cloudfunctions.net/batch-update-scores" \
  --http-method=POST \
  --time-zone="America/Bogota"
```

#### Fase 2: Actualizar n8n Workflows (Semana 2)

**Workflow 1: Eventos Críticos**
```
[Trigger: MySQL] → [Filtro: evento crítico] → [HTTP Request a Cloud Function]

Filtro crítico:
- event_type IN ('client_default', 'plan_defaulted', 'plan_cancelled')

HTTP Request:
POST https://us-central1-platam-analytics.cloudfunctions.net/update-score-critical
Body: {"cedula": "{{$json.cedula}}", "event": "{{$json.event_type}}"}
```

**Workflow 2: Eventos Normales**
```
[Trigger: MySQL] → [Filtro: evento normal] → [Insert a events_queue]

Filtro normal:
- event_type IN ('payment_made', 'payment_late', 'new_loan', 'limit_increase')

Insert:
INSERT INTO events_queue (cedula, event_type, event_data)
VALUES ('{{$json.cedula}}', '{{$json.event_type}}', '{{$json}}')
```

#### Fase 3: Actualizar API (Semana 3)

**Modificar `api_scoring_cedula.py`**
```python
import pymysql
from functools import lru_cache
from datetime import datetime, timedelta

# Connection pool
db_pool = create_engine(f"mysql+pymysql://{user}:{pwd}@{host}/platam")

@lru_cache(maxsize=500)
def get_client_from_mysql(cedula: str) -> dict:
    """Lee score actualizado desde MySQL con cache 5 minutos"""
    with db_pool.connect() as conn:
        result = pd.read_sql(
            f"SELECT * FROM clients WHERE cedula = '{cedula}'",
            conn
        )

    if result.empty:
        return None

    return result.iloc[0].to_dict()

@app.post("/predict")
async def predict(request: ClientRequest):
    """Lee de MySQL en tiempo real"""
    client_data = get_client_from_mysql(request.cedula)

    if not client_data:
        # Fallback: buscar en CSV backup
        client_data = get_from_csv_backup(request.cedula)

    # Resto del flujo igual...
```

#### Fase 4: Testing y Validación (Semana 4)

**1. Test unitario de Cloud Functions**
```bash
# Test función crítica
curl -X POST https://us-central1-platam-analytics.cloudfunctions.net/update-score-critical \
  -H "Content-Type: application/json" \
  -d '{"cedula":"1006157869", "event":"client_default"}'

# Verificar en MySQL
mysql> SELECT cedula, platam_score, hybrid_score, updated_at, updated_by_event
       FROM clients WHERE cedula = '1006157869';
```

**2. Test batch function**
```bash
# Insertar eventos de prueba
INSERT INTO events_queue (cedula, event_type) VALUES
  ('1006157869', 'payment_made'),
  ('1192925596', 'payment_late');

# Trigger batch manualmente
curl -X POST https://us-central1-platam-analytics.cloudfunctions.net/batch-update-scores

# Verificar processed = TRUE
mysql> SELECT * FROM events_queue WHERE processed = TRUE;
```

**3. Test API**
```bash
# Verificar que API lee de MySQL
curl -X POST https://scoring-api-741488896424.us-central1.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{"cedula":"1006157869"}'
```

---

## 📈 IMPACTO EN EL MODELO ML

### ¿Cuándo requiere reentrenamiento?

El modelo ML **NO requiere reentrenamiento** por eventos individuales. Solo cuando:

1. **Drift significativo** (trimestral con `check_model_drift.py`)
2. **Nuevos patrones de default** no capturados (cada 6 meses)
3. **Features nuevas agregadas** (ej: agregar más demografía)

### ¿Cómo se actualiza la predicción ML?

**Predicción ML se recalcula en cada evento**, pero usa el **mismo modelo entrenado**:

```python
# El modelo YA está desplegado en Vertex AI
# Solo necesitamos llamarlo con features actualizadas

def update_ml_prediction(cedula: str):
    """
    Recalcula predicción ML con features actualizadas
    NO reentrena el modelo
    """
    # 1. Leer features actualizadas de MySQL
    client_data = get_client_from_mysql(cedula)

    # 2. Extraer 22 features en orden correcto
    features = extract_features_for_ml(client_data)

    # 3. Llamar al MISMO modelo en Vertex AI
    prediction = endpoint.predict(instances=[features])

    # 4. Guardar nueva probabilidad en MySQL
    save_ml_prediction(cedula, prediction)
```

### Monitoreo de Drift

**Cloud Function adicional para drift mensual**:
```bash
gcloud scheduler jobs create http monthly-drift-check \
  --schedule="0 0 1 * *" \
  --uri="https://us-central1-platam-analytics.cloudfunctions.net/check-model-drift" \
  --http-method=POST
```

```python
@functions_framework.http
def check_model_drift(request):
    """
    Ejecuta check_model_drift.py mensualmente
    Alerta si AUC cae >5%
    """
    from check_model_drift import detect_drift

    drift_report = detect_drift(
        model_version='v2.2',
        data_path='gs://platam-scoring/latest_scores.csv'
    )

    if drift_report['auc_drop'] > 0.05:
        send_slack_alert(f"⚠️ Model drift detectado: AUC cayó {drift_report['auc_drop']*100:.1f}%")

    return drift_report
```

---

## 🚀 PLAN DE ROLLOUT

### Cronograma (4 semanas)

| Semana | Tareas | Responsable |
|--------|--------|-------------|
| **Semana 1** | - Crear tabla events_queue<br>- Deploy Cloud Functions<br>- Setup Cloud Scheduler | DevOps |
| **Semana 2** | - Actualizar workflows n8n<br>- Testing de triggers<br>- Configurar alertas | Data Team |
| **Semana 3** | - Migrar API a lectura MySQL<br>- Testing end-to-end<br>- Performance testing | Backend |
| **Semana 4** | - Rollout gradual 10% → 50% → 100%<br>- Monitoreo intensivo<br>- Ajustes finales | Full Team |

### Métricas de Éxito

1. **Latencia de actualización**: <5s para eventos críticos
2. **Batch processing time**: <60s para 500 clientes
3. **API response time**: <500ms (igual o mejor que actual)
4. **Costo mensual**: <$20/mes
5. **Uptime**: >99.9%

---

## 📝 PRÓXIMOS PASOS INMEDIATOS

1. ✅ **Aprobar arquitectura** (Opción 3 recomendada)
2. ⏳ **Crear tabla events_queue en MySQL**
3. ⏳ **Desarrollar Cloud Function para eventos críticos**
4. ⏳ **Configurar Cloud Scheduler para batch**
5. ⏳ **Actualizar workflow n8n para triggers**

---

**Documento creado por:** PLATAM Data Team
**Última actualización:** Enero 23, 2026
**Versión:** 1.0
