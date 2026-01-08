# 📁 Future Implementation - Sistema de Actualización Automática

## 📋 Contenido de esta Carpeta

Esta carpeta contiene código y documentación para **implementación futura** del sistema de actualización automática semanal.

### Archivos:

1. **`ACTUALIZACION_AUTOMATICA.md`**
   - Documentación completa del sistema propuesto
   - Arquitectura y opciones (A, B, C)
   - SQL query requerido para MySQL
   - Costos estimados (~$0.12/mes)

2. **`cloud_function_update_scores.py`**
   - Cloud Function para actualización semanal
   - Query SQL → Calcula scores → Guarda en Cloud Storage
   - Se ejecuta automáticamente cada domingo 2am

3. **`api_scoring_auto_update.py`**
   - API v2.0 con carga dinámica desde Cloud Storage
   - Fallback a base de datos si cliente no existe
   - Endpoint `/reload` para forzar actualización

---

## 🚫 NO Usar Ahora

**Estos archivos son para REFERENCIA FUTURA.**

**Sistema actual (en producción):**
- `api_scoring_cedula.py` - API en Cloud Run
- Actualización manual del CSV
- Funciona perfectamente para las necesidades actuales

---

## 🔮 Cuándo Implementar

Implementar este sistema cuando:
- ✅ Equipo haya discutido y aprobado
- ✅ Se tenga acceso a MySQL configurado
- ✅ Se necesite actualización más frecuente (semanal)
- ✅ Volumen de clientes justifique automatización

---

## 📊 Beneficios de Implementación

**Ventajas:**
- ✅ Datos actualizados automáticamente cada semana
- ✅ Cero esfuerzo manual
- ✅ Predicciones ML con features frescos
- ✅ Escalable a miles de clientes

**Costos:**
- Cloud Function: ~$0/mes (free tier)
- Cloud Scheduler: $0.10/mes
- Cloud Storage: $0.02/mes
- **Total: ~$0.12/mes adicional**

---

## 🛠️ Pasos para Implementación (Cuando estén listos)

### 1. Configurar Base de Datos
```bash
# Verificar acceso a MySQL
# Probar query SQL del documento
```

### 2. Ajustar Query SQL
```sql
-- Editar en cloud_function_update_scores.py
-- Ajustar nombres de tablas según tu BD
```

### 3. Crear Cloud Storage Bucket
```bash
gsutil mb -p platam-analytics gs://platam-scoring-data
```

### 4. Desplegar Cloud Function
```bash
gcloud functions deploy update-scores-weekly \
  --runtime python311 \
  --trigger-http \
  --entry-point main
```

### 5. Configurar Scheduler
```bash
gcloud scheduler jobs create http weekly-score-update \
  --schedule="0 2 * * 0" \
  --uri="https://...cloudfunctions.net/update-scores-weekly" \
  --time-zone="America/Bogota"
```

### 6. Actualizar API
```bash
# Reemplazar api_scoring_cedula.py con api_scoring_auto_update.py
# Redesplegar a Cloud Run
```

---

## 📞 Para Más Información

Leer: `ACTUALIZACION_AUTOMATICA.md` (en esta carpeta)

**Base de datos:** MySQL
**Query SQL:** Documentado en `cloud_function_update_scores.py`

---

**Estado:** 📚 Documentado y listo para implementación futura
**Decisión:** Pendiente de discusión con equipo
**Fecha creación:** Enero 2026
