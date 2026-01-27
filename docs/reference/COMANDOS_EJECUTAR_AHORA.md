# ⚡ COMANDOS A EJECUTAR AHORA - En Orden

**Copia y pega estos comandos EN ORDEN en tu terminal**

---

## 🎯 ORDEN CORRECTO:

```
1. Push a GitHub (guardar todo)
2. Deploy Cloud Function (obtener URL)
3. Configurar n8n (con la URL del paso 2)
```

---

## 📦 PASO 1: Push a GitHub (2 minutos)

```bash
# 1. Ir al directorio del proyecto
cd "/Users/jpchacon/Scoring Interno"

# 2. Verificar que config/.env NO se subirá
git check-ignore config/.env

# Debe mostrar: config/.env ← Esto es BUENO

# 3. Agregar archivos nuevos
git add MAPA_COMPLETO.md PUSH_GITHUB.md COMANDOS_EJECUTAR_AHORA.md

# 4. Crear commit
git commit -m "docs: Add complete project documentation and GitHub push guide

- MAPA_COMPLETO.md: Visual map of entire project
- PUSH_GITHUB.md: Step-by-step GitHub push guide
- COMANDOS_EJECUTAR_AHORA.md: Exact commands to execute
- INSTRUCCIONES_N8N_PARA_LLM.md: Detailed n8n setup for AI assistants
- INICIO_RAPIDO.md: Quick start in 3 steps
- deploy_auto.sh: Automatic deployment with credentials from .env

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 5. Push a GitHub
git push origin main
```

**Resultado esperado:**
```
✅ Enumerating objects...
✅ Counting objects...
✅ Writing objects...
✅ Total X (delta Y), reused 0 (delta 0)
✅ To github.com:tu_usuario/tu_repo.git
```

---

## ☁️ PASO 2: Deploy Cloud Function (5 minutos)

```bash
# 1. Ir al directorio de Cloud Function
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"

# 2. Verificar que deploy_auto.sh existe
ls -lh deploy_auto.sh

# Debe mostrar: -rwxr-xr-x ... deploy_auto.sh

# 3. Ejecutar deployment
./deploy_auto.sh
```

**Lo que verás:**

```
========================================================================
  PLATAM - Deployment AUTOMÁTICO Cloud Function: Calculate Scores
========================================================================

✅ Cargando credenciales desde ../config/.env

📋 Credenciales cargadas:
  • AWS Access Key: AKIASGIOBO...
  • S3 Bucket: fft-analytics-data-lake
  • S3 Prefix: ppay/prod/

📋 Resumen del Deployment:
  • Proyecto:     platam-analytics
  • Región:       us-central1
  • Función:      calculate-scores
  • Runtime:      python311
  • S3 Bucket:    fft-analytics-data-lake
  • S3 Prefix:    ppay/prod/

¿Continuar con el deployment? (y/n):
```

**Escribe:** `y` y presiona Enter

**Espera ~3-5 minutos...**

**Al finalizar verás:**

```
========================================================================
✅ DEPLOYMENT COMPLETADO
========================================================================

📍 URL de la Cloud Function:
   https://calculate-scores-abc123xyz-uc.a.run.app

🔐 Credenciales AWS configuradas desde config/.env

📝 IMPORTANTE: Copia esta URL y configúrala en n8n
```

**⚠️ IMPORTANTE:** COPIA la URL que te da (la necesitas para el siguiente paso)

---

## 🧪 PASO 2.5: Test Cloud Function (1 minuto)

Antes de configurar n8n, prueba que la Cloud Function funciona:

```bash
# REEMPLAZA TU_URL_AQUI con la URL que copiaste
curl -X POST https://TU_URL_AQUI \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI"},
    "payments": [{"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}],
    "payment_plans": []
  }'
```

**Resultado esperado:**

```json
{
  "status": "success",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  "ml_probability_default": 0.12,
  "ml_risk_level": "Bajo",
  ...
}
```

**Si ves esto, ✅ la Cloud Function funciona perfectamente!**

---

## 🤖 PASO 3: Configurar n8n con IA (15 minutos)

### 3.1 Abrir el archivo de instrucciones

```bash
# Abrir el archivo en tu editor
open "/Users/jpchacon/Scoring Interno/INSTRUCCIONES_N8N_PARA_LLM.md"

# O con VSCode:
code "/Users/jpchacon/Scoring Interno/INSTRUCCIONES_N8N_PARA_LLM.md"

# O con cualquier editor de texto
```

### 3.2 Copiar TODO el contenido

1. Seleccionar TODO (Cmd+A en Mac)
2. Copiar (Cmd+C)

### 3.3 Abrir ChatGPT, Claude o Gemini

