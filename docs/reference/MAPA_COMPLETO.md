# 🗺️ MAPA COMPLETO DEL PROYECTO

**Versión visual para entender TODO de un vistazo**

---

## 🎯 TU MISIÓN

Configurar sistema de scoring en tiempo real que recibe triggers y actualiza WordPress automáticamente.

---

## 📊 ESTADO ACTUAL

```
✅ Código completo y probado
✅ Credenciales AWS en config/.env
✅ Queries SQL listas
✅ Documentación completa
✅ Scripts de deployment listos

❌ Cloud Function sin desplegar (TÚ DEBES HACERLO)
❌ n8n sin configurar (TÚ DEBES HACERLO)
```

---

## 🚀 QUÉ HACER AHORA (EN ORDEN)

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  1️⃣  LEE ESTE ARCHIVO                                          │
│     📄 INICIO_RAPIDO.md                                        │
│     ⏱️  3 minutos                                              │
│                                                                │
│  2️⃣  EJECUTA DEPLOYMENT                                        │
│     💻 cd cloud_function_calculate_scores                      │
│     💻 ./deploy_auto.sh                                        │
│     ⏱️  5 minutos                                              │
│                                                                │
│  3️⃣  COPIA LA URL                                              │
│     📋 https://calculate-scores-xxx.run.app                    │
│     ⏱️  10 segundos                                            │
│                                                                │
│  4️⃣  CONFIGURA N8N                                             │
│     🤖 Usa: INSTRUCCIONES_N8N_PARA_LLM.md                      │
│     🤖 Pégalo en ChatGPT/Claude/Gemini                         │
│     ⏱️  15 minutos                                             │
│                                                                │
│  5️⃣  PRUEBA TODO                                               │
│     🧪 Test Cloud Function (cURL)                              │
│     🧪 Test n8n workflow                                       │
│     🧪 Verificar WordPress                                     │
│     ⏱️  5 minutos                                              │
│                                                                │
│  ✅ LISTO! Sistema en producción                               │
│                                                                │
└────────────────────────────────────────────────────────────────┘

