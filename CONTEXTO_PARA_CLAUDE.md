# Contexto del Proyecto - Sistema de Scoring PLATAM

**Última actualización:** 7 de enero de 2026
**Fase actual:** Sistema V2.0 + Defaults integrados - Listo para Machine Learning

---

## 📋 Resumen Ejecutivo

Sistema de scoring crediticio interno para PLATAM BNPL con 3 componentes principales:
- **Payment Performance** (600 pts, 60%)
- **Payment Plan History** (150 pts, 15%)
- **Deterioration Velocity** (250 pts, 25%)

Sistema híbrido que combina PLATAM V2.0 + HCPN (Experian) con pesos dinámicos según madurez del cliente.

---

## ✅ Lo Que Hemos Completado

### 1. Sistema de Scoring V2.0
- [x] Migración de 5 componentes → 3 componentes
- [x] Eliminación de Purchase Consistency y Utilization (penalizaban injustamente)
- [x] Implementación completa en `scripts/03_calculate_platam_score.py`
- [x] Scores recalculados para 1,836 clientes

### 2. Sistema Híbrido Inteligente
- [x] Pesos dinámicos según madurez del cliente (muy_nuevo → maduro)
- [x] Ajustes por cantidad de historial (±10% según num_pagos)
- [x] Implementado en `scripts/08_calculate_hybrid_scores.py`
- [x] Documentado en `HYBRID_SCORING_GUIDE.md`

### 3. **Corrección Crítica: Lógica de Planes de Pago** ✅
**Fecha:** 30 diciembre 2025

**Problema identificado:**
- El sistema anterior NO interpretaba correctamente el status de los planes de pago
- Penalizaba clientes con planes "Pendientes" (no activados)

**Solución implementada:**
- Created `scripts/fix_payment_plans_and_recalculate.py`
- Lógica correcta:
  - **"Activo"** = plan activado → -50 pts
  - **"Pendiente"** = plan no activado → **0 pts** (sin penalización)
  - **"Default/Cancelado"** = plan incumplido → -100 pts

**Fuente de datos:**
- CSV: `export-planes_de_pago-30-12-2025.csv`
- Mapeo: `data/processed/clientes_clean.csv` (client_id → cedula)

**Resultados:**
- 13 clientes con planes en el sistema
- TODOS tienen status "Pendiente" (25 planes)
- Payment plan component: **150.0/150** para todos (correcto)
- PLATAM V2.0 promedio: **760.8** (antes: 724.7, +36 pts)
- Hybrid score promedio: **764.7** (antes: 746.9, +17.8 pts)

**Archivos actualizados:**
- ✅ `SCORES_V2_ANALISIS_COMPLETO.csv` (1,835 clientes, 24 columnas)
- ✅ `ESTADISTICAS_SCORES_V2.csv` (estadísticas completas)
- ✅ `data/processed/platam_scores.csv`
- ✅ `data/processed/hybrid_scores.csv`
- ✅ Commit: `75b1c92` - "fix: Correct payment plan logic in scoring calculation"

### 4. Integración de Scores Empresariales
**Fecha:** 6 enero 2026

**Problema:** Empresas (personas jurídicas) no tenían scores Experian

**Solución:**
- Procesamiento de 172 PDFs de Experian para empresas
- Normalización de escala 0-5 (invertida) a 0-1000
- 125 empresas procesadas exitosamente (72.7% tasa de éxito)
- 60 empresas con scores Experian integrados
- 30 empresas sin score usan base 500 pts
- Documentado en `PROCESO_SCORES_EMPRESARIALES.md`

**Archivos actualizados:**
- ✅ `scores_empresas_experian_normalized.csv`
- ✅ `master_dataset.csv` (con scores empresariales)
- ✅ `hybrid_scores.csv` (recalculados con empresas)
- ✅ Commit: `3bfcd37` - "feat: Integrate Experian business scores"

### 5. Integración de Datos de Defaults
**Fecha:** 7 enero 2026

**Objetivo:** Preparar sistema para Machine Learning con variable target real

**Fuente:** `Defaults.csv` (9,097 préstamos, 1,704 clientes únicos)

**Criterios de Default:**
- l_status = "Default", O
- Mora > 180 días

**Resultados:**
- **100 clientes en default** (5.45% tasa de default)
- Balance en default: $186,228,906
- Mora máxima: 853 días
- **VALIDACIÓN:** Los scores SÍ predicen defaults
  - Clientes sin default: Hybrid Score promedio = 767.9
  - Clientes con default: Hybrid Score promedio = 623.2
  - **Diferencia: -144.7 puntos**

