# Resultados del Merge de Datos BNPL + HCPN

**Fecha:** 19 de diciembre de 2025
**Status:** ✅ Completado exitosamente

## Resumen Ejecutivo

Se completó el proceso de limpieza y merge de todas las tablas de datos (BNPL + HCPN), generando un **dataset maestro unificado** listo para el cálculo del scoring PLATAM.

### Datos Procesados

| Tabla | Registros Originales | Registros Limpios | % Removidos |
|-------|---------------------|-------------------|-------------|
| **Clientes** | 1,836 | 1,836 | 0% |
| **Pagos** | 14,130 | 12,304 | 12.9% |
| **Préstamos** | 8,916 | 8,916 | 0% |
| **Solicitudes Cupo** | 2,704 | 2,704 | 0% |
| **HCPN** | 2,138 | 2,085 | 2.5% |

**Pagos removidos:** 1,826 registros (write-offs y ajustes contables)
**HCPN removidos:** 53 duplicados por cédula (se mantuvo el más reciente)

---

## Dataset Maestro

### Estadísticas Generales

- **Total de clientes:** 1,836
- **Total de columnas:** 62 features
- **Tamaño del archivo:** 0.95 MB
- **Ubicación:** `data/processed/master_dataset.csv`

### Cobertura de Datos

| Tipo de Dato | Clientes | Cobertura |
|--------------|----------|-----------|
| **Con HCPN (Experian)** | 1,559 | 84.9% |
| **Con historial de pagos** | 1,418 | 77.2% |
| **Con solicitud de cupo** | 1,419 | 77.3% |
| **Con datos completos (HCPN + Pagos)** | ~1,200 | ~65% |

---

## Métricas Clave

### 1. Experian Score (HCPN)

- **Promedio:** 704.2 puntos
- **Mediana:** 750.0 puntos
- **Rango:** 0 - 924 puntos
- **Clientes con score:** 1,559 (84.9%)

**Distribución:**
```
Excelente (850+):    ~117 clientes
Muy Bueno (750-850): ~794 clientes  ⬅ Mayoría
Bueno (650-750):     ~501 clientes
Medio (500-650):     ~181 clientes
Bajo (300-500):      ~370 clientes
Muy Bajo (0-300):    ~169 clientes
```

### 2. Comportamiento de Pagos

**Estadísticas generales:**
- **Promedio de pagos por cliente:** 8.5 pagos
- **Total pagos procesados:** 12,304 (después de filtrar ajustes)
- **Total pagado:** $10,058,079,437 COP (~$10B COP)
- **Pagos con due_date calculado:** 12,109 (98.4%)

**Days Past Due (DPD):**
- **Promedio DPD:** -29.7 días (¡pagan anticipado!)
- **Mediana DPD:** -31.0 días
- **Interpretación:** La mayoría de los clientes pagan ANTES de la fecha de vencimiento

**Distribución de puntualidad:**
```
Early (antes de due_date):   10,251 pagos (84.7%) ⬅ Excelente
On time (en due_date):           68 pagos (0.6%)
Late (después de due_date):   1,985 pagos (16.4%)
```

**Distribución de mora:**
```
Al día (on_time):        10,319 pagos (85.2%)
1-30 días tarde:            883 pagos (7.3%)
31-60 días tarde:           174 pagos (1.4%)
61-90 días tarde:           108 pagos (0.9%)
90+ días tarde:             625 pagos (5.2%)
```

### 3. Créditos y Cupos

**Del sistema BNPL (clientes):**
- **Cupo total otorgado:** $6.6B COP
- **Cupo disponible:** Variable por cliente
- **Promedio utilización:** Calculado en master dataset

**De HCPN (historial externo):**
- **Ingreso declarado promedio:** Disponible para 1,559 clientes
- **Créditos vigentes promedio:** Disponible en HCPN
- **Créditos en mora promedio:** Disponible en HCPN

---

## Features Generadas

### A. Datos Demográficos y de Cliente (19 columnas)
- `client_id`, `cedula`, `email`, `phone`
- `first_name`, `last_name`
- `client_type`, `estado`
- `cupo_total`, `cupo_disponible`, `cupo_utilizado`, `pct_utilization`
- `city`, `business_type`
- `collection_score`, `payment_probability_score`, `risk_profile`
- `status_plan`
- `months_as_client` (calculado)

