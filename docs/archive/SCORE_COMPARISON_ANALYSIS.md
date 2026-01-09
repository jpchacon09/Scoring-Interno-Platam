# Análisis Comparativo: PLATAM Score vs Experian Score

**Fecha:** 19 de diciembre de 2025
**Clientes analizados:** 1,836 (1,559 con ambos scores)

---

## 🎯 Hallazgo Principal

**El score PLATAM es significativamente MÁS ESTRICTO que el score de Experian.**

```
Promedio PLATAM:    621.5 puntos
Promedio Experian:  762.1 puntos
Diferencia:        -140.6 puntos (PLATAM es más bajo)
```

**Correlación: 0.263** (baja) - Los scores miden aspectos diferentes del riesgo crediticio.

---

## 📊 Distribución de Scores PLATAM

### Por Rating Crediticio

| Rating | Clientes | % | Rango de Puntos | Interpretación |
|--------|----------|---|-----------------|----------------|
| **A+** | 39 | 2.1% | 900-1000 | Excelente |
| **A** | 61 | 3.3% | 850-899 | Muy Bueno |
| **A-** | 96 | 5.2% | 800-849 | Bueno+ |
| **B+** | 182 | 9.9% | 750-799 | Bueno |
| **B** | 378 | 20.6% | 700-749 | Satisfactorio ⬅ MAYORÍA |
| **B-** | 197 | 10.7% | 650-699 | Aceptable |
| **C+** | 154 | 8.4% | 600-649 | Regular+ |
| **C** | 101 | 5.5% | 550-599 | Regular |
| **C-** | 97 | 5.3% | 500-549 | Regular- |
| **D+** | 212 | 11.5% | 450-499 | Deficiente+ |
| **D** | 158 | 8.6% | 400-449 | Deficiente |
| **F** | 161 | 8.8% | 0-399 | Muy Deficiente |

**Total ratings buenos (A+, A, A-): 10.6%**
**Total ratings aceptables (B+, B, B-): 41.2%**
**Total ratings problemáticos (D+, D, F): 28.9%**

### Estadísticas Generales

- **Mediana:** 660.0 puntos (rating B-)
- **Mínimo:** 230.0 puntos
- **Máximo:** 1000.0 puntos
- **Desviación estándar:** 160.0 puntos (alta variabilidad)

---

## 🔍 Análisis por Componente

### Desempeño de Cada Componente (sobre el máximo posible)

| Componente | Promedio | Máximo | % del Máximo | Evaluación |
|------------|----------|--------|--------------|------------|
| **Payment Performance** | 282.8 | 400 | 70.7% | ✅ BUENO |
| **Payment Plan History** | 113.9 | 150 | 75.9% | ✅ BUENO |
| **Deterioration Velocity** | 69.0 | 100 | 69.0% | ⚠️ REGULAR |
| **Purchase Consistency** | 86.8 | 200 | 43.4% | ❌ DÉBIL |
| **Utilization** | 65.1 | 150 | 43.4% | ❌ DÉBIL |

### 🎯 Componentes Fuertes

1. **Payment Plan History (75.9%):** La mayoría de clientes NO tienen planes de pago activos y tienen buen perfil de riesgo.

2. **Payment Performance (70.7%):** Comportamiento de pago sólido - recordemos que el 84.7% paga ANTES del vencimiento.

### ⚠️ Componentes Débiles

1. **Purchase Consistency (43.4%):**
   - Indica baja frecuencia de compras
   - Muchos clientes inactivos o con poca recurrencia
   - **Problema:** Este componente penaliza demasiado a clientes con pocos pagos

2. **Utilization (43.4%):**
   - Baja utilización del cupo disponible
   - Muchos clientes con cupo pero sin usarlo
   - **Problema:** La curva de utilización puede estar mal calibrada

---

## 📈 Comparación PLATAM vs Experian

### Estadísticas Comparativas (1,559 clientes con ambos scores)

| Métrica | PLATAM | Experian (normalizado) | Diferencia |
|---------|--------|------------------------|------------|
| **Promedio** | 621.5 | 762.1 | -140.6 |
| **Mediana** | 660.0 | 811.7 | -151.7 |
| **Mínimo** | 230.0 | 0.0 | - |
| **Máximo** | 1000.0 | 1000.0 | - |
| **Std Dev** | 158.5 | 164.2 | - |

### Diferencias por Cliente

**Diferencia promedio:** -140.6 puntos (PLATAM más bajo)
**Diferencia absoluta promedio:** 195.6 puntos
**Diferencia máxima:** 830.0 puntos

### Categorización de Diferencias

| Categoría | Clientes | % | Interpretación |
|-----------|----------|---|----------------|
| **Muy Similar (0-50)** | 233 | 14.9% | Scores alineados |
| **Similar (50-100)** | 243 | 15.6% | Diferencia aceptable |
| **Moderada (100-150)** | 242 | 15.5% | Diferencia notable |
| **Alta (150-200)** | 222 | 14.2% | Diferencia significativa |
| **Muy Alta (200+)** | 619 | 39.7% | ⚠️ Diferencia alarmante |

