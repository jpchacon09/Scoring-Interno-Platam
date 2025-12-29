# Roadmap de Machine Learning con Vertex AI

**Fecha:** 29 de Diciembre de 2025
**Sistema Actual:** PLATAM Scoring V2.0 + Híbrido
**Objetivo:** Migración a Machine Learning con Google Vertex AI

---

## 📋 Tabla de Contenidos

1. [Estado Actual](#estado-actual)
2. [¿Qué Nos Falta?](#qué-nos-falta)
3. [Train/Test Split](#traintest-split-estrategia)
4. [Arquitectura del Sistema ML](#arquitectura-del-sistema-ml)
5. [Triggers y Recálculo](#triggers-y-recálculo)
6. [Plan de Implementación](#plan-de-implementación-por-fases)
7. [Preparación de Datos](#preparación-de-datos-detallada)

---

## 🎯 Estado Actual

### Lo Que YA Tenemos ✅

1. **Scoring V2.0 Robusto**
   - 3 componentes bien calibrados
   - 1,836 clientes calculados
   - Promedio: 724.7 puntos

2. **Sistema Híbrido Inteligente**
   - Combina PLATAM + HCPN con pesos dinámicos
   - Promedio: 746.9 puntos
   - Estabilidad: Desviación estándar 159.4

3. **Datos Estructurados**
   - `hybrid_scores.csv` con 30 columnas
   - `DASHBOARD_SCORING_DINAMICO.csv` con 62 columnas ⭐
   - Variables categorizadas y limpias

4. **Infraestructura de Análisis**
   - Scripts de cálculo automatizados
   - Visualizaciones profesionales
   - Documentación completa

### Ventaja Competitiva

Ya tenemos **scores de referencia** (V2.0 y Híbrido) que podemos usar como:
- **Target labels** para entrenamiento supervisado
- **Baseline** para comparar performance del ML
- **Guardrail** en producción (nunca 100% ML)

---

## 🔧 ¿Qué Nos Falta?

### 1. Datos de Default Reales (CRÍTICO) ⚠️

**Problema:** NO tenemos variable de default histórica

**Lo que necesitamos:**
```python
# Columna que identifique clientes que cayeron en default
df['default_flag'] = 0 o 1

Ejemplos:
- Cliente A: 5 pagos a tiempo → default_flag = 0
- Cliente B: 3 pagos + 1 incumplimiento >90d → default_flag = 1
```

**Definición de Default** (sugerida):
- Mora >90 días consecutivos
- Cargo a pérdidas
- Cuenta enviada a cobranza
- Score de castigo

**Acción Inmediata:**
1. Revisar base de datos histórica
2. Identificar clientes con incumplimientos severos
3. Crear columna `default_flag` en datos
4. Validar con equipo de cobranza/riesgo

### 2. Datos Temporales para Validación

**Problema:** Necesitamos datos históricos con fechas

**Lo que necesitamos:**
- Snapshot de scores en diferentes momentos
- Comportamiento post-score (¿el cliente pagó? ¿incumplió?)
- Mínimo 6-12 meses de historial

**Ejemplo:**
```
Cliente  | Score_Enero | Score_Junio | Default_Flag (Julio-Dic)
---------|-------------|-------------|-------------------------
123      | 750         | 720         | 0 (pagó normal)
456      | 650         | 580         | 1 (incumplió en Agosto)
```

### 3. Feature Engineering

**Lo que tenemos:**
- Variables básicas (DPD, pagos, utilization)

**Lo que necesitamos agregar:**
- Features de tendencia (DPD último mes vs hace 6 meses)
- Features de estacionalidad (mes del año, día del pago)
- Features de interacción (utilización × DPD)
- Features derivadas del HCPN (ratio deuda/ingreso)

### 4. Configuración de Vertex AI

**Lo que necesitamos:**
1. Proyecto GCP creado
2. API de Vertex AI habilitada
3. Bucket de GCS para datos
4. Service account con permisos
5. Créditos GCP asignados

### 5. Pipeline de ML

**Lo que necesitamos construir:**
1. Script de preparación de datos
2. Script de entrenamiento
3. Script de evaluación
4. Script de deployment
5. Script de monitoreo

---

## 📊 Train/Test Split - Estrategia

### ¿Por Qué SÍ Dividir?

**Respuesta:** SÍ, SIEMPRE dividir en train/test para:
- Validar que el modelo generaliza
- Evitar overfitting
- Estimar performance real en producción
- Comparar múltiples modelos objetivamente

### Estrategia Recomendada: **Temporal + Estratificado**

#### Opción 1: Split Temporal (PREFERIDO)

```python
# 80% datos antiguos = TRAIN
# 20% datos recientes = TEST

Ejemplo con 1,836 clientes:
- Train: Enero 2024 - Octubre 2024 (1,469 clientes)
- Test: Noviembre 2024 - Diciembre 2024 (367 clientes)
```

**Ventajas:**
- ✅ Simula producción real (entrenar con pasado, predecir futuro)
- ✅ Evita data leakage
- ✅ Refleja cambios de comportamiento temporal

**Desventajas:**
- ⚠️ Requiere datos con fecha de snapshot
- ⚠️ Test set puede tener distribución diferente

#### Opción 2: Split Estratificado por Rating (ALTERNATIVA)

```python
from sklearn.model_selection import StratifiedShuffleSplit

# Dividir manteniendo proporción de ratings
split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)

for train_idx, test_idx in split.split(X, y=df['platam_rating']):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
```

**Ventajas:**
- ✅ Fácil de implementar
- ✅ Garantiza distribución similar en train/test
- ✅ No requiere datos temporales

**Desventajas:**
- ⚠️ No simula flujo temporal real
- ⚠️ Puede haber data leakage si clientes aparecen múltiples veces

#### Opción 3: Split por Default (IDEAL si tenemos defaults)

```python
from sklearn.model_selection import StratifiedShuffleSplit

# Estratificar por default_flag (0 o 1)
split = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)

for train_idx, test_idx in split.split(X, y=df['default_flag']):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

# Asegurar que ambos sets tengan defaults y no-defaults
```

**Ventajas:**
- ✅ Balanceo correcto de clases
- ✅ Evita sets sin defaults (crítico para métricas)

### Distribución Recomendada

| Set | % Datos | Uso | Clientes (de 1,836) |
|-----|---------|-----|---------------------|
| **Train** | 70% | Entrenar modelo | 1,285 |
| **Validation** | 15% | Ajustar hiperparámetros | 275 |
| **Test** | 15% | Evaluar final | 276 |

**Alternativa para datasets pequeños:**

| Set | % Datos | Uso | Clientes (de 1,836) |
|-----|---------|-----|---------------------|
| **Train** | 80% | Entrenar modelo | 1,469 |
| **Test** | 20% | Evaluar final | 367 |

Usar **K-Fold Cross-Validation** (k=5) en train para hiperparámetros.

---

## 🏗️ Arquitectura del Sistema ML

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. INGESTA DE DATOS                                             │
│    • BigQuery / Cloud SQL → Raw Data                            │
│    • Datos de pagos, cupos, HCPN                                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FEATURE ENGINEERING                                          │
│    • Limpieza de datos                                          │
│    • Imputación de missing values                               │
│    • Normalización (StandardScaler)                             │
│    • One-hot encoding de categóricas                            │
│    • Features derivadas (ratios, tendencias)                    │
│    • Feature store (Vertex AI Feature Store)                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. ENTRENAMIENTO (Vertex AI Training)                           │
│    • Train/Validation/Test split                                │
│    • Múltiples modelos:                                         │
│      - XGBoost (recomendado para tabular)                       │
│      - Random Forest                                            │
│      - LightGBM                                                 │
│      - Logistic Regression (baseline)                           │
│    • Hyperparameter tuning (Vertex AI Hyperparameter Tuning)    │
│    • Cross-validation                                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. EVALUACIÓN                                                   │
│    • Métricas de clasificación:                                 │
│      - AUC-ROC                                                  │
│      - Precision, Recall, F1                                    │
│      - Confusion Matrix                                         │
│    • Métricas de regresión (si predicción de score):            │
│      - MAE, RMSE, R²                                            │
│    • Comparación con baseline (Híbrido)                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. DEPLOYMENT (Vertex AI Endpoints)                             │
│    • Registro del modelo en Model Registry                      │
│    • Deployment a endpoint                                      │
│    • A/B testing (20% ML, 80% Híbrido)                          │
│    • Monitoring de predicciones                                 │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. SCORING HÍBRIDO EN PRODUCCIÓN                                │
│    • Score_Final = (Híbrido × 0.7) + (ML × 0.3)                 │
│    • Explicabilidad (SHAP values)                               │
│    • Guardrails (mín/máx score)                                 │
│    • Logging de predicciones                                    │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. MONITOREO Y RE-ENTRENAMIENTO                                 │
│    • Model monitoring (data drift, prediction drift)            │
│    • Re-entrenamiento mensual automático                        │
│    • Champion/Challenger comparison                             │
│    • Alertas de degradación de performance                      │
└─────────────────────────────────────────────────────────────────┘
```

### Stack Tecnológico

| Componente | Tecnología | Uso |
|------------|------------|-----|
| **Orquestación** | Vertex AI Pipelines | Automatizar flujo completo |
| **Feature Store** | Vertex AI Feature Store | Almacenar features procesadas |
| **Training** | Vertex AI Training | Entrenar modelos a escala |
| **Hyperparameter Tuning** | Vertex AI Vizier | Optimizar hiperparámetros |
| **Model Registry** | Vertex AI Model Registry | Versionar modelos |
| **Deployment** | Vertex AI Endpoints | Servir predicciones en tiempo real |
| **Monitoring** | Vertex AI Model Monitoring | Detectar drift y degradación |
| **Batch Prediction** | Vertex AI Batch Prediction | Scoring batch mensual |
| **Storage** | Google Cloud Storage (GCS) | Datos, modelos, logs |
| **Data Warehouse** | BigQuery | Datos estructurados |
| **Notebooks** | Vertex AI Workbench | Experimentación y desarrollo |

---

## ⚙️ Triggers y Recálculo

### Triggers de Re-Scoring Individual

Recalcular score de un cliente cuando:

| Evento | Trigger | Cálculo | Latencia |
|--------|---------|---------|----------|
| **Pago realizado** | POST /payment | V2.0 + Híbrido + ML | Real-time (<1s) |
| **Nuevo crédito** | POST /loan | V2.0 + Híbrido + ML | Real-time (<1s) |
| **Incumplimiento** | POST /default | V2.0 + Híbrido + ML | Real-time (<1s) |
| **Actualización HCPN** | Webhook | Híbrido + ML | Near real-time (<5s) |
| **Cambio manual** | Admin panel | V2.0 + Híbrido + ML | Real-time (<1s) |

**Implementación:**

```python
# API endpoint ejemplo
@app.post("/api/v1/payment")
async def create_payment(payment: Payment):
    # 1. Registrar pago en DB
    db.payments.insert(payment)

    # 2. Trigger re-scoring
    client_id = payment.client_id

    # Calcular scores (paralelo)
    platam_score = await calculate_platam_v2(client_id)
    hcpn_score = await get_hcpn_score(client_id)
    hybrid_score = calculate_hybrid(platam_score, hcpn_score, ...)

    # Predicción ML (Vertex AI endpoint)
    ml_score = await vertex_ai_predict(client_id, features)

    # Score final combinado
    final_score = (hybrid_score * 0.7) + (ml_score * 0.3)

    # 3. Guardar scores
    db.scores.update(client_id, {
        'platam_score': platam_score,
        'hybrid_score': hybrid_score,
        'ml_score': ml_score,
        'final_score': final_score,
        'updated_at': now()
    })

    # 4. Retornar respuesta
    return {"score": final_score, "rating": get_rating(final_score)}
```

### Triggers de Re-Entrenamiento del Modelo ML

Re-entrenar modelo completo cuando:

| Trigger | Frecuencia | Método | Validación |
|---------|------------|--------|------------|
| **Mensual automático** | Cada 1er día del mes | Vertex AI Pipeline | Champion vs Challenger |
| **Data drift detectado** | Alerta automática | On-demand | Comparar distribuciones |
| **Performance degradación** | AUC cae >5% | On-demand | Backtesting |
| **Nuevas features** | Manual | On-demand | A/B test |
| **Cambio de negocio** | Manual | On-demand | Validación stakeholders |

**Implementación:**

```python
# Cloud Function que se ejecuta mensualmente
@functions_framework.cloud_event
def retrain_model(cloud_event):
    """
    Trigger: Cloud Scheduler (1er día del mes, 2:00 AM)
    """

    # 1. Extraer datos del último mes
    df_new = query_bigquery(f"""
        SELECT * FROM scores
        WHERE calculation_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)
    """)

    # 2. Verificar data drift
    drift_detected = check_data_drift(df_new, df_baseline)

    if drift_detected:
        send_alert("⚠️ Data drift detectado - Re-entrenamiento necesario")

    # 3. Preparar datos
    X_train, X_test, y_train, y_test = prepare_data(df_new)

    # 4. Entrenar modelo (Vertex AI Pipeline)
    pipeline_job = vertex_ai.PipelineJob(
        display_name="monthly-retrain",
        template_path="gs://bucket/pipeline.json",
        parameter_values={
            "train_data": "gs://bucket/train.csv",
            "test_data": "gs://bucket/test.csv",
            "model_type": "xgboost"
        }
    )

    pipeline_job.run()

    # 5. Evaluar nuevo modelo (Challenger)
    challenger_metrics = evaluate_model(new_model, X_test, y_test)
    champion_metrics = get_production_model_metrics()

    # 6. Comparar Champion vs Challenger
    if challenger_metrics['auc'] > champion_metrics['auc']:
        # Promover Challenger a Champion
        deploy_model(new_model, endpoint="production")
        send_notification("✅ Nuevo modelo desplegado - AUC mejoró")
    else:
        send_notification("⚠️ Nuevo modelo NO superó al actual")
```

### Batch Re-Scoring (Mensual)

Recalcular todos los scores una vez al mes:

```python
# Cloud Function programada mensualmente
@functions_framework.cloud_event
def batch_rescoring(cloud_event):
    """
    Trigger: Cloud Scheduler (último domingo del mes, 3:00 AM)
    """

    # 1. Obtener todos los clientes activos
    clients = db.clients.find({"status": "active"})

    # 2. Preparar datos para batch prediction
    features_df = prepare_features_batch(clients)

    # 3. Batch prediction con Vertex AI
    batch_job = vertex_ai.BatchPredictionJob.create(
        job_display_name="monthly-batch-scoring",
        model_name="projects/PROJECT/locations/REGION/models/MODEL_ID",
        instances_format="csv",
        gcs_source="gs://bucket/features_batch.csv",
        gcs_destination_prefix="gs://bucket/predictions/",
        machine_type="n1-standard-4"
    )

    batch_job.wait()

    # 4. Cargar predicciones
    ml_scores = load_predictions("gs://bucket/predictions/")

    # 5. Calcular scores híbridos
    for client_id, ml_score in ml_scores.items():
        platam_score = get_platam_score(client_id)
        hcpn_score = get_hcpn_score(client_id)
        hybrid_score = calculate_hybrid(platam_score, hcpn_score, ...)

        final_score = (hybrid_score * 0.7) + (ml_score * 0.3)

        # Guardar
        db.scores.update(client_id, {
            'ml_score': ml_score,
            'hybrid_score': hybrid_score,
            'final_score': final_score,
            'last_batch_update': now()
        })

    send_notification(f"✅ Batch re-scoring completado: {len(ml_scores)} clientes")
```

---

## 📅 Plan de Implementación por Fases

### FASE 0: Preparación de Datos (1-2 semanas)

**Objetivos:**
- ✅ Obtener datos de default históricos
- ✅ Crear variable target (`default_flag`)
- ✅ Limpiar y validar datos
- ✅ Feature engineering inicial

**Tareas:**
1. Reunión con equipo de cobranza/riesgo para definir "default"
2. Query a base de datos histórica
3. Crear columna `default_flag` en `DASHBOARD_SCORING_DINAMICO.csv`
4. Análisis exploratorio de defaults:
   - ¿Cuántos clientes cayeron en default?
   - ¿Cuál es el balance de clases? (default vs no-default)
   - ¿Hay suficientes defaults para ML? (mínimo 50-100)
5. Crear features adicionales:
   - Tendencias temporales (DPD último mes - DPD hace 6 meses)
   - Ratios financieros (deuda/ingreso, cuota/ingreso)
   - Features de HCPN (créditos activos, mora externa)

**Entregables:**
- `ml_training_data.csv` con variable `default_flag`
- Notebook de EDA (Exploratory Data Analysis)
- Reporte de calidad de datos

### FASE 1: Setup de Infraestructura GCP (1 semana)

**Objetivos:**
- ✅ Configurar proyecto GCP
- ✅ Habilitar APIs necesarias
- ✅ Crear buckets y datasets

**Tareas:**
1. Crear proyecto GCP (o usar existente)
2. Habilitar APIs:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage-api.googleapis.com
   gcloud services enable bigquery.googleapis.com
   ```
3. Crear bucket de GCS:
   ```bash
   gsutil mb -l us-central1 gs://platam-ml-scoring/
   ```
4. Crear dataset de BigQuery:
   ```bash
   bq mk --dataset --location=US platam_scoring
   ```
5. Configurar service account con permisos
6. Subir datos a GCS y BigQuery

**Entregables:**
- Proyecto GCP configurado
- Buckets y datasets creados
- Datos subidos y accesibles

### FASE 2: Baseline ML (2-3 semanas)

**Objetivos:**
- ✅ Entrenar primer modelo baseline
- ✅ Evaluar performance vs Híbrido
- ✅ Establecer métricas de éxito

**Tareas:**
1. Train/Test split (80/20, estratificado por default_flag)
2. Entrenar modelos baseline:
   - Logistic Regression
   - Random Forest
   - XGBoost
3. Evaluar en test set:
   - AUC-ROC, Precision, Recall, F1
   - Comparar con Híbrido como baseline
4. Feature importance analysis
5. Hyperparameter tuning (grid search)
6. Documentar resultados

**Código ejemplo:**
```python
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, classification_report

# 1. Cargar datos
df = pd.read_csv('ml_training_data.csv')

# 2. Features y target
feature_cols = ['dpd_promedio', 'pagos_total', 'utilizacion_pct',
                'meses_como_cliente', 'score_platam_v2', 'score_hcpn_normalizado',
                'comp1_payment_performance_pct', 'comp2_payment_plan_pct',
                'comp3_deterioration_velocity_pct', 'hcpn_creditos_activos']

X = df[feature_cols]
y = df['default_flag']

# 3. Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 4. Normalización
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. Entrenar XGBoost
model = XGBClassifier(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=100,
    random_state=42
)

model.fit(X_train_scaled, y_train)

# 6. Evaluar
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
auc = roc_auc_score(y_test, y_pred_proba)

print(f"AUC-ROC: {auc:.3f}")
print(classification_report(y_test, model.predict(X_test_scaled)))

# 7. Feature importance
import matplotlib.pyplot as plt

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

plt.barh(feature_importance['feature'], feature_importance['importance'])
plt.title('Feature Importance')
plt.savefig('feature_importance.png')
```

**Entregables:**
- Modelos baseline entrenados
- Reporte de evaluación (AUC, métricas)
- Feature importance charts

### FASE 3: Migración a Vertex AI (2-3 semanas)

**Objetivos:**
- ✅ Migrar pipeline a Vertex AI
- ✅ Automatizar entrenamiento
- ✅ Deploy modelo a endpoint

**Tareas:**
1. Crear pipeline de Vertex AI (Kubeflow Pipelines)
2. Configurar Vertex AI Training job
3. Hyperparameter tuning con Vizier
4. Registrar modelo en Model Registry
5. Deploy a Vertex AI Endpoint
6. Probar predicciones en tiempo real

**Entregables:**
- Pipeline automatizado
- Modelo desplegado en endpoint
- API de predicción funcionando

### FASE 4: Integración con Sistema Híbrido (1-2 semanas)

**Objetivos:**
- ✅ Combinar ML con Híbrido
- ✅ Implementar triggers
- ✅ A/B testing

**Tareas:**
1. Modificar API para llamar endpoint de Vertex AI
2. Implementar scoring combinado: (Híbrido × 0.7) + (ML × 0.3)
3. Configurar triggers de re-scoring individual
4. A/B testing: 20% ML, 80% Híbrido
5. Monitoreo de latencia y errores

**Entregables:**
- API actualizada con ML
- Sistema de triggers funcionando
- Dashboard de A/B testing

### FASE 5: Monitoreo y Optimización (Continuo)

**Objetivos:**
- ✅ Monitorear performance
- ✅ Re-entrenar mensualmente
- ✅ Optimizar features

**Tareas:**
1. Configurar Vertex AI Model Monitoring
2. Alertas de data drift y prediction drift
3. Pipeline de re-entrenamiento mensual
4. Iteración de features
5. Ajuste de pesos Híbrido/ML

**Entregables:**
- Sistema de monitoreo activo
- Re-entrenamiento automático configurado

---

## 🧹 Preparación de Datos Detallada

### 1. Limpieza de Datos

```python
import pandas as pd
import numpy as np

df = pd.read_csv('DASHBOARD_SCORING_DINAMICO.csv')

# 1.1 Eliminar duplicados
df = df.drop_duplicates(subset='cliente_id')

# 1.2 Eliminar columnas irrelevantes
drop_cols = ['nombre', 'email', 'fecha_calculo', 'version_scoring']
df = df.drop(columns=drop_cols)

# 1.3 Manejar missing values
# Opción A: Imputar con mediana (variables numéricas)
from sklearn.impute import SimpleImputer

imputer = SimpleImputer(strategy='median')
numeric_cols = df.select_dtypes(include=[np.number]).columns
df[numeric_cols] = imputer.fit_transform(df[numeric_cols])

# Opción B: Imputar con moda (variables categóricas)
cat_cols = df.select_dtypes(include=['object']).columns
for col in cat_cols:
    df[col].fillna(df[col].mode()[0], inplace=True)

# 1.4 Detectar outliers (opcional)
from scipy import stats

# Z-score method
z_scores = np.abs(stats.zscore(df[numeric_cols]))
df_no_outliers = df[(z_scores < 3).all(axis=1)]

print(f"Clientes eliminados por outliers: {len(df) - len(df_no_outliers)}")
```

### 2. Feature Engineering

```python
# 2.1 Features de tendencia
df['dpd_trend'] = df['dpd_max'] - df['dpd_promedio']
df['score_trend'] = df['score_hibrido'] - df['score_platam_v2']

# 2.2 Features de ratio
df['ratio_cupo_utilizado'] = df['cupo_utilizado'] / (df['cupo_total'] + 1)  # +1 para evitar división por 0
df['ratio_pagos_mora'] = df['dpd_promedio'] / (df['pagos_total'] + 1)

# 2.3 Features categóricas binarias
df['es_cliente_maduro'] = (df['meses_como_cliente'] >= 12).astype(int)
df['tiene_mora_actual'] = (df['flag_mora_actual'] == True).astype(int)
df['alta_utilizacion'] = (df['utilizacion_pct'] > 80).astype(int)

# 2.4 Interacciones
df['dpd_x_utilizacion'] = df['dpd_promedio'] * df['utilizacion_pct']
df['score_x_pagos'] = df['score_platam_v2'] * df['pagos_total']

# 2.5 Bucketing (discretización)
df['dpd_bucket'] = pd.cut(df['dpd_promedio'], bins=[0, 5, 15, 30, 60, np.inf], labels=['0-5', '6-15', '16-30', '31-60', '60+'])
df['score_bucket'] = pd.cut(df['score_hibrido'], bins=[0, 500, 700, 850, 1000], labels=['Bajo', 'Medio', 'Alto', 'Excelente'])
```

### 3. Normalización

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler

# Opción A: StandardScaler (z-score normalization)
scaler = StandardScaler()
numeric_features = ['dpd_promedio', 'pagos_total', 'utilizacion_pct', 'meses_como_cliente']
df[numeric_features] = scaler.fit_transform(df[numeric_features])

# Opción B: MinMaxScaler (0-1 scaling)
scaler = MinMaxScaler()
df[numeric_features] = scaler.fit_transform(df[numeric_features])

# Guardar scaler para uso en producción
import joblib
joblib.dump(scaler, 'scaler.pkl')
```

### 4. Encoding de Categóricas

```python
from sklearn.preprocessing import OneHotEncoder, LabelEncoder

# Opción A: One-Hot Encoding (para pocas categorías)
categorical_cols = ['meses_categoria', 'utilizacion_categoria', 'segmento_riesgo_hibrido']

df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

# Opción B: Label Encoding (para muchas categorías o tree-based models)
le = LabelEncoder()
df['meses_categoria_encoded'] = le.fit_transform(df['meses_categoria'])

# Opción C: Target Encoding (avanzado)
# Codificar categoría por promedio de target
for col in categorical_cols:
    target_mean = df.groupby(col)['default_flag'].mean()
    df[f'{col}_target_enc'] = df[col].map(target_mean)
```

### 5. Balanceo de Clases (si hay desbalance)

```python
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler

# Si default_flag está desbalanceado (ej: 5% defaults, 95% no-defaults)

# Opción A: SMOTE (Synthetic Minority Over-sampling)
smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

# Opción B: Random Under-sampling
rus = RandomUnderSampler(random_state=42)
X_resampled, y_resampled = rus.fit_resample(X_train, y_train)

# Opción C: Usar class_weight en el modelo
model = XGBClassifier(scale_pos_weight=len(y[y==0]) / len(y[y==1]))
```

---

## 🚀 Siguiente Paso Inmediato

### ACCIÓN REQUERIDA:

**1. Obtener variable de default** ⚠️

Sin esta variable, NO podemos entrenar modelo supervisado de ML.

**Opciones:**
- **Opción A (Ideal):** Consultar base de datos histórica para clientes que cayeron en default
- **Opción B (Workaround):** Usar score actual como proxy de "riesgo" y entrenar modelo de regresión para predecir score
- **Opción C (Temporal):** Clustering no supervisado para identificar grupos de riesgo

**2. Decidir si empezar ahora o esperar datos**

- **Empezar ahora:** Usar Opción B o C, entrenar modelo de regresión para predecir score
- **Esperar:** Recolectar datos de default por 3-6 meses, luego entrenar clasificador

---

**¿Quieres que empecemos con la implementación?**

Podemos comenzar con:
1. Feature engineering avanzado
2. Modelo de regresión (predecir score) como primer MVP
3. Setup de Vertex AI
4. Pipeline básico de entrenamiento

Dime qué prefieres y arrancamos! 🚀
