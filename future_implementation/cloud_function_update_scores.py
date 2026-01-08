"""
Cloud Function para actualizar scores semanalmente

Desplegar:
gcloud functions deploy update-scores-weekly \
  --runtime python311 \
  --trigger-http \
  --entry-point main \
  --memory 2GB \
  --timeout 540s \
  --region us-central1

Scheduler (ejecutar cada domingo 2am):
gcloud scheduler jobs create http weekly-score-update \
  --schedule="0 2 * * 0" \
  --uri="https://us-central1-platam-analytics.cloudfunctions.net/update-scores-weekly" \
  --http-method=POST \
  --time-zone="America/Bogota"
"""

import pandas as pd
import numpy as np
from google.cloud import storage
from google.cloud import bigquery
from datetime import datetime
import json

# ==============================================================
# CONFIGURACIÓN
# ==============================================================

PROJECT_ID = "platam-analytics"
BUCKET_NAME = "platam-scoring-data"
CSV_FILENAME = "hybrid_scores.csv"

# Tu query SQL (ajusta según tu base de datos)
SQL_QUERY = """
SELECT
    c.cedula,
    c.client_name,
    CURRENT_DATE AS calculation_date,

    -- Score Experian
    e.experian_score,
    e.experian_score / 950.0 * 1000 AS experian_score_normalized,

    -- Historial de pagos
    CASE WHEN COUNT(p.payment_id) > 0 THEN TRUE ELSE FALSE END AS has_payment_history,
    COUNT(DISTINCT DATE_TRUNC('month', p.payment_date)) AS payment_history_months,
    COUNT(p.payment_id) AS payment_id_count,
    AVG(p.days_past_due) AS days_past_due_mean,
    MAX(p.days_past_due) AS days_past_due_max,

    -- Early/Late payments
    SUM(CASE WHEN p.days_past_due < 0 THEN 1 ELSE 0 END)::FLOAT /
        NULLIF(COUNT(p.payment_id), 0) AS pct_early,
    SUM(CASE WHEN p.days_past_due > 0 THEN 1 ELSE 0 END)::FLOAT /
        NULLIF(COUNT(p.payment_id), 0) AS pct_late,

    -- Otros features
    CURRENT_DATE - MAX(p.payment_date) AS days_since_last_payment,
    c.cupo_total,
    c.saldo_actual::FLOAT / NULLIF(c.cupo_total, 0) AS pct_utilization,
    pl.status AS status_plan,
    c.risk_profile,

    -- Antigüedad
    EXTRACT(EPOCH FROM (CURRENT_DATE - c.created_date))/2592000 AS months_as_client,
    COUNT(p.payment_id) AS payment_count,

    -- Planes de pago
    COUNT(CASE WHEN pl.status = 'activo' THEN 1 END) > 0 AS tiene_plan_activo,
    COUNT(CASE WHEN pl.status = 'default' THEN 1 END) > 0 AS tiene_plan_default,
    COUNT(CASE WHEN pl.status = 'pendiente' THEN 1 END) > 0 AS tiene_plan_pendiente,
    COUNT(DISTINCT pl.plan_id) AS num_planes

FROM clientes c
LEFT JOIN pagos p ON c.client_id = p.client_id
LEFT JOIN experian_scores e ON c.cedula = e.cedula
LEFT JOIN planes_pago pl ON c.client_id = pl.client_id

WHERE c.status = 'activo'

GROUP BY
    c.cedula, c.client_name, c.client_id,
    e.experian_score, c.cupo_total, c.saldo_actual,
    c.risk_profile, c.created_date, pl.status

ORDER BY c.cedula
"""

# ==============================================================
# FUNCIONES DE CÁLCULO DE SCORES (copiadas de tu código actual)
# ==============================================================

