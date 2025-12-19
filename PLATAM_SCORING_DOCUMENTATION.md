# PLATAM Internal Credit Score - Documentación Técnica

## Tabla de Contenidos
1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema de Scoring](#arquitectura-del-sistema-de-scoring)
3. [Componentes del Score (1000 puntos)](#componentes-del-score-1000-puntos)
4. [Lógica de Negocio](#lógica-de-negocio)
5. [Integración con Datos](#integración-con-datos)
6. [Fortalezas del Sistema Actual](#fortalezas-del-sistema-actual)
7. [Limitaciones del Approach Basado en Reglas](#limitaciones-del-approach-basado-en-reglas)

---

## Resumen Ejecutivo

El **PLATAM Internal Credit Score Calculator** es un sistema de scoring crediticio basado en reglas que evalúa clientes comerciales en una escala de 0-1000 puntos. El sistema combina 5 dimensiones de comportamiento crediticio para determinar:

- **Credit Rating**: De A+ a D/F
- **Credit Limit**: Ajustes automáticos basados en performance
- **Account Status**: Freeze automático para cuentas de alto riesgo

### Escala de Rating
| Score | Rating | Acción |
|-------|--------|--------|
| 900+ | A+ | Sin reducción |
| 850-899 | A | Sin reducción |
| 800-849 | A- | Sin reducción |
| 750-799 | B+ | Sin reducción |
| 700-749 | B | Sin reducción |
| 650-699 | B- | Reducción 15% |
| 600-649 | C+ | Reducción 25% |
| 550-599 | C | Reducción 35% |
| 500-549 | C- | Reducción 50% |
| <500 | D/F | Congelado + Cobranza |

---

## Arquitectura del Sistema de Scoring

### Flujo de Cálculo

```
┌─────────────────┐
│  Client Data    │
│  + Reference    │
│    Date         │
└────────┬────────┘
         │
         ▼
┌────────────────────────────────────────────────────┐
│         Cálculo de 5 Componentes                   │
├────────────────────────────────────────────────────┤
│ 1. Payment Performance      (400 pts)              │
│ 2. Purchase Consistency     (200 pts)              │
│ 3. Utilization Score        (150 pts)              │
│ 4. Payment Plan History     (150 pts)              │
│ 5. Deterioration Velocity   (100 pts)              │
└────────────────┬───────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │  Total Score  │
         │   (0-1000)    │
         └───────┬───────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
  ┌─────────┐      ┌──────────────┐
  │ Rating  │      │ Limit Actions│
  │ (A+ ~ F)│      │ (Reduction)  │
  └─────────┘      └──────────────┘
```

---

## Componentes del Score (1000 puntos)

### 1. Payment Performance (400 puntos máx)

**Propósito**: Evaluar la calidad y consistencia de pagos del cliente.

**Sub-componentes**:

#### A. Timeliness Score (0-100)
- Evalúa qué tan puntual paga el cliente
- Usa **recency weighting**: pagos recientes pesan más (1.5^months_ago)
- Escala de calidad por payment:

```python
DPD (Days Past Due)    Score
─────────────────────  ─────
≤ 0 días               100
1-15 días              100 - (dpd × 3)
16-30 días             55 - (dpd × 2)
31-60 días             max(0, 30 - dpd)
> 60 días              0
```

**Fórmula**:
```
timeliness_score = Σ(payment_score × recency_weight) / Σ(recency_weight)
```

#### B. Pattern Score (0-100)
- Evalúa la **consistencia** del comportamiento de pago
- Solo considera últimos 6 meses
- Detecta "pattern breaks" usando z-score

**Componentes**:
1. **Consistency Score**: `100 - (payment_stddev × 2)`
2. **Pattern Break Penalty**:
   - z ≤ 1.5: 0 puntos penalty
   - z ≤ 2.5: 15 puntos penalty
   - z ≤ 3.5: 35 puntos penalty
   - z > 3.5: 60 puntos penalty

**Pesos Dinámicos por Madurez**:
```python
Months as Client    Timeliness Weight    Pattern Weight
───────────────────────────────────────────────────────
< 6 months          85%                  15%
6-12 months         70%                  30%
> 12 months         50%                  50%
```

**Lógica de Negocio**: Clientes nuevos son evaluados más por puntualidad individual, clientes maduros por consistencia de patrón.

**Referencia**: `# @PLATAM Internal Credit Score Calculat.py:18-124`

---

### 2. Purchase Consistency (200 puntos máx)

**Propósito**: Evaluar la estabilidad del negocio del cliente con PLATAM.

#### A. Frequency Score (120 puntos)
```python
score = min(120, orders_per_month × 12)
```
- Máximo alcanzado con 10 órdenes/mes
- Recompensa frecuencia de compra regular

#### B. Stability Score (80 puntos)
```python
CV = (std_order_value / mean_order_value) × 100
stability_score = max(0, 80 - (CV × 1.5))
```
- Penaliza alta variabilidad en montos de orden
- Coeficiente de Variación (CV) bajo = mayor estabilidad

**Requisito Mínimo**: 6 órdenes para scoring completo, si no default a 100 pts.

**Referencia**: `# @PLATAM Internal Credit Score Calculat.py:127-176`

---

### 3. Utilization Score (150 puntos máx)

**Propósito**: Penalizar **volatilidad** en el uso del crédito, no el uso alto.

**Fórmula**:
```python
score = max(0, 150 - (utilization_stddev × 300))
```

**Lógica de Negocio**:
- Cliente que usa 80% consistentemente → Score alto
- Cliente que varía entre 20% y 95% → Score bajo
- **No penaliza utilización alta, solo inconsistencia**

**Ventana**: Últimos 6 meses de data de utilización

**Requisito Mínimo**: 6 meses de data, si no default a 75 pts.

**Referencia**: `# @PLATAM Internal Credit Score Calculat.py:178-206`

---

### 4. Payment Plan History (150 puntos máx)

**Propósito**: Evaluar historial de reestructuraciones y comportamiento en crisis.

**Sistema Acumulativo con Reset**:
- **Ventana**: Solo considera últimos 12 meses
- **Score Base**: 150 puntos (cliente sin planes = perfecto)
- **Reset**: Si no hay planes en 12 meses, score vuelve a 150

**Eventos y Scoring**:
```python
Event                Points      Impact
─────────────────────────────────────────
Active Plan          -50         Por plan activo
Completed Plan       +30         Recompensa cumplimiento
Defaulted Plan       -100        Penalización severa
```

**Fórmula Final**:
```python
score = 150 + (completed × 30) - (active × 50) - (defaulted × 100)
score = max(0, min(150, score))  # Bounded
```

**Lógica de Negocio**:
- Clientes que completan planes exitosamente pueden recuperar puntos
- Planes activos reducen score temporalmente
- Default en plan = pérdida severa de confianza
- Sin actividad en 12 meses = "clean slate"

**Referencia**: `# @PLATAM Internal Credit Score Calculat.py:209-277`

---

### 5. Deterioration Velocity (100 puntos máx)

**Propósito**: Detectar tendencias de **empeoramiento rápido** en comportamiento de pago.

**Metodología**:
- Compara promedio DPD últimos 1 mes vs últimos 6 meses
- **Trend Delta** = DPD_1mo - DPD_6mo

**Fórmula**:
```python
score = 100 - (trend_delta × 3)
score = max(0, min(100, score))
```

**Interpretación**:
| Trend Delta | Significado | Score Aprox |
|-------------|-------------|-------------|
| -10 días | Mejorando | 130 → 100 |
| 0 días | Estable | 100 |
| +10 días | Deteriorando | 70 |
| +20 días | Deterioro severo | 40 |
| +33+ días | Colapso | 0 |

**Requisitos**:
- Al menos 3 pagos en ventana de 6 meses
- Al menos 1 pago en último mes
- Si no cumple: default a 50 pts

**Referencia**: `# @PLATAM Internal Credit Score Calculat.py:280-345`

---

## Lógica de Negocio

### Credit Limit Actions

El sistema determina ajustes de límite de crédito basado en:
1. **Total Score** → Base Reduction %
2. **Velocity Score** → Multiplier (acelera o modera reducción)

#### Base Reduction por Score
```python
Total Score    Base Reduction
─────────────────────────────
≥ 700          0%
650-699        15%
600-649        25%
550-599        35%
500-549        50%
< 500          100% (Collections)
```

#### Velocity Multiplier
```python
Velocity Score    Multiplier    Effect
──────────────────────────────────────────
≥ 95              0.8×          Modera reducción
85-94             1.0×          Sin cambio
70-84             1.3×          Acelera reducción
50-69             1.7×          Acelera más
30-49             2.5×          Acelera significativamente
< 30              3.0×          Acción urgente
```

**Fórmula Final**:
```python
final_reduction = min(1.0, base_reduction × velocity_multiplier)
new_limit = current_limit × (1 - final_reduction)
```

**Ejemplo**:
- Score = 640 (B-) → Base reduction = 15%
- Velocity = 60 (deteriorando) → Multiplier = 1.7×
- Final reduction = 15% × 1.7 = 25.5%

**Account Freeze**:
```python
is_frozen = (has_active_plan) OR (total_score < 500)
```

**Referencia**: `# @PLATAM Internal Credit Score Calculat.py:387-428`

---

## Integración con Datos

### Inputs Requeridos

#### 1. Client Data (Dict)
```python
{
    'client_id': str,
    'client_name': str,
    'months_as_client': int,
    'current_credit_limit': float,
    'current_outstanding': float
}
```

#### 2. Payments DataFrame
```python
columns = [
    'client_id',
    'payment_date',      # datetime
    'due_date',          # datetime
    'days_past_due',     # int
    'payment_amount'     # float
]
```

#### 3. Orders DataFrame
```python
columns = [
    'client_id',
    'order_date',        # datetime
    'order_value'        # float
]
```

#### 4. Utilization DataFrame
```python
columns = [
    'client_id',
    'month',             # str 'YYYY-MM'
    'avg_outstanding',   # float
    'credit_limit',      # float
    'utilization_pct'    # float (0-1)
]
```

#### 5. Payment Plans DataFrame
```python
columns = [
    'client_id',
    'plan_start_date',   # datetime
    'plan_end_date',     # datetime (nullable)
    'plan_status'        # str: 'active', 'completed', 'defaulted'
]
```

### Output Structure
```python
{
    'client_id': str,
    'client_name': str,
    'calculation_date': datetime,
    'months_as_client': int,

    # Scores
    'payment_performance': float,
    'purchase_consistency': float,
    'utilization': float,
    'payment_plan_history': float,
    'deterioration_velocity': float,
    'total_score': float,
    'credit_rating': str,

    # Details (nested dicts con métricas)
    'payment_performance_details': {...},
    'purchase_consistency_details': {...},
    'utilization_details': {...},
    'payment_plan_details': {...},
    'deterioration_velocity_details': {...},

    # Actions
    'current_credit_limit': float,
    'limit_actions': {
        'base_reduction_pct': float,
        'velocity_multiplier': float,
        'final_reduction_pct': float,
        'new_credit_limit': float,
        'reduction_amount': float,
        'is_frozen': bool
    }
}
```

---

## Fortalezas del Sistema Actual

### 1. **Excelente Entendimiento del Negocio**
- Los pesos y umbrales reflejan conocimiento real del dominio
- Sistema de "maturity weighting" es muy sofisticado
- Considera múltiples dimensiones de riesgo

### 2. **Interpretabilidad Total**
- Cada punto es trazable a una regla específica
- Facilita explicación a clientes y stakeholders
- Auditable y transparente

### 3. **Manejo de Edge Cases**
- Defaults inteligentes para clientes nuevos
- Ventanas temporales bien pensadas
- Manejo de datos insuficientes

### 4. **Detección de Tendencias**
- Velocity score detecta deterioro temprano
- Recency weighting prioriza comportamiento reciente
- Pattern break detection identifica anomalías

### 5. **Código Limpio y Modular**
- Funciones bien separadas por responsabilidad
- Type hints para mejor mantenibilidad
- Documentación clara en docstrings

---

## Limitaciones del Approach Basado en Reglas

### 1. **Rigidez de Umbrales**
- Los umbrales (ej: 15%, 25%, 35%) son fijos
- No se adaptan a cambios en la distribución de clientes
- Difícil optimizar sin rediseñar todo el sistema

### 2. **Interacciones No Capturadas**
- No puede descubrir patrones complejos entre variables
- Ejemplo: "alta utilización + baja variabilidad + pago consistente" podría ser perfil de bajo riesgo específico

### 3. **Pesos Subjetivos**
- ¿Por qué Payment Performance vale 400 y no 350?
- ¿Es óptimo el ratio 85/15 para clientes nuevos?
- Difícil validar si los pesos son óptimos

### 4. **Escalabilidad de Mantenimiento**
- Cada nueva variable requiere nueva función
- Ajustar un componente puede tener efectos no previstos en el total
- Testing manual de escenarios

### 5. **No Aprende de Outcomes**
- Si un cliente con score 720 hace default, el sistema no ajusta automáticamente
- No hay feedback loop entre predicciones y resultados reales

### 6. **Falta de Calibración Probabilística**
- Score de 650 vs 750, ¿cuánto menos riesgo realmente?
- No se traduce directamente a probabilidad de default

---

## Próximos Pasos Recomendados

Este sistema es una **excelente base** para evolucionar hacia Machine Learning porque:

1. Ya tiene las variables correctas identificadas
2. El feature engineering está bien pensado
3. La lógica de negocio es clara y documentada
4. Los datos históricos permitirán validar y mejorar

**Ver**: `PLATAM_ML_MIGRATION_PLAN.md` para roadmap completo de migración a ML.