**Tasa de Default por Rating (Validación del Sistema):**
- Rating D: 21.9% default rate (16/73)
- Rating C: 13.1% default rate (8/61)
- Rating A+: 3.6% default rate (31/858)
- Rating A: 1.5% default rate (1/65)

**Archivos creados/actualizados:**
- ✅ `ml_training_data.csv` - Dataset listo para ML (1,835 clientes, 26 features)
- ✅ `master_dataset.csv` (con default_flag y métricas)
- ✅ `SCORES_V2_ANALISIS_COMPLETO.csv` (con información de defaults)
- ✅ Script: `scripts/integrate_defaults_data.py`

### 6. Visualizaciones y Análisis
- [x] Dashboard dinámico CSV generado
- [x] Gráficos comparativos (PLATAM vs HCPN vs Híbrido)
- [x] Análisis estadístico completo (mean, median, std, skewness, kurtosis)
- [x] Simulador interactivo de scoring

### 5. Documentación
- [x] `README.md` - Guía principal del proyecto
- [x] `PLATAM_SCORING_DOCUMENTATION.md` - Documentación técnica V2.0
- [x] `HYBRID_SCORING_GUIDE.md` - Guía del sistema híbrido
- [x] `RESUMEN_EJECUTIVO.md` - Resumen para stakeholders
- [x] `VERTEX_AI_ML_ROADMAP.md` - Roadmap de migración a ML

---

## 📊 Estado Actual de los Datos

### Scores Actuales (Post-Corrección)
| Métrica | PLATAM V2.0 | HCPN | Híbrido |
|---------|-------------|------|---------|
| **Promedio** | 760.8 | 762.1 | 764.7 |
| **Mediana** | 805.0 | 811.7 | 792.4 |
| **Desv. Std** | 190.1 | 164.2 | 148.7 |
| **Mínimo** | 245.0 | 0.0 | 115.0 |
| **Máximo** | 1000.0 | 1000.0 | 1000.0 |
| **Skewness** | -0.57 | -1.86 | -1.16 |
| **Kurtosis** | -0.82 | 4.15 | 1.44 |

### Distribución de Ratings PLATAM V2.0
- **A+**: 858 clientes (46.8%)
- **C+**: 492 clientes (26.8%)
- **B+**: 216 clientes (11.8%)
- **B**: 70 clientes (3.8%)
- **A**: 65 clientes (3.5%)
- **C**: 61 clientes (3.3%)
- **D**: 73 clientes (4.0%)

### Componentes Promedio
- **Payment Performance**: 438.4/600 pts (73.1%)
- **Payment Plan**: 150.0/150 pts (100%) ✅
- **Deterioration**: 172.5/250 pts (69.0%)

### Planes de Pago
- Total planes: 25
- Clientes únicos: 13
- Status "Pendiente": 25 (100%)
- Status "Activo": 0
- Status "Default": 0

---

## 🎯 Próximos Pasos - Machine Learning

### ✅ COMPLETADO: Preparación de Datos para ML
- [x] Recopilar datos de defaults (100 clientes identificados)
- [x] Crear variable target `default_flag`
- [x] Validar poder predictivo del sistema actual
- [x] Crear dataset `ml_training_data.csv` (1,835 clientes, 26 features)

### 🚀 PASO INMEDIATO: Baseline ML Local
**Duración estimada:** 1 semana

1. **Entrenar Modelo Baseline** ⭐
   ```bash
   python train_baseline.py
   ```
   - Entrenar XGBoost localmente
   - Validar AUC-ROC > 0.70
   - Analizar feature importance
   - Guardar modelo y scaler

2. **Validar Resultados**
   - Revisar métricas (Precision, Recall, F1, AUC)
   - Comparar con baseline del sistema actual
   - Identificar top features predictivas
   - Documentar hallazgos

### 🏗️ SIGUIENTE: Migración a Vertex AI
**Duración estimada:** 1-2 semanas

Ver roadmap completo en `VERTEX_AI_ML_ROADMAP.md`

1. **Setup de Infraestructura GCP**
   - [ ] Crear/configurar proyecto GCP
   - [ ] Habilitar Vertex AI API
   - [ ] Crear bucket GCS
   - [ ] Subir ml_training_data.csv

