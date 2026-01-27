# ⚡ INICIO RÁPIDO - Deployment en 3 Pasos

**Todo está listo. Solo necesitas ejecutar 3 comandos.**

---

## ✅ PASO 1: Deploy Cloud Function (5 minutos)

### Opción A: Deployment AUTOMÁTICO (RECOMENDADO)

Usa tus credenciales que ya están en `config/.env`:

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
chmod +x deploy_auto.sh
./deploy_auto.sh
```

Cuando te pregunte "¿Continuar con el deployment? (y/n):", escribe `y` y presiona Enter.

**Listo!** Te dará la URL de la Cloud Function.

---

### Opción B: Deployment Manual

Si prefieres ingresar las credenciales manualmente:

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
chmod +x deploy.sh
./deploy.sh
```

Te pedirá:
- AWS Access Key ID: (las que están en config/.env)
- AWS Secret Access Key: (las que están en config/.env)
- S3 Bucket: `fft-analytics-data-lake`
- S3 Prefix: `ppay/prod/`

---

## ✅ PASO 2: Copiar URL

Al finalizar el deployment verás:

```
📍 URL de la Cloud Function:
   https://calculate-scores-abc123xyz-uc.a.run.app
```

**COPIA ESTA URL** (la necesitarás para n8n).

---

## ✅ PASO 3: Configurar n8n

### Opción A: Con ayuda de IA (RECOMENDADO)

1. Abre ChatGPT, Claude o Gemini

2. Copia y pega COMPLETO el archivo:
   ```
   INSTRUCCIONES_N8N_PARA_LLM.md
   ```

3. Dile al asistente:
   ```
   "Ayúdame a configurar este workflow de n8n paso a paso.
   La URL de mi Cloud Function es: [TU_URL_AQUI]"
   ```

4. Sigue las instrucciones del asistente nodo por nodo.

---

### Opción B: Manual

Abre el archivo:
```
N8N_QUERIES_FINALES.md
```

Y configura los 7 nodos copiando las queries exactas.

---

## 🧪 PASO 4: Probar

### Test 1: Cloud Function

```bash
curl -X POST https://TU_URL_CLOUD_FUNCTION_AQUI \
  -H "Content-Type: application/json" \
  -d '{
    "cedula": "1116614340",
    "client_data": {"months_as_client": 3, "ciudad": "MANI"},
    "payments": [{"payment_date": "2023-11-09", "days_past_due": 7, "payment_amount": 2000000}],
    "payment_plans": []
  }'
```

Debes ver:
```json
{
  "status": "success",
  "platam_score": 730.5,
  "hybrid_score": 745.2,
  ...
}
```

### Test 2: n8n

En n8n:
1. Click "Execute Workflow"
2. Verifica que los 7 nodos ejecuten correctamente

### Test 3: WordPress

1. Ve a WordPress admin
2. Busca cliente ID 1702
3. Verifica que los scores se actualizaron

---

## ✅ ¡LISTO!

Tu sistema está funcionando. Cuando tu equipo de tech envíe triggers como:

```json
{"client_id": "1702", "trigger": "late_7"}
```

El sistema calculará y actualizará scores automáticamente.

---

## 📁 Archivos Importantes

```
📂 Scoring Interno/
│
├── 🚀 INICIO_RAPIDO.md ................... ⭐ ESTE ARCHIVO
│
├── 🤖 INSTRUCCIONES_N8N_PARA_LLM.md ...... ⭐ Para configurar n8n con IA
│
├── 📖 RESUMEN_DEPLOYMENT.md .............. Overview completo
│
├── 📋 N8N_QUERIES_FINALES.md ............. Queries SQL
│
└── 📂 cloud_function_calculate_scores/
    ├── deploy_auto.sh .................... ⭐ Deployment automático
    └── deploy.sh ......................... Deployment manual
```

---

## 🆘 Si algo falla

### Cloud Function no responde

```bash
gcloud functions logs read calculate-scores \
  --region=us-central1 \
  --limit=20
```

### Ver comandos completos

Abre: `COMANDOS_DEPLOYMENT.md`

### Troubleshooting completo

Abre: `GUIA_DEPLOYMENT_FINAL.md` → Sección "Troubleshooting"

---

## ⏱️ Tiempo Total

- Deployment Cloud Function: **5 minutos**
- Configurar n8n (con IA): **15 minutos**
- Testing: **5 minutos**

**Total: 25 minutos**

---

## 🎯 Tu Próxima Acción

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
./deploy_auto.sh
```

**¡Éxito!** 🚀

---

**Creado:** 2026-01-26
