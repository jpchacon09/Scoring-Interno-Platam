# Roadmap de Machine Learning con Vertex AI

**Fecha:** 7 de Enero de 2026
**Sistema Actual:** PLATAM Scoring V2.0 + Híbrido + Defaults Integrados
**Objetivo:** Implementar ML predictivo con Google Vertex AI

---

## 1. Estado Actual - Lo Que YA Tenemos ✅

### Datos Completos para ML

**Dataset:** `ml_training_data.csv` - **1,835 clientes, 26 features**

**Variable Target:** `default_flag` (0 o 1)
- **100 clientes en default** (5.45%)
- **1,735 clientes sin default** (94.55%)
- Criterio: l_status = "Default" OR mora >180 días
- Balance total en default: $186,228,906
- Mora máxima: 853 días

### Validación del Sistema: Los Scores SÍ Predicen Defaults

| Métrica | Sin Default | Con Default | Diferencia |
|---------|-------------|-------------|------------|
| **PLATAM Score** | 766.8 | 658.1 | **-108.7** |
| **Experian Score** | 765.7 | 639.8 | **-125.8** |
| **Hybrid Score** | 767.9 | 623.2 | **-144.7** |

### Tasa de Default por Rating (Validación del Sistema)

| Rating | Tasa Default | Clientes |
|--------|--------------|----------|
| **D** | 21.9% | 16/73 |
| **C** | 13.1% | 8/61 |
| **C+** | 5.9% | 29/492 |
| **B** | 5.7% | 4/70 |
| **B+** | 5.1% | 11/216 |
| **A+** | 3.6% | 31/858 |
| **A** | 1.5% | 1/65 |

**Conclusión:** El sistema actual tiene poder predictivo real. ML puede mejorarlo.

### Features Disponibles

**Identificación:**
- cedula, client_type

**Target:**
- **default_flag** ⭐

**Scores (Pueden usarse como features o targets):**
- platam_score, experian_score_normalized, hybrid_score
- platam_rating, hybrid_rating

**Componentes PLATAM:**
- score_payment_performance, score_payment_plan, score_deterioration

**Comportamiento de Pago:**
- payment_count, months_as_client
- days_past_due_mean, days_past_due_max
- pct_early, pct_late

**Pesos y Madurez:**
- peso_platam_usado, peso_hcpn_usado, categoria_madurez

**Métricas de Default:**
- max_days_past_due, num_defaults, balance_default_total

**Planes de Pago:**
- tiene_plan_activo, tiene_plan_default, tiene_plan_pendiente, num_planes

---

## 2. Problema a Resolver con ML

### Enfoque: Clasificación Binaria

**Pregunta:** ¿Este cliente va a caer en default?

**Input:** Features del cliente (comportamiento de pago, scores, mora, etc.)
**Output:** Probabilidad de default (0-100%)

### Desafío: Clases Desbalanceadas

- 94.6% No-Default (clase mayoritaria)
- 5.4% Default (clase minoritaria)

**Soluciones:**
1. `class_weight='balanced'` en modelos
2. SMOTE para oversampling de defaults
3. Métricas: Precision, Recall, F1, AUC-ROC (NO solo accuracy)

---

## 3. Qué Necesitamos para Empezar

### Infraestructura GCP

