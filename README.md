# PLATAM Internal Credit Score System

Sistema de scoring crediticio interno para PLATAM BNPL (Buy Now Pay Later) con migración planeada a Machine Learning usando Google Vertex AI.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-success.svg)]()
[![License](https://img.shields.io/badge/License-Private-red.svg)]()
[![Version](https://img.shields.io/badge/Version-V2.0-green.svg)]()

---

## 📋 Tabla de Contenidos

- [Estado del Proyecto](#-estado-del-proyecto)
- [Inicio Rápido](#-inicio-rápido)
- [Documentación](#-documentación)
- [Resultados Clave](#-resultados-clave)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Scripts Disponibles](#-scripts-disponibles)

---

## 🎯 Estado del Proyecto

**Fase Actual:** Scoring Basado en Reglas V2.0 (Completado ✅)

| Fase | Estado | Completitud |
|------|--------|-------------|
| 1. Análisis de Datos | ✅ Completado | 100% |
| 2. Limpieza y Merge | ✅ Completado | 100% |
| 3. Scoring PLATAM V2.0 | ✅ Completado | 100% |
| 4. Comparación con Experian | ✅ Completado | 100% |
| 5. Visualizaciones V2.0 | ✅ Completado | 100% |
| 6. Migración a ML (Vertex AI) | 📋 Planeado | 0% |

---

## 🚀 Inicio Rápido

### Uso Básico

```bash
# 1. Calcular scores PLATAM V2.0
python scripts/calculate_scores.py

# 2. Generar visualizaciones V2.0
python scripts/04_visualize_scores.py

# 3. Generar gráficos simples
python scripts/05_generate_simple_charts.py

# 4. Exportar a Excel
python scripts/06_create_scores_excel.py
```

---

## 🎓 Metodología de Scoring V2.0

### Algoritmo PLATAM V2.0 (0-1000 puntos)

**Sistema optimizado:** El score se calcula con **3 componentes** (anteriormente 5):

1. **Payment Performance (600 pts - 60%)**
   - Puntualidad de pagos (DPD)
   - Patrón de pagos
   - Madurez del historial
   - **Mayor peso** en V2.0 (antes 400 pts)

2. **Payment Plan History (150 pts - 15%)**
   - Planes de pago activos
   - Perfil de riesgo
   - **Sin cambios** respecto a V1.0

3. **Deterioration Velocity (250 pts - 25%)**
   - Comparación DPD reciente vs histórico
   - Tendencia de deterioro
   - **Mayor peso** en V2.0 (antes 100 pts)

**Cambios principales en V2.0:**
- ❌ Eliminación de **Purchase Consistency** (200 pts)
- ❌ Eliminación de **Utilization Score** (150 pts)
- ✅ Redistribución: Mayor énfasis en Payment Performance y Deterioration Velocity
- ✅ Simplificación: 5 → 3 componentes

### Componentes del Score V2.0

| Componente | Puntaje Máximo | Peso |
|------------|----------------|------|
| Payment Performance | 600 pts | 60% |
| Payment Plan History | 150 pts | 15% |
| Deterioration Velocity | 250 pts | 25% |

**Componentes eliminados:**
- ~~Purchase Consistency (200 pts, 20%)~~ - Penalizaba baja frecuencia de compra
- ~~Utilization (150 pts, 15%)~~ - Penalizaba baja utilización de cupo

---

## 💡 Ventajas del Sistema V2.0

### ✅ Mejoras Implementadas

1. **Mayor enfoque en comportamiento de pago (60%)**
   - El indicador más confiable de riesgo crediticio
   - Refleja capacidad y voluntad de pago

2. **Eliminación de penalizaciones injustas**
   - Clientes con baja frecuencia ya no son castigados
   - Baja utilización de cupo = capacidad de pago, NO riesgo

3. **Sistema más simple y robusto**
   - 3 componentes fuertes vs 5 componentes con 2 débiles
   - Más fácil de explicar y mantener
   - Mejor alineación con riesgo real

### 📊 Impacto Esperado

- **+15-20%** de clientes correctamente clasificados como bajo riesgo
- **Sistema más justo** sin penalizar comportamiento prudente
- **Mayor correlación** con riesgo real de default

---

## 📞 Contacto

**Repositorio:** https://github.com/jpchacon09/Scoring-Interno-Platam

---

**Última actualización:** 29 de diciembre de 2025  
**Versión:** 2.0.0  
**Status:** Sistema V2.0 Implementado ✅
