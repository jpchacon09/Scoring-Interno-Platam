# 📚 Documentación Técnica - PLATAM Scoring System

## 📋 Tabla de Contenidos

- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Algoritmo de Scoring PLATAM](#algoritmo-de-scoring-platam)
- [Sistema de Scoring Híbrido](#sistema-de-scoring-híbrido)
- [Modelo de Machine Learning](#modelo-de-machine-learning)
- [Features y Variables](#features-y-variables)
- [API de Producción](#api-de-producción)

---

## 🏗️ Arquitectura del Sistema

### Stack Tecnológico

```
┌─────────────────────────────────────────────────────┐
│                  PRODUCCIÓN                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Frontend/Consumo:                                  │
│  └─ n8n Workflows                                   │
│  └─ API REST Calls                                  │
│                                                     │
│  Cloud Run API (Python/FastAPI):                    │
│  └─ api_scoring_cedula.py                          │
│  └─ Data: CSV en memoria (1,835 clientes)         │
│  └─ URL: scoring-api-...run.app                   │
│                                                     │
│  Vertex AI (Google Cloud):                          │
│  └─ Modelo: XGBoost (platam-custom-final)         │
│  └─ Endpoint: 3426032820691755008                  │
│  └─ Región: us-central1                            │
│                                                     │
│  Data Source:                                       │
│  └─ data/processed/hybrid_scores.csv               │
│  └─ Actualización: Manual                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Flujo de Predicción

```
1. Cliente → Request API (POST /predict)
   {
     "cedula": "1006157869"
   }

2. API → Busca en CSV
   - 17 features del cliente
   - Scores precalculados (PLATAM + híbrido)

3. API → Vertex AI
   - Envía 17 features
   - Modelo XGBoost predice

4. Vertex AI → Response
   - probability_default: 0.392
   - probability_no_default: 0.608

5. API → Genera recomendación
   - Combina: scores + ML + reglas negocio
   - attention_level: "Atención moderada"
   - action_plan: "Recordatorio preventivo"

6. Cliente ← Response completa
   {
     "scoring": {...},
     "ml_prediction": {...},
     "recommendation": {...}
   }
```

---

## 📊 Algoritmo de Scoring PLATAM

### Componentes (Sistema V2.0)

El score PLATAM se calcula con **3 componentes principales**:

#### 1. Score de Desempeño de Pagos (60%)
**Rango:** 300-900 puntos | **Base:** 600 puntos

**Factores:**
- ✅ **Pagos tempranos (DPD < 0):** +200 pts
- ❌ **Pagos tardíos (DPD > 0):** -150 pts
- ⚠️ **Mora promedio:**
  - DPD > 30 días: -200 pts
  - DPD 15-30 días: -100 pts
  - DPD 5-15 días: -50 pts

**Código:**
```python
def calculate_score_payment_performance(row):
    score = 600  # Base

    # Bonus pagos tempranos
    if row['pct_early']:
        score += row['pct_early'] * 200

    # Penalización pagos tardíos
    if row['pct_late']:
        score -= row['pct_late'] * 150

    # Penalización mora
    if row['days_past_due_mean'] > 30:
        score -= 200
    elif row['days_past_due_mean'] > 15:
        score -= 100
    elif row['days_past_due_mean'] > 5:
        score -= 50

    return max(300, min(900, score))
```

#### 2. Score de Planes de Pago (15%)
**Rango:** 300-900 puntos | **Base:** 600 puntos

**Factores:**
- ❌ **Plan en default:** -250 pts
- ✅ **Plan activo:** +50 pts
- ⚠️ **Plan pendiente:** -50 pts
- ⚠️ **Múltiples planes:**
  - > 3 planes: -100 pts
  - > 1 plan: -50 pts

#### 3. Score de Deterioro (25%)
**Rango:** 300-900 puntos | **Base:** 600 puntos

**Factores:**
- ⚠️ **Tiempo sin pagar:**
  - > 90 días: -300 pts
  - 60-90 días: -200 pts
  - 30-60 días: -100 pts

- ⚠️ **Mora máxima histórica:**
  - > 60 días: -200 pts
  - > 30 días: -100 pts

### Score PLATAM Final

```python
platam_score = (
    score_payment_performance * 0.60 +
    score_payment_plan * 0.15 +
    score_deterioration * 0.25
)
```

**Rango:** 300-900 puntos

**Categorización:**
| Score | Categoría |
|-------|-----------|
| ≥ 750 | Excelente |
| 650-749 | Bueno |
| 550-649 | Medio |
| 450-549 | Regular |
| < 450 | Bajo |

---

## 🔀 Sistema de Scoring Híbrido

### Concepto

El **sistema híbrido** combina:
1. **Score PLATAM** (comportamiento interno)
2. **Score Experian** (historial crediticio externo)

### Ponderación Dinámica

**NO usamos 50/50 fijo.** Los pesos se ajustan según:

#### Reglas de Madurez

| Categoría | Tiempo | Pagos | Peso PLATAM | Peso Experian |
|-----------|--------|-------|-------------|---------------|
| Muy Nuevo | < 3 meses | < 5 | 20% | 80% |
| Nuevo | 3-6 meses | 5-10 | 40% | 60% |
| Intermedio | 6-12 meses | 10-20 | 50% | 50% |
| Establecido | 12-24 meses | 20-50 | 60% | 40% |
| Maduro | > 24 meses | > 50 | 70% | 30% |

#### Ajustes Adicionales

```python
# Cliente con historial amplio
if payment_count >= 20:
    peso_platam += 0.10

# Cliente con historial insuficiente
if payment_count < 5:
    peso_platam -= 0.10

# Límites
peso_platam = max(0.20, min(0.80, peso_platam))
peso_experian = 1.0 - peso_platam
```

### Casos Especiales

1. **Solo PLATAM (sin Experian):**
   ```python
   hybrid_score = platam_score  # 100% PLATAM
   ```

2. **Solo Experian (cliente nuevo sin historial):**
   ```python
   hybrid_score = experian_score * 0.80 + 500 * 0.20
   ```

3. **Sin datos (thin file):**
   ```python
   hybrid_score = 500  # Score conservador
   ```

### Fórmula Final

```python
hybrid_score = (platam_score * peso_platam) +
               (experian_score * peso_experian)
```

**Rango:** 300-1000 puntos

**Ventajas:**
- ✅ Justo para clientes nuevos y establecidos
- ✅ Confía más en PLATAM con más historial
- ✅ Usa Experian cuando historial interno es limitado
- ✅ Flexible según disponibilidad de datos

---

## 🤖 Modelo de Machine Learning

### Arquitectura

**Algoritmo:** XGBoost (Gradient Boosting)

**Objetivo:** Predecir probabilidad de default (incumplimiento de pago)

**Output:**
- `probability_default` (0-1): Probabilidad de incumplir
- `probability_no_default` (0-1): Probabilidad de cumplir

### Entrenamiento

**Datos de entrenamiento:**
- 1,835 clientes históricos
- Features: 17 variables
- Target: `default` (0 = cumplió, 1 = incumplió)

**Parámetros XGBoost:**
```python
{
    'max_depth': 6,
    'learning_rate': 0.1,
    'n_estimators': 100,
    'objective': 'binary:logistic',
    'random_state': 42
}
```

**Normalización:**
- StandardScaler en todas las features numéricas

### Deployment

**Plataforma:** Google Vertex AI
- **Endpoint ID:** 3426032820691755008
- **Región:** us-central1
- **Modelo:** platam-custom-final
- **Container:** Custom Python 3.11

### Niveles de Atención (basados en probabilidad)

| Prob. Default | Nivel de Atención | Plan de Acción |
|---------------|-------------------|----------------|
| < 20% | Monitoreo normal | Sin acción - Cliente confiable |
| 20-40% | Atención moderada | Recordatorio preventivo |
| 40-60% | Seguimiento cercano | Contacto preventivo |
| > 60% | Alerta crítica | Cobranza inmediata |

---

## 📐 Features y Variables

### 17 Features del Modelo ML

#### Scores Base (2):
1. `platam_score` - Score interno (300-900)
2. `experian_score_normalized` - Score externo (0-1000)

#### Scores Componentes (3):
3. `score_payment_performance` - Desempeño de pagos
4. `score_payment_plan` - Planes de pago
5. `score_deterioration` - Velocidad de deterioro

#### Historial de Pagos (6):
6. `payment_count` - Cantidad de pagos realizados
7. `months_as_client` - Antigüedad en meses
8. `days_past_due_mean` - Mora promedio (días)
9. `days_past_due_max` - Mora máxima (días)
10. `pct_early` - % de pagos anticipados
11. `pct_late` - % de pagos tardíos

#### Pesos Híbridos (2):
12. `peso_platam_usado` - Peso asignado a PLATAM (0-1)
13. `peso_hcpn_usado` - Peso asignado a Experian (0-1)

#### Planes de Pago (4):
14. `tiene_plan_activo` - Tiene plan activo (boolean)
15. `tiene_plan_default` - Tiene plan en default (boolean)
16. `tiene_plan_pendiente` - Tiene plan pendiente (boolean)
17. `num_planes` - Cantidad de planes de pago

### Estructura de Datos

**Archivo:** `data/processed/hybrid_scores.csv`

**Columnas principales:**
```csv
cedula,client_name,platam_score,experian_score_normalized,
hybrid_score,payment_count,months_as_client,
days_past_due_mean,pct_early,pct_late,
tiene_plan_activo,tiene_plan_default,num_planes,...
```

**Tamaño:** 1,835 clientes

---

## 🚀 API de Producción

### Información General

**URL Base:** `https://scoring-api-741488896424.us-central1.run.app`

**Tecnología:** FastAPI + Python 3.11

**Deployment:** Google Cloud Run

**Documentación interactiva:** `/docs`

### Endpoint Principal: POST /predict

**Request:**
```json
{
  "cedula": "1006157869"
}
```

**Response:**
```json
{
  "client_info": {
    "cedula": "1006157869",
    "months_as_client": 0,
    "payment_count": 0,
    "has_payment_history": false
  },
  "scoring": {
    "platam_score": 575.0,
    "experian_score": 715.4,
    "hybrid_score": 687.3,
    "hybrid_category": "Bueno",
    "peso_platam": 0.2,
    "peso_experian": 0.8
  },
  "ml_prediction": {
    "probability_default": 0.392,
    "probability_no_default": 0.608,
    "risk_level": "Medio",
    "attention_level": "Atención moderada"
  },
  "recommendation": {
    "action_plan": "Recordatorio preventivo - Seguimiento mensual",
    "priority": "Media",
    "reason": "Riesgo moderado (39.2%) con score bueno",
    "requires_follow_up": true,
    "flags": ["🆕 Cliente muy nuevo (<3 meses)"]
  }
}
```

### Otros Endpoints

**GET /health** - Estado de la API
```json
{
  "status": "healthy",
  "data_loaded": true,
  "vertex_ai": "connected",
  "clientes": 1835
}
```

**GET /stats** - Estadísticas de datos
```json
{
  "total_clientes": 1835,
  "score_promedio": 687.3,
  "score_min": 300,
  "score_max": 950
}
```

### Latencia y Performance

- **Latencia promedio:** ~500ms
- **Cold start:** ~2-3s (primera request)
- **Requests simultáneos:** Hasta 1000
- **Auto-escalado:** 0-10 instancias

---

## 🔧 Mantenimiento

### Actualización de Datos

**Frecuencia:** Manual (cuando sea necesario)

**Proceso:**
1. Actualizar `data/processed/hybrid_scores.csv`
2. Reconstruir imagen Docker
3. Redesplegar a Cloud Run

Ver: `GUIA_MANTENIMIENTO.md` para detalles.

### Monitoreo del Modelo

**Frecuencia:** Trimestral (cada 3 meses)

**Script:** `check_model_drift.py`

**Ejecutar:**
```bash
python check_model_drift.py
```

**Qué revisa:**
- Data drift (cambios en distribución)
- Precisión del modelo
- Necesidad de reentrenamiento

### Reentrenamiento

**Cuándo:**
- Cada 6+ meses
- Si data drift > 20%
- Si precisión baja significativamente

**Ver:** `GUIA_MANTENIMIENTO.md` para proceso completo

---

## 📚 Referencias

### Documentación Relacionada

- **API en producción:** `API_CLOUD_RUN.md`
- **Mantenimiento:** `GUIA_MANTENIMIENTO.md`
- **Vertex AI:** `VERTEX_AI_GUIA.md`
- **Sistema futuro:** `future_implementation/`

### Archivos Clave

**Producción:**
- `api_scoring_cedula.py` - API principal
- `data/processed/hybrid_scores.csv` - Datos
- `check_model_drift.py` - Monitoreo

**Vertex AI:**
- Endpoint: 3426032820691755008
- Región: us-central1
- Modelo: platam-custom-final

---

**Última actualización:** Enero 2026
**Versión del sistema:** 2.0 (Producción)
**Estado:** ✅ Operacional
