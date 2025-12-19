# Guía de Carga de Datos - PLATAM Scoring

## Estructura de Carpetas

```
/Users/jpchacon/Scoring Interno/
├── data/
│   ├── raw/                    ← AQUÍ SUBES TUS CSVs
│   │   ├── clients/           ← CSV de clientes
│   │   ├── payments/          ← CSV de pagos
│   │   ├── orders/            ← CSV de órdenes
│   │   ├── utilization/       ← CSV de utilización mensual
│   │   ├── payment_plans/     ← CSV de planes de pago
│   │   └── defaults/          ← CSV de defaults (OPCIONAL)
│   │
│   ├── hcpn/                   ← Aquí se descargan los HCPN de S3
│   │   └── (archivos JSON automáticamente)
│   │
│   └── processed/              ← Datos procesados (automático)
│       └── features/
│
├── config/
│   └── .env                    ← Configurar AWS credentials
│
└── scripts/                    ← Scripts para procesar
```

---

## CSVs Necesarios (según el código Python)

### 1. **clients.csv** (OBLIGATORIO)
**Ubicación**: `data/raw/clients/clients.csv`

**Columnas requeridas**:
```
client_id,client_name,tax_id,months_as_client,current_credit_limit,current_outstanding
```

**Descripción**:
- `client_id`: ID único del cliente (ej: "FERR001", "FARM001")
- `client_name`: Nombre del cliente
- `tax_id`: NIT o documento de identidad (para match con HCPN)
- `months_as_client`: Meses como cliente (número entero)
- `current_credit_limit`: Límite de crédito actual (en pesos)
- `current_outstanding`: Saldo pendiente actual (en pesos)

**IMPORTANTE**: El `tax_id` se usa para hacer match con los archivos HCPN del bucket S3.

---

### 2. **payments.csv** (OBLIGATORIO)
**Ubicación**: `data/raw/payments/payments.csv`

**Columnas requeridas**:
```
client_id,payment_date,due_date,days_past_due,payment_amount
```

**Descripción**:
- `client_id`: Debe coincidir con clients.csv
- `payment_date`: Fecha del pago (YYYY-MM-DD)
- `due_date`: Fecha de vencimiento (YYYY-MM-DD)
- `days_past_due`: Días de atraso (número entero, puede ser 0 o negativo si pagó antes)
- `payment_amount`: Monto del pago (en pesos)

**Mínimo requerido**: Al menos 3 pagos por cliente para cálculo de score

---

### 3. **orders.csv** (OBLIGATORIO)
**Ubicación**: `data/raw/orders/orders.csv`

**Columnas requeridas**:
```
client_id,order_date,order_value
```

**Descripción**:
- `client_id`: Debe coincidir con clients.csv
- `order_date`: Fecha de la orden (YYYY-MM-DD)
- `order_value`: Valor de la orden (en pesos)

**Mínimo requerido**: Al menos 6 órdenes por cliente para cálculo de consistencia

---

### 4. **utilization_monthly.csv** (OBLIGATORIO)
**Ubicación**: `data/raw/utilization/utilization_monthly.csv`

**Columnas requeridas**:
```
client_id,month,avg_outstanding,credit_limit,utilization_pct
```

**Descripción**:
- `client_id`: Debe coincidir con clients.csv
- `month`: Mes (formato YYYY-MM-01, siempre día 01)
- `avg_outstanding`: Promedio de saldo en el mes (en pesos)
- `credit_limit`: Límite de crédito en ese mes (en pesos)
- `utilization_pct`: Porcentaje de utilización (0.0 a 1.0, ej: 0.75 = 75%)

**Mínimo requerido**: Últimos 6 meses por cliente

---

### 5. **payment_plans.csv** (OPCIONAL)
**Ubicación**: `data/raw/payment_plans/payment_plans.csv`

**Columnas requeridas**:
```
client_id,plan_start_date,plan_end_date,plan_status
```

**Descripción**:
- `client_id`: Debe coincidir con clients.csv
- `plan_start_date`: Fecha inicio del plan (YYYY-MM-DD)
- `plan_end_date`: Fecha fin del plan (YYYY-MM-DD o vacío si activo)
- `plan_status`: Estado del plan ("active", "completed", "defaulted")

**Si no hay planes**: Dejar la carpeta vacía, el script asignará 150 puntos por default.

---

### 6. **defaults.csv** (OPCIONAL - Para ML futuro)
**Ubicación**: `data/raw/defaults/defaults.csv`