2. **Entrenamiento en Vertex AI**
   - [ ] Crear Vertex AI Workbench
   - [ ] Entrenar modelo en la nube
   - [ ] Registrar en Model Registry
   - [ ] Deploy a endpoint

3. **Integración con Sistema**
   - [ ] API de predicción
   - [ ] Combinar ML + Híbrido
   - [ ] Monitoreo en producción
   - [ ] Re-entrenamiento mensual

---

## 🔧 Scripts Principales

### Cálculo de Scores
```bash
# Calcular scores PLATAM V2.0
python scripts/03_calculate_platam_score.py

# Calcular scores híbridos
python scripts/08_calculate_hybrid_scores.py

# Recalcular con lógica correcta de planes de pago
python scripts/fix_payment_plans_and_recalculate.py
```

### Visualizaciones
```bash
# Generar visualizaciones comparativas
python scripts/09_visualize_hybrid_comparison.py

# Generar gráficos simples
python scripts/05_generate_simple_charts.py

# Crear simulador interactivo
python scripts/11_create_interactive_simulator.py
```

---

## 📁 Archivos Importantes

### CSVs de Análisis (Raíz del Proyecto)
- **`SCORES_V2_ANALISIS_COMPLETO.csv`** - Análisis completo para el equipo de analytics
  - 1,835 clientes, 24+ columnas
  - Incluye: scores, ratings, componentes, pesos, flags de planes de pago, default_flag

- **`ml_training_data.csv`** ⭐ - Dataset listo para Machine Learning
  - 1,835 clientes, 26 features
  - Incluye: default_flag (target), scores, componentes, métricas de mora, planes de pago
  - Balance de clases: 94.6% no-default, 5.4% default

- **`ESTADISTICAS_SCORES_V2.csv`** - Estadísticas agregadas
  - Mean, median, std, min, max, quartiles, skewness, kurtosis

- **`Defaults.csv`** - Fuente de datos de defaults
  - 9,097 préstamos, 1,704 clientes únicos
  - Columnas: l_cl_doc_number, l_status, l_due_days, l_balance_total

- **`export-planes_de_pago-30-12-2025.csv`** - Fuente de planes de pago
  - 25 planes, 13 clientes únicos
  - TODOS status "Pendiente"

### CSVs Procesados (data/processed/)
- `platam_scores.csv` - Scores PLATAM V2.0
- `hybrid_scores.csv` - Scores híbridos
- `clientes_clean.csv` - Mapeo client_id → cedula
- `master_dataset.csv` - Dataset consolidado

### Documentación
- `README.md` - Entrada principal
- `PLATAM_SCORING_DOCUMENTATION.md` - Docs técnicas
- `HYBRID_SCORING_GUIDE.md` - Guía del híbrido
- `CONTEXTO_PARA_CLAUDE.md` - Este archivo

---

## 🐛 Issues Conocidos y Soluciones

### Issue 1: ~~Lógica de Planes de Pago Incorrecta~~ ✅ RESUELTO
**Status:** RESUELTO (30 dic 2025)
- Planes "Pendientes" ya NO penalizan
- Script `fix_payment_plans_and_recalculate.py` implementado

### Issue 2: Clientes sin HCPN (277 clientes)
**Status:** Manejado con estrategia de fallback
- Usan 100% PLATAM score
- 15% de la base de datos
- No afecta funcionamiento

### Issue 3: Clientes sin Historial de Pagos
**Status:** Manejado con scores base conservadores
- Payment Performance: 300/600 pts (base conservador)
- Deterioration: 125/250 pts (neutral)
- Score total: ~575 pts (rating C+)

---

## 💡 Decisiones Clave Tomadas

### 1. Por Qué Eliminamos 2 Componentes
**Eliminados:** Purchase Consistency (200 pts) y Utilization (150 pts)

**Razón:**
- Penalizaban comportamiento prudente (baja frecuencia, baja utilización)
- Baja utilización = capacidad de pago, NO riesgo
- Baja frecuencia de compra no indica mal comportamiento crediticio

**Impacto:**
- Sistema más justo
- +15-20% clientes correctamente clasificados como bajo riesgo
- Mayor enfoque en comportamiento de pago (60% del score)

### 2. Por Qué Pesos Dinámicos en Híbrido
**Enfoque:** NO usar 50/50 fijo

