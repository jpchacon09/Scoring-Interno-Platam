# 📋 Guía de Mantenimiento del Sistema de Scoring

## 🎯 Estado Actual del Sistema

### ✅ En Producción (Usar):

#### 1. **API Principal**
- **Archivo:** `api_scoring_cedula.py`
- **URL:** https://scoring-api-741488896424.us-central1.run.app
- **Función:** Consulta scoring por cédula
- **Datos:** CSV con 1,835 clientes
- **Actualización:** Manual (cuando sea necesario)

#### 2. **Monitoreo Trimestral del Modelo**
- **Archivo:** `check_model_drift.py`
- **Frecuencia:** Cada 3 meses
- **Función:** Detecta si modelo necesita reentrenamiento
- **Comando:** `python check_model_drift.py`
- **Próxima ejecución:** Abril 2026

---

### 📚 Para Referencia Futura (No usar ahora):

#### 3. **Actualización Automática (Futuro)**
- **Archivos:**
  - `cloud_function_update_scores.py`
  - `api_scoring_auto_update.py`
  - `ACTUALIZACION_AUTOMATICA.md`
- **Para qué:** Sistema de actualización semanal automática
- **Nota:** Implementar después de discutir con equipo
- **Base de datos:** MySQL (ya documentado)

---

## 🗓️ Calendario de Mantenimiento

### 📅 Trimestral (Cada 3 meses):

```
✅ Enero 2026 - Ejecutado
🔲 Abril 2026 - Pendiente
🔲 Julio 2026 - Pendiente
🔲 Octubre 2026 - Pendiente
```

**Acción:**
```bash
cd "/Users/jpchacon/Scoring Interno"
python check_model_drift.py
```

**Revisar:**
- ⚠️ Alertas de data drift
- 📊 Cambios en distribución de scores
- 🚨 Recomendación de reentrenamiento

---

### 🔄 Cuando sea necesario (Manual):

#### Actualizar datos de clientes:

**Opción A - Actualización completa:**
```bash
# 1. Exportar nuevo CSV con scores calculados
# 2. Reemplazar: data/processed/hybrid_scores.csv
# 3. Reconstruir Docker:
gcloud builds submit --tag gcr.io/platam-analytics/scoring-api:latest

# 4. Redesplegar:
gcloud run deploy scoring-api \
  --image gcr.io/platam-analytics/scoring-api:latest \
  --region us-central1 \
  --project platam-analytics
```

**Opción B - Solo agregar clientes nuevos:**
- Agregar filas al CSV existente
- Seguir pasos 3-4 de Opción A

---

### 🧠 Reentrenar Modelo (Si check_model_drift.py lo recomienda):

**Cuándo reentrenar:**
- ✅ Han pasado 6+ meses
- ✅ Data drift > 20% en métricas clave
- ✅ Precisión del modelo bajó significativamente
- ✅ Cambios importantes en política de crédito

**Pasos:**
```bash
# 1. Preparar datos actualizados con columna 'default' (0/1)
python train_model.py  # O el script que uses

# 2. Validar nuevo modelo
python validate_model.py

# 3. Si mejora el anterior, desplegar a Vertex AI
# (Ver VERTEX_AI_GUIA.md para pasos)

# 4. Actualizar fecha en check_model_drift.py:
# fecha_entrenamiento = datetime(2026, 4, 15)  # Nueva fecha
```

---

## 📊 Archivos Importantes

### Producción Actual:
```
api_scoring_cedula.py          ← API en Cloud Run
data/processed/hybrid_scores.csv  ← Datos de clientes
check_model_drift.py           ← Monitoreo trimestral
API_CLOUD_RUN.md               ← Documentación de uso
```

### Documentación:
```
VERTEX_AI_GUIA.md              ← Cómo usar Vertex AI
GUIA_MANTENIMIENTO.md          ← Este archivo
```

### Futuro (Referencia):
```
ACTUALIZACION_AUTOMATICA.md    ← Plan de actualización automática
cloud_function_update_scores.py  ← Para implementar después
api_scoring_auto_update.py     ← API v2.0 (futuro)
```

---

## 🚨 Alertas y Troubleshooting

### Si el modelo predice mal:
1. Ejecutar `check_model_drift.py`
2. Revisar si datos están desactualizados
3. Considerar reentrenamiento si es necesario

### Si la API no responde:
1. Verificar Cloud Run: https://console.cloud.google.com/run?project=platam-analytics
2. Revisar logs de errores
3. Verificar que Vertex AI endpoint esté activo

### Si necesitas actualizar datos urgentemente:
- Opción rápida: Actualizar CSV y redesplegar (20 min)
- Opción futura: Implementar sistema automático (1 día de setup)

---

## 📞 Contactos y Recursos

### Servicios en Google Cloud:
- **Proyecto:** platam-analytics
- **Cloud Run:** scoring-api
- **Vertex AI Endpoint:** 3426032820691755008
- **Región:** us-central1

### URLs Importantes:
- **API Producción:** https://scoring-api-741488896424.us-central1.run.app
- **Docs API:** https://scoring-api-741488896424.us-central1.run.app/docs
- **Cloud Console:** https://console.cloud.google.com/run?project=platam-analytics

---

## ✅ Checklist Trimestral

Cada 3 meses, ejecutar esta checklist:

```
🔲 1. Ejecutar check_model_drift.py
🔲 2. Revisar alertas de data drift
🔲 3. Verificar precisión del modelo
🔲 4. Decidir si necesita reentrenamiento
🔲 5. Actualizar datos si han cambiado mucho
🔲 6. Documentar decisiones y resultados
🔲 7. Programar próxima revisión
```

---

## 💡 Próximos Pasos (Discutir con equipo)

### Sistema de Actualización Automática:

**Beneficios:**
- ✅ Datos siempre frescos (actualización semanal)
- ✅ Cero esfuerzo manual
- ✅ Predicciones más precisas
- ✅ Escalable

**Requerimientos:**
- 📊 Query SQL a MySQL (ya documentado)
- ⚙️ Cloud Function (código listo)
- 💰 Costo: ~$0.12/mes adicional

**Decisión:** Pendiente de discusión con equipo

---

**Última actualización:** Enero 2026
**Versión del sistema:** 1.0
**Estado:** ✅ Producción estable