**Columnas requeridas**:
```
client_id,event_date,event_type,severity
```

**Descripción**:
- `client_id`: Debe coincidir con clients.csv
- `event_date`: Fecha del evento (YYYY-MM-DD)
- `event_type`: Tipo ("late_payment", "plan_default", "collections")
- `severity`: Severidad ("minor", "moderate", "severe")

**Uso**: Para entrenar modelos ML que predigan defaults. No necesario para scoring actual.

---

## HCPN (Historial Crediticio)

### Formato esperado en S3

Los archivos HCPN deben estar en tu bucket S3 con formato:
```
s3://platam-hcpn/hcpn_{tax_id}.json
```

**Ejemplo**: Si un cliente tiene `tax_id = "123456789"`, el script buscará:
```
s3://platam-hcpn/hcpn_123456789.json
```

### Estructura JSON esperada (ajustar según tu formato)

```json
{
  "tax_id": "123456789",
  "fecha_consulta": "2024-12-01",
  "estado_solicitud": "aprobado",
  "puntaje_credito": 750,
  "defaults_bureau": 0,
  "deuda_total_externa": 15000000,
  "creditos_activos": 2,
  "historial_pagos": [...]
}
```

**NOTA**: El script de descarga es flexible y se puede adaptar a tu estructura HCPN real.

---

## Proceso de Carga

### Paso 1: Configurar AWS Credentials

```bash
cd "/Users/jpchacon/Scoring Interno"
cp config/.env.template config/.env
# Editar config/.env con tus credentials de AWS
```

### Paso 2: Subir tus CSVs

Copia tus archivos CSV a las carpetas correspondientes:

```bash
# Ejemplo (ajustar con tus archivos reales)
cp ~/Downloads/clientes_platam.csv data/raw/clients/clients.csv
cp ~/Downloads/pagos_platam.csv data/raw/payments/payments.csv
cp ~/Downloads/ordenes_platam.csv data/raw/orders/orders.csv
cp ~/Downloads/utilizacion_platam.csv data/raw/utilization/utilization_monthly.csv
# ... etc
```

### Paso 3: Descargar HCPN de S3

```bash
python scripts/download_hcpn.py
```

Este script:
1. Lee `tax_id` de clients.csv
2. Descarga `hcpn_{tax_id}.json` de S3
3. Guarda en `data/hcpn/`

### Paso 4: Validar datos

```bash
python scripts/validate_data.py
```

Este script verifica:
- Todos los CSVs tienen las columnas requeridas
- Los `client_id` son consistentes entre archivos
- No hay datos faltantes críticos
- Fechas tienen formato correcto

### Paso 5: Calcular scoring

```bash
python scripts/calculate_scores.py
```

Este script:
1. Lee todos los CSVs
2. Calcula score para cada cliente (usando código Python actual)
3. Genera reporte con resultados
4. Guarda en `data/processed/scores_YYYY-MM-DD.csv`

---

## Formatos de Fecha

**IMPORTANTE**: Todas las fechas deben estar en formato ISO:
- Formato: `YYYY-MM-DD`
- Ejemplo: `2024-12-19`
- NO usar: `19/12/2024` o `12-19-2024`

Si tus CSVs tienen otro formato, el script de validación puede convertirlos automáticamente.

---

## Tamaño Recomendado de Datos

Para empezar:
- **Mínimo**: 10-20 clientes con datos completos
- **Ideal**: 50-100 clientes con historial de 6-12 meses
- **Para ML**: 200+ clientes con al menos 20-30 defaults conocidos

---

## Preguntas Frecuentes

### ¿Qué pasa si no tengo payment_plans.csv?
No hay problema. El script asignará automáticamente 150 puntos (score máximo) a todos los clientes en ese componente.

### ¿Puedo tener múltiples archivos CSV en una carpeta?
Sí, el script leerá todos los `.csv` en cada carpeta y los concatenará automáticamente.

### ¿Cómo manejo datos incrementales?
Puedes ir agregando archivos con fechas:
- `payments_2024-11.csv`
- `payments_2024-12.csv`

El script los procesará todos juntos.

### ¿Qué pasa si un cliente no tiene HCPN en S3?
El script lo reportará en el log pero continuará el procesamiento. Ese cliente no tendrá features de HCPN, pero el scoring funcionará igual.

---

## Próximo Paso

Una vez que tengas tus CSVs listos en las carpetas, ejecuta:

```bash
python scripts/validate_data.py
```

Y me avisas qué errores te sale para ajustar.
