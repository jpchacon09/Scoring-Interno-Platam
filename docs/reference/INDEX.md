# 📚 ÍNDICE - Sistema de Scoring en Tiempo Real

**Proyecto:** PLATAM Analytics - Actualización Automática de Scores
**Fecha:** 2026-01-26
**Status:** ✅ **LISTO PARA DEPLOYMENT**

---

## 🎯 INICIO RÁPIDO

**Si quieres empezar AHORA mismo:**

1. Lee: `RESUMEN_DEPLOYMENT.md` (5 min)
2. Ejecuta: `cd cloud_function_calculate_scores && ./deploy.sh` (5 min)
3. Configura n8n usando: `N8N_QUERIES_FINALES.md` (20 min)
4. Test: Cliente ID 1702

**Tiempo total:** 30 minutos

---

## 📁 ESTRUCTURA DE ARCHIVOS

### 🚀 Para Deployment (CRÍTICO)

| Archivo | Descripción | Cuándo usar |
|---------|-------------|-------------|
| **RESUMEN_DEPLOYMENT.md** | Resumen ejecutivo con pasos principales | **LEER PRIMERO** |
| **GUIA_DEPLOYMENT_FINAL.md** | Guía completa paso a paso (30-45 min) | Durante deployment |
| **N8N_QUERIES_FINALES.md** | Queries SQL exactas para copiar/pegar en n8n | Al configurar n8n |
| **COMANDOS_DEPLOYMENT.md** | Comandos de terminal para deployment y troubleshooting | Referencia rápida |

### 🏗️ Código y Configuración