Abre uno de estos:
- ChatGPT: https://chat.openai.com
- Claude: https://claude.ai
- Gemini: https://gemini.google.com

### 3.4 Pegar las instrucciones

Pega TODO el contenido del archivo.

### 3.5 Agregar tu URL

Después de pegar, escribe:

```
"Ayúdame a configurar este workflow de n8n paso a paso.

La URL de mi Cloud Function es:
https://calculate-scores-abc123xyz-uc.a.run.app

Por favor guíame nodo por nodo."
```

**REEMPLAZA** `https://calculate-scores-abc123xyz-uc.a.run.app` con tu URL real.

### 3.6 Seguir las instrucciones del asistente

El asistente te guiará nodo por nodo:

```
Nodo 1: Webhook
Nodo 2: Select Cliente
Nodo 3: Select Pagos
Nodo 4: Select Préstamos
Nodo 5: Preparar Datos (Function)
Nodo 6: HTTP Request → Cloud Function
Nodo 7: HTTP Request → WordPress
```

El asistente validará cada paso antes de continuar.

---

## ✅ PASO 4: Test Final (5 minutos)

### 4.1 Test en n8n

1. En n8n: Click "Execute Workflow"
2. Verifica que los 7 nodos ejecutan correctamente (todos en verde)

### 4.2 Test con cURL

```bash
# REEMPLAZA con tu URL webhook de n8n
curl -X POST https://TU_N8N.com/webhook/scoring-trigger \
  -H "Content-Type: application/json" \
  -d '{"client_id": "1702", "trigger": "test"}'
```

### 4.3 Verificar en WordPress

1. Ve a WordPress admin
2. Busca cliente ID 1702 o cédula 1116614340
3. Verifica que estos campos tienen valores NUEVOS:
   - cl_platam_score
   - cl_hybrid_score
   - cl_ml_risk_level

**Si todo esto funciona, ✅ ¡SISTEMA COMPLETADO!**

---

## 🎉 DESPUÉS DE ESTO

Tu sistema estará funcionando. Cuando tu equipo de tech envíe:

```json
{"client_id": "1702", "trigger": "late_7"}
```

El sistema:
1. Recibirá el trigger en n8n
2. Consultará MySQL (cliente, pagos, préstamos)
3. Enviará datos a Cloud Function
4. Cloud Function calculará scores + ML
5. Actualizará WordPress

**Todo en ~3 segundos.**

---

## 📊 RESUMEN DE TIEMPOS

| Paso | Tiempo |
|------|--------|
| Push a GitHub | 2 min |
| Deploy Cloud Function | 5 min |
| Test Cloud Function | 1 min |
| Configurar n8n (con IA) | 15 min |
| Test final | 5 min |
| **TOTAL** | **28 min** |

---

## 🆘 SI ALGO FALLA

### Error en Push a GitHub

```bash
# Ver el error completo
git status

# Si pide pull primero:
git pull origin main --rebase
git push origin main
```

### Error en Deployment

```bash
# Ver logs
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --limit=20
```

### Cloud Function devuelve error

Ver archivo: `COMANDOS_DEPLOYMENT.md` → Sección Troubleshooting

### n8n da error

El asistente IA te ayudará a debuggear. Solo muéstrale el error.

---

## 📋 CHECKLIST COMPLETO

Marca cada paso al completarlo:

- [ ] Push a GitHub completado
- [ ] Cloud Function deployada
- [ ] URL de Cloud Function copiada
- [ ] Test Cloud Function con cURL exitoso
- [ ] Archivo INSTRUCCIONES_N8N_PARA_LLM.md copiado
- [ ] Pegado en ChatGPT/Claude/Gemini
- [ ] URL agregada al prompt
- [ ] 7 nodos configurados en n8n
- [ ] Variable CLOUD_FUNCTION_URL configurada en n8n
- [ ] Test workflow en n8n exitoso
- [ ] Test con cURL al webhook exitoso
- [ ] WordPress muestra scores actualizados
- [ ] Equipo tech puede enviar triggers

---

## 🎯 EMPEZAR AHORA

**Copia y pega este comando en tu terminal:**

```bash
cd "/Users/jpchacon/Scoring Interno" && git check-ignore config/.env && echo "✅ Credenciales protegidas - Listo para push"
```

Si ves: `✅ Credenciales protegidas - Listo para push`

**Entonces ejecuta:**

```bash
git add MAPA_COMPLETO.md PUSH_GITHUB.md COMANDOS_EJECUTAR_AHORA.md && \
git commit -m "docs: Add complete project documentation" && \
git push origin main
```

**¡Éxito!** 🚀

---

**Creado:** 2026-01-26
**Versión:** 1.0 Final