**Solo 30.5% de clientes tienen scores "similares" (diferencia <100 puntos)**

### Dirección de las Diferencias

| Dirección | Clientes | % | Significado |
|-----------|----------|---|-------------|
| **PLATAM >> Experian (+150)** | 105 | 6.7% | PLATAM más optimista |
| **PLATAM ≈ Experian (±150)** | 718 | 46.1% | Scores comparables |
| **PLATAM << Experian (-150)** | 736 | 47.2% | ⚠️ PLATAM MÁS PESIMISTA |

**47.2% de los clientes tienen un score PLATAM mucho más bajo que Experian.**

Esto significa que **casi la mitad de los clientes** serían calificados como de **mayor riesgo** por PLATAM que por Experian.

---

## 🔴 Problemas Identificados

### 1. Correlación Baja (0.263)

**¿Qué significa?**
- Los dos scores están midiendo cosas MUY diferentes
- PLATAM se enfoca en comportamiento interno (pagos, compras, utilización)
- Experian incluye historial externo completo (múltiples entidades financieras, antigüedad, mix de créditos)

**¿Es malo?**
- NO necesariamente - pueden ser complementarios
- PERO una correlación tan baja sugiere que PLATAM puede estar "fallando" en capturar el riesgo real

### 2. PLATAM es Demasiado Conservador

**Evidencia:**
- 47.2% de clientes tienen PLATAM -150 puntos vs Experian
- Promedio PLATAM 140 puntos más bajo

**Posibles causas:**
1. **Falta de datos:** 22.8% de clientes sin historial de pagos reciben score bajo por defecto
2. **Componentes débiles:** Purchase Consistency y Utilization están arrastrando el score hacia abajo
3. **Calibración incorrecta:** Las curvas de puntuación pueden ser muy severas
4. **Missing data:** Clientes nuevos son penalizados excesivamente

### 3. Componentes que Penalizan Demasiado

#### A. Purchase Consistency (43.4% promedio)

**Problema:** Clientes con poca frecuencia de compras reciben score muy bajo, incluso si pagan perfecto.

**Ejemplo:**
- Cliente con 2 préstamos, ambos pagados a tiempo = 43% del componente
- Pero esto NO significa que sea riesgoso, solo que compra poco

**Solución sugerida:**
- NO penalizar tanto por baja frecuencia
- Enfocarse más en RECENCY (actividad reciente)
- Dar más peso a calidad de pagos que a cantidad

#### B. Utilization (43.4% promedio)

**Problema:** Muchos clientes tienen baja utilización porque tienen cupos altos pero compran poco.

**Ejemplo:**
- Cliente con cupo de $5M pero usa $500K = 10% utilización
- Score de utilización: solo 50/150 puntos
- Pero baja utilización NO es riesgo, ¡es señal de capacidad de pago!

**Solución sugerida:**
- Ajustar la curva: NO penalizar utilización baja
- Penalizar solo utilización MUY alta (>90%)
- Rango óptimo: 30-70% en lugar de 30-50%

---

## ✅ Componentes que Funcionan Bien

### 1. Payment Performance (70.7% promedio)

**Por qué funciona:**
- Captura bien la puntualidad de pagos
- El 84.7% de pagos tempranos se refleja en el score
- Penaliza apropiadamente la mora

**Recomendación:** Mantener como está, es el componente más valioso.

### 2. Payment Plan History (75.9% promedio)

**Por qué funciona:**
- Usa risk_profile como proxy
- Penaliza planes de pago activos
- La mayoría de clientes tienen buen perfil

**Recomendación:** Mantener, pero mejorar cuando tengamos más data de planes de pago.

---

## 📋 Casos de Estudio

### Caso 1: Cliente con Scores Alineados (diferencia <50)

**Perfil típico:**
- Historial completo de pagos (8+ pagos)
- Paga a tiempo o temprano
- Utilización moderada (30-70%)
- No tiene planes de pago activos
- Score PLATAM: 700-750
- Score Experian: 720-780

**Conclusión:** El scoring funciona bien para clientes con datos completos.

### Caso 2: PLATAM Mucho Más Bajo que Experian (diferencia -200+)

**Perfil típico:**
- Pocos pagos registrados (1-3 pagos)
- Baja utilización (<10%)
- Sin actividad reciente (60+ días)
- Score PLATAM: 400-500 (D/C-)
- Score Experian: 700-800 (Bueno)

**Problema:** PLATAM está penalizando por falta de datos internos, cuando Experian ve un buen historial externo.

**Conclusión:** Necesitamos ajustar cómo manejamos clientes con poca data interna pero buen score externo.

### Caso 3: PLATAM Mucho Más Alto que Experian (diferencia +200+)

