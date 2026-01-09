# 🚀 PLATAM - Sistema de Scoring Crediticio

Sistema de scoring crediticio híbrido con Machine Learning para evaluación de riesgo de clientes PLATAM BNPL (Buy Now Pay Later).

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green.svg)](https://fastapi.tiangolo.com/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-orange.svg)](https://cloud.google.com/vertex-ai)
[![Status](https://img.shields.io/badge/Status-Production-success.svg)]()

---

## 📋 Tabla de Contenidos

- [¿Qué es este sistema?](#-qué-es-este-sistema)
- [Estado Actual](#-estado-actual)
- [Inicio Rápido](#-inicio-rápido)
- [Arquitectura](#-arquitectura)
- [Cómo Funciona](#-cómo-funciona)
- [Documentación](#-documentación)
- [Estructura del Proyecto](#-estructura-del-proyecto)

---

## 🎯 ¿Qué es este sistema?

**PLATAM Scoring System** es un sistema completo de evaluación crediticia que:

✅ **Calcula scores internos** basados en comportamiento de pago de clientes
✅ **Integra scores externos** (Experian/HCPN) con ponderación dinámica
✅ **Predice riesgo de default** usando Machine Learning (XGBoost)
✅ **Genera recomendaciones** de seguimiento y cobranza
✅ **API en producción** accesible 24/7 en Google Cloud Run

### Caso de Uso

```
Input:  Cédula del cliente (ej: "1006157869")
        ↓
Output: Evaluación completa 360°
        • Score híbrido: 687 (Bueno)
        • Probabilidad default: 39.2%
        • Nivel de atención: Atención moderada
        • Plan de acción: Recordatorio preventivo
```

---

## 🌟 Estado Actual

### ✅ Sistema en Producción (Enero 2026)

| Componente | Estado | Descripción |
|------------|--------|-------------|
| **API Cloud Run** | 🟢 Live | https://scoring-api-...run.app |
| **Modelo ML (Vertex AI)** | 🟢 Deployed | XGBoost - platam-custom-final |
| **Datos** | 🟢 Loaded | 1,835 clientes activos |
| **Scoring Híbrido** | 🟢 Active | PLATAM + Experian |
| **Monitoreo** | 🟢 Scheduled | Trimestral |

### Métricas del Sistema

- **Clientes:** 1,835 con scoring completo
- **Latencia API:** ~500ms promedio
- **Uptime:** 99.9% (Cloud Run)
- **Precisión ML:** Monitoreada trimestralmente
- **Costo mensual:** ~$70 (Vertex AI)

---

## 🚀 Inicio Rápido

### Para Desarrolladores

#### 1. Consultar la API

```bash
curl -X POST "https://scoring-api-741488896424.us-central1.run.app/predict" \
  -H "Content-Type: application/json" \
  -d '{"cedula":"1006157869"}'
```

#### 2. Integración con n8n

```javascript
// HTTP Request Node
{
  method: "POST",
  url: "https://scoring-api-741488896424.us-central1.run.app/predict",
  body: {
    cedula: "{{ $json.cedula }}"
  }
}
```

#### 3. Python SDK

```python
import requests

response = requests.post(
    "https://scoring-api-741488896424.us-central1.run.app/predict",
    json={"cedula": "1006157869"}
)

result = response.json()
print(f"Score híbrido: {result['scoring']['hybrid_score']}")
print(f"Riesgo default: {result['ml_prediction']['probability_default']:.1%}")
print(f"Acción sugerida: {result['recommendation']['action_plan']}")
```

### Para Administradores

#### Monitoreo Trimestral

```bash
cd "/Users/jpchacon/Scoring Interno"
python check_model_drift.py
```

Ver: [`GUIA_MANTENIMIENTO.md`](GUIA_MANTENIMIENTO.md) para más detalles.

---

## 🏗️ Arquitectura

```
┌────────────────────────────────────────────────────────┐
│                    FRONTEND                            │
│              n8n Workflows / API Clients               │
└──────────────────┬─────────────────────────────────────┘
                   │
                   │ HTTPS POST /predict
                   ↓
┌────────────────────────────────────────────────────────┐
│               CLOUD RUN API (FastAPI)                  │
│  • api_scoring_cedula.py                               │
│  • Data: CSV en memoria (1,835 clientes)              │
│  • Región: us-central1                                 │
└──────────────────┬─────────────────────────────────────┘
                   │
                   │ 17 features
                   ↓
┌────────────────────────────────────────────────────────┐
│            VERTEX AI (Google Cloud)                    │
│  • Modelo: XGBoost (platam-custom-final)              │
│  • Endpoint: 3426032820691755008                       │
│  • Predice: Probabilidad de default                   │
└────────────────────────────────────────────────────────┘
```

### Stack Tecnológico

**Backend:**
- Python 3.11
- FastAPI (REST API)
- Pandas (procesamiento de datos)
- XGBoost (Machine Learning)

**Cloud:**
- Google Cloud Run (API hosting)
- Google Vertex AI (ML deployment)
- Docker (containerización)

**Data:**
- CSV (1,835 clientes)
- 17 features por cliente
- Scores precalculados

---

## 💡 Cómo Funciona

### 1. Sistema de Scoring PLATAM (Interno)

Calcula score **0-900** basado en:

- **Payment Performance (60%):** Puntualidad de pagos, mora promedio
- **Payment Plan (15%):** Planes de pago activos/default
- **Deterioration (25%):** Velocidad de deterioro del comportamiento

### 2. Sistema Híbrido Inteligente

Combina **PLATAM Score** + **Experian Score** con ponderación dinámica:

| Antigüedad | Peso PLATAM | Peso Experian |
|------------|-------------|---------------|
| < 3 meses | 20% | 80% |
| 3-6 meses | 40% | 60% |
| 6-12 meses | 50% | 50% |
| 12-24 meses | 60% | 40% |
| > 24 meses | 70% | 30% |

**¿Por qué dinámico?**
- Clientes nuevos: Confía más en historial externo (Experian)
- Clientes maduros: Confía más en comportamiento interno (PLATAM)

### 3. Modelo de Machine Learning

**XGBoost** entrenado con 1,835 clientes históricos predice:

- `probability_default`: 0-100% (riesgo de incumplimiento)
- Basado en 17 features de comportamiento

### 4. Sistema de Recomendaciones

Combina scoring + ML para generar:

- **Nivel de atención:** Monitoreo normal → Alerta crítica
- **Plan de acción:** Desde "Sin acción" hasta "Cobranza inmediata"
- **Prioridad:** Ninguna → Crítica
- **Flags:** Alertas específicas del cliente

### 5. Proceso de Scores Empresariales

Para clientes empresariales (NIT), el sistema:

1. **Obtiene datos Experian:** PDFs empresariales → Extracción automática de scores
2. **Normaliza scores:** Escala 0-950 → 0-1000 (comparable con personas naturales)
3. **Calcula híbrido:** Mismo algoritmo con ponderación ajustada
4. **Genera predicción:** Modelo ML entrenado incluye empresas

**Resultado:** Scoring unificado para personas naturales y jurídicas.

---

## 📚 Documentación

### Guías Principales

| Documento | Descripción |
|-----------|-------------|
| **[API_CLOUD_RUN.md](API_CLOUD_RUN.md)** | Documentación completa de la API en producción |
| **[DOCUMENTACION_TECNICA.md](DOCUMENTACION_TECNICA.md)** | Arquitectura, algoritmos y detalles técnicos |
| **[GUIA_MANTENIMIENTO.md](GUIA_MANTENIMIENTO.md)** | Mantenimiento y monitoreo del sistema |
| **[VERTEX_AI_GUIA.md](VERTEX_AI_GUIA.md)** | Uso y gestión de Vertex AI |

### Recursos Adicionales

- **[future_implementation/](future_implementation/)** - Sistema de actualización automática (MySQL)
- **[docs/archive/](docs/archive/)** - Documentos históricos del proyecto

### API Docs Interactiva

Swagger UI: https://scoring-api-741488896424.us-central1.run.app/docs

---

## 📁 Estructura del Proyecto

```
.
├── api_scoring_cedula.py              # API principal (Cloud Run)
├── check_model_drift.py               # Monitoreo trimestral del modelo
├── data/
│   └── processed/
│       └── hybrid_scores.csv          # Datos de clientes (1,835)
├── future_implementation/             # Sistema de actualización automática
│   ├── README.md
│   └── ACTUALIZACION_AUTOMATICA.md
├── docs/
│   └── archive/                       # Documentos históricos
├── config/
│   └── key.json                       # Credenciales GCP
├── README.md                          # Este archivo
├── API_CLOUD_RUN.md                   # Docs API
├── DOCUMENTACION_TECNICA.md           # Docs técnicas
├── GUIA_MANTENIMIENTO.md              # Mantenimiento
└── VERTEX_AI_GUIA.md                  # Vertex AI
```

### Archivos Clave en Producción

**API:**
- `api_scoring_cedula.py` - FastAPI application
- `Dockerfile` - Container configuration
- `requirements-api.txt` - Python dependencies

**Data:**
- `data/processed/hybrid_scores.csv` - 1,835 clientes con scores

**Monitoreo:**
- `check_model_drift.py` - Health check trimestral

**Deployment:**
- `.gcloudignore` - Exclude files from deployment
- `config/key.json` - GCP credentials

---

## 🔧 Desarrollo Local

### Prerrequisitos

```bash
Python 3.11+
pandas
fastapi
uvicorn
google-cloud-aiplatform
```

### Ejecutar API Localmente

```bash
# 1. Instalar dependencias
pip install -r requirements-api.txt

# 2. Configurar credenciales GCP
export GOOGLE_APPLICATION_CREDENTIALS="config/key.json"

# 3. Ejecutar API
python api_scoring_cedula.py

# 4. Probar
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"cedula":"1006157869"}'
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Stats
curl http://localhost:8000/stats

# Docs
open http://localhost:8000/docs
```

---

## 🔄 Actualizaciones y Mantenimiento

### Actualizar Datos

**Frecuencia:** Manual (cuando sea necesario)

```bash
# 1. Actualizar CSV
# Reemplazar: data/processed/hybrid_scores.csv

# 2. Rebuild Docker
gcloud builds submit --tag gcr.io/platam-analytics/scoring-api:latest

# 3. Redesplegar
gcloud run deploy scoring-api \
  --image gcr.io/platam-analytics/scoring-api:latest \
  --region us-central1
```

Ver [`GUIA_MANTENIMIENTO.md`](GUIA_MANTENIMIENTO.md) para detalles.

### Monitoreo del Modelo

**Frecuencia:** Trimestral (cada 3 meses)

```bash
python check_model_drift.py
```

**Próxima ejecución:** Abril 2026

### Reentrenar Modelo

**Cuándo:**
- Cada 6+ meses
- Si data drift > 20%
- Si precisión baja significativamente

Ver [`GUIA_MANTENIMIENTO.md`](GUIA_MANTENIMIENTO.md) para proceso completo.

---

## 🌐 URLs de Producción

### API
- **Base:** https://scoring-api-741488896424.us-central1.run.app
- **Docs:** https://scoring-api-741488896424.us-central1.run.app/docs
- **Health:** https://scoring-api-741488896424.us-central1.run.app/health
- **Stats:** https://scoring-api-741488896424.us-central1.run.app/stats

### Google Cloud Console
- **Cloud Run:** [scoring-api](https://console.cloud.google.com/run/detail/us-central1/scoring-api?project=platam-analytics)
- **Vertex AI:** [Endpoint 3426032820691755008](https://console.cloud.google.com/vertex-ai/endpoints/3426032820691755008?project=platam-analytics)

---

## 📊 Métricas y Performance

### API Performance
- **Latencia:** ~500ms promedio
- **Cold start:** ~2-3s (primera request)
- **Throughput:** Hasta 1000 requests simultáneos
- **Disponibilidad:** 99.9% (Cloud Run SLA)

### Modelo ML
- **Clientes evaluados:** 1,835
- **Features por cliente:** 17
- **Score híbrido promedio:** 687.3
- **Rango de scores:** 300-950

### Costos
- **Cloud Run:** $0/mes (free tier)
- **Vertex AI:** ~$70/mes (n1-standard-2 24/7)
- **Cloud Storage:** ~$0.02/mes
- **Total:** ~$70/mes

---

## 🎓 Para Aprender Más

### Algoritmos

**Scoring PLATAM:**
- Ver sección "Algoritmo de Scoring" en [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md)

**Sistema Híbrido:**
- Ver sección "Sistema Híbrido" en [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md)

**Machine Learning:**
- Ver sección "Modelo ML" en [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md)

### Arquitectura

- Ver [`DOCUMENTACION_TECNICA.md`](DOCUMENTACION_TECNICA.md) - Arquitectura completa
- Ver [`API_CLOUD_RUN.md`](API_CLOUD_RUN.md) - Detalles de deployment

---

## 🤝 Contribuir

### Workflow de Desarrollo

1. Crear feature branch
2. Desarrollar y probar localmente
3. Commit con mensajes descriptivos
4. Push y crear Pull Request
5. Review y merge a main

### Commits

```bash
git commit -m "tipo: descripción breve

Detalles adicionales si necesario.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Tipos de commit:**
- `feat:` - Nueva funcionalidad
- `fix:` - Bug fix
- `docs:` - Documentación
- `refactor:` - Refactorización
- `test:` - Tests
- `chore:` - Mantenimiento

---

## 📞 Contacto y Soporte

**Proyecto:** PLATAM - Sistema de Scoring Interno

**Cloud Project:** platam-analytics

**Repositorio:** https://github.com/jpchacon09/Scoring-Interno-Platam

---

## 📜 Historial de Versiones

### v2.0 - Enero 2026 (Actual)
- ✅ API en producción (Cloud Run)
- ✅ Modelo ML desplegado (Vertex AI)
- ✅ Sistema híbrido implementado
- ✅ Monitoreo trimestral
- ✅ Scoring empresarial integrado

### v1.0 - Diciembre 2025
- Scoring PLATAM V2.0
- Sistema híbrido con Experian
- Análisis y visualizaciones

---

**Última actualización:** Enero 2026
**Versión:** 2.0
**Estado:** 🟢 Producción

---

**🚀 Sistema listo para uso en producción**
