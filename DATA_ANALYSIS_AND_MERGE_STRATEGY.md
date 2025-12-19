# Análisis de Datos BNPL y Estrategia de Merge con Scoring Interno

## Fecha: 19 de Diciembre de 2025

---

## Tabla de Contenidos
1. [Hallazgos Clave](#hallazgos-clave)
2. [Estructura de Datos Actual](#estructura-de-datos-actual)
3. [Mapeo de IDs y Claves](#mapeo-de-ids-y-claves)
4. [Estrategia de Unión de Datos](#estrategia-de-unión-de-datos)
5. [Transformaciones Requeridas](#transformaciones-requeridas)
6. [Plan de Implementación](#plan-de-implementación)
7. [Arquitectura de Datos Propuesta](#arquitectura-de-datos-propuesta)

---

## Hallazgos Clave

### 1. Volumen de Datos

| Tabla | Registros | Período | Estado |
|-------|-----------|---------|--------|
| **Clientes** | 1,836 | Histórico completo | ✅ Completo |
| **Pagos** | 14,130 | Ene 2023 - Dic 2025 | ✅ Completo |
| **Solicitudes Cupo** | 2,704 | Histórico completo | ✅ Completo |
| **Solicitudes Préstamo** | 8,916 | Histórico completo | ✅ Completo |
| **HCPN (S3)** | ~1,836 | Variable por cliente | ⏳ Por descargar |

**Total de datos históricos**: ~3 años de operación crediticia

### 2. Identificadores y Claves

#### ✅ Campo Único Primario: `cl_doc_number` (Cédula)

**Análisis de unicidad**:
- 1,836 clientes con 1,836 cédulas únicas (100% único)
- **Sin duplicados** en cédula (excelente para merge)
- Presente en TODAS las tablas como campo de relación

#### Relaciones entre Tablas:

```
export-clientes-19-12-2025.csv
├── _ID (internal WordPress ID)
├── cl_doc_number ◄─── CLAVE PRINCIPAL (cédula)
├── cl_clr_id (link a solicitud de cupo)
└── cl_email

export-pagos-19-12-2025.csv
├── p_cl_id (link a cliente por _ID)
├── p_cl_doc_number ◄─── CLAVE PARA JOIN
└── p_l_id (link a préstamo)

export-solicitudes_cupo-19-12-2025.csv
├── clr_cl_id (link a cliente)
└── clr_doc_number ◄─── CLAVE PARA JOIN

export-solicitud_prestamo-19-12-2025.csv
├── lr_cl_id (link a cliente)
└── lr_doc_number ◄─── CLAVE PARA JOIN

HCPN (S3: s3://fft-analytics-data-lake/ppay/prod/)
└── tax_id / doc_number ◄─── CLAVE PARA JOIN
```

### 3. Estados de Clientes

| Estado | Count | % | Implicación para Scoring |
|--------|-------|---|--------------------------|
| **Activo** | 1,308 | 71.2% | Calcular scoring completo |
| **Bloqueado** | 501 | 27.3% | Alto riesgo, revisar causas |
| **Desvinculado** | 27 | 1.5% | Excluir del scoring activo |

### 4. Cobertura de Datos por Cliente

| Métrica | Valor | % del Total |
|---------|-------|-------------|
| Clientes totales | 1,836 | 100% |
| Clientes con pagos | 1,476 | 80.4% |
| Clientes con solicitud de cupo | 1,838 | 100.1%* |
| Clientes con solicitud de préstamo | ~1,500 | ~81.7% |

*Nota: Hay más solicitudes que clientes activos porque incluye rechazados y duplicados.

### 5. Estadísticas Financieras

#### Cupos Otorgados:
- **Total otorgado**: $6,592,070,000 COP
- **Disponible**: $4,895,148,166 COP
- **Promedio por cliente**: $3,590,452 COP
- **Mediana**: $2,000,000 COP

#### Pagos Procesados:
- **Total pagado**: $10,704,064,451 COP
- **Promedio por pago**: $757,542 COP
- **Rango temporal**: Enero 2023 - Diciembre 2025

#### Préstamos Solicitados:
- **Total solicitado**: $12,440,976,701 COP
- **Promedio por préstamo**: $1,395,354 COP

### 6. Perfiles de Riesgo Existentes

La plataforma BNPL ya tiene scoring interno:

| Campo | Cobertura | Descripción |
|-------|-----------|-------------|
| `cl_collection_priority_score` | 99.0% | Score de prioridad de cobranza |
| `cl_risk_profile` | 99.8% | Perfil: Bajo/Moderado/Alto/Muy Alto |
| `cl_payment_probability_score` | 98.8% | Probabilidad de pago |
| `clr_credit_study_score` | Variable | Score del estudio de crédito (0-924) |

**Distribución de Riesgo Actual**:
- Riesgo bajo: 1,005 clientes (54.7%)
- Riesgo moderado: 477 clientes (26.0%)
- Riesgo alto: 341 clientes (18.6%)
- Riesgo muy alto: 243 clientes (13.2%)

---

## Estructura de Datos Actual

### Tabla: `export-clientes-19-12-2025.csv` (1,836 registros)

**Campos clave para Scoring**:

| Campo | Tipo | Descripción | Uso en Scoring |
|-------|------|-------------|----------------|
| `_ID` | INT | ID interno WordPress | Primary Key interno |
| `cl_doc_number` | STRING | Cédula/NIT | **CLAVE PRINCIPAL DE MERGE** |
| `cl_estado` | ENUM | Activo/Bloqueado/Desvinculado | Filtro de elegibilidad |
| `cl_cupo` | DECIMAL | Cupo total otorgado | `current_credit_limit` |
| `cl_cupo_disponible` | DECIMAL | Cupo disponible | Cálculo de utilización |
| `cl_type` | ENUM | Persona/Empresa | Segmentación |
| `cl_first_name` | STRING | Nombre | Identificación |
| `cl_last_name` | STRING | Apellido | Identificación |
| `cl_email` | STRING | Email | Contacto |
| `cl_phone` | STRING | Teléfono | Contacto |
| `cl_city` | STRING | Ciudad | Segmentación geográfica |
| `cl_bus_type` | STRING | Tipo de negocio | Segmentación industria |
| `cl_bus_name` | STRING | Nombre del negocio | Identificación |
| `cl_collection_priority_score` | FLOAT | Score de cobranza existente | **Comparar con nuestro score** |
| `cl_risk_profile` | ENUM | Perfil de riesgo | **Validación** |
| `cl_payment_probability_score` | FLOAT | Score de pago | **Validación** |
| `cct_created` | TIMESTAMP | Fecha de creación | `registration_date` |
| `cct_modified` | TIMESTAMP | Última modificación | Auditoría |

### Tabla: `export-pagos-19-12-2025.csv` (14,130 registros)

**Campos clave para Scoring**:

| Campo | Tipo | Descripción | Uso en Scoring |
|-------|------|-------------|----------------|
| `_ID` | INT | ID del pago | Identificador |
| `p_cl_doc_number` | STRING | Cédula del cliente | **JOIN KEY** |
| `p_l_id` | INT | ID del préstamo | Relación con préstamo |
| `p_payment_date` | DATE | Fecha del pago | **CRÍTICO: payment_date** |
| `p_payment_amount` | DECIMAL | Monto pagado | **payment_amount** |
| `p_type` | STRING | Tipo de pago | Clasificación |
| `p_status` | ENUM | Estado del pago | Filtro |
| `p_balance_principal` | DECIMAL | Balance de principal | Outstanding |
| `p_balance_fee` | DECIMAL | Balance de comisión | Outstanding |
| `p_balance_penalty` | DECIMAL | Balance de penalidad | **DPD indicator** |

**⚠️ PROBLEMA IDENTIFICADO**:
- **NO hay campo `due_date` directo** en la tabla de pagos
- **NO hay campo `days_past_due` directo**
- Necesitamos calcularlo desde los préstamos

### Tabla: `export-solicitud_prestamo-19-12-2025.csv` (8,916 registros)

**Campos clave**:

| Campo | Tipo | Descripción | Uso en Scoring |
|-------|------|-------------|----------------|
| `_ID` | INT | ID de solicitud | Primary Key |
| `lr_doc_number` | STRING | Cédula del cliente | **JOIN KEY** |
| `lr_status` | ENUM | Estado | Filtro (Aprobada) |
| `lr_order_value` | DECIMAL | Monto solicitado | `order_value` |
| `lr_timestamp` | DATE | Fecha solicitud | `order_date` |
| `lr_partner_id` | INT | Partner/Aliado | Segmentación |
| `lr_cp_term` | INT | Plazo en días | **Calcular due_date** |

**💡 SOLUCIÓN para `due_date`**:
```python
due_date = lr_timestamp + timedelta(days=lr_cp_term)
```

### Tabla: `export-solicitudes_cupo-19-12-2025.csv` (2,704 registros)

**Campos clave**:

| Campo | Tipo | Descripción | Uso en Scoring |
|-------|------|-------------|----------------|
| `clr_doc_number` | STRING | Cédula | **JOIN KEY** |
| `clr_status` | ENUM | Estado | Filtro |
| `clr_credit_study_score` | FLOAT | Score (0-924) | **Feature para ML** |
| `clr_credit_study_result` | ENUM | Aprobado/Rechazado | Target histórico |
| `clr_risk_profile` | ENUM | Perfil riesgo | Feature |
| `clr_requested_loc` | DECIMAL | Cupo solicitado | Feature |

---

## Mapeo de IDs y Claves

### Estrategia de Identificación Única

```
CLAVE MAESTRA: cl_doc_number (Cédula)
│
├─ En Clientes: cl_doc_number
├─ En Pagos: p_cl_doc_number
├─ En Solicitudes Cupo: clr_doc_number
├─ En Solicitudes Préstamo: lr_doc_number
└─ En HCPN S3: tax_id (dentro del JSON)
```

### Validación de Integridad

**Test de Unicidad**:
```python
# Validado: ✅
clientes['cl_doc_number'].nunique() == len(clientes)  # True
clientes['cl_doc_number'].duplicated().sum() == 0     # True
```

**Test de Join**:
```python
# Clientes con pagos
clientes_con_pagos = set(clientes['cl_doc_number']) & set(pagos['p_cl_doc_number'])
# Resultado: 1,476 de 1,836 (80.4%)
```

### HCPN - Mapeo con Cédula

**Formato esperado en S3**:
```
s3://fft-analytics-data-lake/ppay/prod/{algo}_{cedula}.json
```

**Dentro del JSON**:
```json
{
  "tax_id": "1006157869",  // ← Debe coincidir con cl_doc_number
  "identification": "1006157869",
  ...
}
```

---

## Estrategia de Unión de Datos

### Fase 1: Preparación de Tablas Base

#### 1.1. Tabla `clients` (desde export-clientes)

```sql
SELECT
    cl_doc_number AS tax_id,           -- CLAVE PRINCIPAL
    _ID AS client_id_original,
    CONCAT(cl_first_name, ' ', cl_last_name) AS client_name,
    cl_doc_number AS tax_id,

    -- Calcular months_as_client
    DATEDIFF(CURRENT_DATE, cct_created) / 30 AS months_as_client,

    -- Credit info
    cl_cupo AS current_credit_limit,
    (cl_cupo - cl_cupo_disponible) AS current_outstanding,
    cl_estado AS account_status,

    -- Metadata
    cl_type,
    cl_city,
    cl_bus_type,
    cl_bus_name,

    -- Existing scores (para comparación)
    cl_collection_priority_score AS existing_collection_score,
    cl_risk_profile AS existing_risk_profile,
    cl_payment_probability_score AS existing_payment_score,

    cct_created AS registration_date,
    cct_modified AS last_modified

FROM export_clientes
WHERE cl_estado IN ('Activo', 'Bloqueado')  -- Excluir desvinculados
```

**Output**: `clients_cleaned.csv` (1,809 registros)

#### 1.2. Tabla `payments` (desde export-pagos + solicitudes_prestamo)

**⚠️ COMPLEJIDAD**: Necesitamos calcular `due_date` y `days_past_due`

```sql
-- Paso 1: Obtener due_date desde préstamos
WITH prestamos AS (
    SELECT
        _ID AS loan_id,
        lr_doc_number AS tax_id,
        lr_timestamp AS loan_date,
        lr_cp_term AS term_days,
        DATE_ADD(STR_TO_DATE(lr_timestamp, '%d/%m/%Y'), INTERVAL lr_cp_term DAY) AS due_date
    FROM export_solicitud_prestamo
    WHERE lr_status = 'Aprobada'
),

-- Paso 2: Join pagos con préstamos
pagos_con_due_date AS (
    SELECT
        p.p_cl_doc_number AS tax_id,
        p.p_payment_date,
        p.p_payment_amount,
        pr.due_date,

        -- Calcular days_past_due
        DATEDIFF(
            STR_TO_DATE(p.p_payment_date, '%d/%m/%Y'),
            pr.due_date
        ) AS days_past_due,

        p.p_l_id AS loan_id,
        p.p_type AS payment_type,
        p.p_status

    FROM export_pagos p
    LEFT JOIN prestamos pr ON p.p_l_id = pr.loan_id
    WHERE p.p_status = 'Registrado'  -- Solo pagos procesados
      AND p.p_payment_amount > 0      -- Excluir ajustes sin monto
)

SELECT
    tax_id,
    STR_TO_DATE(p_payment_date, '%d/%m/%Y') AS payment_date,
    due_date,
    days_past_due,
    p_payment_amount AS payment_amount,
    payment_type,
    loan_id

FROM pagos_con_due_date
ORDER BY tax_id, payment_date
```

**Output**: `payments_cleaned.csv` (~12,000 registros)

**Consideraciones**:
- Algunos pagos no tienen préstamo asociado (ajustes)
- Para esos casos, `due_date` será NULL y `days_past_due` = 0
- Filtrar pagos tipo "Write off" y ajustes internos

#### 1.3. Tabla `orders` (desde solicitudes_prestamo)

```sql
SELECT
    lr_doc_number AS tax_id,
    STR_TO_DATE(lr_timestamp, '%d/%m/%Y') AS order_date,
    lr_order_value AS order_value,
    lr_status AS order_status,
    _ID AS order_id,
    lr_partner_id AS partner_id

FROM export_solicitud_prestamo
WHERE lr_status IN ('Aprobada', 'Aprobación partner pendiente')
  AND lr_order_value > 0

ORDER BY tax_id, order_date
```

**Output**: `orders_cleaned.csv` (~8,000 registros)

#### 1.4. Tabla `utilization_monthly`

**CRÍTICO**: Necesitamos calcular utilización mensual desde los datos históricos

```sql
WITH monthly_balances AS (
    SELECT
        p.p_cl_doc_number AS tax_id,
        DATE_FORMAT(STR_TO_DATE(p.p_payment_date, '%d/%m/%Y'), '%Y-%m-01') AS month,

        -- Calcular outstanding promedio del mes
        AVG(p.p_balance_principal + p.p_balance_fee) AS avg_outstanding,
        MAX(p.p_balance_principal + p.p_balance_fee) AS max_outstanding

    FROM export_pagos p
    WHERE p.p_status = 'Registrado'
    GROUP BY tax_id, month
),

client_limits AS (
    SELECT
        cl_doc_number AS tax_id,
        cl_cupo AS credit_limit
    FROM export_clientes
)

SELECT
    mb.tax_id,
    mb.month,
    mb.avg_outstanding,
    mb.max_outstanding,
    cl.credit_limit,

    -- Calcular utilization_pct
    mb.avg_outstanding / NULLIF(cl.credit_limit, 0) AS utilization_pct

FROM monthly_balances mb
JOIN client_limits cl ON mb.tax_id = cl.tax_id
WHERE mb.avg_outstanding > 0

ORDER BY tax_id, month
```

**Output**: `utilization_monthly_cleaned.csv` (~10,000 registros)

#### 1.5. Tabla `payment_plans` (si existe data)

**NOTA**: No vi campo específico de planes de pago en los CSVs.

**Opciones**:
1. Inferir desde `cl_status_plan` (actualmente vacío)
2. Buscar en solicitudes de cupo rechazadas/reestructuradas
3. Dejar vacío por ahora (score = 150 por default)

### Fase 2: Descarga y Merge con HCPN

#### 2.1. Descargar HCPN desde S3

```python
# Usar script download_hcpn.py adaptado

import boto3
import json
from pathlib import Path

s3_client = boto3.client('s3',
    aws_access_key_id='REDACTED',
    aws_secret_access_key='REDACTED'
)

BUCKET = 'fft-analytics-data-lake'
PREFIX = 'ppay/prod/'

def download_hcpn_for_client(tax_id):
    """
    Busca HCPN en S3 con múltiples formatos
    """
    possible_keys = [
        f'{PREFIX}hcpn_{tax_id}.json',
        f'{PREFIX}{tax_id}.json',
        f'{PREFIX}HCPN_{tax_id}.json',
        f'hcpn/{tax_id}.json',
        f'{tax_id}_hcpn.json',
    ]

    for key in possible_keys:
        try:
            response = s3_client.get_object(Bucket=BUCKET, Key=key)
            hcpn_data = json.loads(response['Body'].read())
            return hcpn_data
        except:
            continue

    return None
```

#### 2.2. Parsear HCPN y Extraer Features

```python
def extract_hcpn_features(hcpn_data):
    """
    Extrae features relevantes del HCPN para scoring
    """
    return {
        'external_credit_score': hcpn_data.get('score_credito'),
        'bureau_defaults': hcpn_data.get('defaults_totales', 0),
        'total_debt_external': hcpn_data.get('deuda_total'),
        'active_credits': hcpn_data.get('creditos_activos', 0),
        'payment_history_score': hcpn_data.get('historial_pagos_score'),
        'hcpn_date': hcpn_data.get('fecha_consulta'),
    }
```

#### 2.3. Merge Final

```python
# Cargar todas las tablas limpias
clients_df = pd.read_csv('data/processed/clients_cleaned.csv')
payments_df = pd.read_csv('data/processed/payments_cleaned.csv')
orders_df = pd.read_csv('data/processed/orders_cleaned.csv')
utilization_df = pd.read_csv('data/processed/utilization_monthly_cleaned.csv')

# Descargar HCPN para cada cliente
hcpn_features = []
for tax_id in clients_df['tax_id']:
    hcpn_data = download_hcpn_for_client(tax_id)
    if hcpn_data:
        features = extract_hcpn_features(hcpn_data)
        features['tax_id'] = tax_id
        hcpn_features.append(features)

hcpn_df = pd.DataFrame(hcpn_features)

# Merge HCPN con clients
clients_with_hcpn = clients_df.merge(hcpn_df, on='tax_id', how='left')
```

---

## Transformaciones Requeridas

### 1. Conversión de Formatos de Fecha

**Problema**: Fechas en formato `dd/mm/yyyy` como STRING

```python
# Convertir en todos los CSVs
df['fecha'] = pd.to_datetime(df['fecha'], format='%d/%m/%Y')
```

### 2. Cálculo de `days_past_due`

**Desde Préstamos**:

```python
# Para cada préstamo
prestamo['due_date'] = prestamo['loan_date'] + timedelta(days=prestamo['term_days'])

# Para cada pago relacionado
pago['days_past_due'] = (pago['payment_date'] - prestamo['due_date']).days
```

**Para pagos sin préstamo** (ajustes):
```python
pago['days_past_due'] = 0  # Asumimos pago a tiempo
```

### 3. Normalización de Estados

```python
# Mapeo de estados
ESTADO_MAP = {
    'Activo': 'active',
    'Bloqueado': 'frozen',
    'Desvinculado': 'inactive'
}

clients_df['account_status'] = clients_df['cl_estado'].map(ESTADO_MAP)
```

### 4. Limpieza de Tipos de Pago

**Filtrar tipos de pago válidos**:

```python
VALID_PAYMENT_TYPES = [
    'Consignación Bancolombia',
    'Transferencia Nequi',
    'Transferencia Bancolombia',
    'Link de pago cuenta Mono',
    'Link de pago payvalida - PSE',
]

payments_df = payments_df[payments_df['p_type'].isin(VALID_PAYMENT_TYPES)]
```

**Excluir ajustes internos**:
```python
EXCLUDE_TYPES = [
    'Write off',
    'Ajuste - Cancelación',
    'Ajuste - Cliente cancela',
]

payments_df = payments_df[~payments_df['p_type'].str.contains('Ajuste')]
```

### 5. Handling de Missing Data

| Campo | % Missing | Estrategia |
|-------|-----------|------------|
| `payment.due_date` | ~15% | Calcular desde préstamo o estimar |
| `client.registration_date` | 0% | ✅ OK |
| `hcpn.external_score` | Variable | Imputar con media o usar flag |

---

## Plan de Implementación

### Paso 1: Limpieza y Transformación (1-2 días)

```bash
# Script 1: Limpiar y transformar CSVs
python scripts/01_clean_bnpl_data.py
```

**Outputs**:
- `data/processed/clients_cleaned.csv`
- `data/processed/payments_cleaned.csv`
- `data/processed/orders_cleaned.csv`
- `data/processed/utilization_monthly_cleaned.csv`

### Paso 2: Descarga de HCPN (medio día)

```bash
# Script 2: Descargar HCPN de S3
python scripts/02_download_and_parse_hcpn.py
```

**Output**:
- `data/hcpn/hcpn_{tax_id}.json` (1,836 archivos)
- `data/processed/hcpn_features.csv` (features parseados)

### Paso 3: Merge y Validación (1 día)

```bash
# Script 3: Merge completo
python scripts/03_merge_all_data.py
```

**Output**:
- `data/processed/master_dataset.csv` (todos los datos unidos)

### Paso 4: Calcular Scoring (medio día)

```bash
# Script 4: Calcular scoring con código actual
python scripts/04_calculate_platam_score.py
```

**Output**:
- `data/processed/scores_bnpl_platam.csv`

### Paso 5: Comparación con Scores Existentes (1 día)

```bash
# Script 5: Comparar nuestro score vs el existente
python scripts/05_compare_scores.py
```

**Análisis**:
- Correlación entre scores
- Discrepancias
- Validación de lógica

---

## Arquitectura de Datos Propuesta

### Estructura de Directorio

```
Scoring Interno/
├── data/
│   ├── raw/                          # CSVs originales (git-ignored)
│   │   ├── export-clientes-19-12-2025.csv
│   │   ├── export-pagos-19-12-2025.csv
│   │   ├── export-solicitudes_cupo-19-12-2025.csv
│   │   └── export-solicitud_prestamo-19-12-2025.csv
│   │
│   ├── processed/                    # Datos limpios
│   │   ├── clients_cleaned.csv
│   │   ├── payments_cleaned.csv
│   │   ├── orders_cleaned.csv
│   │   ├── utilization_monthly_cleaned.csv
│   │   ├── hcpn_features.csv
│   │   └── master_dataset.csv        # ← Dataset completo
│   │
│   ├── hcpn/                          # HCPNs descargados
│   │   └── hcpn_{tax_id}.json
│   │
│   └── scoring/                       # Resultados de scoring
│       ├── scores_bnpl_platam.csv
│       └── score_comparison.csv
│
├── scripts/
│   ├── 01_clean_bnpl_data.py         # Limpieza
│   ├── 02_download_and_parse_hcpn.py # HCPN
│   ├── 03_merge_all_data.py          # Merge
│   ├── 04_calculate_platam_score.py  # Scoring
│   └── 05_compare_scores.py          # Comparación
│
└── notebooks/
    ├── EDA_bnpl_data.ipynb           # Análisis exploratorio
    └── Score_validation.ipynb         # Validación de scores
```

### Flujo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│                    FUENTES DE DATOS                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [export-clientes]  [export-pagos]  [solicitudes]  [S3/HCPN]│
│         │                  │              │            │     │
└─────────┼──────────────────┼──────────────┼────────────┼─────┘
          │                  │              │            │
          ▼                  ▼              ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│               PASO 1: LIMPIEZA Y TRANSFORMACIÓN             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • Normalizar formatos de fecha                             │
│  • Calcular due_date y days_past_due                        │
│  • Filtrar registros inválidos                              │
│  • Mapear estados                                           │
│                                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│              PASO 2: MERGE POR tax_id (cédula)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  clients_cleaned                                            │
│     LEFT JOIN payments_cleaned ON tax_id                    │
│     LEFT JOIN orders_cleaned ON tax_id                      │
│     LEFT JOIN utilization_monthly ON tax_id                 │
│     LEFT JOIN hcpn_features ON tax_id                       │
│                                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│             PASO 3: FEATURE ENGINEERING                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FOR EACH CLIENT:                                           │
│    • Payment Performance (400 pts)                          │
│    • Purchase Consistency (200 pts)                         │
│    • Utilization Score (150 pts)                            │
│    • Payment Plan History (150 pts)                         │
│    • Deterioration Velocity (100 pts)                       │
│                                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                PASO 4: SCORING FINAL                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TOTAL SCORE (0-1000)                                       │
│  CREDIT RATING (A+ ~ F)                                     │
│  RECOMMENDED ACTIONS                                        │
│                                                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│         PASO 5: VALIDACIÓN Y COMPARACIÓN                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • Comparar con cl_collection_priority_score                │
│  • Comparar con cl_risk_profile                             │
│  • Identificar discrepancias                                │
│  • Generar reporte de validación                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Próximos Pasos Inmediatos

### 1. Validar Formato de HCPN en S3 (URGENTE)

**Acción**:
```bash
# Listar archivos en S3 para ver formato real
aws s3 ls s3://fft-analytics-data-lake/ppay/prod/ --recursive | grep -i hcpn | head -20
```

**Necesitamos saber**:
- ¿Qué formato tienen los nombres? (`hcpn_123456.json`, `123456_report.json`, etc.)
- ¿Qué estructura tiene el JSON interno?
- ¿Hay HCPN para todos los 1,836 clientes?

### 2. Crear Scripts de Limpieza

Basándome en el análisis, crear:
- `01_clean_bnpl_data.py` ✅ (próximo paso)
- `02_download_and_parse_hcpn.py` ✅ (adaptar existente)
- `03_merge_all_data.py`
- `04_calculate_platam_score.py`
- `05_compare_scores.py`

### 3. Definir Reglas de Negocio Faltantes

**Preguntas para ti**:
1. ¿Cómo se determina un "default" en tu plataforma?
   - ¿Días de atraso > X?
   - ¿Clientes en estado "Bloqueado"?

2. ¿Qué hacer con clientes sin préstamos pero con cupo?
   - ¿Calcular score solo con cupo y comportamiento?

3. ¿Validar contra qué período?
   - ¿Últimos 6 meses?
   - ¿Todo el histórico?

---

## Resumen Ejecutivo

### ✅ LO QUE TENEMOS

1. **1,836 clientes** con data completa de identificación
2. **14,130 pagos** históricos (3 años de data)
3. **Cédula única** como clave maestra de merge (100% única)
4. **Scoring existente** en la plataforma para comparación
5. **Acceso a HCPN** en S3

### ⚠️ DESAFÍOS IDENTIFICADOS

1. **No hay `due_date` directo** en pagos → Calcular desde préstamos
2. **No hay `days_past_due` directo** → Calcular
3. **Formatos de fecha inconsistentes** → Normalizar
4. **~20% de clientes sin pagos** → Scoring limitado
5. **Formato de HCPN desconocido** → Validar primero

### 🎯 ESTRATEGIA CLARA

1. **Limpiar y normalizar** los 4 CSVs
2. **Calcular campos faltantes** (due_date, dpd)
3. **Merge por cédula** (tax_id)
4. **Descargar y parsear HCPN**
5. **Calcular scoring PLATAM**
6. **Comparar con scoring existente**

### 📊 ENTREGABLES

1. Dataset maestro limpio y merged
2. Scores calculados para 1,836 clientes
3. Comparación con scores existentes
4. Reporte de validación
5. Scripts reproducibles

### ⏱️ ESTIMACIÓN DE TIEMPO

- **Limpieza**: 1-2 días
- **Merge y HCPN**: 1 día
- **Scoring**: medio día
- **Validación**: 1 día
- **Total**: 3-4 días de trabajo

---

## Siguiente Paso

**ACCIÓN INMEDIATA**: Necesito que valides:

1. ¿El formato de archivos HCPN en S3 es correcto según lo documentado?
2. ¿Apruebas la estrategia de usar `cl_doc_number` como clave maestra?
3. ¿Hay alguna regla de negocio específica que deba considerar?

Una vez confirmes, procedo a crear los scripts de limpieza y merge.