### B. Datos de HCPN - Experian (12 columnas)
- `hcpn_id`, `hcpn_type`
- `experian_score` ⭐ **Score externo 0-924**
- `declared_income`
- `total_monthly_payment` (cuota total de todos los créditos)
- `active_credits`, `closed_credits`, `credits_in_default`
- `negative_history_12m`
- `payment_behavior` (string con historial: C=current, N=late)
- `pct_current_payments` (% de pagos al día en historial)
- `score_decision`
- `hcpn_url` (link al JSON completo en S3)

### C. Métricas de Comportamiento de Pagos (28 columnas)

**Agregados de pagos:**
- `payment_id_count` - Total de pagos
- `payment_amount_sum/mean/median` - Estadísticas de montos
- `days_past_due_mean/median/max/min/std` - Estadísticas de DPD
- `payment_date_min/max` - Rango temporal

**Conteos por categoría:**
- `payments_on_time`, `payments_1-30_days`, `payments_31-60_days`
- `payments_61-90_days`, `payments_90+_days`
- `payments_early`, `payments_late`

**Porcentajes calculados:**
- `pct_on_time` - % de pagos puntuales
- `pct_late` - % de pagos tardíos
- `pct_early` - % de pagos anticipados

**Recency y antigüedad:**
- `days_since_last_payment` - Días desde último pago
- `payment_history_months` - Meses de historial de pagos

### D. Última Solicitud de Cupo (4 columnas)
- `last_cupo_requested_loc` - Último cupo solicitado
- `last_cupo_credit_study_score` - Score del estudio de crédito
- `last_cupo_credit_study_result` - Resultado (aprobado/rechazado)
- `last_cupo_risk_profile` - Perfil de riesgo asignado

### E. Flags de Disponibilidad (3 columnas)
- `has_hcpn` - Tiene datos de Experian
- `has_payment_history` - Tiene historial de pagos
- `has_cupo_request` - Tiene solicitud de cupo

---

## Calidad de Datos

### Completitud por Feature (Top 10 con más missing)

| Feature | % Missing | Comentario |
|---------|-----------|------------|
| `status_plan` | 100% | Campo no utilizado en origen |
| `days_past_due_std` | 38.3% | Normal - clientes con 1 solo pago |
| `payment_id_count` | 22.8% | Clientes sin pagos registrados |
| `has_payment_history` | 22.8% | Mismo grupo anterior |
| `last_cupo_requested_loc` | 22.7% | Clientes sin solicitud de cupo |
| `last_cupo_risk_profile` | 21.4% | No todos los cupos tienen perfil |
| `payment_behavior` | 15.4% | Falta en algunos HCPN |
| `experian_score` | 15.1% | Clientes sin HCPN |
| `has_hcpn` | 15.1% | Mismo grupo anterior |
| `last_cupo_credit_study_score` | 9.3% | Algunos cupos sin score |

### Integridad Referencial

✅ **100% de clientes tienen cédula** (campo clave para merge)
✅ **98.4% de pagos tienen due_date calculado** (merge exitoso con préstamos)
✅ **0 duplicados** en el dataset maestro por cédula

---

## Hallazgos Importantes

### 1. 🎯 Comportamiento de Pago Excelente

**El 84.7% de los pagos se realizan ANTES de la fecha de vencimiento.**

Esto es excepcional y sugiere:
- Clientes responsables y proactivos
- Sistema de recordatorios efectivo
- Posiblemente incentivos por pago temprano
- Bajo riesgo de cartera vencida

**Implicación para scoring:** El algoritmo PLATAM debe **premiar** el pago anticipado, no solo penalizar la mora.

### 2. 📊 Alta Cobertura de Datos

**84.9% de clientes tienen HCPN (Experian score)** - esto es excelente para:
- Validación del score interno vs externo
- Entrenamiento de modelos ML con features externas
- Benchmarking contra bureau de crédito

### 3. 🔍 Segmentación Natural

Los clientes se pueden segmentar claramente en:

**A. Clientes completos (65%):**
- Tienen HCPN + historial de pagos + cupo
- Suficiente data para scoring robusto

**B. Clientes con HCPN pero sin pagos (15%):**
- Recién activados o inactivos
- Usar score Experian + datos de aplicación

