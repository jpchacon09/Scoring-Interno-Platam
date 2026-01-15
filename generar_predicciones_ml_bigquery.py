#!/usr/bin/env python3
"""
Script para generar predicciones ML para BigQuery/Metabase
Output: CSV separado SOLO con predicciones ML (sin scoring interno)

Este CSV se puede hacer JOIN con tus datos existentes en BigQuery:
SELECT * FROM scoring.clientes c
LEFT JOIN scoring.predicciones_ml p ON c.cedula = p.cedula
"""

import pandas as pd
import numpy as np
from google.cloud import aiplatform
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================
# CONFIGURACIÓN
# ============================================
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"  # Modelo v2.2
MODEL_VERSION = "v2.2"

# Paths
CSV_SOURCE = "SCORES_V2_ANALISIS_COMPLETO.csv"  # Solo para leer features
CSV_OUTPUT = "PREDICCIONES_ML_V2.2.csv"  # Output separado

# Features del modelo v2.2 (22 features)
FEATURE_ORDER = [
    'platam_score', 'experian_score_normalized',
    'score_payment_performance', 'score_payment_plan', 'score_deterioration',
    'payment_count', 'months_as_client',
    'pct_early', 'pct_late',
    'peso_platam_usado', 'peso_hcpn_usado',
    'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes',
    'genero_encoded', 'edad', 'ciudad_encoded',
    'cuota_mensual', 'creditos_vigentes', 'creditos_mora', 'hist_neg_12m'
]

print("="*80)
print("🤖 GENERANDO PREDICCIONES ML PARA BIGQUERY/METABASE")
print("="*80)
print(f"\n📌 Modelo: Vertex AI v2.2")
print(f"📌 Endpoint: {ENDPOINT_ID}")
print(f"📌 Output: {CSV_OUTPUT}")
print("="*80)

# ============================================
# 1. CARGAR DATOS FUENTE
# ============================================
print("\n📂 Cargando datos fuente...")
df_source = pd.read_csv(CSV_SOURCE)
print(f"✅ Cargados {len(df_source)} clientes")

# ============================================
# 2. CONECTAR CON VERTEX AI
# ============================================
print("\n🌐 Conectando con Vertex AI...")
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)
print(f"✅ Conectado al endpoint v2.2")

# ============================================
# 3. FUNCIONES AUXILIARES
# ============================================

def prepare_instance(row):
    """Prepara instancia para predicción"""
    instance = []
    for feature in FEATURE_ORDER:
        value = row.get(feature, 0)
        if pd.isna(value) or value is None:
            if feature == 'edad':
                value = 35
            elif feature in ['genero_encoded', 'ciudad_encoded']:
                value = 0
            else:
                value = 0
        if isinstance(value, bool):
            value = int(value)
        instance.append(float(value))
    return instance

def classify_risk_level(prob_default):
    """Clasifica nivel de riesgo"""
    if prob_default < 0.10:
        return "Muy Bajo"
    elif prob_default < 0.20:
        return "Bajo"
    elif prob_default < 0.40:
        return "Medio"
    elif prob_default < 0.60:
        return "Alto"
    else:
        return "Muy Alto"

def get_attention_level(prob_default):
    """Determina nivel de atención requerido"""
    if prob_default >= 0.60:
        return "Alerta crítica"
    elif prob_default >= 0.40:
        return "Seguimiento cercano"
    elif prob_default >= 0.20:
        return "Atención moderada"
    else:
        return "Monitoreo normal"

def calculate_risk_score(prob_default):
    """Convierte probabilidad a score 0-1000 (para gráficas)"""
    return int(prob_default * 1000)

def requires_follow_up(prob_default):
    """Determina si requiere seguimiento"""
    return prob_default >= 0.20

# ============================================
# 4. GENERAR PREDICCIONES
# ============================================
print("\n🤖 Generando predicciones ML...")
print("⏳ Esto puede tardar varios minutos...")

predictions_data = []

for idx, row in df_source.iterrows():
    if idx % 100 == 0:
        print(f"  📊 Procesados {idx}/{len(df_source)} clientes ({idx/len(df_source)*100:.1f}%)")

    try:
        # Preparar instancia
        instance = prepare_instance(row)

        # Llamar a Vertex AI
        pred = endpoint.predict(instances=[instance])

        # Extraer probabilidades
        prob_no_default = pred.predictions[0][0]
        prob_default = pred.predictions[0][1]

        # Calcular métricas derivadas
        risk_level = classify_risk_level(prob_default)
        attention_level = get_attention_level(prob_default)
        risk_score = calculate_risk_score(prob_default)
        follow_up = requires_follow_up(prob_default)

        # Agregar a resultados
        predictions_data.append({
            'cedula': str(row['cedula']),
            'prob_default': round(prob_default, 4),
            'prob_no_default': round(prob_no_default, 4),
            'prob_default_pct': round(prob_default * 100, 2),  # Para gráficas
            'risk_level': risk_level,
            'risk_score': risk_score,  # 0-1000 para gráficas
            'attention_level': attention_level,
            'requires_follow_up': follow_up,
            'prediction_date': datetime.now().isoformat(),
            'model_version': MODEL_VERSION
        })

    except Exception as e:
        print(f"  ⚠️ Error en cliente {row['cedula']}: {e}")
        # Agregar con valores null en caso de error
        predictions_data.append({
            'cedula': str(row['cedula']),
            'prob_default': None,
            'prob_no_default': None,
            'prob_default_pct': None,
            'risk_level': 'Error',
            'risk_score': None,
            'attention_level': 'Error',
            'requires_follow_up': None,
            'prediction_date': datetime.now().isoformat(),
            'model_version': MODEL_VERSION
        })