def calculate_score_payment_performance(row):
    """Calcula score de desempeño de pagos"""
    if pd.isna(row['payment_count']) or row['payment_count'] == 0:
        return 500  # Default para clientes sin historial

    # Base score
    score = 600

    # Bonus por pagos tempranos
    if not pd.isna(row['pct_early']):
        score += row['pct_early'] * 200

    # Penalización por pagos tardíos
    if not pd.isna(row['pct_late']):
        score -= row['pct_late'] * 150

    # Penalización por mora promedio
    if not pd.isna(row['days_past_due_mean']):
        if row['days_past_due_mean'] > 30:
            score -= 200
        elif row['days_past_due_mean'] > 15:
            score -= 100
        elif row['days_past_due_mean'] > 5:
            score -= 50

    return max(300, min(900, score))


def calculate_score_payment_plan(row):
    """Calcula score de planes de pago"""
    score = 600

    if row.get('tiene_plan_default', False):
        score -= 250

    if row.get('tiene_plan_activo', False):
        score += 50

    if row.get('tiene_plan_pendiente', False):
        score -= 50

    num_planes = row.get('num_planes', 0)
    if num_planes > 3:
        score -= 100
    elif num_planes > 1:
        score -= 50

    return max(300, min(900, score))


def calculate_score_deterioration(row):
    """Calcula score de deterioro"""
    score = 600

    days_since = row.get('days_since_last_payment', 0)
    if pd.notna(days_since):
        if days_since > 90:
            score -= 300
        elif days_since > 60:
            score -= 200
        elif days_since > 30:
            score -= 100

    if row.get('payment_count', 0) > 0:
        days_past_due_max = row.get('days_past_due_max', 0)
        if pd.notna(days_past_due_max):
            if days_past_due_max > 60:
                score -= 200
            elif days_past_due_max > 30:
                score -= 100

    return max(300, min(900, score))


def calculate_platam_score(row):
    """Calcula score PLATAM interno"""
    score_perf = calculate_score_payment_performance(row)
    score_plan = calculate_score_payment_plan(row)
    score_deter = calculate_score_deterioration(row)

    # Promedio ponderado
    platam_score = (
        score_perf * 0.50 +
        score_plan * 0.30 +
        score_deter * 0.20
    )

    return platam_score


def calculate_hybrid_score(row):
    """Calcula score híbrido (PLATAM + Experian)"""
    platam_score = row['platam_score']
    experian_score = row['experian_score_normalized']

    # Determinar pesos según madurez del cliente
    months = row.get('months_as_client', 0)
    payment_count = row.get('payment_count', 0)

    if months < 3 or payment_count < 3:
        # Cliente nuevo: confiar más en Experian
        peso_platam = 0.20
        peso_experian = 0.80
    elif months < 6 or payment_count < 10:
        # Cliente en desarrollo: balance
        peso_platam = 0.40
        peso_experian = 0.60
    else:
        # Cliente maduro: confiar más en PLATAM
        peso_platam = 0.70
        peso_experian = 0.30

    hybrid_score = (platam_score * peso_platam) + (experian_score * peso_experian)

    return hybrid_score, peso_platam, peso_experian


def categorize_score(score):
    """Categoriza el score"""
    if score >= 750:
        return "Excelente"
    elif score >= 650:
        return "Bueno"
    elif score >= 550:
        return "Medio"
    elif score >= 450:
        return "Regular"
    else:
        return "Bajo"


# ==============================================================
# FUNCIÓN PRINCIPAL
# ==============================================================