1. **Proyecto GCP** (nuevo o existente)
2. **APIs habilitadas:**
   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage-api.googleapis.com
   gcloud services enable notebooks.googleapis.com
   ```
3. **Google Cloud Storage Bucket:**
   ```bash
   gsutil mb -l us-central1 gs://platam-ml-scoring/
   ```
4. **Service Account** con permisos:
   - Vertex AI User
   - Storage Object Admin
5. **Credenciales locales** (para desarrollo)

### Software Local

```bash
# Python 3.9+
pip install google-cloud-aiplatform
pip install scikit-learn xgboost lightgbm
pip install pandas numpy matplotlib seaborn
pip install imbalanced-learn  # Para SMOTE
```

---

## 4. Plan de Implementación (3 Fases)

### FASE 1: Baseline ML Local (1 semana)

**Objetivo:** Entrenar primer modelo localmente, validar que funciona

**Pasos:**

1. **Train/Test Split Estratificado**
   ```python
   from sklearn.model_selection import train_test_split

   # 80% train, 20% test, balanceado por default_flag
   X_train, X_test, y_train, y_test = train_test_split(
       X, y, test_size=0.2, stratify=y, random_state=42
   )
   ```

2. **Entrenar 3 modelos baseline:**
   - Logistic Regression (baseline simple)
   - Random Forest (ensemble)
   - XGBoost (gradient boosting) ⭐ Recomendado

3. **Evaluar con métricas apropiadas:**
   ```python
   from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix

   # AUC-ROC (principal métrica)
   auc = roc_auc_score(y_test, y_pred_proba)

   # Precision, Recall, F1
   print(classification_report(y_test, y_pred))
   ```

4. **Analizar feature importance**
   - ¿Qué features son más predictivas?
   - ¿Podemos eliminar features redundantes?

**Entregable:** Modelo XGBoost con AUC > 0.70 (target inicial)

### FASE 2: Migración a Vertex AI (1-2 semanas)

**Objetivo:** Subir datos y modelo a Vertex AI, entrenar en la nube

**Pasos:**

1. **Subir datos a GCS:**
   ```bash
   gsutil cp ml_training_data.csv gs://platam-ml-scoring/data/
   ```

2. **Crear Vertex AI Workbench** (Jupyter notebook en la nube)
   ```bash
   gcloud notebooks instances create platam-ml-notebook \
       --location=us-central1-a \
       --machine-type=n1-standard-4
   ```

3. **Entrenar modelo en Vertex AI Training:**
   ```python
   from google.cloud import aiplatform

   aiplatform.init(
       project='YOUR_PROJECT_ID',
       location='us-central1',
       staging_bucket='gs://platam-ml-scoring'
   )

   job = aiplatform.CustomTrainingJob(
       display_name='platam-xgboost-v1',
       script_path='train.py',
       container_uri='us-docker.pkg.dev/vertex-ai/training/xgboost-cpu.1-6:latest'
   )

   model = job.run(
       dataset=dataset,
       model_display_name='platam-default-predictor-v1',
       machine_type='n1-standard-4'
   )
   ```

4. **Registrar modelo en Model Registry**

5. **Deploy a Vertex AI Endpoint:**
   ```python
   endpoint = model.deploy(
       machine_type='n1-standard-2',
       min_replica_count=1,
       max_replica_count=3
   )
   ```

6. **Probar predicciones:**
   ```python
   # Predicción en tiempo real
   prediction = endpoint.predict(instances=[features])
   default_probability = prediction.predictions[0]
   ```

**Entregable:** Modelo desplegado en endpoint de Vertex AI

### FASE 3: Integración y Producción (1-2 semanas)

**Objetivo:** Integrar ML con sistema actual, monitorear

**Pasos:**

1. **API de Predicción:**
   ```python
   @app.post("/api/v1/predict-default")
   async def predict_default(cedula: str):
       # 1. Obtener features del cliente
       features = get_client_features(cedula)

       # 2. Predicción ML (Vertex AI)
       prediction = vertex_endpoint.predict(instances=[features])
       default_prob = prediction.predictions[0]

       # 3. Retornar
       return {
           "cedula": cedula,
           "default_probability": default_prob,
           "risk_category": "Alto" if default_prob > 0.15 else "Medio" if default_prob > 0.05 else "Bajo"
       }
   ```

2. **Score Híbrido ML:**
   ```python
   # Combinar score híbrido actual con ML
   # Convertir probabilidad de default a score (invertido)
   ml_score = (1 - default_prob) * 1000

   # Combinar con híbrido
   final_score = (hybrid_score * 0.7) + (ml_score * 0.3)
   ```

3. **Monitoreo:**
   - Configurar Vertex AI Model Monitoring
   - Alertas de data drift
   - Métricas de predicción (latencia, errores)

4. **Re-entrenamiento mensual:**
   - Cloud Function que ejecuta cada mes
   - Entrena con nuevos datos
   - Compara Champion vs Challenger
   - Deploy automático si mejora AUC

**Entregable:** Sistema ML en producción con monitoreo

---

## 5. Código Base para Empezar

### Script de Entrenamiento Local (`train_baseline.py`)

```python
#!/usr/bin/env python3
"""
Entrenamiento Baseline - Modelo de Predicción de Defaults
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# 1. CARGAR DATOS
print("Cargando datos...")
df = pd.read_csv('ml_training_data.csv')

# 2. SELECCIONAR FEATURES
# Excluir: cedula (ID), client_type (categórica), ratings (derivados de scores)
feature_cols = [
    'platam_score', 'experian_score_normalized',
    'score_payment_performance', 'score_payment_plan', 'score_deterioration',
    'payment_count', 'months_as_client',
    'days_past_due_mean', 'days_past_due_max',
    'pct_early', 'pct_late',
    'peso_platam_usado', 'peso_hcpn_usado',
    'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
]

# Filtrar features disponibles
feature_cols = [col for col in feature_cols if col in df.columns]

X = df[feature_cols].fillna(0)  # Imputar NaN con 0
y = df['default_flag']

print(f"Features: {len(feature_cols)}")
print(f"Clientes: {len(df)}")
print(f"Defaults: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")

# 3. TRAIN/TEST SPLIT
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print(f"\nTrain: {len(X_train)} clientes ({y_train.sum()} defaults)")
print(f"Test: {len(X_test)} clientes ({y_test.sum()} defaults)")

# 4. NORMALIZACIÓN
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. ENTRENAR XGBOOST
print("\nEntrenando XGBoost...")

# Calcular scale_pos_weight para balancear clases
scale_pos_weight = len(y_train[y_train==0]) / len(y_train[y_train==1])

model = XGBClassifier(
    max_depth=4,
    learning_rate=0.1,
    n_estimators=100,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='auc'
)

model.fit(X_train_scaled, y_train)

# 6. EVALUAR
print("\n" + "="*60)
print("EVALUACIÓN EN TEST SET")
print("="*60)

# Predicciones
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
y_pred = model.predict(X_test_scaled)

# AUC-ROC
auc = roc_auc_score(y_test, y_pred_proba)
print(f"\nAUC-ROC: {auc:.3f}")

# Classification Report
print("\n" + classification_report(y_test, y_pred))

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"TN: {cm[0,0]}  FP: {cm[0,1]}")
print(f"FN: {cm[1,0]}  TP: {cm[1,1]}")

# 7. FEATURE IMPORTANCE
print("\n" + "="*60)
print("FEATURE IMPORTANCE")
print("="*60)

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(feature_importance.head(10))

# Guardar gráfico
plt.figure(figsize=(10, 6))
plt.barh(feature_importance['feature'][:10], feature_importance['importance'][:10])
plt.xlabel('Importance')
plt.title('Top 10 Features')
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150)
print("\nGráfico guardado: feature_importance.png")

# 8. GUARDAR MODELO
import joblib
joblib.dump(model, 'xgboost_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("\nModelo guardado: xgboost_model.pkl")
print("Scaler guardado: scaler.pkl")
```

---

## 6. Próximos Pasos Inmediatos

### Paso 1: Ejecutar Baseline Local

```bash
cd "/Users/jpchacon/Scoring Interno"
python train_baseline.py
```

**Validar:**
- AUC-ROC > 0.70 (bueno)
- Precision para defaults > 0.20
- Top features tienen sentido de negocio

### Paso 2: Confirmar Infraestructura GCP

**Necesito saber:**
- ¿Ya tienes un proyecto GCP?
- ¿Tienes créditos GCP disponibles?
- ¿Cuál es el PROJECT_ID que vamos a usar?

### Paso 3: Subir a Vertex AI

Una vez validado el baseline local:
1. Crear bucket GCS
2. Subir `ml_training_data.csv`
3. Ejecutar entrenamiento en Vertex AI
4. Deploy a endpoint

### Paso 4: Integración con Sistema

Una vez el endpoint esté activo:
1. Crear API que consulte Vertex AI
2. Combinar predicción ML con score híbrido
3. Probar con clientes reales

---

## 7. Métricas de Éxito

| Métrica | Target Inicial | Target Ideal |
|---------|---------------|--------------|
| **AUC-ROC** | > 0.70 | > 0.80 |
| **Precision (Defaults)** | > 0.20 | > 0.40 |
| **Recall (Defaults)** | > 0.50 | > 0.70 |
| **Latencia Predicción** | < 200ms | < 100ms |

**Comparación con Baseline:**
- Sistema actual usa ratings con tasas default 1.5%-21.9%
- ML debe superar esta segmentación

---

## 8. Resumen Ejecutivo

**Lo que tenemos:**
- 1,835 clientes con 26 features
- 100 defaults identificados (5.4%)
- Scores actuales ya son predictivos

**Lo que vamos a hacer:**
- Entrenar modelo XGBoost de clasificación binaria
- Predecir probabilidad de default
- Integrar con sistema híbrido actual

**Lo que necesitamos:**
1. Proyecto GCP configurado
2. Ejecutar `train_baseline.py` localmente
3. Validar resultados
4. Migrar a Vertex AI

**Tiempo estimado:** 3-4 semanas para MVP en producción

---

**¿Listo para empezar?** Primero ejecuta el script de baseline y me cuentas los resultados.