⏱️  TIEMPO TOTAL: 25-30 MINUTOS
```

---

## 📁 ARCHIVOS DEL PROYECTO

### 🟢 ARCHIVOS QUE VAS A USAR AHORA

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ⭐ INICIO_RAPIDO.md                                            │
│     📖 Lee PRIMERO. Te dice exactamente qué hacer.             │
│     ⏱️  Lectura: 3 minutos                                      │
│                                                                 │
│  ⭐ cloud_function_calculate_scores/deploy_auto.sh             │
│     🚀 Ejecuta ESTO para hacer deployment.                     │
│     💻 ./deploy_auto.sh                                         │
│     ⏱️  Ejecución: 5 minutos                                    │
│                                                                 │
│  ⭐ INSTRUCCIONES_N8N_PARA_LLM.md                               │
│     🤖 Copia COMPLETO y pega en ChatGPT/Claude/Gemini          │
│     📋 El asistente te guiará paso a paso                      │
│     ⏱️  Configuración: 15 minutos                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 🟡 ARCHIVOS DE REFERENCIA (Si necesitas ayuda)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  📖 N8N_QUERIES_FINALES.md                                      │
│     Queries SQL completas (si configuras n8n manualmente)     │
│                                                                 │
│  📖 COMANDOS_DEPLOYMENT.md                                      │
│     Comandos de terminal para troubleshooting                  │
│                                                                 │
│  📖 GUIA_DEPLOYMENT_FINAL.md                                    │
│     Guía completa paso a paso (detallada)                      │
│                                                                 │
│  📖 ARQUITECTURA_COMPLETA.md                                    │
│     Diagrama técnico del sistema completo                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 🔵 ARCHIVOS INTERNOS (No necesitas tocar)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  💻 cloud_function_calculate_scores/main.py                     │
│     Código de Cloud Function (591 líneas Python)               │
│                                                                 │
│  💻 cloud_function_calculate_scores/requirements.txt            │
│     Dependencies (boto3, pandas, etc.)                         │
│                                                                 │
│  🔐 config/.env                                                 │
│     Credenciales AWS S3 (ya configuradas)                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎬 FLUJO COMPLETO DEL SISTEMA

```
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  👨‍💻 EQUIPO DE TECH                                               │
│     Envía trigger:                                               │
│     {"client_id": "1702", "trigger": "late_7"}                   │
│                                                                   │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  🔄 N8N WORKFLOW (7 nodos)                                        │
│                                                                   │
│  1. Webhook recibe trigger                                       │
│  2. Query MySQL → Cliente                                        │
│  3. Query MySQL → Pagos                                          │
│  4. Query MySQL → Préstamos                                      │
│  5. Preparar JSON                                                │
│  6. HTTP Request → Cloud Function                                │
│  7. HTTP Request → WordPress                                     │
│                                                                   │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  ☁️  GOOGLE CLOUD FUNCTION                                        │
│                                                                   │
│  • Descarga HCPN de S3                                           │
│  • Calcula PLATAM Score (Payment + Plan + Deterioration)        │
│  • Calcula Hybrid Score (PLATAM + Experian)                     │
│  • Llama Vertex AI (ML prediction)                              │
│  • Retorna scores                                                │
│                                                                   │
└─────────────────────────┬─────────────────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│  📝 WORDPRESS                                                     │
│                                                                   │
│  Actualiza 8 campos:                                             │
│  • cl_platam_score                                               │
│  • cl_hybrid_score                                               │
│  • cl_ml_probability_default                                     │
│  • cl_ml_probability_no_default                                  │
│  • cl_ml_risk_level                                              │
│  • cl_hybrid_weight_platam                                       │
│  • cl_hybrid_weight_experian                                     │
│  • cl_ml_modified                                                │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘

⏱️  TIEMPO TOTAL: ~3 segundos por trigger
```

---

## 💾 TUS CREDENCIALES (Ya configuradas)

```
📁 /Users/jpchacon/Scoring Interno/config/.env

✅ AWS_ACCESS_KEY_ID = AKIASGIOBQM5BZ6PM3UQ
✅ AWS_SECRET_ACCESS_KEY = P0If1***************
✅ S3_HCPN_BUCKET = fft-analytics-data-lake
✅ S3_PREFIX = ppay/prod/

El script deploy_auto.sh lee estas credenciales automáticamente.
```

---

## 🎯 DATOS DE PRUEBA

```
Cliente de prueba:
  ID: 1702
  Cédula: 1116614340
  Nombre: ANGELA YARITZA DEVIA CIERRA
  Ciudad: MANI (C/NARE)

Trigger de prueba:
  {"client_id": "1702", "trigger": "test"}

HCPN en S3:
  s3://fft-analytics-data-lake/ppay/prod/hcpn_1116614340.json
```

---

## 📊 COMPONENTES TÉCNICOS

```
┌──────────────────────────────────────────────────────────────┐
│ GOOGLE CLOUD                                                 │
├──────────────────────────────────────────────────────────────┤
│ • Project: platam-analytics                                  │
│ • Cloud Function: calculate-scores (Python 3.11)            │
│ • Vertex AI Endpoint: 7891061911641391104                   │
│ • Región: us-central1                                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ AWS S3                                                       │
├──────────────────────────────────────────────────────────────┤
│ • Bucket: fft-analytics-data-lake                           │
│ • Prefix: ppay/prod/                                        │
│ • Archivos: hcpn_{cedula}.json                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ MYSQL / WORDPRESS                                            │
├──────────────────────────────────────────────────────────────┤
│ • wp_jet_cct_clientes (clientes)                           │
│ • wp_jet_cct_pagos (pagos)                                 │
│ • wp_jet_cct_prestamos (préstamos)                         │
│ • REST API: platampay.com/wp-json/jet-cct/clientes/{ID}   │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ N8N                                                          │
├──────────────────────────────────────────────────────────────┤
│ • Workflow: ActualizarML                                     │
│ • Nodos: 7 (Webhook + 3 MySQL + Function + 2 HTTP)         │
│ • Conexión MySQL: Ya configurada                            │
│ • WordPress Auth: Ya configurada                            │
└──────────────────────────────────────────────────────────────┘
```

---

## ✅ CHECKLIST DE DEPLOYMENT

```
Antes:
□ Tienes acceso a GCP project platam-analytics
□ Tienes gcloud CLI instalado y autenticado
□ Tienes acceso a n8n
□ Tienes credenciales MySQL y WordPress en n8n