def main(request):
    """
    Cloud Function principal que se ejecuta semanalmente
    """

    try:
        print(f"🚀 Iniciando actualización de scores: {datetime.now()}")

        # 1. OBTENER DATOS DE LA BASE DE DATOS
        print("📊 Consultando base de datos...")
        client = bigquery.Client(project=PROJECT_ID)

        df = client.query(SQL_QUERY).to_dataframe()

        print(f"✅ Datos obtenidos: {len(df)} clientes")

        # 2. CALCULAR SCORES PLATAM
        print("🧮 Calculando scores PLATAM...")

        df['score_payment_performance'] = df.apply(calculate_score_payment_performance, axis=1)
        df['score_payment_plan'] = df.apply(calculate_score_payment_plan, axis=1)
        df['score_deterioration'] = df.apply(calculate_score_deterioration, axis=1)
        df['platam_score'] = df.apply(calculate_platam_score, axis=1)
        df['platam_rating'] = df['platam_score'].apply(categorize_score)

        print("✅ Scores PLATAM calculados")

        # 3. CALCULAR SCORES HÍBRIDOS
        print("🔀 Calculando scores híbridos...")

        hybrid_data = df.apply(calculate_hybrid_score, axis=1, result_type='expand')
        df['hybrid_score'] = hybrid_data[0]
        df['peso_platam_usado'] = hybrid_data[1]
        df['peso_hcpn_usado'] = hybrid_data[2]
        df['hybrid_rating'] = df['hybrid_score'].apply(categorize_score)

        # Categoría de madurez
        df['categoria_madurez'] = df.apply(
            lambda row: 'Nuevo' if row['months_as_client'] < 3
                   else 'Desarrollo' if row['months_as_client'] < 6
                   else 'Maduro',
            axis=1
        )

        # Estrategia
        df['estrategia_hibrido'] = df.apply(
            lambda row: f"PLATAM {int(row['peso_platam_usado']*100)}% - Experian {int(row['peso_hcpn_usado']*100)}%",
            axis=1
        )

        print("✅ Scores híbridos calculados")

        # 4. GUARDAR EN CLOUD STORAGE
        print("💾 Guardando en Cloud Storage...")

        # Convertir a CSV
        csv_buffer = df.to_csv(index=False)

        # Subir a Cloud Storage
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_FILENAME)

        blob.upload_from_string(csv_buffer, content_type='text/csv')

        print(f"✅ CSV guardado en gs://{BUCKET_NAME}/{CSV_FILENAME}")

        # 5. ESTADÍSTICAS
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_clientes': len(df),
            'score_promedio': float(df['hybrid_score'].mean()),
            'score_min': float(df['hybrid_score'].min()),
            'score_max': float(df['hybrid_score'].max()),
            'clientes_nuevos': int((df['months_as_client'] < 3).sum()),
            'clientes_maduros': int((df['months_as_client'] >= 6).sum()),
            'distribucion': {
                'excelente': int((df['hybrid_rating'] == 'Excelente').sum()),
                'bueno': int((df['hybrid_rating'] == 'Bueno').sum()),
                'medio': int((df['hybrid_rating'] == 'Medio').sum()),
                'regular': int((df['hybrid_rating'] == 'Regular').sum()),
                'bajo': int((df['hybrid_rating'] == 'Bajo').sum()),
            }
        }

        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS DE ACTUALIZACIÓN")
        print("="*60)
        print(f"Total clientes: {stats['total_clientes']}")
        print(f"Score promedio: {stats['score_promedio']:.1f}")
        print(f"Rango: {stats['score_min']:.0f} - {stats['score_max']:.0f}")
        print(f"\nDistribución:")
        for categoria, count in stats['distribucion'].items():
            print(f"  {categoria.capitalize()}: {count}")
        print("="*60)

        # 6. TRIGGER PARA REFRESCAR CLOUD RUN (opcional)
        # Puedes agregar lógica para hacer redeploy de Cloud Run aquí
        # o simplemente dejar que Cloud Run recargue el CSV en el próximo cold start

        return {
            'status': 'success',
            'message': f'Scores actualizados: {len(df)} clientes',
            'stats': stats
        }, 200

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)

        return {
            'status': 'error',
            'message': error_msg
        }, 500


# ==============================================================
# PARA TESTING LOCAL
# ==============================================================

if __name__ == "__main__":
    print("🧪 Ejecutando en modo test local...")

    # Simular request
    class MockRequest:
        pass

    result = main(MockRequest())
    print(f"\n✅ Resultado: {result}")
