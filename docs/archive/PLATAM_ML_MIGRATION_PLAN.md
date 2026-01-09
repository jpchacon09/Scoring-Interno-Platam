# PLATAM Credit Scoring - Plan de Migración a Machine Learning

## Tabla de Contenidos
1. [Visión Estratégica](#visión-estratégica)
2. [Enfoque Híbrido: Rules + ML](#enfoque-híbrido-rules--ml)
3. [Arquitectura Técnica](#arquitectura-técnica)
4. [Roadmap de Implementación](#roadmap-de-implementación)
5. [Feature Engineering para ML](#feature-engineering-para-ml)
6. [Modelos Propuestos](#modelos-propuestos)
7. [Validación y Monitoreo](#validación-y-monitoreo)
8. [Consideraciones de Costos](#consideraciones-de-costos)

---

## Visión Estratégica

### Objetivo Principal
Evolucionar el scoring basado en reglas hacia un **sistema híbrido** que combine:
- **Interpretabilidad** del sistema actual (reglas de negocio)
- **Poder predictivo** de Machine Learning
- **Adaptabilidad** continua a nuevos patrones

### Principios Rectores

1. **Evolución, No Revolución**
   - Mantener sistema actual funcionando en producción
   - ML complementa, no reemplaza inmediatamente
   - Transición gradual con validación constante

2. **Explicabilidad Primero**
   - Modelos ML deben ser interpretables
   - Cada decisión debe poder explicarse al cliente
   - SHAP values y feature importance obligatorios

3. **Validación Rigurosa**
   - Backtest exhaustivo con datos históricos
   - A/B testing en producción
   - Champion/Challenger framework

4. **Infraestructura Cloud-Native**
   - Aprovechar Vertex AI (créditos Google)
   - Integración con AWS Aurora existente
   - Pipeline automatizado end-to-end

---

## Enfoque Híbrido: Rules + ML

### Fase 1: Augmented Scoring (0-6 meses)
```
┌─────────────────┐
│   Rule-Based    │
│   Score (1000)  │ ◄─── Sistema actual
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   ML Model      │
│   (Probability) │ ◄─── Nuevo: Predice P(default)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Combined      │
│   Decision      │ ◄─── Weighted ensemble
└─────────────────┘
```

**Outputs**:
- Rule-based score (mantener para continuidad)
- ML probability score (nueva métrica)
- Combined recommendation (weighted)
- Explanation report (por qué ML difiere de rules)

### Fase 2: ML-First con Safety Rails (6-12 meses)
```
┌─────────────────┐
│   ML Model      │ ◄─── Primary scoring
│   (Probability) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Rule-Based    │ ◄─── Safety checks
│   Validators    │      - Hard stops (ej: default activo)
└────────┬────────┘      - Business constraints
         │
         ▼
┌─────────────────┐
│   Final         │
│   Decision      │
└─────────────────┘
```

### Fase 3: Fully ML-Driven (12+ meses)
- ML es el motor principal
- Rules solo como "circuit breakers" para casos extremos
- Continuous learning con nuevos datos

---

## Arquitectura Técnica

### Stack Propuesto

```
┌─────────────────────────────────────────────────────────────┐
│                     PRODUCCIÓN                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │ AWS Aurora   │───────▶│  Airflow/    │                  │
│  │   (MySQL)    │        │  Cloud       │                  │
│  │              │        │  Composer    │                  │
│  │ - Payments   │        │              │                  │
│  │ - Orders     │        │ (Data ETL)   │                  │
│  │ - Clients    │        └──────┬───────┘                  │
│  │ - Plans      │               │                          │
│  └──────────────┘               │                          │
│                                 │                          │
│                                 ▼                          │
│                        ┌─────────────────┐                 │
│                        │  BigQuery       │                 │
│                        │                 │                 │
│                        │ - Feature Store │                 │
│                        │ - Training Data │                 │
│                        │ - Predictions   │                 │
│                        └────────┬────────┘                 │
│                                 │                          │
│                                 ▼                          │
│                        ┌─────────────────┐                 │
│                        │  Vertex AI      │                 │
│                        │                 │                 │
│                        │ - Training      │                 │
│                        │ - AutoML        │                 │
│                        │ - Endpoints     │                 │
│                        │ - Monitoring    │                 │
│                        └────────┬────────┘                 │
│                                 │                          │
│                                 ▼                          │
│  ┌──────────────┐      ┌─────────────────┐                │
│  │ Application  │◄─────│  Prediction API │                │
│  │   Server     │      │  (Cloud Run)    │                │
│  │              │      │                 │                │
│  │ - Scoring    │      │ - Real-time     │                │
│  │ - Decisions  │      │ - Batch         │                │
│  │ - Alerts     │      └─────────────────┘                │
│  └──────────────┘                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Componentes Detallados

#### 1. Data Pipeline (Airflow/Cloud Composer)
```python
# DAG diario para feature engineering
platam_scoring_pipeline/
├── extract_from_aurora.py      # Conecta a AWS Aurora
├── transform_features.py       # Calcula features (basado en código actual)
├── load_to_bigquery.py         # Persiste en BigQuery
└── trigger_predictions.py      # Invoca modelo ML
```

**Frecuencia**: Diario (batch) + Near real-time (streaming)

#### 2. Feature Store (BigQuery)
```sql
-- Tabla principal de features
CREATE TABLE platam_ml.client_features (
    client_id STRING,
    feature_date DATE,

    -- Payment Performance Features (del código actual)
    payment_timeliness_score FLOAT64,
    payment_pattern_score FLOAT64,
    payment_count_6mo INT64,
    avg_dpd_6mo FLOAT64,
    weighted_dpd_score FLOAT64,

    -- Purchase Consistency Features
    orders_per_month FLOAT64,
    order_value_cv FLOAT64,
    total_order_volume_6mo FLOAT64,

    -- Utilization Features
    avg_utilization_6mo FLOAT64,
    utilization_stddev FLOAT64,
    max_utilization_6mo FLOAT64,

    -- Payment Plan Features
    active_plans_count INT64,
    completed_plans_12mo INT64,
    defaulted_plans_12mo INT64,
    months_since_last_plan FLOAT64,

    -- Deterioration Features
    dpd_1mo FLOAT64,
    dpd_6mo FLOAT64,
    dpd_trend_delta FLOAT64,

    -- Derived Features (nuevos para ML)
    payment_volatility FLOAT64,
    business_tenure_months INT64,
    seasonal_order_pattern FLOAT64,
    credit_utilization_trend FLOAT64,

    -- Target Variable (para training)
    default_next_30d BOOL,
    default_next_60d BOOL,
    default_next_90d BOOL,

    -- Metadata
    created_at TIMESTAMP
);
```

#### 3. Vertex AI Training Pipeline
```python
# platam_ml/training/train_model.py
from google.cloud import aiplatform
from sklearn.ensemble import GradientBoostingClassifier
import xgboost as xgb

def train_scoring_model():
    """
    Entrena modelo de scoring usando Vertex AI
    """
    # 1. Load data from BigQuery
    query = """
        SELECT * FROM `platam_ml.client_features`
        WHERE feature_date BETWEEN '2023-01-01' AND '2024-12-01'
    """

    # 2. Feature engineering (usar funciones del código actual)
    # 3. Train model
    # 4. Validate with holdout
    # 5. Deploy to Vertex AI endpoint
    pass
```

#### 4. Prediction API (Cloud Run)
```python
# platam_ml/api/predict.py
from fastapi import FastAPI
from google.cloud import aiplatform

app = FastAPI()

@app.post("/score/predict")
async def predict_score(client_data: ClientData):
    """
    Endpoint para scoring en tiempo real

    Returns:
        - rule_based_score: Score del sistema actual
        - ml_probability: P(default) del modelo ML
        - combined_score: Ensemble ponderado
        - recommendation: Acción sugerida
        - explanations: SHAP values para interpretabilidad
    """
    # 1. Calculate rule-based score (código actual)
    rule_score = calculate_client_score(...)

    # 2. Get ML prediction from Vertex AI
    endpoint = aiplatform.Endpoint(endpoint_name=ENDPOINT_ID)
    ml_pred = endpoint.predict(features)

    # 3. Combine predictions
    combined = ensemble_predictions(rule_score, ml_pred)

    # 4. Generate explanations
    shap_values = explain_prediction(features, ml_pred)

    return {
        "rule_based_score": rule_score,
        "ml_probability": ml_pred["probability"],
        "combined_score": combined,
        "recommendation": get_recommendation(combined),
        "explanations": shap_values
    }
```

---

## Roadmap de Implementación

### Fase 0: Preparación (Mes 1-2)

#### Milestone 0.1: Data Infrastructure
- [ ] Configurar Cloud Composer (managed Airflow)
- [ ] Crear proyecto en Google Cloud con Vertex AI habilitado
- [ ] Configurar conectividad segura AWS Aurora → Google Cloud
  - VPN o Cloud Interconnect
  - Service accounts con permisos mínimos
- [ ] Crear dataset en BigQuery para feature store

#### Milestone 0.2: Data Collection
- [ ] Migrar Excel de solicitudes a BigQuery
- [ ] Crear schema normalizado para:
  - `clients`
  - `payments`
  - `orders`
  - `utilization_monthly`
  - `payment_plans`
  - `defaults` (tabla de outcomes - CRÍTICO)
- [ ] Cargar datos históricos (mínimo 12 meses)
- [ ] Documentar data dictionary

#### Milestone 0.3: Baseline Validation
- [ ] Implementar código Python actual como pipeline
- [ ] Ejecutar scoring histórico (backtest)
- [ ] Generar benchmark metrics:
  - Distribución de scores
  - Correlación score vs defaults reales
  - Precision/Recall del sistema actual
  - ROC-AUC si es posible

**Entregable**: Dashboard con performance del sistema actual

---

### Fase 1: MVP de ML (Mes 3-4)

#### Milestone 1.1: Feature Engineering
```python
# platam_ml/features/payment_features.py
def create_payment_features(payments_df: pd.DataFrame) -> pd.DataFrame:
    """
    Replica feature engineering del código actual
    + adicionales descubiertos en EDA
    """
    features = pd.DataFrame()

    # Del código actual
    features['payment_timeliness_score'] = calculate_timeliness(...)
    features['payment_pattern_score'] = calculate_pattern(...)

    # Nuevos features para ML
    features['payment_count_trend'] = calculate_trend(...)
    features['late_payment_acceleration'] = detect_acceleration(...)
    features['payment_day_of_month_mode'] = find_payment_pattern(...)

    return features
```

- [ ] Modularizar funciones del código actual
- [ ] Agregar features adicionales basados en EDA
- [ ] Crear feature validation pipeline
- [ ] Documentar cada feature (business meaning)

#### Milestone 1.2: Target Definition
**CRÍTICO**: Definir correctamente la variable objetivo

Opciones:
1. **Default Binario**: Cliente hizo default (sí/no) en próximos N días
2. **Severity Score**: Monto en riesgo en caso de default
3. **Multi-class**: Normal / Watch / Collections

**Recomendación Inicial**:
```python
# Target: Default en próximos 60 días
# Definición de default:
#   - DPD > 60 días consecutivos, O
#   - Plan de pago defaulteado, O
#   - Cuenta enviada a cobranza

CREATE VIEW platam_ml.training_labels AS
SELECT
    client_id,
    observation_date,

    -- Target: Default próximos 60 días
    MAX(CASE
        WHEN days_past_due > 60
        OR plan_status = 'defaulted'
        OR account_status = 'collections'
        THEN 1 ELSE 0
    END) OVER (
        PARTITION BY client_id
        ORDER BY observation_date
        ROWS BETWEEN CURRENT ROW AND 60 FOLLOWING
    ) as default_next_60d

FROM payment_events
```

- [ ] Definir target con equipo de negocio
- [ ] Validar suficiente prevalencia (idealmente 5-15% defaults)
- [ ] Crear train/validation/test split temporal
  - Train: Ene 2023 - Oct 2024
  - Validation: Nov 2024
  - Test: Dic 2024

#### Milestone 1.3: Primer Modelo (AutoML)
**Por qué AutoML primero**:
- Rápido tiempo a primer resultado
- Establece benchmark de ML
- Vertex AI AutoML maneja class imbalance automáticamente

```python
# platam_ml/training/automl_baseline.py
from google.cloud import aiplatform

def train_automl_baseline():
    """
    Entrena modelo baseline con Vertex AI AutoML Tables
    """
    aiplatform.init(project=PROJECT_ID, location=REGION)

    # 1. Create dataset
    dataset = aiplatform.TabularDataset.create(
        display_name="platam_credit_scoring_v1",
        bq_source=f"bq://{PROJECT_ID}.platam_ml.training_data"
    )

    # 2. Train AutoML model
    job = aiplatform.AutoMLTabularTrainingJob(
        display_name="platam_scoring_automl_v1",
        optimization_prediction_type="classification",
        optimization_objective="maximize-au-prc",  # Mejor para datos desbalanceados
    )

    model = job.run(
        dataset=dataset,
        target_column="default_next_60d",
        training_fraction_split=0.8,
        validation_fraction_split=0.1,
        test_fraction_split=0.1,
        budget_milli_node_hours=8000,  # ~8 horas, ajustar según créditos
        model_display_name="platam_scoring_v1",
    )

    return model
```

- [ ] Ejecutar AutoML training
- [ ] Analizar feature importance
- [ ] Comparar con rule-based baseline
- [ ] Generar evaluation report

**Entregable**:
- Modelo AutoML deployado en Vertex AI
- Comparison report: AutoML vs Rules
- Feature importance analysis

---

### Fase 2: Production Pipeline (Mes 5-6)

#### Milestone 2.1: Prediction API
- [ ] Desarrollar FastAPI service en Cloud Run
- [ ] Implementar dual scoring (Rules + ML)
- [ ] Agregar SHAP explanations
- [ ] Testing de carga y latencia

#### Milestone 2.2: Monitoring Dashboard
```python
# Métricas a trackear
metrics = {
    # Model Performance
    "prediction_distribution": histogram de scores,
    "feature_drift": KS-test entre train y producción,
    "prediction_drift": cambios en distribución de outputs,

    # Business Metrics
    "default_rate_by_score_bucket": defaults reales por bucket,
    "credit_limit_changes": distribución de acciones,
    "override_rate": % de veces que humano override al modelo,

    # System Health
    "prediction_latency_p95": latencia del API,
    "feature_freshness": age de features en predicción,
    "model_version": qué modelo está sirviendo
}
```

- [ ] Crear dashboard en Looker/Data Studio
- [ ] Configurar alertas automáticas
- [ ] Weekly report automático

#### Milestone 2.3: A/B Testing Framework
**Champion/Challenger Setup**:
```
┌─────────────┐
│ New Client  │
│  Request    │
└──────┬──────┘
       │
       ▼
  ┌────────────┐
  │ Random     │
  │ Assignment │
  └──┬─────┬───┘
     │     │
     ▼     ▼
┌─────┐  ┌─────┐
│ 90% │  │ 10% │
│     │  │     │
│Rule │  │ ML  │
│Based│  │Model│
└──┬──┘  └──┬──┘
   │        │
   └────┬───┘
        ▼
   ┌─────────┐
   │ Compare │
   │ Outcomes│
   └─────────┘
```

- [ ] Implementar traffic splitting
- [ ] Definir success metrics
- [ ] Configurar data collection de ambos brazos
- [ ] Plan de rollout gradual (10% → 25% → 50% → 100%)

**Entregable**: Sistema de scoring dual en producción con A/B testing

---

### Fase 3: Modelo Customizado (Mes 7-9)

#### Milestone 3.1: Model Experimentation
**Por qué custom model después de AutoML**:
- Mayor control sobre arquitectura
- Incorporar domain knowledge específico
- Optimizar para interpretabilidad

**Modelos a evaluar**:

1. **Gradient Boosting (XGBoost/LightGBM)**
   - PRO: Excelente performance, interpretable con SHAP
   - CON: Requiere tuning cuidadoso

```python
import xgboost as xgb

params = {
    'objective': 'binary:logistic',
    'eval_metric': 'aucpr',  # Area under Precision-Recall
    'max_depth': 4,  # Shallow trees = más interpretable
    'min_child_weight': 10,  # Previene overfitting
    'scale_pos_weight': 5,  # Ajustar por class imbalance
}

model = xgb.train(params, dtrain, num_boost_round=100)
```

2. **Elastic Net Logistic Regression**
   - PRO: Máxima interpretabilidad, coeficientes = importancia
   - CON: Menor performance que tree-based

```python
from sklearn.linear_model import LogisticRegressionCV

model = LogisticRegressionCV(
    penalty='elasticnet',
    solver='saga',
    l1_ratios=[0.1, 0.5, 0.9],
    cv=5,
    class_weight='balanced'
)
```

3. **Two-Stage Model** (Híbrido)
```python
# Stage 1: Predict probability of default
stage1 = xgb.XGBClassifier(...)

# Stage 2: Si P(default) > threshold, predict severity
stage2 = xgb.XGBRegressor(...)  # Predice monto en riesgo

# Combined score
score = stage1.predict_proba() * stage2.predict()
```

**Experimentos**:
- [ ] Entrenar 3 modelos candidates
- [ ] Cross-validation riguroso
- [ ] Backtesting con datos históricos
- [ ] Calibration analysis (predicted vs actual default rates)
- [ ] Interpretability analysis (SHAP, feature importance)

#### Milestone 3.2: Model Selection
**Criterios de Selección**:

| Criterio | Peso | Medición |
|----------|------|----------|
| Predictive Power | 30% | AUC-PR, F1-score |
| Calibration | 20% | Brier score, reliability diagram |
| Interpretability | 25% | SHAP consistency, feature count |
| Business Alignment | 15% | Correlation con rule-based |
| Computational Cost | 10% | Latency, infra cost |

- [ ] Scorecard de evaluación
- [ ] Presentación a stakeholders
- [ ] Selección de modelo champion

#### Milestone 3.3: Hyperparameter Optimization
```python
# Usar Vertex AI Hyperparameter Tuning
from google.cloud import aiplatform

job = aiplatform.HyperparameterTuningJob(
    display_name='platam_xgb_tuning',
    custom_job=custom_job,
    metric_spec={
        'auc_pr': 'maximize',
    },
    parameter_spec={
        'max_depth': hpt.IntegerParameterSpec(min=3, max=7, scale='linear'),
        'learning_rate': hpt.DoubleParameterSpec(min=0.01, max=0.3, scale='log'),
        'min_child_weight': hpt.IntegerParameterSpec(min=5, max=20, scale='linear'),
    },
    max_trial_count=50,
    parallel_trial_count=5,
)

job.run()
```

**Entregable**: Modelo custom optimizado superando AutoML baseline

---

### Fase 4: Advanced Features (Mes 10-12)

#### Milestone 4.1: Feature Engineering Avanzado

**Nuevos features basados en domain knowledge**:

```python
# 1. Behavioral Change Detection
def detect_behavioral_shifts(client_history):
    """
    Detecta cambios significativos en comportamiento usando change point detection
    """
    from ruptures import Pelt

    # Aplicar PELT algorithm a serie de DPD
    algo = Pelt(model="rbf").fit(client_history['dpd'].values)
    change_points = algo.predict(pen=10)

    return {
        'has_recent_change': len(change_points) > 0,
        'months_since_change': calculate_months(change_points[-1]),
        'change_severity': calculate_severity(change_points)
    }

# 2. Seasonality Features
def add_seasonal_features(df):
    """
    Captura patrones estacionales en órdenes y pagos
    """
    df['month'] = df['date'].dt.month
    df['is_year_end'] = (df['month'] >= 11).astype(int)
    df['is_quarter_end'] = (df['month'] % 3 == 0).astype(int)

    # Seasonal decomposition
    from statsmodels.tsa.seasonal import seasonal_decompose
    result = seasonal_decompose(df['order_value'], period=12)
    df['seasonal_component'] = result.seasonal

    return df

# 3. Network Features (si disponible data de relaciones)
def add_network_features(client_id, clients_network):
    """
    Features basados en red de clientes similares
    """
    similar_clients = find_similar_clients(client_id, top_k=10)

    return {
        'peer_avg_score': similar_clients['score'].mean(),
        'peer_default_rate': similar_clients['defaulted'].mean(),
        'network_risk_exposure': calculate_contagion_risk(client_id)
    }

# 4. External Data Integration
def add_external_features(client_data):
    """
    Integrar data externa si disponible
    """
    return {
        # Macroeconomic indicators
        'gdp_growth_rate': get_gdp_growth(client_data['country']),
        'unemployment_rate': get_unemployment(client_data['region']),

        # Industry-specific
        'industry_health_index': get_industry_metrics(client_data['industry']),

        # Bureau scores (si disponible)
        'external_credit_score': get_bureau_score(client_data['tax_id'])
    }
```

- [ ] Implementar advanced features
- [ ] Evaluar incremento en performance
- [ ] Análisis costo/beneficio de cada feature

#### Milestone 4.2: Model Ensembles
```python
# Ensemble de múltiples modelos para maximizar robustness
from sklearn.ensemble import VotingClassifier

ensemble = VotingClassifier(
    estimators=[
        ('xgb', xgb_model),
        ('lgbm', lgbm_model),
        ('logistic', logistic_model)
    ],
    voting='soft',  # Usa probabilidades
    weights=[0.5, 0.3, 0.2]  # Optimizar con cross-validation
)
```

#### Milestone 4.3: Continuous Learning Pipeline
```python
# Automatic model retraining
# platam_ml/training/continuous_learning.py

def should_retrain(current_model_metrics, recent_performance):
    """
    Decide si es necesario reentrenar modelo
    """
    # Trigger retraining si:
    triggers = {
        'performance_drop': recent_performance['auc_pr'] < current_model_metrics['auc_pr'] * 0.95,
        'significant_drift': detect_drift(current_features, training_features) > 0.1,
        'time_based': days_since_training > 90,
        'new_data_volume': new_samples_count > 1000
    }

    return any(triggers.values())

# Airflow DAG para retraining automático
platam_model_retraining_dag = DAG(
    'platam_model_retraining',
    schedule_interval='@weekly',
    tasks=[
        check_performance,
        detect_drift,
        trigger_retraining_if_needed,
        validate_new_model,
        deploy_if_better
    ]
)
```

**Entregable**: Sistema de ML auto-optimizable

---

## Feature Engineering para ML

### Features del Sistema Actual (Portar tal cual)

#### Payment Performance Features
```python
features = {
    # Timeliness
    'payment_timeliness_score': float,  # 0-100
    'avg_dpd_all_time': float,
    'avg_dpd_6mo': float,
    'avg_dpd_3mo': float,
    'weighted_dpd_score': float,  # Con recency weighting

    # Pattern
    'payment_pattern_score': float,  # 0-100
    'payment_stddev_6mo': float,
    'payment_stddev_3mo': float,
    'pattern_break_detected': bool,
    'pattern_break_severity': float,  # z-score

    # Volume
    'payment_count_6mo': int,
    'payment_count_3mo': int,
    'payments_per_month': float
}
```

#### Purchase Consistency Features
```python
features = {
    'orders_per_month': float,
    'order_value_mean': float,
    'order_value_stddev': float,
    'order_value_cv': float,  # Coefficient of variation
    'total_order_volume_6mo': float,
    'order_frequency_score': float  # 0-120
}
```

#### Utilization Features
```python
features = {
    'avg_utilization_6mo': float,  # 0-1
    'utilization_stddev': float,
    'max_utilization_6mo': float,
    'min_utilization_6mo': float,
    'utilization_trend': float,  # Slope de regresión
    'months_above_80pct': int
}
```

#### Payment Plan Features
```python
features = {
    'active_plans_count': int,
    'total_plans_12mo': int,
    'completed_plans_12mo': int,
    'defaulted_plans_12mo': int,
    'plan_completion_rate': float,  # completed / total
    'months_since_last_plan': float,
    'currently_in_plan': bool
}
```

#### Deterioration Features
```python
features = {
    'dpd_1mo': float,
    'dpd_3mo': float,
    'dpd_6mo': float,
    'dpd_12mo': float,
    'dpd_trend_1mo_vs_6mo': float,  # Delta
    'dpd_trend_3mo_vs_6mo': float,
    'deterioration_velocity_score': float  # 0-100
}
```

### Nuevos Features Propuestos para ML

#### Temporal Features
```python
features = {
    # Tenure
    'months_as_client': int,
    'is_new_client': bool,  # < 6 months
    'client_maturity_tier': str,  # 'new', 'growing', 'mature'

    # Recency
    'days_since_last_payment': int,
    'days_since_last_order': int,
    'days_since_account_opened': int,

    # Calendar
    'current_month': int,  # Seasonality
    'is_year_end': bool,
    'is_quarter_end': bool
}
```

#### Ratio Features
```python
features = {
    # Efficiency ratios
    'payment_to_order_ratio': float,  # Cuánto paga vs cuánto ordena
    'credit_usage_efficiency': float,  # Utilization vs payment performance
    'growth_rate_6mo': float,  # Cambio en order volume

    # Risk ratios
    'overdue_to_total_ratio': float,
    'plan_frequency': float,  # Plans per year
    'order_to_limit_ratio': float  # Avg order size vs credit limit
}
```

#### Interaction Features
```python
features = {
    # High utilization + late payments (muy riesgoso)
    'high_util_late_pay': float,  # utilization * dpd

    # Deterioration + volatility (indicador de crisis)
    'deterioration_volatility': float,  # trend * stddev

    # New client + high utilization (riesgo desconocido)
    'new_client_risk': float,  # (1 / months_as_client) * utilization
}
```

### Feature Selection Strategy

**Criterios para incluir features en modelo**:
1. **Predictive Power**: Correlation con target > 0.05
2. **Stability**: No drift significativo entre train/test
3. **Business Sense**: Interpretable y accionable
4. **Data Quality**: < 5% missing values
5. **Redundancy**: Correlation con otros features < 0.9

**Herramientas**:
```python
# Feature selection automático
from sklearn.feature_selection import SelectFromModel
from xgboost import XGBClassifier

# Train initial model
xgb_model = XGBClassifier()
xgb_model.fit(X_train, y_train)

# Select features based on importance
selector = SelectFromModel(xgb_model, prefit=True, threshold='median')
X_train_selected = selector.transform(X_train)

# Get selected feature names
selected_features = X_train.columns[selector.get_support()]
```

---

## Modelos Propuestos

### Modelo Recomendado: Gradient Boosting Ensemble

**Por qué GBM**:
1. State-of-art performance en datos tabulares
2. Maneja relaciones no-lineales
3. Robusto a outliers
4. Interpretable con SHAP
5. Production-ready (Vertex AI tiene soporte nativo)

### Arquitectura del Modelo

```python
# platam_ml/models/ensemble_model.py

class PLATAMScoringModel:
    """
    Ensemble de modelos para scoring crediticio
    """

    def __init__(self):
        # Modelo principal: XGBoost optimizado para precision
        self.primary_model = xgb.XGBClassifier(
            objective='binary:logistic',
            eval_metric='aucpr',
            max_depth=5,
            learning_rate=0.05,
            n_estimators=200,
            min_child_weight=10,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=self._calculate_scale_pos_weight(),
            tree_method='hist',
            enable_categorical=True
        )

        # Modelo secundario: LightGBM optimizado para recall
        self.secondary_model = lgb.LGBMClassifier(
            objective='binary',
            metric='auc',
            num_leaves=31,
            learning_rate=0.05,
            n_estimators=200,
            class_weight='balanced'
        )

        # Modelo de calibración
        self.calibrator = CalibratedClassifierCV(
            base_estimator=self.primary_model,
            method='isotonic',
            cv=5
        )

    def fit(self, X_train, y_train, X_val, y_val):
        """
        Entrena ensemble con early stopping
        """
        # Train primary
        self.primary_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )

        # Train secondary
        self.secondary_model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )

        # Calibrate
        self.calibrator.fit(X_train, y_train)

        return self

    def predict_proba(self, X):
        """
        Ensemble prediction con weighted average
        """
        # Get predictions from all models
        pred_primary = self.primary_model.predict_proba(X)[:, 1]
        pred_secondary = self.secondary_model.predict_proba(X)[:, 1]
        pred_calibrated = self.calibrator.predict_proba(X)[:, 1]

        # Weighted ensemble (optimizar pesos con validation set)
        ensemble_pred = (
            0.5 * pred_primary +
            0.2 * pred_secondary +
            0.3 * pred_calibrated
        )

        return ensemble_pred

    def explain_prediction(self, X, index):
        """
        Generate SHAP explanation for single prediction
        """
        import shap

        explainer = shap.TreeExplainer(self.primary_model)
        shap_values = explainer.shap_values(X.iloc[index:index+1])

        return {
            'shap_values': shap_values,
            'base_value': explainer.expected_value,
            'feature_values': X.iloc[index].to_dict()
        }
```

### Interpretability Layer

```python
# platam_ml/explainability/shap_explainer.py

class ScoringExplainer:
    """
    Genera explicaciones human-readable de predicciones
    """

    def __init__(self, model, feature_names, business_rules):
        self.model = model
        self.feature_names = feature_names
        self.business_rules = business_rules

    def explain(self, client_features):
        """
        Genera explicación completa de la predicción
        """
        # 1. Get SHAP values
        shap_values = self.model.explain_prediction(client_features)

        # 2. Identify top contributing features
        top_features = self._get_top_features(shap_values, n=5)

        # 3. Translate to business language
        explanation = {
            'risk_level': self._categorize_risk(prediction),
            'main_factors': [
                {
                    'feature': feat,
                    'value': client_features[feat],
                    'impact': shap_values[feat],
                    'explanation': self.business_rules.explain(feat, client_features[feat])
                }
                for feat in top_features
            ],
            'recommendation': self._generate_recommendation(prediction, top_features)
        }

        return explanation

    def _generate_recommendation(self, prediction, top_features):
        """
        Genera recomendación accionable
        """
        if prediction > 0.7:
            return {
                'action': 'FREEZE',
                'reason': 'High default probability',
                'next_steps': [
                    'Contact client immediately',
                    'Review outstanding balance',
                    'Consider payment plan'
                ]
            }
        elif prediction > 0.3:
            return {
                'action': 'REDUCE_LIMIT',
                'amount': self._calculate_reduction(prediction),
                'reason': 'Elevated risk detected',
                'next_steps': [
                    'Monitor closely',
                    'Set payment reminders',
                    'Review in 30 days'
                ]
            }
        else:
            return {
                'action': 'MAINTAIN',
                'reason': 'Low risk profile',
                'next_steps': [
                    'Continue regular monitoring'
                ]
            }
```

---

## Validación y Monitoreo

### Validation Strategy

#### 1. Temporal Cross-Validation
```python
# No usar random split - usar temporal split
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)

for train_index, val_index in tscv.split(X):
    X_train, X_val = X.iloc[train_index], X.iloc[val_index]
    y_train, y_val = y.iloc[train_index], y.iloc[val_index]

    model.fit(X_train, y_train)
    score = model.score(X_val, y_val)
```

**Por qué temporal**: Evita data leakage, simula realidad de producción

#### 2. Backtest Exhaustivo
```python
# Simular scoring en cada mes histórico
def backtest_model(model, historical_data, start_date, end_date):
    """
    Evalúa modelo en cada punto temporal
    """
    results = []

    for prediction_date in pd.date_range(start_date, end_date, freq='M'):
        # Features hasta prediction_date
        features = get_features_at_date(historical_data, prediction_date)

        # Predicciones
        predictions = model.predict_proba(features)

        # Outcomes reales 60 días después
        actuals = get_actuals_at_date(
            historical_data,
            prediction_date + timedelta(days=60)
        )

        # Evaluar
        metrics = calculate_metrics(predictions, actuals)
        results.append({
            'date': prediction_date,
            'metrics': metrics,
            'sample_size': len(features)
        })

    return pd.DataFrame(results)
```

#### 3. Business Metrics Validation
```python
# Además de métricas ML, validar impact en negocio
business_metrics = {
    # Financial Impact
    'expected_loss_reduction': calculate_expected_loss(model_decisions) - calculate_expected_loss(current_decisions),
    'false_positive_cost': count_good_clients_rejected * avg_client_lifetime_value,
    'false_negative_cost': count_defaults_not_detected * avg_default_loss,

    # Operational
    'manual_review_rate': pct_predictions_in_grey_zone,
    'decision_speed': avg_time_to_decision,

    # Customer Experience
    'limit_reduction_frequency': pct_clients_with_limit_change,
    'approval_rate': pct_applications_approved
}
```

### Production Monitoring

#### Dashboard de Monitoreo (Looker/Data Studio)

**1. Model Performance Tab**
```sql
-- Query para model performance tracking
WITH predictions AS (
    SELECT
        prediction_date,
        client_id,
        predicted_probability,
        predicted_class,
        actual_outcome,
        CASE
            WHEN predicted_probability >= 0.7 THEN 'High Risk'
            WHEN predicted_probability >= 0.3 THEN 'Medium Risk'
            ELSE 'Low Risk'
        END as risk_bucket
    FROM platam_ml.prediction_log
    WHERE prediction_date >= CURRENT_DATE - 30
)
SELECT
    risk_bucket,
    COUNT(*) as total_predictions,
    AVG(predicted_probability) as avg_predicted_prob,
    AVG(actual_outcome) as actual_default_rate,
    ABS(AVG(predicted_probability) - AVG(actual_outcome)) as calibration_error
FROM predictions
GROUP BY risk_bucket
```

**Visualizaciones**:
- Calibration curve (predicted vs actual)
- Precision-Recall por threshold
- Confusion matrix
- ROC curve

**2. Data Drift Tab**
```python
# Detectar drift en features
from scipy.stats import ks_2samp

def detect_feature_drift(train_features, production_features, threshold=0.05):
    """
    Kolmogorov-Smirnov test para cada feature
    """
    drift_report = {}

    for col in train_features.columns:
        statistic, p_value = ks_2samp(
            train_features[col].dropna(),
            production_features[col].dropna()
        )

        drift_report[col] = {
            'ks_statistic': statistic,
            'p_value': p_value,
            'has_drift': p_value < threshold,
            'severity': 'HIGH' if statistic > 0.2 else 'MEDIUM' if statistic > 0.1 else 'LOW'
        }

    return drift_report
```

**Visualizaciones**:
- Distribution comparison (train vs production)
- Feature drift score over time
- Alert cuando drift significativo

**3. Business Impact Tab**
```sql
-- Impacto financiero del modelo
SELECT
    DATE_TRUNC(decision_date, MONTH) as month,

    -- Decisiones del modelo
    COUNTIF(model_recommendation = 'APPROVE') as approvals,
    COUNTIF(model_recommendation = 'REJECT') as rejections,
    COUNTIF(model_recommendation = 'REDUCE') as reductions,

    -- Outcomes
    SUM(CASE WHEN actual_outcome = 1 THEN default_amount ELSE 0 END) as total_losses,
    SUM(CASE WHEN actual_outcome = 0 THEN revenue_generated ELSE 0 END) as total_revenue,

    -- ROI del modelo
    SUM(revenue_generated - default_amount) as net_profit

FROM platam_ml.model_decisions
LEFT JOIN platam_ml.client_outcomes USING(client_id, decision_date)
GROUP BY month
ORDER BY month DESC
```

**4. Alert Configuration**
```python
# Automated alerts via email/Slack
alerts = {
    'model_performance_degradation': {
        'condition': 'current_auc_pr < baseline_auc_pr * 0.95',
        'severity': 'HIGH',
        'action': 'Trigger model retraining'
    },
    'significant_drift_detected': {
        'condition': 'feature_drift_count > 5',
        'severity': 'MEDIUM',
        'action': 'Review feature engineering'
    },
    'prediction_volume_anomaly': {
        'condition': 'daily_predictions < avg_daily * 0.5',
        'severity': 'HIGH',
        'action': 'Check data pipeline'
    },
    'calibration_error_increase': {
        'condition': 'calibration_error > 0.1',
        'severity': 'MEDIUM',
        'action': 'Recalibrate model'
    }
}
```

---

## Consideraciones de Costos

### Google Cloud (Vertex AI) - Estimación Mensual

#### Compute Costs
```
Training (mensual, con retraining semanal):
- AutoML: ~$3-5 per node hour × 8 hours × 4 trainings = $96-160/mes
- Custom training (n1-standard-8): $0.38/hour × 4 hours × 4 = $6/mes

Prediction Serving:
- Vertex AI Endpoint (n1-standard-2): $0.19/hour × 730 hours = $139/mes
- Batch predictions: ~$5/mes

TOTAL COMPUTE: ~$150-250/mes
```

#### Storage Costs
```
BigQuery:
- Storage: 100 GB × $0.02/GB = $2/mes
- Queries: 1 TB processed × $5/TB = $5/mes

Cloud Storage (model artifacts):
- 50 GB × $0.02/GB = $1/mes

TOTAL STORAGE: ~$8/mes
```

#### Data Transfer
```
AWS Aurora → Google Cloud:
- Estimado 10 GB/día × 30 × $0.01/GB = $3/mes

TOTAL TRANSFER: ~$3/mes
```

**TOTAL MENSUAL ESTIMADO: $260-320/mes**

Con créditos de Google Cloud, esto puede cubrir varios meses de operación inicial.

### Optimizaciones para Reducir Costos

1. **Batch Predictions vs Real-time**
   - Real-time solo para casos críticos
   - Batch diario para scoring regular
   - Ahorro: ~50% en serving costs

2. **Preemptible VMs para Training**
   - Usar VMs preemptible (hasta 80% descuento)
   - Implementar checkpointing para reintentos
   - Ahorro: ~$120/mes

3. **BigQuery Slots Flat-Rate**
   - Si queries > 2TB/mes, considerar flat-rate
   - $2000/mes para slots ilimitados (solo si escala mucho)

4. **Model Compression**
   - Quantization de modelos para menor latency
   - Distillation a modelo más pequeño para serving
   - Ahorro: 30-50% serving costs

### ROI Esperado

**Assumptions**:
- 1000 clientes activos
- Tasa de default actual: 5%
- Default amount promedio: $20M COP
- Mejora esperada en detection: 20%

**Cálculo**:
```
Pérdidas actuales/mes = 1000 × 0.05 × $20M = $1,000M COP
Reducción con ML = $1,000M × 0.20 = $200M COP/mes saved

Costo ML = $300 USD/mes ≈ $1.2M COP/mes

ROI = ($200M - $1.2M) / $1.2M = 16,566%

Payback period < 1 día
```

**Conclusión**: Incluso con assumptions conservadores, ROI es extraordinario.

---

## Cronograma Resumido

| Fase | Duración | Entregables Clave | Equipo Necesario |
|------|----------|-------------------|------------------|
| **Fase 0: Preparación** | 2 meses | - Infraestructura Cloud<br>- Datos históricos limpios<br>- Baseline metrics | 1 Data Engineer<br>1 ML Engineer |
| **Fase 1: MVP ML** | 2 meses | - AutoML model deployado<br>- A/B testing framework<br>- Monitoring dashboard | 1 ML Engineer<br>1 Analytics Engineer |
| **Fase 2: Production** | 2 meses | - Prediction API<br>- Dual scoring system<br>- A/B test results | 1 ML Engineer<br>1 Backend Engineer |
| **Fase 3: Optimización** | 3 meses | - Custom model optimizado<br>- Advanced features<br>- Continuous learning | 1 ML Engineer<br>1 Data Scientist |
| **Fase 4: Escala** | 3 meses | - Ensemble models<br>- Auto-retraining<br>- Full production rollout | 1 ML Engineer<br>1 MLOps Engineer |

**Total: 12 meses para sistema completamente productivo**

---

## Próximos Pasos Inmediatos

### Semana 1-2: Discovery
- [ ] Reunión con stakeholders para definir success criteria
- [ ] Auditoría de datos en AWS Aurora (calidad, completeness)
- [ ] Definir formalmente qué es "default" para el negocio
- [ ] Solicitar acceso a créditos de Google Cloud

### Semana 3-4: Setup
- [ ] Crear proyecto en Google Cloud Platform
- [ ] Configurar conectividad AWS → GCP
- [ ] Migrar Excel de solicitudes a formato estructurado
- [ ] Setup inicial de BigQuery datasets

### Mes 2: Baseline
- [ ] Cargar 12+ meses de datos históricos
- [ ] Ejecutar código Python actual como backtest
- [ ] Generar baseline metrics document
- [ ] Identificar gaps en datos

### Mes 3: First Model
- [ ] Feature engineering en BigQuery
- [ ] Primer entrenamiento con AutoML
- [ ] Comparación AutoML vs Rules
- [ ] Go/No-Go decision para continuar con ML

---

## Conclusión

El código actual de scoring es una **base excepcional** para ML porque:

1. Las features están bien pensadas y alineadas con el negocio
2. La lógica es interpretable y documentada
3. El approach modular facilita migration

La estrategia propuesta permite:
- **Inicio rápido** con AutoML (3-4 meses a primer modelo)
- **Riesgo controlado** con approach híbrido y A/B testing
- **ROI claro** con métricas de negocio tracked desde día 1
- **Escalabilidad** con infraestructura cloud-native

**Recomendación**: Proceder con Fase 0 (Preparación) mientras se valida acceso a créditos de Google Cloud y se completa auditoría de datos históricos.