print(f"✅ Predicciones generadas para {len(predictions_data)} clientes")

# ============================================
# 5. CREAR DATAFRAME Y GUARDAR
# ============================================
print("\n💾 Creando CSV para BigQuery...")

df_predictions = pd.DataFrame(predictions_data)

# Ordenar por riesgo (mayor a menor)
df_predictions = df_predictions.sort_values('prob_default', ascending=False, na_position='last')

# Guardar CSV
df_predictions.to_csv(CSV_OUTPUT, index=False)
print(f"✅ Guardado: {CSV_OUTPUT}")

# ============================================
# 6. ESTADÍSTICAS Y RESUMEN
# ============================================
print("\n" + "="*80)
print("📊 ESTADÍSTICAS DE PREDICCIONES ML")
print("="*80)

# Filtrar errores para estadísticas
df_valid = df_predictions[df_predictions['prob_default'].notna()]

print(f"\n🎯 Total clientes procesados: {len(df_predictions):,}")
print(f"✅ Predicciones exitosas: {len(df_valid):,}")
print(f"❌ Errores: {len(df_predictions) - len(df_valid):,}")

if len(df_valid) > 0:
    print(f"\n📈 Probabilidad de Default:")
    print(f"   • Promedio: {df_valid['prob_default'].mean():.2%}")
    print(f"   • Mediana: {df_valid['prob_default'].median():.2%}")
    print(f"   • Mínimo: {df_valid['prob_default'].min():.2%}")
    print(f"   • Máximo: {df_valid['prob_default'].max():.2%}")

    print(f"\n🎯 Distribución por Nivel de Riesgo:")
    risk_dist = df_valid['risk_level'].value_counts()
    for level in ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]:
        count = risk_dist.get(level, 0)
        pct = count / len(df_valid) * 100
        print(f"   • {level:12s}: {count:4d} clientes ({pct:5.1f}%)")

    print(f"\n⚠️ Clientes que Requieren Seguimiento:")
    follow_up_count = df_valid['requires_follow_up'].sum()
    follow_up_pct = follow_up_count / len(df_valid) * 100
    print(f"   • Sí: {follow_up_count:,} clientes ({follow_up_pct:.1f}%)")
    print(f"   • No: {len(df_valid) - follow_up_count:,} clientes ({100-follow_up_pct:.1f}%)")

# ============================================
# 7. PREVIEW DEL CSV
# ============================================
print("\n" + "="*80)
print("👀 PREVIEW DEL CSV (Primeros 5 registros)")
print("="*80)
print(df_predictions[['cedula', 'prob_default_pct', 'risk_level', 'attention_level']].head(5).to_string(index=False))

# ============================================
# 8. INSTRUCCIONES PARA BIGQUERY
# ============================================
print("\n" + "="*80)
print("📝 SIGUIENTE PASO: SUBIR A BIGQUERY")
print("="*80)
print(f"""
1️⃣ Crear dataset (si no existe):
   bq mk --dataset platam-analytics:scoring_ml

2️⃣ Subir CSV a BigQuery:
   bq load \\
     --source_format=CSV \\
     --autodetect \\
     --replace \\
     platam-analytics:scoring_ml.predicciones_v22 \\
     {CSV_OUTPUT}

3️⃣ Verificar en BigQuery:
   bq query "SELECT COUNT(*) as total FROM platam-analytics:scoring_ml.predicciones_v22"

4️⃣ En Metabase, usar query SQL:
   SELECT * FROM `platam-analytics.scoring_ml.predicciones_v22`
   WHERE risk_level = 'Alto'

5️⃣ JOIN con tus datos existentes:
   SELECT
     c.*,
     p.prob_default_pct,
     p.risk_level,
     p.attention_level
   FROM `platam-analytics.scoring.clientes` c
   LEFT JOIN `platam-analytics.scoring_ml.predicciones_v22` p
     ON c.cedula = p.cedula
""")

print("\n" + "="*80)
print("✅ PROCESO COMPLETADO")
print("="*80)
print(f"\n📁 Archivo generado: {CSV_OUTPUT}")
print(f"📊 Total registros: {len(df_predictions):,}")
print(f"🗓️  Fecha de predicción: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🤖 Modelo: Vertex AI {MODEL_VERSION}")
print("\n¡Listo para subir a BigQuery! 🚀\n")