**C. Clientes sin HCPN (15%):**
- Depender de comportamiento interno
- Mayor peso a payment performance

### 4. ⚠️ Campos Faltantes No Críticos

Los campos con 100% missing (`status_plan`) se pueden eliminar del dataset.

Los missing en métricas de pagos son **esperados** para clientes sin historial.

---

## Validaciones Realizadas

### ✅ Limpieza de Datos

1. **Normalización de cédulas:** Removidos puntos, guiones, espacios
2. **Conversión de fechas:** De dd/mm/yyyy a datetime estándar
3. **Filtrado de pagos:** Excluidos write-offs y ajustes contables (1,826 removidos)
4. **Deduplicación HCPN:** Removidos 53 duplicados, conservando el más reciente
5. **Cálculo de due_date:** Generado para 98.4% de pagos (loan_date + term_days)

### ✅ Integridad del Merge

1. **Merge por cédula:** Campo único y normalizado
2. **Left joins:** Se preservan todos los clientes (1,836)
3. **Agregaciones:** Métricas calculadas por cliente sin duplicación
4. **Tipos de datos:** Normalizados a string para cedula antes de merge

---

## Archivos Generados

### Procesados (data/processed/)

1. **clientes_clean.csv** (1,836 registros)
   - Clientes normalizados con cédulas únicas

2. **pagos_clean.csv** (12,304 registros)
   - Pagos válidos (sin write-offs ni ajustes)

3. **pagos_enriched.csv** (12,304 registros)
   - Pagos + due_date + days_past_due calculados
   - Categorización de puntualidad

4. **solicitudes_prestamo_clean.csv** (8,916 registros)
   - Préstamos con due_date calculado

5. **solicitudes_cupo_clean.csv** (2,704 registros)
   - Solicitudes de cupo limpias

6. **hcpn_clean.csv** (2,085 registros)
   - HCPN deduplicados con scores parseados

7. **master_dataset.csv** (1,836 registros, 62 columnas) ⭐ **DATASET PRINCIPAL**
   - Merge completo de todas las tablas
   - Listo para cálculo de scoring PLATAM

---

## Próximos Pasos

### 1. ✅ Completado
- [x] Limpieza de datos
- [x] Cálculo de due_date y days_past_due
- [x] Merge de todas las tablas
- [x] Generación de features de comportamiento

### 2. 🔄 En Progreso
- [ ] Calcular PLATAM Score para cada cliente
- [ ] Comparar PLATAM Score vs Experian Score
- [ ] Analizar correlaciones entre features

### 3. 📋 Pendiente
- [ ] Validar business rules de scoring
- [ ] Crear visualizaciones de distribución de scores
- [ ] Preparar datos para training ML en Vertex AI
- [ ] Definir estrategia de segmentación por score

---

## Scripts Utilizados

1. **scripts/01_clean_bnpl_data.py**
   - Limpia y normaliza los 5 CSVs originales
   - Convierte formatos de fecha
   - Filtra registros inválidos

2. **scripts/02_merge_all_data.py**
   - Enriquece pagos con due_dates
   - Agrega métricas por cliente
   - Genera dataset maestro

**Próximo script:**
3. **scripts/03_calculate_platam_score.py**
   - Calculará los 5 componentes del score PLATAM
   - Asignará rating (A+ a F)
   - Comparará con Experian Score

---

## Notas de Seguridad

⚠️ **IMPORTANTE:** Los archivos CSV de exportación (`export-*.csv`) y los datos procesados (`data/processed/*.csv`) contienen **información sensible de clientes reales**.

### Protección Implementada

- ✅ Agregados al `.gitignore`
- ✅ NO se suben al repositorio de GitHub
- ✅ Credenciales AWS redactadas en documentación
- ✅ AWSAccessKeyId limpiados de CSVs antes del commit

### Manejo de Datos

- 📁 **Mantener localmente:** Todos los CSV de exportación
- 🔒 **No compartir:** Datos procesados fuera del equipo
- 🗑️ **Eliminar cuando termine el proyecto:** Datos de prueba

---

**Generado el:** 2025-12-19
**Dataset maestro:** `/Users/jpchacon/Scoring Interno/data/processed/master_dataset.csv`
**Status:** ✅ Listo para scoring
