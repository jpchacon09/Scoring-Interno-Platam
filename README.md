# 🚀 PLATAM - Sistema de Scoring Crediticio v2.2

Sistema de scoring crediticio híbrido con Machine Learning y features demográficas para evaluación de riesgo de clientes PLATAM BNPL (Buy Now Pay Later).

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green.svg)](https://fastapi.tiangolo.com/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-orange.svg)](https://cloud.google.com/vertex-ai)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0.3-red.svg)](https://xgboost.readthedocs.io/)
[![Status](https://img.shields.io/badge/Status-Production-success.svg)]()

---

## 📋 Tabla de Contenidos

- [¿Qué es este sistema?](#-qué-es-este-sistema)
- [Novedades v2.2](#-novedades-v22-enero-2026)
- [Endpoints Disponibles](#-endpoints-disponibles)
- [Inicio Rápido](#-inicio-rápido)
- [Arquitectura](#-arquitectura)
- [Documentación](#-documentación)
- [Estructura del Proyecto](#-estructura-del-proyecto)

---

## 🎯 ¿Qué es este sistema?

**PLATAM Scoring System** es un sistema completo de evaluación crediticia que:

✅ **Calcula scores internos** basados en comportamiento de pago de clientes
✅ **Integra scores externos** (Experian/HCPN) con ponderación dinámica
✅ **Usa datos demográficos** (edad, ciudad, créditos en mora, cuota mensual)
✅ **Predice riesgo de default** usando XGBoost sin data leakage
✅ **Genera recomendaciones** de seguimiento y cobranza
✅ **API en producción** 24/7 en Google Cloud Run

### Caso de Uso

```
Input:  Cédula del cliente (ej: "1192925596")
        ↓
Output: Evaluación completa 360°
        • Score híbrido: 479 (Regular)
        • Probabilidad default: 19.0% (v2.2) vs 52.1% (v1.0)
        • Nivel de riesgo: Bajo
        • Ciudad: Barranquilla
        • Créditos en mora: 1 de 7
        • Plan de acción: Monitoreo normal
```

---

## 🌟 Novedades v2.2 (Enero 2026)

### ✅ Modelo con Features Demográficas

**Nuevo modelo desplegado en Vertex AI con:**
- 🔢 **22 features** (15 originales + 7 demográficas confiables)
- 🐍 **Python 3.11** + **XGBoost 2.0.3** (custom container)
- 🎯 **AUC: 0.760** (sin data leakage)
- 🏙️ **Datos demográficos:** edad, ciudad, créditos en mora, cuota mensual
- ❌ **Sin features de ingresos** (decisión de negocio por economía informal)

### 🔍 Features Agregadas

| Feature | Descripción | Importancia |
|---------|-------------|-------------|
| `cuota_mensual` | Cuota mensual real de HCPN | 7.5% |
| `ciudad_encoded` | Ciudad del cliente (geolocalización) | 6.1% |
| `creditos_mora` | Número de créditos en mora | 6.0% |
| `edad` | Edad del cliente | 5.6% |
| `creditos_vigentes` | Total créditos vigentes | 3.2% |
| `hist_neg_12m` | Historial negativo últimos 12m | 2.8% |
| `genero_encoded` | Género (sin data actualmente) | 0.1% |

### 🚫 Features Removidas

- ❌ `days_past_due_mean` - **Data leakage corregido**
- ❌ `days_past_due_max` - **Data leakage corregido**
- ❌ `ingresos_smlv` - No confiable (economía informal)
- ❌ `nivel_ingresos_encoded` - Deriva de ingresos
- ❌ `ratio_cuota_ingreso` - Depende de ingresos sesgados

### 💡 Insights de Negocio Descubiertos

- 🔴 **Manizales:** 48.8% tasa de default (vs 5.4% promedio)
- 🟡 **642 clientes** con ratio cuota/ingreso >45% (alto riesgo)
- 🟢 **Barranquilla/Bucaramanga:** <5% default rate
- 💰 **Ahorro potencial:** $142M/año con políticas basadas en insights

---

## 🌐 Endpoint en Producción

### ✅ Endpoint v2.2 (ACTIVO)

**Endpoint ID:** `7891061911641391104`
**Estado:** ✅ En producción desde enero 2026
**Features:** 22 (15 originales + 7 demográficas)
**Python:** 3.11 + XGBoost 2.0.3
**Container:** `gcr.io/platam-analytics/platam-scoring-py311:v2.2`

**URL API:** `https://scoring-api-741488896424.us-central1.run.app/predict`

**Ventajas:**
- ✅ Sin data leakage (days_past_due removido)
- ✅ Features demográficas confiables
- ✅ AUC: 0.760
- ✅ Probabilidad default promedio: 15.03%
- ✅ 54.4% clientes con riesgo muy bajo

**Usado por:**
- ✅ API actual en Cloud Run
- ✅ Integraciones n8n/Make

---

## 🚀 Inicio Rápido

### Prerequisitos

```bash
python >= 3.11
gcloud CLI configurado
Credenciales de GCP (key.json)
```

### 1. Probar Endpoint v2.2

```bash
# Probar con script de prueba
python test_vertex_endpoint.py

# O probar con cédula específica
python comparar_modelos.py  # Compara v1.0 vs v2.2
```

**Output esperado:**
```
✅ PREDICCIÓN EXITOSA
📊 Resultados:
   • Probabilidad NO Default: 0.810 (81.0%)
   • Probabilidad Default:    0.190 (19.0%)
   • Nivel de Riesgo:         Bajo
```

### 2. Desplegar Custom Container (si modificas el modelo)

```bash
cd vertex_custom_py311/

# Build container
gcloud builds submit --tag gcr.io/platam-analytics/platam-scoring-py311:v2.2

# Registrar en Vertex AI
gcloud ai models upload \
  --region=us-central1 \
  --display-name=platam-scoring-py311 \
  --container-image-uri=gcr.io/platam-analytics/platam-scoring-py311:v2.2 \
  --container-health-route=/health \
  --container-predict-route=/predict \
  --container-ports=8080
```

### 3. Actualizar API (si modificas el código)

```bash
# Redesplegar API a Cloud Run
gcloud run deploy scoring-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 🏗️ Arquitectura

```
┌─────────────────┐
│   n8n / Make    │  ← Integraciones
└────────┬────────┘
         │ POST /predict
         │ {"cedula": "..."}
         ▼
┌─────────────────┐
│  Cloud Run API  │  ← FastAPI en producción
└────────┬────────┘
         │
         ├─────────────────────┐
         │                     │
         ▼                     ▼
┌────────────────┐    ┌────────────────┐
│ Vertex AI v1.0 │    │ Vertex AI v2.2 │  ← ML Models
│ 17 features    │    │ 22 features    │
│ Python 3.7     │    │ Python 3.11    │
└────────────────┘    └────────────────┘
         │                     │
         │                     │
         ▼                     ▼
┌──────────────────────────────────────┐
│   SCORES_V2_ANALISIS_COMPLETO.csv    │  ← Datos (39 columnas)
│   1,870 clientes × 39 features       │
└──────────────────────────────────────┘
```

---

## 📚 Documentación

### Documentos Principales

| Documento | Descripción |
|-----------|-------------|
| **[ESTADO_FINAL_DEPLOYMENT.md](ESTADO_FINAL_DEPLOYMENT.md)** | 📖 **Lee este primero** - Estado completo, cómo probar, cómo migrar |
| **[INSIGHTS_Y_POLITICAS_DE_NEGOCIO.md](INSIGHTS_Y_POLITICAS_DE_NEGOCIO.md)** | 💡 Análisis de negocio y políticas recomendadas |
| **[DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md)** | 🔧 Detalles técnicos del sistema |

### Scripts Útiles

| Script | Uso |
|--------|-----|
| `test_vertex_endpoint.py` | Probar endpoint v2.2 |
| `comparar_modelos.py` | Comparar v1.0 vs v2.2 con cédula real |
| `add_demographics_to_scores_v2.py` | Agregar demografía a CSV (ya ejecutado) |

---

## 📁 Estructura del Proyecto

```
Scoring Interno/
│
├── 📊 Datos
│   ├── SCORES_V2_ANALISIS_COMPLETO.csv    # Datos con 39 columnas
│   └── data/analytics/                     # Segmentaciones y dashboards
│
├── 🤖 Modelos
│   ├── models/vertex_ai_final/             # Modelo v2.2 desplegado
│   │   ├── model.pkl                       # XGBoost 2.0.3
│   │   ├── scaler.pkl                      # StandardScaler
│   │   ├── feature_names.json              # 22 features
│   │   ├── model_metadata.json             # Metadatos
│   │   └── deployment_info.json            # Info de deployment
│   │
│   └── vertex_custom_py311/                # Custom container ⭐
│       ├── Dockerfile                      # Python 3.11 container
│       ├── predictor.py                    # Flask API
│       ├── model.pkl                       # Modelo embebido
│       ├── scaler.pkl
│       └── feature_names.json
│
├── 🌐 API
│   ├── api_scoring_cedula.py               # API principal (FastAPI)
│   └── Dockerfile                          # Container para Cloud Run
│
├── 🧪 Scripts de Prueba
│   ├── test_vertex_endpoint.py             # Probar endpoint
│   └── comparar_modelos.py                 # Comparar v1.0 vs v2.2
│
├── 📖 Documentación
│   ├── README.md                           # Este archivo
│   ├── ESTADO_FINAL_DEPLOYMENT.md          # Doc principal ⭐
│   ├── INSIGHTS_Y_POLITICAS_DE_NEGOCIO.md  # Análisis de negocio
│   └── DOCUMENTACION_TECNICA.md            # Detalles técnicos
│
└── 🔑 Configuración
    └── key.json                            # Credenciales GCP (no en git)
```

---

## 🎯 Próximos Pasos Recomendados

### Optimización y Monitoreo

1. **Analizar gráficas del modelo**
   ```bash
   # Ver gráficas en charts/
   open charts/v2.2_feature_importance.png
   open charts/v2.2_distribucion_probabilidades.png
   ```

2. **Implementar políticas de negocio**
   - Revisar `INSIGHTS_Y_POLITICAS_DE_NEGOCIO.md`
   - Aplicar políticas por ciudad (ej: Manizales 48.8% default)
   - Monitorear clientes con cuota/ingreso >45%

3. **Configurar monitoreo**
   - Alertas de drift del modelo
   - Seguimiento de performance
   - Ver `GUIA_MANTENIMIENTO.md`

4. **Actualización automática de datos** (futuro)
   - Ver `future_implementation/ACTUALIZACION_AUTOMATICA.md`

---

## 💰 Costos Actuales

| Servicio | Costo Mensual |
|----------|---------------|
| Vertex AI Endpoint v2.2 | $50-80/mes |
| Cloud Run API | $20-30/mes |
| **Total** | **~$70-110/mes** |

**Ahorro logrado:** ~$40-60/mes vs configuración anterior con 2 endpoints

---

## 📞 Información del Sistema

**Proyecto:** platam-analytics
**Región:** us-central1
**Endpoint Activo:** `7891061911641391104` (v2.2)
**API URL:** `https://scoring-api-741488896424.us-central1.run.app/predict`
**Container:** `gcr.io/platam-analytics/platam-scoring-py311:v2.2`

**Recursos en Producción:**
- 1 Endpoint Vertex AI (v2.2)
- 1 Modelo ML (platam-scoring-py311-custom)
- 1 Servicio Cloud Run (scoring-api)

---

## 📊 Changelog

### v2.2.1 (Enero 15, 2026) - Optimización de Recursos

✅ Eliminado endpoint v1.0 (ahorro $40-60/mes)
✅ Eliminados 5 modelos no utilizados
✅ Gráficas actualizadas con modelo v2.2
✅ README y documentación actualizados
✅ Solo 1 endpoint en producción: v2.2

### v2.2 (Enero 13, 2026) - Demografía sin Data Leakage

✅ Agregadas 7 features demográficas confiables
✅ Removido data leakage (days_past_due)
✅ Removidas features de ingresos (no confiables)
✅ Custom container Python 3.11 + XGBoost 2.0.3
✅ AUC: 0.760
✅ Desplegado a producción

### v1.0 (Diciembre 2025) - Sistema Base

✅ Score híbrido PLATAM + Experian
✅ Modelo ML con 17 features
✅ API en Cloud Run
✅ Integración n8n/Make
❌ Deprecado enero 2026

---

## 📈 Gráficas del Modelo

Las siguientes visualizaciones están disponibles en `charts/`:

1. **`v2.2_feature_importance.png`** - Importancia de las 22 features
2. **`v2.2_distribucion_probabilidades.png`** - Distribución de predicciones
3. **`v2.2_scatter_score_vs_prob.png`** - Score vs Probabilidad de default
4. **`v2.2_distribucion_niveles_riesgo.png`** - Segmentación por riesgo
5. **`v2.2_features_demograficas.png`** - Análisis features demográficas

---

**🎉 Sistema optimizado y en producción - Un solo endpoint v2.2**