**Perfil típico:**
- Muchos pagos tempranos (10+ pagos, 90%+ a tiempo)
- Alta utilización pero sin mora
- Actividad reciente
- Score PLATAM: 800-900 (A)
- Score Experian: 500-600 (Regular)

**Conclusión:** El comportamiento interno es excelente a pesar de historial externo regular. PLATAM captura bien el "buen comportamiento actual".

---

## 🎯 Recomendaciones

### 1. URGENTE: Ajustar Componentes Débiles

#### A. Purchase Consistency
```python
# ANTES (actual):
if payments_per_month < 0.5:
    frequency_score = 20  # MUY BAJO

# PROPUESTA:
if payments_per_month < 0.5:
    frequency_score = 60  # Neutro, no penalizar tanto
```

**Justificación:** No tener muchas compras NO es riesgo crediticio.

#### B. Utilization
```python
# ANTES (actual):
if pct_util <= 10:
    score = 50  # Penaliza baja utilización

# PROPUESTA:
if pct_util <= 30:
    score = 120  # Baja utilización es OK
elif pct_util <= 60:
    score = 150  # Óptimo
```

**Justificación:** Baja utilización muestra capacidad de pago, no debería penalizarse.

### 2. Implementar Lógica de Fallback

Para clientes con poco historial interno pero buen Experian Score:

```python
if has_experian_score and payment_history_months < 3:
    # Dar más peso a Experian
    platam_score = (platam_score * 0.4) + (experian_score_normalized * 0.6)
```

### 3. Crear Score Híbrido

**Propuesta:** PLATAM Score V2 = Score Combinado

```python
if has_experian_score:
    hybrid_score = (platam_internal * 0.6) + (experian_score * 0.4)
else:
    hybrid_score = platam_internal
```

**Ventajas:**
- Aprovecha la fortaleza de ambos scores
- Reduce variabilidad
- Mejor predicción de riesgo

### 4. Segmentar Clientes por Disponibilidad de Datos

| Segmento | Características | Estrategia de Scoring |
|----------|-----------------|----------------------|
| **Full Data** | HCPN + Pagos + Cupo | 100% PLATAM interno |
| **HCPN Only** | HCPN + Sin pagos | 70% Experian + 30% PLATAM |
| **Internal Only** | Pagos + Sin HCPN | 100% PLATAM interno |
| **Minimal Data** | Solo aplicación | Usar score de aplicación + Experian |

---

## 📊 Distribución por Rating vs Experian

| Rating PLATAM | Clientes | Experian Promedio | Gap |
|---------------|----------|-------------------|-----|
| A+ | 39 | 789.1 | +127.8 |
| A | 61 | 764.2 | +101.2 |
| A- | 96 | 755.8 | +63.8 |
| B+ | 182 | 748.9 | -22.0 |
| B | 378 | 755.3 | -31.7 |
| B- | 197 | 691.6 | -17.9 |
| C+ | 154 | 603.0 | +20.1 |
| C | 101 | 649.4 | +81.0 |
| C- | 97 | 704.0 | +185.8 |
| D+ | 212 | 750.9 | +291.2 |
| D | 158 | 664.8 | +250.9 |
| F | 161 | 574.9 | +241.9 |

**Observación crítica:** Los clientes con rating D, D+, F según PLATAM tienen Experian promedio de 600-750 (¡BUENO!).

Esto confirma que **PLATAM está siendo demasiado estricto** con clientes que tienen poco historial interno pero buen perfil externo.

---

## 🚀 Próximos Pasos

### Inmediato (esta semana)

1. ✅ Calcular scores PLATAM
2. ✅ Comparar con Experian
3. ⏳ **Ajustar componentes débiles** (Purchase Consistency + Utilization)
4. ⏳ **Recalcular scores** con ajustes
5. ⏳ **Validar mejora** en correlación

### Corto Plazo (2-4 semanas)

1. Implementar score híbrido (PLATAM + Experian)
2. Crear segmentación por disponibilidad de datos
3. Validar scores con datos de default real (si están disponibles)
4. Definir puntos de corte (cutoffs) para aprobación/rechazo

### Mediano Plazo (1-3 meses)

1. Preparar datos para ML en Vertex AI
2. Entrenar modelo con features de PLATAM + HCPN
3. Comparar performance: Rules vs ML
4. Implementar modelo ganador

---

## 📁 Archivos Generados

- **platam_scores.csv** (1,836 clientes, 69 columnas)
  - Todos los clientes con scores PLATAM completos
  - 5 componentes + score total + rating

- **score_comparison.csv** (1,559 clientes con ambos scores)
  - Comparación detallada PLATAM vs Experian
  - Diferencias calculadas
  - Categorización de gaps

---

**Generado:** 2025-12-19
**Archivos:** `/Users/jpchacon/Scoring Interno/data/processed/`
**Status:** ⚠️ Requiere ajustes en componentes débiles
