# ✅ Estado del Sistema - Optimizado y en Producción

**Fecha:** 15 de Enero 2026
**Status:** Sistema optimizado - Solo endpoint v2.2 en producción
**Ahorro:** ~$40-60/mes vs configuración anterior

---

## 🎯 Sistema Actual (v2.2.1)

### ✅ Endpoint en Producción

**Endpoint ID:** `7891061911641391104`
**Modelo ID:** `8594054462069276672` (platam-scoring-py311-custom)
**Estado:** ✅ **PRODUCCIÓN** (desde enero 13, 2026)

**URL API:** `https://scoring-api-741488896424.us-central1.run.app/predict`

**Características:**
- **22 features** (15 originales + 7 demográficas)
- **Custom Container:** Python 3.11 + XGBoost 2.0.3
- **AUC: 0.760** (sin data leakage)
- **Sin features de ingresos** (decisión de negocio por economía informal)
- Probado y validado ✅

**Features demográficas incluidas:**
1. `genero_encoded` - Género del cliente
2. `edad` - Edad del cliente (importancia: 5.6%)
3. `ciudad_encoded` - Ciudad del cliente (importancia: 6.1%)
4. `cuota_mensual` - Cuota mensual real HCPN (importancia: 7.5%) ⭐
5. `creditos_vigentes` - Total créditos vigentes (importancia: 3.2%)
6. `creditos_mora` - Número créditos en mora (importancia: 6.0%) ⭐
7. `hist_neg_12m` - Historial negativo 12 meses (importancia: 2.8%)

**Features REMOVIDAS vs modelo v1.0:**
- ❌ `days_past_due_mean` - Data leakage corregido
- ❌ `days_past_due_max` - Data leakage corregido
- ❌ `ingresos_smlv` - No confiable (economía informal)
- ❌ `nivel_ingresos_encoded` - Deriva de ingresos sesgados
- ❌ `ratio_cuota_ingreso` - Depende de ingresos no confiables

---

## 📊 Estadísticas del Modelo en Producción

**Análisis sobre 1,870 clientes:**

| Métrica | Valor |
|---------|-------|
| Probabilidad default promedio | 15.03% |
| Probabilidad default mediana | 9.18% |
| AUC | 0.760 |
| Total features | 22 |

**Distribución de clientes por nivel de riesgo:**

| Nivel | Clientes | Porcentaje |
|-------|----------|------------|
| Muy Bajo | 1,017 | 54.4% ✅ |
| Bajo | 379 | 20.3% |
| Medio | 421 | 22.5% |
| Alto | 41 | 2.2% |
| Muy Alto | 12 | 0.6% |

**Insights clave:**
- 🟢 74.7% de clientes en categoría "Bajo riesgo" o mejor
- 🟡 22.5% requieren monitoreo moderado
- 🔴 Solo 2.8% en categorías de alto riesgo

---

## 🧪 Cómo Probar el Endpoint

### Opción 1: Script de Prueba (Recomendado)

```bash
cd "/Users/jpchacon/Scoring Interno"
python test_vertex_endpoint.py
```

**Output esperado:**
```
✅ PREDICCIÓN EXITOSA
📊 Resultados:
   • Probabilidad NO Default: 0.810 (81.0%)
   • Probabilidad Default:    0.190 (19.0%)
   • Nivel de Riesgo:         Bajo
```

### Opción 2: Probar API Completa

```bash
curl -X POST "https://scoring-api-741488896424.us-central1.run.app/predict" \
  -H "Content-Type: application/json" \
  -d '{"cedula":"1192925596"}'
```

**Response esperado:**
```json
{
  "client_info": {
    "cedula": "1192925596",
    "months_as_client": 4,
    "payment_count": 2
  },
  "scoring": {
    "hybrid_score": 479.09,
    "hybrid_category": "Regular"
  },
  "ml_prediction": {
    "probability_default": 0.19,
    "risk_level": "Bajo",
    "attention_level": "Monitoreo normal"
  },
  "recommendation": {
    "action_plan": "Monitoreo rutinario - Revisar score bajo",
    "priority": "Baja"
  }
}
```

### Opción 3: Probar desde Python

```python
from google.cloud import aiplatform
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"

# Conectar
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

# Datos de prueba (22 features en orden correcto)
test_instance = [
    750,      # platam_score
    715,      # experian_score_normalized
    680,      # score_payment_performance
    600,      # score_payment_plan
    700,      # score_deterioration
    50,       # payment_count
    24,       # months_as_client
    0.1,      # pct_early
    0.05,     # pct_late
    0.6,      # peso_platam_usado
    0.4,      # peso_hcpn_usado
    0,        # tiene_plan_activo
    0,        # tiene_plan_default
    0,        # tiene_plan_pendiente
    0,        # num_planes
    # 7 demográficas
    0,        # genero_encoded
    35,       # edad
    0,        # ciudad_encoded
    1500000,  # cuota_mensual
    5,        # creditos_vigentes
    0,        # creditos_mora
    0         # hist_neg_12m
]

# Predecir
prediction = endpoint.predict(instances=[test_instance])
print(f"Probabilidad Default: {prediction.predictions[0][1]:.2%}")
```

---

## 📈 Gráficas del Modelo

Las siguientes visualizaciones están disponibles en `charts/`:

1. **`v2.2_feature_importance.png`**
   Importancia de las 22 features del modelo

2. **`v2.2_distribucion_probabilidades.png`**
   Distribución de predicciones (histograma + boxplot)

3. **`v2.2_scatter_score_vs_prob.png`**
   Relación entre Score Híbrido y Probabilidad de Default

4. **`v2.2_distribucion_niveles_riesgo.png`**
   Segmentación de clientes por nivel de riesgo