Durante:
□ Ejecutaste deploy_auto.sh
□ Copiaste URL de Cloud Function
□ Configuraste variable CLOUD_FUNCTION_URL en n8n
□ Configuraste 7 nodos en n8n
□ Conectaste los nodos correctamente

Después:
□ Test Cloud Function con cURL funciona
□ Test n8n workflow ejecuta sin errores
□ WordPress muestra scores actualizados
□ Equipo tech puede enviar triggers
```

---

## 🆘 AYUDA RÁPIDA

```
┌─────────────────────────────────────────────────────────────┐
│ PROBLEMA                │ SOLUCIÓN                          │
├─────────────────────────┼───────────────────────────────────┤
│ No sé por dónde empezar │ Lee INICIO_RAPIDO.md              │
├─────────────────────────┼───────────────────────────────────┤
│ Error en deployment     │ Ver logs:                         │
│                         │ gcloud functions logs read        │
│                         │   calculate-scores --limit=20     │
├─────────────────────────┼───────────────────────────────────┤
│ No sé configurar n8n    │ Usa INSTRUCCIONES_N8N_PARA_LLM.md │
│                         │ con ChatGPT/Claude                │
├─────────────────────────┼───────────────────────────────────┤
│ n8n da error            │ Revisa query SQL exacta en        │
│                         │ N8N_QUERIES_FINALES.md            │
├─────────────────────────┼───────────────────────────────────┤
│ Cloud Function no       │ Verifica URL en n8n               │
│ responde                │ COMANDOS_DEPLOYMENT.md            │
└─────────────────────────┴───────────────────────────────────┘
```

---

## 🎯 SIGUIENTE ACCIÓN (AHORA)

```bash
# 1. Abre terminal

# 2. Ejecuta estos comandos:

cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"

./deploy_auto.sh

# 3. Cuando termine, copia la URL que te dé

# 4. Abre INSTRUCCIONES_N8N_PARA_LLM.md y pégalo en ChatGPT/Claude
```

---

## 📈 DESPUÉS DEL DEPLOYMENT

Tu sistema estará recibiendo triggers como:

```json
{"client_id": "1702", "trigger": "late_7"}
{"client_id": "1702", "trigger": "late_14"}
{"client_id": "1702", "trigger": "new_loan"}
{"client_id": "1702", "trigger": "payment"}
```

Y actualizará scores automáticamente en ~3 segundos.

---

## 🎉 RESUMEN

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  ✅ Todo el código está listo                                  │
│  ✅ Tus credenciales AWS están configuradas                    │
│  ✅ Tienes 3 archivos principales:                             │
│     1. INICIO_RAPIDO.md (lee esto)                            │
│     2. deploy_auto.sh (ejecuta esto)                          │
│     3. INSTRUCCIONES_N8N_PARA_LLM.md (pega en ChatGPT)        │
│                                                                │
│  ⏱️  En 25 minutos tendrás todo funcionando                    │
│                                                                │
│  🚀 Tu próxima acción:                                         │
│     ./deploy_auto.sh                                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

**Creado:** 2026-01-26
**Versión:** 1.0 Final
**Status:** ✅ READY TO GO!
