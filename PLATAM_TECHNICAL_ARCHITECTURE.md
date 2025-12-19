# PLATAM ML Scoring - Arquitectura Técnica (CSV-Based)

## Tabla de Contenidos
1. [Diagrama de Arquitectura](#diagrama-de-arquitectura)
2. [Flujo de Datos](#flujo-de-datos)
3. [Data Ingestion Strategy](#data-ingestion-strategy)
4. [Feature Store en BigQuery](#feature-store-en-bigquery)
5. [Vertex AI Pipeline](#vertex-ai-pipeline)
6. [Prediction API](#prediction-api)
7. [Security & Compliance](#security--compliance)
8. [Code Structure](#code-structure)

---

## Diagrama de Arquitectura

### Vista Simplificada (CSV-Based)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                      │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                                                                │         │
│  │  ┌──────────────────────┐         ┌──────────────────────┐    │         │
│  │  │  AWS Aurora MySQL    │         │  Application Server  │    │         │
│  │  │  (Internal Use Only) │         │                      │    │         │
│  │  │                      │         │  - Export CSVs       │    │         │
│  │  │  NOT directly        │────────▶│    diarios/semanales │    │         │
│  │  │  connected to GCP    │         │                      │    │         │
│  │  └──────────────────────┘         └───────────┬──────────┘    │         │
│  │                                               │               │         │
│  │                                               │ Upload CSV    │         │
│  │                                               ▼               │         │
│  │  ┌──────────────────────────────────────────────────┐         │         │
│  │  │  S3 Buckets                                      │         │         │
│  │  │                                                  │         │         │
│  │  │  s3://platam-ml-data/                            │         │         │
│  │  │  ├── clients/                                    │         │         │
│  │  │  │   └── clients_YYYY-MM-DD.csv                  │         │         │
│  │  │  ├── payments/                                   │         │         │
│  │  │  │   └── payments_YYYY-MM-DD.csv                 │         │         │
│  │  │  ├── orders/                                     │         │         │
│  │  │  ├── utilization/                                │         │         │
│  │  │  └── payment_plans/                              │         │         │
│  │  │                                                  │         │         │
│  │  │  s3://platam-hcpn/ (EXISTENTE)                   │         │         │
│  │  │  └── hcpn_{client_id}.json                       │         │         │
│  │  │      - Historial crediticio                      │         │         │
│  │  │      - Clientes rechazados/aprobados             │         │         │
│  │  │      - Data histórica completa                   │         │         │
│  │  └──────────────────────────────────────────────────┘         │         │
│  │                                                                │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                 │                                           │
│                                 │ Cross-cloud transfer                      │
│                                 │ (S3 → GCS sync)                           │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GOOGLE CLOUD                                   │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │  Cloud Storage (GCS)                                           │         │
│  │                                                                │         │
│  │  gs://platam-ml-staging/                                       │         │
│  │  ├── raw/                   ◄──── Sync from S3 (daily)         │         │
│  │  │   ├── clients/                                              │         │
│  │  │   ├── payments/                                             │         │
│  │  │   ├── orders/                                               │         │
│  │  │   ├── utilization/                                          │         │
│  │  │   └── payment_plans/                                        │         │
│  │  │                                                             │         │
│  │  ├── hcpn/                  ◄──── Sync from S3 (weekly)        │         │
│  │  │   └── hcpn_*.json                                           │         │
│  │  │                                                             │         │
│  │  └── processed/             ◄──── After feature engineering    │         │
│  │      └── features_YYYY-MM-DD.parquet                           │         │
│  └────────────┬───────────────────────────────────────────────────┘         │
│               │                                                             │
│               ▼                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │  Cloud Composer (Managed Airflow)                             │         │
│  │                                                                │         │
│  │  DAGs:                                                         │         │
│  │  1. s3_to_gcs_sync           - Sync CSVs from S3 daily        │         │
│  │  2. csv_to_bigquery          - Load CSVs to BigQuery          │         │
│  │  3. calculate_features       - Feature engineering            │         │
│  │  4. train_model_weekly       - Model training                 │         │
│  │  5. batch_predictions        - Daily scoring                  │         │
│  └────────────┬───────────────────────────────────────────────────┘         │
│               │                                                             │
│               ▼                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │  BigQuery                                                      │         │
│  │                                                                │         │
│  │  Datasets:                                                     │         │
│  │  - platam_raw          (staging tables from CSV)              │         │
│  │  - platam_features     (engineered features)                  │         │
│  │  - platam_ml           (training data & predictions)          │         │
│  │  - platam_hcpn         (parsed HCPN data)                     │         │
│  └────────────┬───────────────────────────────────────────────────┘         │
│               │                                                             │
│               ▼                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │  Vertex AI                                                     │         │
│  │  - Training (AutoML + Custom XGBoost)                          │         │
│  │  - Model Registry                                              │         │
│  │  - Prediction Endpoints                                        │         │
│  └────────────┬───────────────────────────────────────────────────┘         │
│               │                                                             │
│               ▼                                                             │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │  Cloud Run - Prediction API                                    │         │
│  │  - Rule-based scoring (código Python actual)                   │         │
│  │  - ML predictions                                              │         │
│  │  - Ensemble & recommendations                                  │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Flujo de Datos

### 1. Data Export (AWS → S3)

**Script de Exportación Diaria** (corre en AWS):

```python
# export_to_s3.py
# Este script corre en tu servidor AWS
import pandas as pd
import mysql.connector
import boto3
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración
AURORA_CONFIG = {
    'host': 'platam-aurora.xxx.us-east-1.rds.amazonaws.com',
    'user': 'export_user',
    'password': 'secure_password',
    'database': 'platam_db'
}

S3_BUCKET = 'platam-ml-data'
S3_CLIENT = boto3.client('s3')

def export_table_to_s3(table_name, date_column=None, lookback_days=1):
    """
    Exporta tabla de Aurora a CSV en S3
    """
    today = datetime.now().date()
    file_date = today.strftime('%Y-%m-%d')

    try:
        # Conectar a Aurora
        conn = mysql.connector.connect(**AURORA_CONFIG)

        # Query con filtro de fecha si aplica
        if date_column:
            query = f"""
                SELECT *
                FROM {table_name}
                WHERE DATE({date_column}) >= CURDATE() - INTERVAL {lookback_days} DAY
            """
        else:
            # Full export para tablas pequeñas (clients, etc)
            query = f"SELECT * FROM {table_name}"

        # Cargar a pandas
        logger.info(f"Exporting {table_name}...")
        df = pd.read_sql(query, conn)

        # Guardar a CSV en memoria
        csv_buffer = df.to_csv(index=False)

        # Upload a S3
        s3_key = f"{table_name}/{table_name}_{file_date}.csv"
        S3_CLIENT.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=csv_buffer,
            ContentType='text/csv'
        )

        logger.info(f"✓ Uploaded {len(df)} rows to s3://{S3_BUCKET}/{s3_key}")

        conn.close()
        return True

    except Exception as e:
        logger.error(f"Error exporting {table_name}: {e}")
        return False

def main():
    """
    Export diario de todas las tablas
    """
    tables_config = [
        # (table_name, date_column, lookback_days)
        ('clients', None, None),  # Full export
        ('payments', 'payment_date', 7),  # Últimos 7 días
        ('orders', 'order_date', 7),
        ('utilization_monthly', 'month', 60),  # Últimos 2 meses
        ('payment_plans', 'updated_at', 30),  # Últimos 30 días
    ]

    results = []
    for config in tables_config:
        success = export_table_to_s3(*config)
        results.append((config[0], success))

    # Summary
    logger.info("\n=== Export Summary ===")
    for table, success in results:
        status = "✓" if success else "✗"
        logger.info(f"{status} {table}")

    # Si todo OK, crear archivo de completion marker
    if all(success for _, success in results):
        marker_key = f"_SUCCESS/{datetime.now().strftime('%Y-%m-%d_%H%M%S')}"
        S3_CLIENT.put_object(
            Bucket=S3_BUCKET,
            Key=marker_key,
            Body=b'Export completed successfully'
        )

if __name__ == '__main__':
    main()
```

**Cron Job en AWS**:
```bash
# Ejecutar diariamente a las 2 AM
0 2 * * * /usr/bin/python3 /opt/platam/export_to_s3.py >> /var/log/platam_export.log 2>&1
```

---

### 2. S3 → GCS Sync (Airflow DAG)

**Opción A: Storage Transfer Service (Recomendado)**

```python
# dags/s3_to_gcs_sync.py
from airflow import DAG
from airflow.providers.google.cloud.transfers.s3_to_gcs import S3ToGCSOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    'owner': 'platam-ml',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['ml-team@platam.com'],
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    's3_to_gcs_sync',
    default_args=default_args,
    description='Sync CSV files from S3 to GCS',
    schedule_interval='0 3 * * *',  # 3 AM daily (después del export)
    start_date=days_ago(1),
    catchup=False,
)

# Sync cada tipo de archivo
tables = ['clients', 'payments', 'orders', 'utilization_monthly', 'payment_plans']

for table in tables:
    sync_task = S3ToGCSOperator(
        task_id=f'sync_{table}',
        bucket='platam-ml-data',
        prefix=f'{table}/',
        dest_gcs='gs://platam-ml-staging/raw/',
        aws_conn_id='aws_s3_platam',
        gcp_conn_id='google_cloud_default',
        replace=False,  # No sobrescribir archivos existentes
        dag=dag,
    )

# Sync HCPN bucket (semanal porque son archivos grandes)
sync_hcpn = S3ToGCSOperator(
    task_id='sync_hcpn',
    bucket='platam-hcpn',
    prefix='',
    dest_gcs='gs://platam-ml-staging/hcpn/',
    aws_conn_id='aws_s3_platam',
    gcp_conn_id='google_cloud_default',
    replace=False,
    dag=dag,
)
```

**Opción B: Manual Sync (más barato pero menos automático)**

```bash
# Ejecutar manualmente cuando sea necesario
gsutil -m rsync -r s3://platam-ml-data/clients/ gs://platam-ml-staging/raw/clients/
gsutil -m rsync -r s3://platam-ml-data/payments/ gs://platam-ml-staging/raw/payments/
# ... etc
```

---

### 3. GCS → BigQuery (Load CSVs)

**Airflow DAG: CSV to BigQuery**

```python
# dags/csv_to_bigquery.py
from airflow import DAG
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyTableOperator
from airflow.providers.google.cloud.transfers.gcs_to_bigquery import GCSToBigQueryOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta

default_args = {
    'owner': 'platam-ml',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'csv_to_bigquery',
    default_args=default_args,
    description='Load CSV files from GCS to BigQuery',
    schedule_interval='0 4 * * *',  # 4 AM (después del sync)
    start_date=days_ago(1),
    catchup=False,
)

# Schema definitions
CLIENTS_SCHEMA = [
    {'name': 'client_id', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'client_name', 'type': 'STRING'},
    {'name': 'tax_id', 'type': 'STRING'},
    {'name': 'registration_date', 'type': 'DATE'},
    {'name': 'industry', 'type': 'STRING'},
    {'name': 'current_credit_limit', 'type': 'FLOAT64'},
    {'name': 'current_outstanding', 'type': 'FLOAT64'},
    {'name': 'account_status', 'type': 'STRING'},
    {'name': 'created_at', 'type': 'TIMESTAMP'},
    {'name': 'updated_at', 'type': 'TIMESTAMP'},
]

PAYMENTS_SCHEMA = [
    {'name': 'payment_id', 'type': 'INT64'},
    {'name': 'client_id', 'type': 'STRING'},
    {'name': 'invoice_id', 'type': 'STRING'},
    {'name': 'payment_date', 'type': 'DATE'},
    {'name': 'due_date', 'type': 'DATE'},
    {'name': 'payment_amount', 'type': 'FLOAT64'},
    {'name': 'days_past_due', 'type': 'INT64'},
    {'name': 'payment_method', 'type': 'STRING'},
    {'name': 'created_at', 'type': 'TIMESTAMP'},
]

# ... definir schemas para otras tablas

def get_latest_csv_file(table_name, **context):
    """
    Encuentra el archivo CSV más reciente en GCS
    """
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket('platam-ml-staging')
    blobs = list(bucket.list_blobs(prefix=f'raw/{table_name}/'))

    if not blobs:
        raise ValueError(f"No CSV files found for {table_name}")

    # Ordenar por fecha de modificación
    latest_blob = sorted(blobs, key=lambda b: b.updated, reverse=True)[0]

    # Push to XCom para usar en siguiente task
    context['task_instance'].xcom_push(key=f'{table_name}_latest_file', value=latest_blob.name)
    return latest_blob.name

# Task 1: Find latest CSV for clients
find_latest_clients = PythonOperator(
    task_id='find_latest_clients',
    python_callable=get_latest_csv_file,
    op_kwargs={'table_name': 'clients'},
    dag=dag,
)

# Task 2: Load to BigQuery (WRITE_TRUNCATE para tabla pequeña)
load_clients = GCSToBigQueryOperator(
    task_id='load_clients_to_bq',
    bucket='platam-ml-staging',
    source_objects=['{{ task_instance.xcom_pull(task_ids="find_latest_clients", key="clients_latest_file") }}'],
    destination_project_dataset_table='platam-ml-prod.platam_raw.clients',
    schema_fields=CLIENTS_SCHEMA,
    write_disposition='WRITE_TRUNCATE',  # Replace completo
    source_format='CSV',
    skip_leading_rows=1,
    create_disposition='CREATE_IF_NEEDED',
    dag=dag,
)

# Para payments (tabla grande), usar WRITE_APPEND con deduplicación
load_payments = GCSToBigQueryOperator(
    task_id='load_payments_to_bq',
    bucket='platam-ml-staging',
    source_objects=['raw/payments/payments_{{ ds }}.csv'],
    destination_project_dataset_table='platam-ml-prod.platam_raw.payments',
    schema_fields=PAYMENTS_SCHEMA,
    write_disposition='WRITE_APPEND',  # Append incremental
    source_format='CSV',
    skip_leading_rows=1,
    dag=dag,
)

# Task 3: Deduplicación (crear tabla cleaned)
deduplicate_payments = BigQueryInsertJobOperator(
    task_id='deduplicate_payments',
    configuration={
        'query': {
            'query': """
                CREATE OR REPLACE TABLE platam_raw.payments_clean AS
                SELECT * EXCEPT(row_num)
                FROM (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY payment_id
                            ORDER BY created_at DESC
                        ) as row_num
                    FROM platam_raw.payments
                )
                WHERE row_num = 1
            """,
            'useLegacySql': False,
        }
    },
    dag=dag,
)

find_latest_clients >> load_clients
load_payments >> deduplicate_payments
```

---

### 4. Parse HCPN Data (JSON → BigQuery)

**Procesar archivos HCPN**:

```python
# dags/parse_hcpn_data.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from google.cloud import storage, bigquery
import json
import pandas as pd
from datetime import datetime

def parse_hcpn_files(**context):
    """
    Lee archivos HCPN de GCS, parsea JSON, carga a BigQuery
    """
    storage_client = storage.Client()
    bq_client = bigquery.Client()

    bucket = storage_client.bucket('platam-ml-staging')
    blobs = bucket.list_blobs(prefix='hcpn/')

    all_records = []

    for blob in blobs:
        if not blob.name.endswith('.json'):
            continue

        # Extraer client_id del nombre del archivo
        # Asumiendo formato: hcpn_{client_id}.json
        client_id = blob.name.split('_')[1].replace('.json', '')

        # Descargar y parsear JSON
        hcpn_data = json.loads(blob.download_as_string())

        # Extraer features relevantes del HCPN
        # (estructura depende de cómo tengan almacenado el HCPN)
        record = {
            'client_id': client_id,
            'hcpn_date': hcpn_data.get('fecha_consulta'),
            'application_status': hcpn_data.get('estado_solicitud'),  # 'rechazado'/'aprobado'
            'rejection_reason': hcpn_data.get('motivo_rechazo'),

            # Scores externos si existen
            'external_credit_score': hcpn_data.get('puntaje_credito'),
            'bureau_defaults': hcpn_data.get('defaults_bureau', 0),

            # Otros campos relevantes
            'total_debt_external': hcpn_data.get('deuda_total_externa'),
            'active_credits': hcpn_data.get('creditos_activos'),

            # Metadata
            'processed_at': datetime.utcnow().isoformat()
        }

        all_records.append(record)

    # Crear DataFrame
    df = pd.DataFrame(all_records)

    # Cargar a BigQuery
    table_id = 'platam-ml-prod.platam_hcpn.client_history'

    job_config = bigquery.LoadJobConfig(
        write_disposition='WRITE_TRUNCATE',
        schema=[
            bigquery.SchemaField('client_id', 'STRING'),
            bigquery.SchemaField('hcpn_date', 'DATE'),
            bigquery.SchemaField('application_status', 'STRING'),
            bigquery.SchemaField('rejection_reason', 'STRING'),
            bigquery.SchemaField('external_credit_score', 'FLOAT64'),
            bigquery.SchemaField('bureau_defaults', 'INT64'),
            bigquery.SchemaField('total_debt_external', 'FLOAT64'),
            bigquery.SchemaField('active_credits', 'INT64'),
            bigquery.SchemaField('processed_at', 'TIMESTAMP'),
        ]
    )

    job = bq_client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for completion

    print(f"✓ Loaded {len(df)} HCPN records to BigQuery")

dag = DAG(
    'parse_hcpn_data',
    schedule_interval='0 5 * * 0',  # Semanal (domingos a las 5 AM)
    start_date=days_ago(1),
    catchup=False,
)

parse_hcpn_task = PythonOperator(
    task_id='parse_hcpn_files',
    python_callable=parse_hcpn_files,
    dag=dag,
)
```

---

## Feature Store en BigQuery

### Estructura de Datos

```sql
-- Dataset: platam_raw (tablas staging desde CSV)
CREATE SCHEMA IF NOT EXISTS platam_raw;

-- Clients (full snapshot)
CREATE TABLE IF NOT EXISTS platam_raw.clients (
    client_id STRING NOT NULL,
    client_name STRING,
    tax_id STRING,
    registration_date DATE,
    industry STRING,
    current_credit_limit FLOAT64,
    current_outstanding FLOAT64,
    account_status STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Payments (incremental con deduplicación)
CREATE TABLE IF NOT EXISTS platam_raw.payments (
    payment_id INT64,
    client_id STRING,
    invoice_id STRING,
    payment_date DATE,
    due_date DATE,
    payment_amount FLOAT64,
    days_past_due INT64,
    payment_method STRING,
    created_at TIMESTAMP
)
PARTITION BY payment_date
CLUSTER BY client_id;

-- Orders
CREATE TABLE IF NOT EXISTS platam_raw.orders (
    order_id INT64,
    client_id STRING,
    order_date DATE,
    order_value FLOAT64,
    order_status STRING,
    created_at TIMESTAMP
)
PARTITION BY order_date
CLUSTER BY client_id;

-- Utilization monthly
CREATE TABLE IF NOT EXISTS platam_raw.utilization_monthly (
    id INT64,
    client_id STRING,
    month DATE,
    avg_outstanding FLOAT64,
    max_outstanding FLOAT64,
    credit_limit FLOAT64,
    utilization_pct FLOAT64
)
PARTITION BY month
CLUSTER BY client_id;

-- Payment plans
CREATE TABLE IF NOT EXISTS platam_raw.payment_plans (
    plan_id INT64,
    client_id STRING,
    plan_start_date DATE,
    plan_end_date DATE,
    original_amount FLOAT64,
    plan_status STRING,
    completion_date DATE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
PARTITION BY plan_start_date
CLUSTER BY client_id, plan_status;

-- HCPN data
CREATE SCHEMA IF NOT EXISTS platam_hcpn;

CREATE TABLE IF NOT EXISTS platam_hcpn.client_history (
    client_id STRING,
    hcpn_date DATE,
    application_status STRING,  -- 'rechazado', 'aprobado'
    rejection_reason STRING,
    external_credit_score FLOAT64,
    bureau_defaults INT64,
    total_debt_external FLOAT64,
    active_credits INT64,
    processed_at TIMESTAMP
)
PARTITION BY hcpn_date
CLUSTER BY client_id;
```

### Feature Engineering (BigQuery SQL)

```sql
-- Dataset: platam_ml
CREATE SCHEMA IF NOT EXISTS platam_ml;

-- Stored Procedure: Calculate Features
-- (Basado en el código Python actual, traducido a SQL)

CREATE OR REPLACE PROCEDURE platam_ml.calculate_client_features(calculation_date DATE)
BEGIN

  -- Temporary table para features de pagos
  CREATE TEMP TABLE payment_features AS
  WITH client_payments AS (
    SELECT
      client_id,
      payment_date,
      due_date,
      days_past_due,
      payment_amount,
      -- Calcular meses desde calculation_date
      DATE_DIFF(calculation_date, payment_date, DAY) / 30.0 AS months_ago
    FROM platam_raw.payments
    WHERE payment_date <= calculation_date
  ),

  payment_scores AS (
    SELECT
      client_id,
      months_ago,
      -- Timeliness score por payment (replicar lógica del código Python)
      CASE
        WHEN days_past_due <= 0 THEN 100
        WHEN days_past_due <= 15 THEN 100 - (days_past_due * 3)
        WHEN days_past_due <= 30 THEN 55 - (days_past_due * 2)
        WHEN days_past_due <= 60 THEN GREATEST(0, 30 - days_past_due)
        ELSE 0
      END AS payment_score,
      -- Recency weight: 1.5^months_ago
      POW(1.5, months_ago) AS recency_weight,
      days_past_due
    FROM client_payments
  ),

  timeliness_calc AS (
    SELECT
      client_id,
      -- Weighted average
      SUM(payment_score * recency_weight) / NULLIF(SUM(recency_weight), 0) AS timeliness_score,
      COUNT(*) AS total_payments
    FROM payment_scores
    GROUP BY client_id
  ),

  pattern_calc AS (
    SELECT
      client_id,
      STDDEV(days_past_due) AS payment_stddev_6mo,
      AVG(days_past_due) AS avg_dpd_6mo,
      COUNT(*) AS payment_count_6mo
    FROM payment_scores
    WHERE months_ago <= 6
    GROUP BY client_id
  ),

  deterioration_calc AS (
    SELECT
      client_id,
      AVG(CASE WHEN months_ago <= 1 THEN days_past_due END) AS dpd_1mo,
      AVG(CASE WHEN months_ago <= 6 THEN days_past_due END) AS dpd_6mo,
      -- Trend delta
      IFNULL(AVG(CASE WHEN months_ago <= 1 THEN days_past_due END), 0) -
      IFNULL(AVG(CASE WHEN months_ago <= 6 THEN days_past_due END), 0) AS dpd_trend_delta
    FROM payment_scores
    GROUP BY client_id
  )

  SELECT
    t.client_id,
    COALESCE(t.timeliness_score, 50) AS payment_timeliness_score,
    COALESCE(p.payment_stddev_6mo, 0) AS payment_stddev_6mo,
    COALESCE(p.avg_dpd_6mo, 0) AS avg_dpd_6mo,
    COALESCE(p.payment_count_6mo, 0) AS payment_count_6mo,
    COALESCE(d.dpd_1mo, 0) AS dpd_1mo,
    COALESCE(d.dpd_6mo, 0) AS dpd_6mo,
    COALESCE(d.dpd_trend_delta, 0) AS dpd_trend_delta,

    -- Pattern score (simplificado)
    GREATEST(0, 100 - (COALESCE(p.payment_stddev_6mo, 0) * 2)) AS payment_pattern_score,

    -- Deterioration velocity score
    LEAST(100, GREATEST(0, 100 - (COALESCE(d.dpd_trend_delta, 0) * 3))) AS deterioration_velocity_score

  FROM timeliness_calc t
  LEFT JOIN pattern_calc p USING(client_id)
  LEFT JOIN deterioration_calc d USING(client_id);

  -- Similar para purchase features, utilization, etc.
  -- (por brevedad omito, pero misma lógica)

  -- Combinar todo en tabla final
  CREATE OR REPLACE TABLE platam_ml.client_features
  PARTITION BY feature_date
  CLUSTER BY client_id
  AS
  SELECT
    calculation_date AS feature_date,
    c.client_id,

    -- Client info
    DATE_DIFF(calculation_date, c.registration_date, DAY) / 30 AS months_as_client,
    c.current_credit_limit,
    c.current_outstanding,
    c.account_status,

    -- Payment features
    pf.*,

    -- Purchase features
    -- ... (calcular similar)

    -- Utilization features
    -- ... (calcular similar)

    -- Payment plan features
    -- ... (calcular similar)

    -- HCPN features (join con tabla HCPN)
    h.external_credit_score,
    h.bureau_defaults,
    h.total_debt_external,

    -- Target variable (para training)
    -- Necesitarás definir qué es un "default" basado en tus reglas de negocio
    FALSE AS default_next_60d,  -- Placeholder, ajustar

    -- Metadata
    CURRENT_TIMESTAMP() AS created_at

  FROM platam_raw.clients c
  LEFT JOIN payment_features pf USING(client_id)
  LEFT JOIN platam_hcpn.client_history h ON c.client_id = h.client_id
  WHERE c.account_status = 'active';  -- Solo clientes activos

END;
```

**Airflow Task para ejecutar feature engineering**:

```python
# En DAG csv_to_bigquery.py, agregar:

calculate_features = BigQueryInsertJobOperator(
    task_id='calculate_features',
    configuration={
        'query': {
            'query': "CALL platam_ml.calculate_client_features(CURRENT_DATE())",
            'useLegacySql': False,
        }
    },
    dag=dag,
)

# Dependencies
[load_clients, deduplicate_payments, ...] >> calculate_features
```

---

## Vertex AI Pipeline

### Training Pipeline (Semanal)

```python
# training/train_model.py
import argparse
from google.cloud import bigquery, aiplatform, storage
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
from datetime import datetime

def load_training_data(project_id, train_end_date):
    """
    Carga datos de training desde BigQuery
    """
    client = bigquery.Client(project=project_id)

    query = f"""
        SELECT *
        FROM `{project_id}.platam_ml.client_features`
        WHERE feature_date BETWEEN
            DATE_SUB('{train_end_date}', INTERVAL 12 MONTH)
            AND '{train_end_date}'
        AND default_next_60d IS NOT NULL  -- Solo registros con target conocido
    """

    df = client.query(query).to_dataframe()
    print(f"Loaded {len(df)} training samples")

    return df

def prepare_features(df):
    """
    Prepara features para training
    """
    # Columnas a excluir
    exclude_cols = [
        'client_id', 'feature_date', 'created_at',
        'default_next_60d',  # Target
        'client_name', 'account_status'  # Metadata
    ]

    feature_cols = [col for col in df.columns if col not in exclude_cols]

    X = df[feature_cols]
    y = df['default_next_60d'].astype(int)

    print(f"Features: {len(feature_cols)}")
    print(f"Target distribution: {y.value_counts().to_dict()}")

    return X, y, feature_cols

def train_xgboost_model(X_train, y_train, X_val, y_val):
    """
    Entrena modelo XGBoost
    """
    # Calculate scale_pos_weight para balancear clases
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'aucpr',
        'max_depth': 5,
        'learning_rate': 0.05,
        'n_estimators': 200,
        'min_child_weight': 10,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'scale_pos_weight': scale_pos_weight,
        'random_state': 42
    }

    model = xgb.XGBClassifier(**params)

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        early_stopping_rounds=20,
        verbose=True
    )

    return model

def evaluate_model(model, X_val, y_val):
    """
    Evalúa modelo en validation set
    """
    y_pred = model.predict(X_val)
    y_pred_proba = model.predict_proba(X_val)[:, 1]

    print("\n=== Model Evaluation ===")
    print(classification_report(y_val, y_pred))

    auc_pr = roc_auc_score(y_val, y_pred_proba, average='weighted')
    print(f"AUC-PR: {auc_pr:.4f}")

    return {
        'auc_pr': auc_pr,
        'evaluation_date': datetime.utcnow().isoformat()
    }

def save_model_to_gcs(model, feature_cols, metrics, bucket_name, model_name):
    """
    Guarda modelo y metadata a GCS
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Guardar modelo
    model_path = f'/tmp/{model_name}.joblib'
    joblib.dump(model, model_path)

    blob = bucket.blob(f'models/{model_name}/{model_name}.joblib')
    blob.upload_from_filename(model_path)

    # Guardar feature names
    feature_path = f'/tmp/{model_name}_features.txt'
    with open(feature_path, 'w') as f:
        f.write('\n'.join(feature_cols))

    blob = bucket.blob(f'models/{model_name}/features.txt')
    blob.upload_from_filename(feature_path)

    # Guardar metrics
    import json
    metrics_path = f'/tmp/{model_name}_metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    blob = bucket.blob(f'models/{model_name}/metrics.json')
    blob.upload_from_filename(metrics_path)

    print(f"✓ Model saved to gs://{bucket_name}/models/{model_name}/")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--train-end-date', default=datetime.now().strftime('%Y-%m-%d'))
    parser.add_argument('--model-bucket', default='platam-ml-models')
    parser.add_argument('--model-name', default=f'platam_scoring_{datetime.now().strftime("%Y%m%d")}')

    args = parser.parse_args()

    # 1. Load data
    print("Loading training data...")
    df = load_training_data(args.project_id, args.train_end_date)

    # 2. Prepare features
    X, y, feature_cols = prepare_features(df)

    # 3. Train/val split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 4. Train model
    print("\nTraining XGBoost model...")
    model = train_xgboost_model(X_train, y_train, X_val, y_val)

    # 5. Evaluate
    metrics = evaluate_model(model, X_val, y_val)

    # 6. Save to GCS
    save_model_to_gcs(model, feature_cols, metrics, args.model_bucket, args.model_name)

    print("\n✓ Training completed successfully!")

if __name__ == '__main__':
    main()
```

**Airflow DAG para training**:

```python
# dags/weekly_model_training.py
from airflow import DAG
from airflow.providers.google.cloud.operators.kubernetes_engine import GKEStartPodOperator
from airflow.utils.dates import days_ago

dag = DAG(
    'weekly_model_training',
    schedule_interval='0 6 * * 0',  # Domingos 6 AM
    start_date=days_ago(1),
    catchup=False,
)

train_model = GKEStartPodOperator(
    task_id='train_xgboost_model',
    name='platam-training-pod',
    namespace='default',
    image='gcr.io/platam-ml-prod/training:latest',
    arguments=[
        '--project-id', 'platam-ml-prod',
        '--train-end-date', '{{ ds }}',
        '--model-bucket', 'platam-ml-models',
        '--model-name', 'platam_scoring_{{ ds_nodash }}',
    ],
    get_logs=True,
    dag=dag,
)
```

---

## Prediction API

**Mismo código que antes, pero ajustado para cargar modelo desde GCS**:

```python
# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import bigquery, storage
import joblib
import pandas as pd
from typing import Dict, List
import logging

app = FastAPI(title="PLATAM Credit Scoring API")
logger = logging.getLogger(__name__)

# Configuration
PROJECT_ID = "platam-ml-prod"
MODEL_BUCKET = "platam-ml-models"
MODEL_NAME = "platam_scoring_latest"  # Apunta a latest version

# Load model al startup
@app.on_event("startup")
async def load_model():
    """
    Descarga modelo de GCS al iniciar API
    """
    global ml_model, feature_names

    storage_client = storage.Client()
    bucket = storage_client.bucket(MODEL_BUCKET)

    # Descargar modelo
    blob = bucket.blob(f'models/{MODEL_NAME}/{MODEL_NAME}.joblib')
    blob.download_to_filename('/tmp/model.joblib')
    ml_model = joblib.load('/tmp/model.joblib')

    # Descargar feature names
    blob = bucket.blob(f'models/{MODEL_NAME}/features.txt')
    feature_content = blob.download_as_string().decode('utf-8')
    feature_names = feature_content.split('\n')

    logger.info(f"✓ Loaded model: {MODEL_NAME} with {len(feature_names)} features")

class ScoringRequest(BaseModel):
    client_id: str
    calculation_date: str = None  # Opcional, default = hoy

class ScoringResponse(BaseModel):
    client_id: str
    calculation_date: str
    ml_probability: float
    ml_score: float
    risk_level: str
    recommended_action: str
    top_risk_factors: List[Dict]

@app.post("/score/predict", response_model=ScoringResponse)
async def predict_score(request: ScoringRequest):
    """
    Predice score para un cliente
    """
    try:
        # 1. Get features from BigQuery
        bq_client = bigquery.Client()

        calc_date = request.calculation_date or 'CURRENT_DATE()'

        query = f"""
            SELECT *
            FROM `{PROJECT_ID}.platam_ml.client_features`
            WHERE client_id = '{request.client_id}'
            AND feature_date = {calc_date}
        """

        df = bq_client.query(query).to_dataframe()

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No features found for client {request.client_id}"
            )

        # 2. Prepare features (solo las que el modelo espera)
        X = df[feature_names]

        # 3. Predict
        ml_probability = ml_model.predict_proba(X)[0][1]  # P(default)
        ml_score = (1 - ml_probability) * 1000  # Scale to 0-1000

        # 4. Determine risk level
        if ml_probability >= 0.7:
            risk_level = "HIGH"
            recommended_action = "FREEZE"
        elif ml_probability >= 0.3:
            risk_level = "MEDIUM"
            recommended_action = "REDUCE_LIMIT"
        else:
            risk_level = "LOW"
            recommended_action = "MAINTAIN"

        # 5. Get top risk factors (feature importance)
        feature_importance = ml_model.feature_importances_
        top_features_idx = feature_importance.argsort()[-5:][::-1]

        top_risk_factors = [
            {
                "feature": feature_names[idx],
                "importance": float(feature_importance[idx]),
                "value": float(X.iloc[0, idx])
            }
            for idx in top_features_idx
        ]

        return ScoringResponse(
            client_id=request.client_id,
            calculation_date=df['feature_date'].iloc[0].strftime('%Y-%m-%d'),
            ml_probability=round(ml_probability, 4),
            ml_score=round(ml_score, 1),
            risk_level=risk_level,
            recommended_action=recommended_action,
            top_risk_factors=top_risk_factors
        )

    except Exception as e:
        logger.error(f"Error predicting for client {request.client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "features": len(feature_names)
    }
```

---

## Security & Compliance

### 1. Data Security

**Encryption**:
- GCS buckets: Default encryption con Google-managed keys
- BigQuery: Encryption at rest automático
- API: TLS 1.3 para todas las comunicaciones

**Access Control**:
```yaml
# IAM roles (principio de least privilege)

# Service account para Airflow
airflow-sa@platam-ml-prod.iam.gserviceaccount.com:
  - roles/storage.objectViewer  # Leer de GCS
  - roles/bigquery.dataEditor   # Escribir a BigQuery

# Service account para API
api-sa@platam-ml-prod.iam.gserviceaccount.com:
  - roles/bigquery.dataViewer   # Solo lectura
  - roles/storage.objectViewer  # Leer modelos

# Usuarios humanos (data scientists)
analyst@platam.com:
  - roles/bigquery.user
  - roles/aiplatform.user
  - No acceso directo a producción
```

### 2. Data Privacy (PII)

**Si hay datos sensibles en los CSVs**:

```python
# Antes de subir a GCS, hash PII fields
import hashlib

def anonymize_csv(df):
    """
    Hash PII fields antes de upload
    """
    pii_fields = ['client_name', 'tax_id', 'contact_email']

    for field in pii_fields:
        if field in df.columns:
            df[field] = df[field].apply(
                lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16]
            )

    return df
```

### 3. Audit Logging

```python
# Configurar Cloud Audit Logs
from google.cloud import logging_v2

def log_prediction(client_id, score, user):
    """
    Log cada predicción para auditoría
    """
    client = logging_v2.Client()
    logger = client.logger('platam-scoring-audit')

    logger.log_struct({
        'event_type': 'prediction',
        'client_id': client_id,
        'score': score,
        'requested_by': user,
        'timestamp': datetime.utcnow().isoformat()
    }, severity='INFO')
```

---

## Code Structure

```
platam-ml-scoring/
├── README.md
├── requirements.txt
│
├── scripts/
│   └── export_to_s3.py          # Corre en AWS, exporta CSVs
│
├── dags/
│   ├── s3_to_gcs_sync.py        # Sync S3 → GCS
│   ├── csv_to_bigquery.py       # Load CSVs → BigQuery
│   ├── parse_hcpn_data.py       # Parse HCPN JSONs
│   ├── calculate_features.py    # Feature engineering
│   └── weekly_training.py       # Model training
│
├── sql/
│   ├── schema_bigquery.sql      # BigQuery schema
│   └── calculate_features.sql   # Feature engineering SQL
│
├── training/
│   ├── Dockerfile
│   ├── train_model.py           # XGBoost training script
│   └── requirements.txt
│
├── api/
│   ├── Dockerfile
│   ├── main.py                  # FastAPI app
│   ├── requirements.txt
│   └── schemas.py
│
├── notebooks/
│   ├── 01_explore_csvs.ipynb
│   ├── 02_hcpn_analysis.ipynb
│   └── 03_model_evaluation.ipynb
│
└── tests/
    ├── test_api.py
    └── test_features.py
```

---

## Próximos Pasos Inmediatos

### Semana 1: Setup Inicial
- [ ] Crear buckets S3 para CSVs (`s3://platam-ml-data`)
- [ ] Implementar script `export_to_s3.py` y probarlo localmente
- [ ] Crear proyecto GCP y habilitar APIs necesarias
- [ ] Crear bucket GCS (`gs://platam-ml-staging`)

### Semana 2: Primera Carga de Datos
- [ ] Exportar snapshot completo de Aurora → S3 CSV
- [ ] Sync manual S3 → GCS (`gsutil rsync`)
- [ ] Cargar CSVs a BigQuery manualmente
- [ ] Validar calidad de datos

### Semana 3: Automatización
- [ ] Configurar Cloud Composer
- [ ] Implementar DAGs de Airflow
- [ ] Probar pipeline end-to-end

### Semana 4: Primer Modelo
- [ ] Implementar feature engineering en SQL
- [ ] Entrenar modelo baseline con AutoML
- [ ] Evaluar performance vs scoring actual

---

## Estimación de Costos (CSV-Based)

### Google Cloud (Mensual)

```
Cloud Storage:
- CSV storage: 50 GB × $0.02/GB = $1/mes
- HCPN storage: 100 GB × $0.02/GB = $2/mes

BigQuery:
- Storage: 200 GB × $0.02/GB = $4/mes
- Queries: 500 GB processed × $5/TB = $2.50/mes

Cloud Composer (Airflow):
- Small environment: $300/mes

Vertex AI:
- AutoML training (semanal): 4 × $50 = $200/mes
- Prediction endpoint: $139/mes

Cloud Run (API):
- With minimal traffic: $20/mes

Data Transfer (S3 → GCS):
- 10 GB/día × 30 × $0.01/GB = $3/mes

TOTAL: ~$670/mes
```

**Con créditos de Google Cloud, esto cubre varios meses de desarrollo.**

---

## Conclusión

Este approach basado en CSVs es:

1. **Más seguro**: No expone Aurora directamente
2. **Más simple**: No requiere VPN ni conectividad compleja
3. **Más barato**: Solo transferencia de archivos
4. **Más flexible**: Fácil auditar y versionar datos

El único trade-off es que no es real-time, pero para scoring crediticio batch diario es suficiente.