5. **`v2.2_features_demograficas.png`**
   Análisis de importancia de features demográficas

**Generar gráficas actualizadas:**
```bash
python generar_graficas_v2.2.py
```

---

## 💰 Costos Actuales

| Servicio | Costo Mensual |
|----------|---------------|
| Vertex AI Endpoint v2.2 | $50-80/mes |
| Cloud Run API | $20-30/mes |
| Cloud Storage | <$5/mes |
| **Total** | **~$70-110/mes** |

**Ahorro logrado:**
- ✅ Eliminado endpoint v1.0: ~$40-60/mes
- ✅ Eliminados 5 modelos no utilizados: Costos de storage
- ✅ **Ahorro total mensual: ~$40-60**

---

## 🏗️ Arquitectura Actual

```
┌─────────────────┐
│   n8n / Make    │  ← Integraciones activas
└────────┬────────┘
         │ POST /predict
         │ {"cedula": "..."}
         ▼
┌─────────────────────────────────────────────────┐
│  Cloud Run API                                  │
│  https://scoring-api-741488896424               │
│       .us-central1.run.app/predict              │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│  Vertex AI Endpoint v2.2                        │
│  ID: 7891061911641391104                        │
│  • Modelo: platam-scoring-py311-custom          │
│  • 22 features (con demografía)                 │
│  • Python 3.11 + XGBoost 2.0.3                  │
└────────┬────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│   SCORES_V2_ANALISIS_COMPLETO.csv               │
│   1,870 clientes × 39 features                  │
└─────────────────────────────────────────────────┘
```

---

## 🔧 Mantenimiento

### Actualizar API (si modificas código)

```bash
cd "/Users/jpchacon/Scoring Interno"

# Redesplegar a Cloud Run
gcloud run deploy scoring-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Regenerar Gráficas

```bash
python generar_graficas_v2.2.py
```

### Verificar Estado del Sistema

```bash
# Listar endpoints activos
gcloud ai endpoints list --region=us-central1

# Listar modelos
gcloud ai models list --region=us-central1

# Verificar API
curl https://scoring-api-741488896424.us-central1.run.app/health
```

---

## 📊 Comparación v1.0 vs v2.2

| Característica | v1.0 (Deprecado) | v2.2 (Actual) |
|----------------|------------------|---------------|
| **Features** | 17 | 22 ✅ |
| **Demografía** | ❌ No | ✅ Sí (7 features) |
| **Data Leakage** | ⚠️ Sí (days_past_due) | ✅ Corregido |
| **Income Features** | ⚠️ Incluidas | ✅ Removidas (decisión de negocio) |
| **AUC** | ~0.98 (inflado) | 0.760 (real) ✅ |
| **Python** | 3.7 | 3.11 ✅ |
| **XGBoost** | 1.x | 2.0.3 ✅ |
| **Estado** | ❌ Eliminado | ✅ En producción |

---

## 🎯 Beneficios del Modelo v2.2

### Mejoras Técnicas:
- ✅ Sin data leakage (predicciones confiables)
- ✅ Modelo más robusto y generalizable
- ✅ Features basadas en datos reales
- ✅ Stack tecnológico moderno (Python 3.11)

### Mejoras de Negocio:
- ✅ Identifica riesgo geográfico (ej: Manizales 48.8% default)
- ✅ Detecta clientes con múltiples créditos en mora
- ✅ Considera cuota mensual real de HCPN
- ✅ Ignora ingresos declarados (economía informal)

### Insights Accionables:
- 642 clientes con ratio cuota/ingreso >45% (alto riesgo)
- Ciudades de alto riesgo identificadas
- **Ahorro potencial: $142M/año** con políticas basadas en insights

---

## 📞 Información del Sistema

**Proyecto GCP:** platam-analytics
**Región:** us-central1
**Endpoint ID:** `7891061911641391104`

**Recursos en Producción:**
- 1 Endpoint Vertex AI (v2.2)
- 1 Modelo ML (platam-scoring-py311-custom)
- 1 Servicio Cloud Run (scoring-api)
- 1 Bucket Storage (platam-analytics-models)

**URLs Importantes:**
- API: `https://scoring-api-741488896424.us-central1.run.app/predict`
- Health: `https://scoring-api-741488896424.us-central1.run.app/health`
- Stats: `https://scoring-api-741488896424.us-central1.run.app/stats`
- Docs: `https://scoring-api-741488896424.us-central1.run.app/docs`

**Container:**
- Image: `gcr.io/platam-analytics/platam-scoring-py311:v2.2`
- Base: Python 3.11-slim
- Dependencies: XGBoost 2.0.3, scikit-learn 1.3.2, pandas 2.1.4

---

## 🎉 Estado Actual

**Tu sistema está optimizado y funcionando:**
- ✅ API de producción 100% funcional
- ✅ n8n/Make integrados y funcionando
- ✅ Endpoint v2.2 con mejores predicciones
- ✅ Costos optimizados (~$40-60/mes de ahorro)
- ✅ Gráficas actualizadas disponibles
- ✅ Documentación completa y actualizada

**Sistema listo para escalar cuando lo necesites!**

---

## 📚 Documentación Relacionada

- **[README.md](README.md)** - Guía principal del proyecto
- **[INSIGHTS_Y_POLITICAS_DE_NEGOCIO.md](INSIGHTS_Y_POLITICAS_DE_NEGOCIO.md)** - Análisis de negocio
- **[DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md)** - Detalles técnicos
- **[GUIA_MANTENIMIENTO.md](GUIA_MANTENIMIENTO.md)** - Guía de mantenimiento

---

**Última actualización:** 15 de Enero 2026, 10:30 EST
**Versión:** 2.2.1 - Sistema optimizado y en producción