| Directorio/Archivo | Descripción |
|-------------------|-------------|
| **cloud_function_calculate_scores/** | Código completo de Cloud Function |
| ├── `main.py` | Cloud Function principal (S3 + Vertex AI) |
| ├── `requirements.txt` | Dependencias Python (boto3, pandas, etc.) |
| └── `deploy.sh` | Script de deployment con AWS credentials |

### 📖 Documentación Técnica

| Archivo | Descripción | Cuándo usar |
|---------|-------------|-------------|
| **ARQUITECTURA_COMPLETA.md** | Diagrama y flujo completo del sistema | Para entender el sistema |
| **API_CLOUD_RUN.md** | Documentación de API Cloud Run (legacy) | Referencia histórica |
| **README.md** | Documentación del proyecto scoring v2.2 | Contexto general |
| **PROPUESTA_ACTUALIZACION_AUTOMATICA_SCORES.md** | Propuesta original (3 opciones) | Contexto del proyecto |

### 📊 Datos de Ejemplo

| Archivo | Descripción |
|---------|-------------|
| **ejemplo_clientes_base.json** | Cliente ID 1702 (para testing) |
| **ejemplo_pagos_base.json** | Pagos del cliente 1702 |
| **ejemplo_prestamos_base.json** | Préstamos del cliente 1702 |

### 📝 Este Archivo

| Archivo | Descripción |
|---------|-------------|
| **INDEX.md** | Este índice (navegación) |

---

## 🗺️ RUTAS DE APRENDIZAJE

### Ruta 1: "Quiero deployar YA" (30 min)

```
1. RESUMEN_DEPLOYMENT.md
   ↓
2. Ejecutar deploy.sh
   ↓
3. N8N_QUERIES_FINALES.md
   ↓
4. Test con cliente 1702
   ✅ LISTO
```

### Ruta 2: "Quiero entender primero" (1 hora)

```
1. ARQUITECTURA_COMPLETA.md (entender sistema)
   ↓
2. GUIA_DEPLOYMENT_FINAL.md (proceso completo)
   ↓
3. Ejecutar deploy.sh
   ↓
4. N8N_QUERIES_FINALES.md
   ↓
5. Test y validación
   ✅ LISTO
```

### Ruta 3: "Soy desarrollador, necesito detalles" (2 horas)

```
1. README.md (contexto proyecto)
   ↓
2. PROPUESTA_ACTUALIZACION_AUTOMATICA_SCORES.md (propuesta original)
   ↓
3. ARQUITECTURA_COMPLETA.md (sistema completo)
   ↓
4. cloud_function_calculate_scores/main.py (código)
   ↓
5. GUIA_DEPLOYMENT_FINAL.md (deployment)
   ↓
6. Ejecutar deploy.sh
   ↓
7. COMANDOS_DEPLOYMENT.md (troubleshooting)
   ✅ EXPERTO
```

---

## 📖 GUÍA DE LECTURA POR ARCHIVO

### RESUMEN_DEPLOYMENT.md
**Tipo:** Resumen ejecutivo
**Tiempo de lectura:** 5 minutos
**Contenido:**
- ✅ Checklist de archivos
- ✅ Pasos principales (1, 2, 3, 4)
- ✅ Datos técnicos clave
- ✅ Caso de prueba (cliente 1702)
- ✅ Troubleshooting rápido

**Leer si:** Quieres overview rápido antes de empezar

---

### GUIA_DEPLOYMENT_FINAL.md
**Tipo:** Guía completa paso a paso
**Tiempo de lectura:** 15 minutos
**Contenido:**
- ✅ Arquitectura del sistema
- ✅ Checklist pre-deployment
- ✅ PASO 1: Deploy Cloud Function (detallado)
- ✅ PASO 2: Testing Cloud Function
- ✅ PASO 3: Configuración n8n (7 nodos)
- ✅ PASO 4: Test flujo completo
- ✅ Logs y monitoreo
- ✅ Troubleshooting detallado
- ✅ Próximos pasos

**Leer si:** Vas a hacer el deployment completo

---

### N8N_QUERIES_FINALES.md
**Tipo:** Queries SQL y configuración n8n
**Tiempo de lectura:** 10 minutos
**Contenido:**
- ✅ Query 1: Select Cliente (wp_jet_cct_clientes)
- ✅ Query 2: Select Pagos (wp_jet_cct_pagos)
- ✅ Query 3: Select Préstamos (wp_jet_cct_prestamos)
- ✅ Function Node: Preparar datos
- ✅ HTTP Request: Cloud Function
- ✅ HTTP Request: WordPress REST API
- ✅ Tests SQL directos

**Usar cuando:** Estés configurando n8n (copiar/pegar queries)

---

### ARQUITECTURA_COMPLETA.md
**Tipo:** Documentación técnica
**Tiempo de lectura:** 20 minutos
**Contenido:**
- ✅ Diagrama ASCII completo del sistema
- ✅ Flujo de datos detallado (cada paso)
- ✅ Componentes (GCP, AWS S3, MySQL, n8n)
- ✅ Performance y tiempos
- ✅ Seguridad y separación de responsabilidades
- ✅ Escalabilidad y límites
- ✅ Casos de uso

**Leer si:** Necesitas entender cómo funciona todo el sistema

---

### COMANDOS_DEPLOYMENT.md
**Tipo:** Referencia rápida de comandos
**Tiempo de lectura:** Consulta según necesidad
**Contenido:**
- ✅ Comandos de deployment
- ✅ Tests (cURL, Python)
- ✅ Monitoreo (logs, métricas)
- ✅ Información y estado (Cloud Function, Vertex AI, S3)
- ✅ Troubleshooting
- ✅ Re-deployment
- ✅ Comandos de emergencia

**Usar cuando:** Necesites ejecutar comandos o troubleshooting

---

### cloud_function_calculate_scores/main.py
**Tipo:** Código Python
**Líneas:** 591
**Contenido:**
- ✅ Funciones S3 (download_hcpn_from_s3, extract_hcpn_demographics)
- ✅ Funciones scoring (payment_performance, payment_plan, deterioration)
- ✅ Cálculo híbrido (PLATAM + Experian)
- ✅ Predicción ML (Vertex AI, 22 features)
- ✅ Función principal (calculate_scores)

**Leer si:** Eres desarrollador o necesitas modificar lógica

---

## 🎯 CASOS DE USO

### Caso 1: Deployment inicial

```
Documentos necesarios:
1. RESUMEN_DEPLOYMENT.md ← Leer
2. N8N_QUERIES_FINALES.md ← Tener abierto
3. COMANDOS_DEPLOYMENT.md ← Referencia

Acción:
cd cloud_function_calculate_scores
./deploy.sh
```

### Caso 2: Troubleshooting - Cloud Function no responde

```
Documentos necesarios:
1. COMANDOS_DEPLOYMENT.md → Ver logs
2. GUIA_DEPLOYMENT_FINAL.md → Sección troubleshooting

Comandos:
gcloud functions logs read calculate-scores --limit=50
```

### Caso 3: Modificar lógica de scoring

```
Documentos necesarios:
1. ARQUITECTURA_COMPLETA.md → Entender flujo
2. cloud_function_calculate_scores/main.py → Código

Modificar:
- Líneas 192-252: calculate_payment_performance()
- Líneas 255-288: calculate_payment_plan_score()
- Líneas 291-312: calculate_deterioration_velocity()
```

### Caso 4: Agregar nueva feature al modelo ML

```
Documentos necesarios:
1. cloud_function_calculate_scores/main.py
2. ARQUITECTURA_COMPLETA.md → Ver feature_order actual

Modificar:
- Línea 366-375: feature_order (agregar nueva feature)
- Línea 382-396: Lógica para calcular nueva feature
```

### Caso 5: Configurar nuevo ambiente (staging/prod)

```
Documentos necesarios:
1. GUIA_DEPLOYMENT_FINAL.md
2. cloud_function_calculate_scores/deploy.sh

Modificar deploy.sh:
- Línea 14: PROJECT_ID
- Línea 15: REGION
- Línea 16: FUNCTION_NAME
```

---

## 📊 MÉTRICAS DEL PROYECTO

### Código

| Métrica | Valor |
|---------|-------|
| Líneas de código Python | 591 |
| Funciones principales | 8 |
| Dependencies (requirements.txt) | 6 |
| Archivos de deployment | 3 |

### Documentación

| Métrica | Valor |
|---------|-------|
| Archivos de documentación | 8 |
| Páginas totales (estimado) | ~50 |
| Diagramas | 2 |
| Queries SQL | 3 |
| Comandos de referencia | ~50 |

### Sistema

| Métrica | Valor |
|---------|-------|
| Componentes del sistema | 6 (n8n, Cloud Function, Vertex AI, S3, MySQL, WordPress) |
| Nodos n8n | 7 |
| Features ML | 22 |
| Tiempo de respuesta | ~3 segundos |
| Triggers soportados | 12 |

---

## ✅ CHECKLIST FINAL

Antes de cerrar este proyecto, verifica:

### Deployment
- [ ] Cloud Function deployada (`./deploy.sh`)
- [ ] URL de Cloud Function guardada
- [ ] Test Cloud Function exitoso (cURL)
- [ ] Logs verificados (sin errores)

### n8n
- [ ] 7 nodos configurados
- [ ] Variable de entorno `CLOUD_FUNCTION_URL` configurada
- [ ] Test workflow en n8n exitoso
- [ ] Conexiones verificadas (MySQL, WordPress)

### Testing
- [ ] Test con cliente 1702 (cédula 1116614340)
- [ ] Verificación en WordPress (scores actualizados)
- [ ] Test con trigger real del equipo tech
- [ ] Logs muestran HCPN descargado de S3

### Documentación
- [ ] Equipo tech informado sobre triggers
- [ ] URL de Cloud Function compartida
- [ ] Documentación entregada
- [ ] Troubleshooting guide accesible

---

## 🆘 AYUDA RÁPIDA

### "¿Por dónde empiezo?"
→ Lee `RESUMEN_DEPLOYMENT.md` (5 min)

### "¿Cómo hago el deployment?"
→ Ejecuta `cd cloud_function_calculate_scores && ./deploy.sh`

### "¿Cómo configuro n8n?"
→ Abre `N8N_QUERIES_FINALES.md` y copia las queries

### "¿Hay un error, qué hago?"
→ `COMANDOS_DEPLOYMENT.md` → Sección Troubleshooting

### "¿Cómo veo los logs?"
→ `gcloud functions logs read calculate-scores --limit=50`

### "¿Cómo funciona el sistema?"
→ Lee `ARQUITECTURA_COMPLETA.md`

### "¿Dónde está el código?"
→ `cloud_function_calculate_scores/main.py`

---

## 📞 SOPORTE

Si necesitas ayuda durante el deployment:

1. **Logs de Cloud Function:**
   ```bash
   gcloud functions logs read calculate-scores --region=us-central1 --limit=100
   ```

2. **Test Cloud Function:**
   ```bash
   # Ver COMANDOS_DEPLOYMENT.md línea 22-42
   ```

3. **Verificar estado:**
   ```bash
   gcloud functions describe calculate-scores --region=us-central1 --gen2
   ```

---

## 🎉 SIGUIENTE PASO

**Ejecuta esto ahora:**

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
chmod +x deploy.sh
./deploy.sh
```

**Después:**

1. Copia la URL que te dará el deployment
2. Abre `N8N_QUERIES_FINALES.md`
3. Configura los 7 nodos en n8n
4. Test con cliente 1702

**En 30 minutos tendrás el sistema funcionando en producción.**

---

## 📚 RESUMEN DE ARCHIVOS

```
Scoring Interno/
│
├── 📖 Documentación
│   ├── INDEX.md ................................. Este archivo
│   ├── RESUMEN_DEPLOYMENT.md .................... ⭐ LEER PRIMERO
│   ├── GUIA_DEPLOYMENT_FINAL.md ................. ⭐ Guía completa
│   ├── N8N_QUERIES_FINALES.md ................... ⭐ Queries para n8n
│   ├── COMANDOS_DEPLOYMENT.md ................... Referencia rápida
│   ├── ARQUITECTURA_COMPLETA.md ................. Arquitectura detallada
│   └── PROPUESTA_ACTUALIZACION_AUTOMATICA_SCORES.md
│
├── 🚀 Cloud Function
│   └── cloud_function_calculate_scores/
│       ├── main.py .............................. ⭐ Código principal
│       ├── requirements.txt ..................... Dependencies
│       └── deploy.sh ............................ ⭐ Script deployment
│
├── 📊 Datos de Ejemplo
│   ├── ejemplo_clientes_base.json
│   ├── ejemplo_pagos_base.json
│   └── ejemplo_prestamos_base.json
│
└── 📋 Otros
    ├── README.md ................................ Proyecto scoring v2.2
    └── API_CLOUD_RUN.md ......................... API (legacy)
```

---

**Creado:** 2026-01-26
**Versión:** 1.0 Final
**Status:** ✅ READY FOR DEPLOYMENT

---

**🎯 ACCIÓN INMEDIATA:**

```bash
cd "/Users/jpchacon/Scoring Interno/cloud_function_calculate_scores"
./deploy.sh
```

**¡Éxito con el deployment!** 🚀
