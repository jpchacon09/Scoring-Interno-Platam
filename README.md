# 🎯 Sistema de Scoring en Tiempo Real - PLATAM Analytics

**Sistema automático de cálculo y actualización de scores crediticios en tiempo real**

[![Status](https://img.shields.io/badge/status-production-success)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![GCP](https://img.shields.io/badge/GCP-Cloud%20Functions-orange)]()
[![ML](https://img.shields.io/badge/ML-Vertex%20AI-green)]()

---

## 📋 ¿Qué es este sistema?

**PLATAM Scoring System** es un sistema completo de evaluación crediticia que:

✅ **Recibe triggers automáticos** de eventos de negocio (pagos tardíos, nuevos préstamos, etc.)
✅ **Consulta datos en tiempo real** de MySQL (clientes, pagos, préstamos)
✅ **Calcula scores internos** basados en comportamiento de pago (PLATAM Score)
✅ **Integra scores externos** (Experian/HCPN) con ponderación dinámica
✅ **Predice riesgo de default** usando Machine Learning (Vertex AI)
✅ **Actualiza WordPress** automáticamente vía REST API

**Tiempo de respuesta:** ~3 segundos de extremo a extremo

---

## 🏗️ Arquitectura del Sistema

```
Trigger (Equipo Tech)
    ↓
    {"client_id": "1702", "trigger": "late_7"}
    ↓
┌─────────────────────────┐
│  n8n Workflow           │ ← Orquestador principal
│  (7 nodos)              │
│  • Webhook              │
│  • 3x MySQL Queries     │
│  • Function (prep data) │
│  • 2x HTTP Requests     │
└────────┬────────────────┘
         │ HTTP POST
         ▼
┌─────────────────────────────────┐
│  Google Cloud Function          │
│  calculate-scores               │
│  • Descarga HCPN de S3         │
│  • Calcula PLATAM Score        │
│  • Calcula Hybrid Score        │
│  • Llama Vertex AI             │
└────────┬────────────────────────┘
         │
         ├──→ AWS S3 (HCPN/Experian data)
         │
         ├──→ Vertex AI Endpoint 7891061911641391104
         │    (Modelo v2.2 - 22 features)
         │
         ▼
┌─────────────────────────┐
│  WordPress REST API     │ ← Actualización automática
│  • cl_platam_score      │
│  • cl_hybrid_score      │
│  • cl_ml_risk_level     │
│  • 5 campos más...      │
└─────────────────────────┘
```

---

## 🚀 Quick Start (30 minutos)

### Prerequisitos

- gcloud CLI instalado y autenticado
- Acceso a proyecto GCP: `platam-analytics`
- Credenciales AWS en `config/.env`
- Acceso a n8n
- Credenciales MySQL y WordPress en n8n

### 1. Deploy Cloud Function

```bash
cd cloud_function_calculate_scores
./deploy_auto_fixed.sh
```

Esto:
- ✅ Lee credenciales de `config/.env` automáticamente
- ✅ Deploya a GCP (us-central1)
- ✅ Configura variables de entorno (AWS S3, etc.)
- ✅ Te da la URL de la Cloud Function

**Tiempo:** ~5 minutos

### 2. Configurar n8n (con ayuda de IA)

1. Abre: **[`INSTRUCCIONES_N8N_PARA_LLM.md`](./INSTRUCCIONES_N8N_PARA_LLM.md)**
2. Copia TODO el contenido (Cmd+A, Cmd+C)
3. Pégalo en ChatGPT, Claude o Gemini
4. Dile: "La URL de mi Cloud Function es: [TU_URL]"
5. Sigue las instrucciones paso a paso

El asistente te guiará para configurar 7 nodos en n8n.

**Tiempo:** ~15 minutos

### 3. Probar

```bash
# Test Cloud Function
curl -X POST https://TU_URL_CLOUD_FUNCTION \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI"},
    "payments": [{"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}],
    "payment_plans": []
  }'

# Test n8n workflow
# En n8n: Click "Execute Workflow"

# Verificar WordPress
# Buscar cliente ID 1702 y verificar scores actualizados
```

**Tiempo:** ~5 minutos

---

## 📁 Estructura del Proyecto

```
Scoring Interno/
│
├── 📄 README.md ............................ Este archivo
├── 📄 INICIO_RAPIDO.md ..................... Guía rápida 3 pasos
├── 📄 INSTRUCCIONES_N8N_PARA_LLM.md ........ Setup n8n paso a paso
├── 📄 N8N_QUERIES_FINALES.md ............... Queries SQL exactas
│
├── 📂 cloud_function_calculate_scores/
│   ├── main.py ............................. Cloud Function (591 líneas)
│   ├── requirements.txt .................... Dependencies (boto3, pandas, etc.)
│   ├── deploy_auto_fixed.sh ................ Script deployment (USAR ESTE)
│   └── deploy.sh ........................... Script manual (legacy)
│
├── 📂 config/
│   └── .env ................................ Credenciales AWS (protegido)
│
├── 📂 docs/
│   ├── reference/ .......................... Docs de referencia
│   │   ├── ARQUITECTURA_COMPLETA.md ........ Diagrama técnico detallado
│   │   ├── COMANDOS_DEPLOYMENT.md .......... Comandos útiles
│   │   ├── GUIA_DEPLOYMENT_FINAL.md ........ Guía completa
│   │   └── ...
│   │
│   └── archive/ ............................ Docs legacy/obsoletos
│
└── 📂 notebooks/ ........................... Análisis y entrenamiento ML
```

---

## 🎯 Componentes del Sistema

### 1. Cloud Function (GCP)

**Función:** `calculate-scores`
**URL:** `https://calculate-scores-k6yfpoyfea-uc.a.run.app`
**Runtime:** Python 3.11
**Región:** us-central1
**Memoria:** 1GB
**Timeout:** 60s

**Responsabilidades:**
1. Descargar HCPN de S3 (`hcpn_{cedula}.json`)
2. Calcular PLATAM Score (1000 pts):
   - Payment Performance (600 pts)
   - Payment Plan (150 pts)
   - Deterioration Velocity (250 pts)
3. Calcular Hybrid Score (PLATAM + Experian ponderado)
4. Llamar Vertex AI para predicción ML (22 features)
5. Retornar scores + predicción + metadata

### 2. Vertex AI Endpoint

**Endpoint ID:** `7891061911641391104`
**Modelo:** XGBoost 2.0.3 (v2.2)
**Features:** 22
**Python:** 3.11
**AUC:** 0.760

**Features del modelo:**
- PLATAM scores (5)
- Payment history (4)
- Payment plans (5)
- Demographics (7): edad, ciudad, género, cuota_mensual, créditos_vigentes, créditos_mora, hist_neg_12m
- Experian score (1)

**Output:**
- Probabilidad de default
- Probabilidad de no default
- Nivel de riesgo (Muy Bajo, Bajo, Medio, Alto, Muy Alto)

### 3. n8n Workflow

**Nombre:** ActualizarML - Scoring en Tiempo Real

**Nodos (7):**
1. **Webhook** - Recibe triggers (`/scoring-trigger`)
2. **MySQL: Select Cliente** - Query tabla `wp_jet_cct_clientes`
3. **MySQL: Select Pagos** - Query tabla `wp_jet_cct_pagos`
4. **MySQL: Select Préstamos** - Query tabla `wp_jet_cct_prestamos`
5. **Function** - Prepara JSON para Cloud Function
6. **HTTP Request** - Llama Cloud Function
7. **HTTP Request** - Actualiza WordPress

### 4. WordPress REST API

**Endpoint:** `https://platampay.com/wp-json/jet-cct/clientes/{ID}`

**Campos actualizados:**
- `cl_platam_score`
- `cl_hybrid_score`
- `cl_ml_probability_default`
- `cl_ml_probability_no_default`
- `cl_ml_risk_level`
- `cl_hybrid_weight_platam`
- `cl_hybrid_weight_experian`
- `cl_ml_modified`

---

## 🔄 Triggers Soportados

```javascript
triggers = [
  'late_1', 'late_7', 'late_14', 'late_25', 'late_34',
  'late_55', 'late_64', 'late_90', 'late_120', 'late_150',
  'new_loan',
  'payment'
]
```

**Formato:**
```json
{
  "client_id": "1702",
  "trigger": "late_7"
}
```

**Flujo automático:**
```
1. Tech team envía trigger
2. n8n recibe y consulta MySQL (datos actuales)
3. Cloud Function calcula scores
4. Vertex AI predice riesgo
5. WordPress actualizado (3 segundos total)
```

---

## 📊 PLATAM Scoring System

### Score Total: 1000 puntos

**1. Payment Performance (600 pts)**
- Evalúa puntualidad de pagos
- Penalización según días de mora:
  - 0 días: 100 pts
  - 1-15 días: 100 - (días × 3)
  - 16-30 días: 55 - (días × 2)
  - >30 días: 0 pts

**2. Payment Plan (150 pts)**
- Base: 150 pts
- Penalizaciones:
  - Plan activo: -50 pts
  - Plan en default: -100 pts
  - Plan completado: +30 pts

**3. Deterioration Velocity (250 pts)**
- Compara mora reciente vs histórica
- Detecta tendencias de mejora/deterioro
- Penaliza deterioro acelerado

### Hybrid Score

Combinación ponderada de PLATAM + Experian:

```
Hybrid = (PLATAM × peso_platam) + (Experian × peso_hcpn)
```

**Pesos dinámicos según antigüedad:**
- Muy nuevo (<3m): 30% PLATAM, 70% Experian
- Nuevo (3-6m): 40% PLATAM, 60% Experian
- Intermedio (6-12m): 50% PLATAM, 50% Experian
- Establecido (12-24m): 60% PLATAM, 40% Experian
- Maduro (>24m): 70% PLATAM, 30% Experian

---

## 🧪 Testing

### Test Cloud Function

```bash
curl -X POST https://calculate-scores-k6yfpoyfea-uc.a.run.app \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI"},
    "payments": [
      {"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}
    ],
    "payment_plans": []
  }'
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "platam_score": 575.0,
  "hybrid_score": 575.0,
  "ml_probability_default": 0.1425,
  "ml_risk_level": "Bajo",
  "processing_time_ms": 1562,
  "hcpn_found": false
}
```

### Ver Logs

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --project=platam-analytics \
  --limit=50
```

---

## 📈 Performance

| Métrica | Valor |
|---------|-------|
| Tiempo total (extremo a extremo) | ~3 segundos |
| Cloud Function | ~1.5 segundos |
| Vertex AI prediction | ~500ms |
| MySQL queries (n8n) | ~300ms |
| WordPress update | ~300ms |

---

## 🔐 Seguridad

### Credenciales Protegidas

**NO están en el repositorio:**
- ✅ `config/.env` (protegido por .gitignore)
- ✅ AWS credentials (solo en Cloud Function env vars)
- ✅ MySQL credentials (solo en n8n)
- ✅ WordPress credentials (solo en n8n)

**Separación de responsabilidades:**
- n8n: Solo MySQL + WordPress
- Cloud Function: Solo S3 + Vertex AI
- Ningún componente tiene acceso completo

---

## 📚 Documentación

### Guías Principales

| Archivo | Descripción | Cuándo usar |
|---------|-------------|-------------|
| **[README.md](./README.md)** | Este archivo - Overview completo | Para entender el sistema |
| **[INICIO_RAPIDO.md](./INICIO_RAPIDO.md)** | Guía de 3 pasos | Para deployment rápido |
| **[INSTRUCCIONES_N8N_PARA_LLM.md](./INSTRUCCIONES_N8N_PARA_LLM.md)** | Setup n8n paso a paso | Para configurar n8n con IA |
| **[N8N_QUERIES_FINALES.md](./N8N_QUERIES_FINALES.md)** | Queries SQL exactas | Referencia de queries |

### Documentación de Referencia

En `docs/reference/`:
- **ARQUITECTURA_COMPLETA.md** - Diagrama técnico detallado
- **COMANDOS_DEPLOYMENT.md** - Comandos útiles de terminal
- **GUIA_DEPLOYMENT_FINAL.md** - Guía completa de deployment
- **INDEX.md** - Índice de toda la documentación

### Documentación Legacy

En `docs/archive/`:
- Propuestas originales
- APIs deprecadas
- Documentación antigua

---

## 🛠️ Troubleshooting

### Cloud Function no responde

```bash
# Ver logs
gcloud functions logs read calculate-scores --region=us-central1 --limit=20

# Verificar estado
gcloud functions describe calculate-scores --region=us-central1 --gen2
```

### n8n da error

- Verifica nombres de tablas en `N8N_QUERIES_FINALES.md`
- Verifica sintaxis de expresiones `{{ }}`
- Usa comillas simples: `$('Nombre')` NO dobles

### HCPN no encontrado

```bash
# Verificar en S3
aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ | grep hcpn_1116614340
```

Si no existe, Cloud Function usa valores por defecto.

---

## 🔄 Mantenimiento

### Re-entrenamiento del Modelo

**Frecuencia:** Cada 6 meses

**Proceso:**
1. Exportar datos de MySQL (últimos 12 meses)
2. Preparar features
3. Entrenar nuevo modelo XGBoost
4. Validar performance (AUC, precision, recall)
5. Deploy a Vertex AI
6. Actualizar endpoint ID en Cloud Function

### Actualización de Cloud Function

```bash
cd cloud_function_calculate_scores
# Modificar main.py según necesidad
./deploy_auto_fixed.sh
```

---

## 💰 Costos

| Servicio | Costo Mensual |
|----------|---------------|
| Cloud Function | $10-20/mes |
| Vertex AI Endpoint | $50-80/mes |
| Cloud Run (legacy API) | $20-30/mes |
| Cloud Build | $5-10/mes |
| **Total** | **~$85-140/mes** |

---

## 📊 Changelog

### v3.0 (Enero 26, 2026) - Sistema en Tiempo Real

✅ Cloud Function con integración S3
✅ Workflow n8n completo (7 nodos)
✅ Actualización automática de WordPress
✅ Sistema completamente automático
✅ Deployment automatizado con credenciales de .env
✅ Documentación completa con instrucciones para IA

### v2.2 (Enero 2026) - Demografía sin Data Leakage

✅ 22 features (15 originales + 7 demográficas)
✅ Sin data leakage (days_past_due removido)
✅ Python 3.11 + XGBoost 2.0.3
✅ AUC: 0.760
✅ Desplegado en Vertex AI

### v1.0 (Diciembre 2025) - Sistema Base

✅ Score híbrido PLATAM + Experian
✅ Modelo ML con 17 features
✅ API en Cloud Run
❌ Deprecado

---

## 📞 Información Técnica

**Proyecto GCP:** platam-analytics
**Región:** us-central1
**Cloud Function:** calculate-scores
**Cloud Function URL:** https://calculate-scores-k6yfpoyfea-uc.a.run.app
**Vertex AI Endpoint:** 7891061911641391104
**S3 Bucket:** fft-analytics-data-lake
**S3 Prefix:** ppay/prod/

---

## 🎉 Status

✅ **Sistema en Producción**

- Cloud Function deployada y probada
- Vertex AI endpoint activo
- n8n workflow configurado
- Sistema completamente automático
- Tiempo de respuesta: ~3 segundos

**Última actualización:** 2026-01-26

---

**¿Necesitas ayuda?** Lee [`INICIO_RAPIDO.md`](./INICIO_RAPIDO.md) para empezar.

🤖 **Generated with [Claude Code](https://claude.com/claude-code)**

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
