# PLATAM Hybrid Scoring System - Guía Completa

**Versión:** 1.0
**Fecha:** 29 de Diciembre de 2025
**Sistema:** PLATAM Credit Scoring + HCPN (Experian)

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [¿Por Qué NO 50/50?](#por-qué-no-5050)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Reglas de Ponderación](#reglas-de-ponderación)
5. [Casos de Uso](#casos-de-uso)
6. [Resultados y Validación](#resultados-y-validación)
7. [Implementación](#implementación)
8. [Mantenimiento](#mantenimiento)

---

## 🎯 Visión General

### ¿Qué es el Scoring Híbrido?

El **PLATAM Hybrid Scoring System** combina inteligentemente dos fuentes de información crediticia:

1. **PLATAM Score V2.0** (0-1000)
   - Basado 100% en comportamiento de pago interno
   - 3 componentes: Payment Performance (60%), Payment Plan History (15%), Deterioration Velocity (25%)
   - Ideal para clientes con historial en la plataforma

2. **HCPN Score** (Experian, normalizado a 0-1000)
   - Historial crediticio externo completo
   - Incluye información de todos los prestamistas
   - Ideal para clientes nuevos o con poco historial interno

### Filosofía del Sistema

**NO usamos una combinación fija (50/50).**

En lugar de eso, calculamos **pesos dinámicos** basados en:
- ✅ **Madurez del cliente** (meses en la plataforma)
- ✅ **Cantidad de historial** (número de pagos)
- ✅ **Disponibilidad de datos** (PLATAM, HCPN, ambos, o ninguno)

---

## 🚫 ¿Por Qué NO 50/50?

### Problemas de un Sistema Fijo

Un sistema de pesos fijos (50% PLATAM + 50% HCPN) presenta varios problemas:

#### 1. **Injusto para Clientes Nuevos**

**Escenario:**
```
Cliente nuevo (1 mes, 2 pagos):
- PLATAM Score: 700 (basado en solo 2 pagos)
- HCPN Score: 850 (historial externo de 5 años)
```

**Con 50/50:**
```
Score Final = (700 × 0.5) + (850 × 0.5) = 775
```
⚠️ **Problema:** Estamos dando igual peso a 2 pagos internos que a 5 años de historial externo.

**Con Pesos Dinámicos:**
```
Score Final = (700 × 0.30) + (850 × 0.70) = 805
```
✅ **Mejor:** Confiamos más en el historial externo extenso.

#### 2. **Injusto para Clientes Establecidos**

**Escenario:**
```
Cliente establecido (24 meses, 30 pagos):
- PLATAM Score: 900 (excelente comportamiento interno)
- HCPN Score: 720 (historial externo con algunos problemas antiguos)
```

**Con 50/50:**
```
Score Final = (900 × 0.5) + (720 × 0.5) = 810
```
⚠️ **Problema:** Penalizamos injustamente el excelente comportamiento interno reciente.

**Con Pesos Dinámicos:**
```
Score Final = (900 × 0.70) + (720 × 0.30) = 846
```
✅ **Mejor:** Confiamos más en el comportamiento interno reciente y comprobado.

#### 3. **No Aprovecha la Información Disponible**

Un sistema fijo no puede adaptarse a casos especiales:
- Cliente sin HCPN pero con 50 pagos internos → Debería usar 100% PLATAM
- Cliente nuevo sin pagos pero con HCPN → Debería usar 80% HCPN + 20% base
- Cliente sin ningún dato → Necesita score conservador por defecto

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: Cliente con datos                                   │
│  - PLATAM Score (o None)                                    │
│  - HCPN Score (o None)                                      │
│  - Meses como cliente                                       │
│  - Cantidad de pagos                                        │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │ ¿Tiene ambos scores?  │
        └───────┬───────────────┘
                │
       ┌────────┴────────┐
       │ SÍ              │ NO
       ▼                 ▼
┌──────────────┐    ┌──────────────┐
│ CASO 1       │    │ ¿Solo PLATAM?│
│ Híbrido con  │    └──────┬───────┘
│ pesos        │           │
│ dinámicos    │    ┌──────┴──────┐
└──────────────┘    │ SÍ          │ NO
                    ▼             ▼
            ┌──────────────┐  ┌──────────────┐
            │ CASO 2       │  │ ¿Solo HCPN?  │
            │ 100% PLATAM  │  └──────┬───────┘
            └──────────────┘         │
                            ┌────────┴────────┐
                            │ SÍ              │ NO
                            ▼                 ▼
                    ┌──────────────┐  ┌──────────────┐
                    │ CASO 3       │  │ CASO 4       │
                    │ 80% HCPN +   │  │ Thin File    │
                    │ 20% base     │  │ Score: 500   │
                    └──────────────┘  └──────────────┘
```

### Componentes del Sistema

```python
hybrid_scoring.py
├── HybridScoringConfig (Clase de configuración)
│   ├── MADUREZ_NUEVO = 3 meses
│   ├── MADUREZ_INTERMEDIO = 6 meses
│   ├── MADUREZ_ESTABLECIDO = 12 meses
│   └── PESOS_PLATAM = {'muy_nuevo': 0.30, 'nuevo': 0.40, ...}
│
├── determinar_categoria_madurez()
│   └── Clasifica cliente en: muy_nuevo, nuevo, intermedio, establecido, maduro
│
├── calcular_peso_platam()
│   └── Calcula peso dinámico basado en madurez y cantidad de pagos
│
├── calculate_hybrid_score()
│   └── Calcula score híbrido para un cliente
│
└── calculate_hybrid_scores_batch()
    └── Procesa DataFrame completo
```

---

## ⚖️ Reglas de Ponderación

### 1. Categorías de Madurez

| Categoría | Tiempo | Pagos | Peso PLATAM Base | Peso HCPN Base |
|-----------|--------|-------|------------------|----------------|
| **Muy Nuevo** | < 3 meses | Cualquiera | 30% | 70% |
| **Nuevo** | 3-6 meses | Cualquiera | 40% | 60% |
| **Intermedio** | 6-12 meses | Cualquiera | 50% | 50% |
| **Establecido** | 12-24 meses | Cualquiera | 60% | 40% |
| **Maduro** | > 24 meses | Cualquiera | 70% | 30% |

### 2. Ajustes por Historial de Pagos

Los pesos base se ajustan según la cantidad de pagos:

- ✅ **+10% peso PLATAM** si tiene **≥20 pagos** (historial amplio y confiable)
- ⚠️ **-10% peso PLATAM** si tiene **<5 pagos** (historial insuficiente)

**Límites:**
- Peso PLATAM mínimo: **20%**
- Peso PLATAM máximo: **80%**

### 3. Casos Especiales

#### Caso 1: Ambos Scores Disponibles (Ideal)

```python
peso_platam = f(meses_como_cliente, cantidad_pagos)
peso_hcpn = 1.0 - peso_platam
hybrid_score = (platam_score × peso_platam) + (hcpn_score × peso_hcpn)
```

**Ejemplo:**
```
Cliente: 12 meses, 15 pagos
Categoría: establecido
Peso base PLATAM: 60%
Ajuste: ninguno (5 ≤ 15 < 20)
Peso final PLATAM: 60%

Scores:
- PLATAM: 800
- HCPN: 750
- Híbrido: (800 × 0.60) + (750 × 0.40) = 780
```

#### Caso 2: Solo PLATAM (Sin HCPN)

```python
peso_platam = 1.0
hybrid_score = platam_score
```

**Ejemplo:**
```
Cliente: 8 meses, 10 pagos, sin HCPN
- PLATAM: 750
- Híbrido: 750
```

**Razón:** Si no hay HCPN, confiamos 100% en nuestro modelo interno.

#### Caso 3: Solo HCPN (Cliente Nuevo Sin Historial)

```python
peso_platam = 0.20  # 20% basado en score de aplicación
peso_hcpn = 0.80
platam_default = 550  # Score conservador
hybrid_score = (platam_default × 0.20) + (hcpn_score × 0.80)
```

**Ejemplo:**
```
Cliente: 0 meses, 0 pagos, con HCPN
- HCPN: 800
- PLATAM default: 550
- Híbrido: (550 × 0.20) + (800 × 0.80) = 750
```

**Razón:** Cliente nuevo, confiamos principalmente en historial externo pero incluimos base conservadora.

#### Caso 4: Sin Datos (Thin File)

```python
hybrid_score = 500  # Score conservador por defecto
```

**Ejemplo:**
```
Cliente: 0 meses, 0 pagos, sin HCPN
- Híbrido: 500
```

**Razón:** Sin información, asignamos score neutral-bajo conservador.

---

## 📊 Casos de Uso Detallados

### Caso A: Cliente Nuevo con Buen HCPN

**Perfil:**
- Tiempo en PLATAM: 1 mes
- Pagos realizados: 2
- PLATAM Score: 650 (limitado por poco historial)
- HCPN Score: 850 (excelente historial externo)

**Cálculo:**
```
Categoría: muy_nuevo
Peso PLATAM base: 30%
Ajuste: -10% (menos de 5 pagos)
Peso PLATAM final: 20%
Peso HCPN final: 80%

Hybrid Score = (650 × 0.20) + (850 × 0.80) = 810
```

**Interpretación:**
El cliente tiene un historial externo excelente de años, pero solo 2 pagos con nosotros. Es justo confiar más en su historial externo comprobado.

---

### Caso B: Cliente Establecido con Excelente Comportamiento

**Perfil:**
- Tiempo en PLATAM: 18 meses
- Pagos realizados: 25
- PLATAM Score: 920 (excelente)
- HCPN Score: 740 (regular, con problemas antiguos)

**Cálculo:**
```
Categoría: establecido
Peso PLATAM base: 60%
Ajuste: +10% (más de 20 pagos)
Peso PLATAM final: 70%
Peso HCPN final: 30%

Hybrid Score = (920 × 0.70) + (740 × 0.30) = 866
```

**Interpretación:**
El cliente ha demostrado excelente comportamiento en 25 pagos durante 18 meses. Su historial reciente interno es más relevante que problemas antiguos externos.

---

### Caso C: Cliente Sin HCPN

**Perfil:**
- Tiempo en PLATAM: 10 meses
- Pagos realizados: 12
- PLATAM Score: 780
- HCPN Score: N/A

**Cálculo:**
```
Sin HCPN disponible
Peso PLATAM: 100%

Hybrid Score = 780
```

**Interpretación:**
No hay información externa, confiamos completamente en nuestro modelo interno que tiene 12 pagos de evidencia.

---

### Caso D: Cliente Nuevo Sin Historial Interno

**Perfil:**
- Tiempo en PLATAM: 0 meses (recién aprobado)
- Pagos realizados: 0
- PLATAM Score: N/A
- HCPN Score: 680

**Cálculo:**
```
Solo HCPN disponible
Peso HCPN: 80%
Peso base aplicación: 20%
Score base: 550

Hybrid Score = (550 × 0.20) + (680 × 0.80) = 654
```

**Interpretación:**
Cliente nuevo, usamos principalmente su historial externo pero mantenemos un piso conservador.

---

## 📈 Resultados y Validación

### Comparación de Sistemas

| Métrica | PLATAM V2.0 | HCPN | **Híbrido** | Mejora |
|---------|-------------|------|-------------|--------|
| **Promedio** | 724.7 | 762.1 | **746.9** | Balanceado |
| **Mediana** | 775.0 | 771.0 | **784.7** | +9.7 vs PLATAM |
| **Desv. Std** | 202.5 | 154.7 | **159.4** | Más estable |
| **Rating A** | 48.6% | 43.8% | **45.4%** | Intermedio |
| **Rating D/F** | 13.2% | 8.5% | **0%** | ✅ Eliminados |

### Distribución por Madurez

| Categoría | Clientes | Peso PLATAM Promedio | Impacto vs V2.0 |
|-----------|----------|---------------------|-----------------|
| Muy Nuevo | 844 (46.0%) | 33.5% | +21.5 pts promedio |
| Nuevo | 100 (5.4%) | 50.4% | +15.2 pts promedio |
| Intermedio | 419 (22.8%) | 54.9% | +24.1 pts promedio |
| Establecido | 470 (25.6%) | 62.9% | +18.7 pts promedio |
| Maduro | 3 (0.2%) | 70.0% | +12.3 pts promedio |

### Impacto del Sistema Híbrido

- ✅ **34.1%** de clientes mejoraron su score (>10 pts)
- ⚖️ **34.6%** se mantuvieron similares (±10 pts)
- ⚠️ **31.3%** empeoraron su score (<-10 pts)

**Conclusión:** El sistema híbrido produce una distribución más balanceada y justa, premiando tanto buen historial externo como excelente comportamiento interno.

---

## 💻 Implementación

### Requisitos

```bash
# Python 3.8+
pip install pandas numpy
```

### Uso Básico

#### 1. Calcular Score Individual

```python
from hybrid_scoring import calculate_hybrid_score

# Cliente con ambos scores
result = calculate_hybrid_score(
    platam_score=800,
    hcpn_score=750,
    months_as_client=12,
    payment_count=15
)

print(f"Score Híbrido: {result['hybrid_score']:.0f}")
print(f"Peso PLATAM: {result['peso_platam']:.1%}")
print(f"Estrategia: {result['estrategia']}")
```

#### 2. Procesar DataFrame Completo

```python
from hybrid_scoring import calculate_hybrid_scores_batch

# Cargar datos
df = pd.read_csv('platam_scores.csv')

# Calcular scores híbridos
df_hybrid = calculate_hybrid_scores_batch(
    df=df,
    platam_col='platam_score',
    hcpn_col='experian_score_normalized',
    months_col='months_as_client',
    payment_count_col='payment_id_count'
)

# Guardar resultados
df_hybrid.to_csv('hybrid_scores.csv', index=False)
```

#### 3. Script Completo

```bash
# Calcular todos los scores híbridos
python scripts/08_calculate_hybrid_scores.py

# Generar visualizaciones comparativas
python scripts/09_visualize_hybrid_comparison.py
```

### Estructura de Archivos

```
Scoring Interno/
├── hybrid_scoring.py                  # Módulo principal
├── scripts/
│   ├── 08_calculate_hybrid_scores.py  # Cálculo batch
│   └── 09_visualize_hybrid_comparison.py  # Visualizaciones
├── data/processed/
│   ├── platam_scores.csv             # Scores V2.0
│   └── hybrid_scores.csv             # Scores híbridos ⭐
└── charts/
    ├── hybrid_01_comparison_distributions.png
    ├── hybrid_02_rating_comparison.png
    ├── hybrid_03_weight_analysis.png
    └── hybrid_04_scatter_comparisons.png
```

---

## 🔧 Mantenimiento

### Ajuste de Configuración

Si necesitas ajustar los pesos, modifica `HybridScoringConfig`:

```python
class HybridScoringConfig:
    # Cambiar umbrales de madurez
    MADUREZ_NUEVO = 3          # Aumentar a 4 si clientes maduran lento
    MADUREZ_INTERMEDIO = 6
    MADUREZ_ESTABLECIDO = 12

    # Cambiar pesos base
    PESOS_PLATAM = {
        'muy_nuevo': 0.30,     # Aumentar a 0.35 para confiar más en PLATAM
        'nuevo': 0.40,
        'intermedio': 0.50,
        'establecido': 0.60,
        'maduro': 0.70         # Aumentar a 0.75 para clientes muy leales
    }

    # Cambiar ajustes por historial
    BONUS_HISTORIAL_AMPLIO = 0.10      # Aumentar a 0.15 para premiar más
    PENALIZACION_HISTORIAL_POCO = -0.10
```

### Validación con Datos de Default

Cuando tengas datos de default reales:

```python
# 1. Agregar columna de default
df['default_flag'] = ...  # 1 = default, 0 = no default

# 2. Calcular AUC y métricas por sistema
from sklearn.metrics import roc_auc_score

auc_platam = roc_auc_score(df['default_flag'], df['platam_score'])
auc_hcpn = roc_auc_score(df['default_flag'], df['hcpn_score'])
auc_hybrid = roc_auc_score(df['default_flag'], df['hybrid_score'])

print(f"AUC PLATAM: {auc_platam:.3f}")
print(f"AUC HCPN: {auc_hcpn:.3f}")
print(f"AUC Híbrido: {auc_hybrid:.3f}")  # Debería ser el mejor

# 3. Ajustar pesos si es necesario
```

### Triggers de Recálculo

Recalcular scores híbridos cuando:

1. ✅ **Cliente hace un nuevo pago** → Actualiza PLATAM → Recalcula Híbrido
2. ✅ **Cliente recibe nuevo crédito** → Actualiza PLATAM → Recalcula Híbrido
3. ✅ **Cliente incumple pago** → Actualiza PLATAM → Recalcula Híbrido
4. ✅ **Actualización mensual de HCPN** → Recalcula Híbrido
5. ✅ **Recálculo batch mensual** → Recalcula todos

### Monitoreo en Producción

Métricas a monitorear:

```python
# 1. Distribución de pesos
peso_promedio = df['peso_platam_usado'].mean()
# Target: 0.45 - 0.55 (balanceado)

# 2. Distribución por categoría
categoria_counts = df['categoria_madurez'].value_counts(normalize=True)
# Target: mayoría en 'establecido' o 'maduro'

# 3. Diferencia promedio vs sistemas individuales
diff_platam = (df['hybrid_score'] - df['platam_score']).mean()
diff_hcpn = (df['hybrid_score'] - df['hcpn_score']).mean()
# Target: <±25 puntos promedio

# 4. Estabilidad del score
df['hybrid_score'].std()
# Target: <180 (menos volátil que V2.0)
```

---

## 🎓 Roadmap: Integración con Machine Learning

### Fase 1 (Meses 0-6): Validación del Híbrido

- ✅ Implementar sistema híbrido
- ✅ Generar visualizaciones y reportes
- 📊 Monitorear performance vs defaults reales
- 📈 Ajustar pesos si es necesario

### Fase 2 (Meses 6-12): Introducción de ML

```
Score Producción = (Híbrido × 70%) + (ML × 30%)
```

- Entrenar modelo ML con features de ambos sistemas
- Validar con datos out-of-sample
- Monitorear performance

### Fase 3 (Meses 12-18): Incremento de ML

```
Score Producción = (Híbrido × 40%) + (ML × 60%)
```

### Fase 4 (Meses 18+): Dominio de ML

```
Score Producción = (Híbrido × 20%) + (ML × 80%)
```

Mantener 20% del híbrido como **guardrail** para casos edge y explainability.

---

## 📚 Referencias

- `hybrid_scoring.py` - Código fuente del módulo
- `scripts/08_calculate_hybrid_scores.py` - Script de cálculo
- `scripts/09_visualize_hybrid_comparison.py` - Visualizaciones
- `MIGRACION_V2_RESULTADOS.md` - Resultados de V2.0
- `PLATAM_SCORING_DOCUMENTATION.md` - Documentación V2.0

---

## ✅ Checklist de Implementación

- [x] Módulo `hybrid_scoring.py` creado y testeado
- [x] Script de cálculo batch implementado
- [x] Scores híbridos calculados para 1,836 clientes
- [x] Visualizaciones comparativas generadas
- [x] Documentación completa creada
- [ ] Validación con datos de default reales
- [ ] Integración en sistema de producción
- [ ] Monitoreo en tiempo real configurado
- [ ] A/B testing vs PLATAM V2.0 puro

---

**Última actualización:** 29 de Diciembre de 2025
**Autor:** PLATAM Data Team
**Versión:** 1.0
