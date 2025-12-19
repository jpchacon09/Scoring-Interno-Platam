# PLATAM Internal Credit Score - Setup

## Estado Actual

✅ **Configuración completa** - Ya puedes empezar a cargar datos

### Archivos creados:

```
Scoring Interno/
├── DATA_UPLOAD_GUIDE.md           # Guía completa de carga de datos
├── PLATAM_SCORING_DOCUMENTATION.md # Documentación del código actual
├── PLATAM_ML_MIGRATION_PLAN.md     # Plan de migración a ML
├── PLATAM_TECHNICAL_ARCHITECTURE.md # Arquitectura técnica
│
├── config/
│   ├── .env                        # ✅ AWS credentials configuradas
│   └── README.md
│
├── data/
│   ├── raw/                        # ← AQUÍ SUBES TUS CSVs
│   │   ├── clients/
│   │   ├── payments/
│   │   ├── orders/
│   │   ├── utilization/
│   │   └── payment_plans/
│   ├── hcpn/                       # HCPN descargados de S3
│   └── processed/                  # Resultados generados
│
├── scripts/
│   ├── download_hcpn.py            # Descargar HCPN de S3
│   ├── validate_data.py            # Validar estructura de CSVs
│   └── calculate_scores.py         # Calcular scoring
│
└── scoring_functions.py            # Funciones del scoring actual
```

---

## Próximos Pasos

### 1. Instalar dependencias

```bash
cd "/Users/jpchacon/Scoring Interno"

# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # En Mac/Linux

# Instalar librerías necesarias
pip install pandas numpy boto3 python-dotenv
```

### 2. Subir tus CSVs

Lee `DATA_UPLOAD_GUIDE.md` para ver la estructura exacta, pero en resumen:

**CSVs obligatorios:**

1. **clients.csv** → `data/raw/clients/clients.csv`
   - Columnas: `client_id, client_name, tax_id, months_as_client, current_credit_limit, current_outstanding`

2. **payments.csv** → `data/raw/payments/payments.csv`
   - Columnas: `client_id, payment_date, due_date, days_past_due, payment_amount`

3. **orders.csv** → `data/raw/orders/orders.csv`
   - Columnas: `client_id, order_date, order_value`

4. **utilization_monthly.csv** → `data/raw/utilization/utilization_monthly.csv`
   - Columnas: `client_id, month, avg_outstanding, credit_limit, utilization_pct`

**CSV opcional:**

5. **payment_plans.csv** → `data/raw/payment_plans/payment_plans.csv` (si no tienes, déjalo vacío)
   - Columnas: `client_id, plan_start_date, plan_end_date, plan_status`

### 3. Descargar HCPN de S3

```bash
python scripts/download_hcpn.py
```

Este script:
- Lee `tax_id` de tu `clients.csv`
- Busca archivos HCPN en S3: `s3://fft-analytics-data-lake/ppay/prod/`
- Los guarda en `data/hcpn/`

**IMPORTANTE**: El script busca el formato de nombre que usen en S3. Si no encuentra archivos, dime qué formato de nombre tienen (ej: `hcpn_{tax_id}.json`, `{tax_id}.json`, etc.) y ajusto el script.

### 4. Validar datos

```bash
python scripts/validate_data.py
```

Este script verifica:
- Columnas correctas en cada CSV
- Formatos de fecha válidos
- Valores numéricos correctos
- Relaciones entre tablas (client_id consistente)

### 5. Calcular scoring

```bash
python scripts/calculate_scores.py
```

Este script:
- Lee todos los CSVs
- Calcula score para cada cliente (usando el código Python actual)
- Genera reporte detallado en `data/processed/scores_YYYYMMDD_HHMMSS.csv`

---

## Estructura de los CSVs

### Ejemplo: clients.csv

```csv
client_id,client_name,tax_id,months_as_client,current_credit_limit,current_outstanding
CLI001,Ferretería El Constructor,123456789,18,100000000,75000000
CLI002,Farmacia San José,987654321,24,125000000,100000000
```

### Ejemplo: payments.csv

```csv
client_id,payment_date,due_date,days_past_due,payment_amount
CLI001,2024-12-01,2024-11-25,6,5000000
CLI001,2024-12-10,2024-12-05,5,3000000
CLI002,2024-12-02,2024-11-30,2,8000000
```

**IMPORTANTE**:
- Fechas en formato `YYYY-MM-DD`
- `days_past_due` puede ser negativo si pagó antes
- Valores monetarios SIN separadores de miles (ej: 5000000, no 5,000,000)

---

## Solución de Problemas

### Error: "No module named 'pandas'"
```bash
pip install pandas numpy boto3 python-dotenv
```

### Error: "AWS credentials not configured"
El archivo `.env` ya está configurado con tus credenciales. Si da error, verifica que esté en `config/.env`

### Error: "No se encontraron CSVs"
Verifica que pusiste los archivos en las carpetas correctas:
- `data/raw/clients/clients.csv`
- `data/raw/payments/payments.csv`
- etc.

### No se descargan HCPNs
Revisa el formato de nombre de archivos en S3. Actualmente busca:
- `hcpn_{tax_id}.json`
- `{tax_id}.json`
- `HCPN_{tax_id}.json`

Si tus archivos tienen otro formato, avísame para ajustar el script.

---

## Contacto

Para preguntas o problemas:
1. Revisa `DATA_UPLOAD_GUIDE.md` para más detalles
2. Ejecuta los scripts y comparte el error exacto que te salga
3. Verifica los logs en cada paso

---

## ¿Qué sigue?

Una vez que tengas scores calculados:

1. **Análisis de resultados**: Revisar distribución de scores, clientes de alto riesgo
2. **Validación con negocio**: Comparar scores con conocimiento del equipo comercial
3. **Ajuste de pesos**: Si es necesario, ajustar los pesos de los componentes
4. **Preparación para ML**: Usar estos datos históricos como baseline para entrenar modelos

Lee `PLATAM_ML_MIGRATION_PLAN.md` para el roadmap completo hacia Machine Learning.