**Razón:**
- Clientes nuevos: poco historial interno → confiar más en HCPN (70-80%)
- Clientes maduros: historial rico → confiar más en PLATAM (60-70%)
- Se ajusta automáticamente según disponibilidad de datos

**Resultado:**
- 34.1% de clientes mejoraron su score vs PLATAM puro
- Más estable (std: 148.7 vs 190.1)
- Justo para todos los segmentos

### 3. Definición de Default
**Criterio:** >180 días de mora (DPD > 180)

**Uso futuro:**
- Target variable para modelos de ML
- Validación de poder predictivo del score
- Benchmarking de tasas de default por rating

---

## 🗣️ Preguntas Frecuentes para Contexto Futuro

### P: ¿Por qué el Payment Plan component es 150 para todos?
**R:** Porque actualmente TODOS los planes tienen status "Pendiente" (no activados). Los planes pendientes no deben penalizar el score. Cuando haya planes "Activos" o "Default", esos clientes tendrán 100 o 50 pts respectivamente.

### P: ¿Por qué subieron los scores ~36 puntos?
**R:** Corrección de bug. Antes penalizábamos incorrectamente a clientes con planes "Pendientes". Ahora solo penalizamos planes realmente activos o incumplidos.

### P: ¿Cuál CSV debe ir al equipo de analytics?
**R:** `SCORES_V2_ANALISIS_COMPLETO.csv` - tiene TODO lo necesario: scores, componentes, ratings, estadísticas, flags de planes de pago.

### P: ¿Cómo se calcula el score híbrido?
**R:** `Híbrido = (peso_platam × PLATAM) + (peso_hcpn × HCPN)` donde los pesos son dinámicos según:
- Madurez del cliente (meses en plataforma)
- Cantidad de historial (número de pagos)
- Disponibilidad de datos

### P: ¿Qué significa skewness negativo (-0.57)?
**R:** La distribución está sesgada hacia la derecha (cola izquierda más larga). Tenemos más clientes con scores altos que bajos (46.8% en A+). Es positivo para el negocio.

### P: ¿Por qué client_id ≠ cedula?
**R:** `client_id` es ID interno del sistema, `cedula` es documento de identidad. Se mapean usando `clientes_clean.csv`.

---

## 📞 Información de Contacto del Proyecto

**Repositorio:** https://github.com/jpchacon09/Scoring-Interno-Platam
**Rama principal:** `main`
**Último commit:** `75b1c92` - "fix: Correct payment plan logic in scoring calculation"

---

## 🎓 Recursos de Aprendizaje

### Para entender el sistema híbrido:
- Leer `HYBRID_SCORING_GUIDE.md`
- Ver ejemplos en `scripts/08_calculate_hybrid_scores.py`

### Para entender V2.0:
- Leer `PLATAM_SCORING_DOCUMENTATION.md`
- Ver implementación en `scripts/03_calculate_platam_score.py`

### Para migración a ML:
- Leer `VERTEX_AI_ML_ROADMAP.md`
- Revisar estructura de datos en `master_dataset.csv`

---

## 🚀 Cómo Continuar Desde Aquí

### PASO INMEDIATO: Entrenar Modelo Baseline 🎯
```bash
cd "/Users/jpchacon/Scoring Interno"
python train_baseline.py
```

**Qué esperar:**
- AUC-ROC entre 0.70-0.85 (bueno a excelente)
- Top features más predictivas identificadas
- Modelo guardado como `xgboost_model.pkl`
- Gráfico de feature importance generado

### Después del baseline local:
1. **Validar resultados** y compartir métricas
2. **Configurar GCP** para Vertex AI
3. **Subir modelo a la nube** y crear endpoint
4. **Integrar con sistema actual** (Híbrido + ML)

### Si quieres optimizar el sistema actual (mientras entrena ML):
1. Analizar casos extremos (ratings D)
2. Ajustar umbrales de rating si necesario
3. A/B testing de pesos híbridos

---

**Notas finales:**
- ✅ Todos los CSVs están actualizados con defaults
- ✅ Sistema validado: scores SÍ predicen defaults (-144.7 pts de diferencia)
- ✅ Dataset ML listo: `ml_training_data.csv`
- ✅ Script baseline listo: `train_baseline.py`
- ✅ Documentación ML actualizada: `VERTEX_AI_ML_ROADMAP.md`
- ✅ Git history preservado para auditoría

**Estado:** ✅ Sistema V2.0 validado + Datos ML preparados + Listo para entrenar primer modelo
