# Prompt para Gemini - Configuración de Vertex AI

Hola Gemini,

Necesito tu ayuda para configurar **Google Cloud Vertex AI** para desplegar un modelo de Machine Learning ya entrenado. Aquí está el contexto:

## 📋 Contexto del Proyecto

**Objetivo:** Desplegar un modelo XGBoost de predicción de defaults crediticios en Vertex AI.

**Lo que YA tenemos:**
- Modelo entrenado localmente: `xgboost_model_final.pkl` (XGBoost)
- Scaler: `scaler_final.pkl` (StandardScaler de scikit-learn)
- Metadata: `model_metadata.json`
- AUC-ROC: 0.743
- Threshold optimizado: 0.60
- 17 features de entrada
- Script de predicción funcionando localmente: `predict.py`

**Lo que NECESITAMOS hacer:**
1. Configurar proyecto GCP con Vertex AI habilitado
2. Crear bucket de Cloud Storage
3. Subir el modelo a Vertex AI
4. Crear un endpoint para predicciones en tiempo real
5. Obtener credenciales para acceder desde Python

---

## 🎯 Lo Que Necesito de Ti

### PASO 1: Configuración de Proyecto GCP

Por favor, guíame paso a paso para:

1. **Crear o usar un proyecto GCP existente**
   - ¿Cómo verifico si ya tengo un proyecto?
   - Si no tengo, ¿cómo creo uno nuevo?
   - ¿Cuál debería ser el PROJECT_ID? (sugiere uno basado en "platam-scoring-ml")

2. **Habilitar las APIs necesarias**
   - Vertex AI API
   - Cloud Storage API
   - Notebooks API (si es necesaria)

   Dame los comandos exactos de `gcloud` o los pasos en la consola web.

3. **Configurar facturación**
   - ¿Cómo asocio una cuenta de facturación?
   - ¿Hay créditos gratis disponibles? ($300 trial?)
   - ¿Cuál es el costo estimado mensual para este proyecto?

### PASO 2: Cloud Storage

Por favor, ayúdame a:

1. **Crear un bucket de Cloud Storage**
   - Nombre sugerido: `platam-ml-scoring`
   - Región recomendada para Latinoamérica: ¿us-central1 o southamerica-east1?
   - Comandos exactos de `gcloud` o `gsutil`

2. **Subir archivos del modelo**
   - ¿Cómo subo `xgboost_model_final.pkl`?
   - ¿Cómo subo `scaler_final.pkl`?
   - ¿Cómo subo `model_metadata.json`?

   Dame los comandos exactos.

### PASO 3: Credenciales y Autenticación

Por favor, explícame:

1. **Service Account**
   - ¿Cómo creo un service account para Vertex AI?
   - ¿Qué roles/permisos necesita? (Vertex AI User, Storage Object Admin, etc.)
   - ¿Cómo descargo el archivo JSON de credenciales?

2. **Configuración local**
   - ¿Cómo configuro `gcloud` en mi máquina local?
   - ¿Cómo autentico usando el service account?
   - Variables de entorno necesarias (GOOGLE_APPLICATION_CREDENTIALS)

### PASO 4: Desplegar Modelo en Vertex AI

Necesito código Python o comandos para:

1. **Registrar el modelo en Vertex AI Model Registry**
   ```python
   # ¿Cómo subo mi modelo XGBoost a Vertex AI?
   # Necesito código completo paso a paso
   ```

2. **Crear un endpoint**
   ```python
   # ¿Cómo creo un endpoint de predicción?
   # Configuración de réplicas, máquinas, etc.
   ```

3. **Hacer una predicción de prueba**
   ```python
   # ¿Cómo hago una predicción usando el endpoint?
   # Ejemplo con mis 17 features
   ```

### PASO 5: Estimación de Costos

Por favor, ayúdame a entender:

1. **Costos de Vertex AI**
   - ¿Cuánto cuesta el endpoint (por hora/mes)?
   - ¿Hay costo por predicción?
   - ¿Cuánto cuesta Cloud Storage para ~10MB de archivos?

2. **Optimización de costos**
   - ¿Debería usar batch predictions en vez de endpoint?
   - ¿Puedo pausar el endpoint cuando no lo use?
   - ¿Hay tier gratuito?

---

## 📝 Información Técnica del Modelo

**Modelo:** XGBoost (xgboost==2.0.3 aprox.)
**Python:** 3.11
**Librerías:**
- xgboost
- scikit-learn
- pandas
- numpy

**Features de entrada (17):**
- platam_score
- experian_score_normalized
- score_payment_performance
- score_payment_plan
- score_deterioration
- payment_count
- months_as_client
- days_past_due_mean
- days_past_due_max
- pct_early
- pct_late
- peso_platam_usado
- peso_hcpn_usado
- tiene_plan_activo
- tiene_plan_default
- tiene_plan_pendiente
- num_planes

**Output:** Probabilidad de default (0.0 - 1.0)
**Threshold:** 0.60 (si prob >= 0.60 → Default, sino → No-Default)

---

## 🎯 Formato de Respuesta Esperado

Por favor, organiza tu respuesta en secciones claras:

### SECCIÓN 1: Setup Inicial (Proyecto + APIs)
- Comandos exactos para ejecutar
- Screenshots o pasos en consola web si aplica

### SECCIÓN 2: Cloud Storage
- Comandos para crear bucket
- Comandos para subir archivos

### SECCIÓN 3: Credenciales
- Pasos para crear service account
- Cómo descargar JSON
- Cómo configurar localmente

### SECCIÓN 4: Código Python para Deployment
- Script completo para subir modelo
- Script completo para crear endpoint
- Script completo para hacer predicción

### SECCIÓN 5: Costos y Consideraciones
- Estimación de costos mensual
- Recomendaciones de optimización

---

## 💡 Notas Adicionales

- **Región preferida:** Cerca de Colombia/Latinoamérica
- **Presupuesto:** Queremos minimizar costos (~$50-100/mes máximo)
- **Uso esperado:** ~100-500 predicciones por día
- **Prioridad:** Simplicidad de deployment sobre features avanzadas

---

## ❓ Pregunta Extra

¿Existe alguna alternativa más económica o simple que Vertex AI para este caso de uso? (Cloud Run con modelo en Docker, Cloud Functions, etc.)

---

Gracias por tu ayuda, Gemini! Por favor sé lo más específico posible con comandos y código.
