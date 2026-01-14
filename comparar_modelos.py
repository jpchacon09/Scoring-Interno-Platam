#!/usr/bin/env python3
"""
Compara predicciones de modelo v1.0 vs v2.2 para una cédula
"""

import pandas as pd
import os
from google.cloud import aiplatform

# Config
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"

# Endpoints
ENDPOINT_V1 = "1160748927884984320"  # Modelo anterior (17 features)
ENDPOINT_V2 = "7891061911641391104"  # Modelo nuevo (22 features)

# Cédula a probar
CEDULA = "1192925596"

print("=" * 80)
print("COMPARACIÓN DE MODELOS v1.0 vs v2.2")
print("=" * 80)

# Cargar datos del cliente
print(f"\n[1/3] Buscando cliente {CEDULA}...")
df = pd.read_csv('SCORES_V2_ANALISIS_COMPLETO.csv', encoding='utf-8-sig')
df['cedula'] = df['cedula'].astype(str)
cliente = df[df['cedula'] == CEDULA].iloc[0].to_dict()

print(f"✓ Cliente encontrado")
print(f"  • PLATAM Score: {cliente.get('platam_score', 0):.0f}")
print(f"  • Hybrid Score: {cliente.get('hybrid_score', 0):.0f}")
print(f"  • Edad: {cliente.get('edad', 'N/A')}")
print(f"  • Ciudad: {cliente.get('ciudad_nombre', 'N/A')}")
print(f"  • Créditos en mora: {cliente.get('creditos_mora', 'N/A')}")

# Preparar features para v1.0 (17 features)
print(f"\n[2/3] Preparando features...")

features_v1 = [
    cliente.get('platam_score', 0),
    cliente.get('experian_score_normalized', 0),
    cliente.get('score_payment_performance', 0),
    cliente.get('score_payment_plan', 0),
    cliente.get('score_deterioration', 0),
    cliente.get('payment_count', 0),
    cliente.get('months_as_client', 0),
    cliente.get('days_past_due_mean', 0),
    cliente.get('days_past_due_max', 0),
    cliente.get('pct_early', 0),
    cliente.get('pct_late', 0),
    cliente.get('peso_platam_usado', 0),
    cliente.get('peso_hcpn_usado', 0),
    cliente.get('tiene_plan_activo', 0),
    cliente.get('tiene_plan_default', 0),
    cliente.get('tiene_plan_pendiente', 0),
    cliente.get('num_planes', 0)
]

# Preparar features para v2.2 (22 features)
features_v2 = [
    cliente.get('platam_score', 0),
    cliente.get('experian_score_normalized', 0),
    cliente.get('score_payment_performance', 0),
    cliente.get('score_payment_plan', 0),
    cliente.get('score_deterioration', 0),
    cliente.get('payment_count', 0),
    cliente.get('months_as_client', 0),
    cliente.get('pct_early', 0),
    cliente.get('pct_late', 0),
    cliente.get('peso_platam_usado', 0),
    cliente.get('peso_hcpn_usado', 0),
    cliente.get('tiene_plan_activo', 0),
    cliente.get('tiene_plan_default', 0),
    cliente.get('tiene_plan_pendiente', 0),
    cliente.get('num_planes', 0),
    # 7 demográficas
    cliente.get('genero_encoded', 0),
    cliente.get('edad', 35),
    cliente.get('ciudad_encoded', 0),
    cliente.get('cuota_mensual', 0),
    cliente.get('creditos_vigentes', 0),
    cliente.get('creditos_mora', 0),
    cliente.get('hist_neg_12m', 0)
]

# Convertir NaN a 0
features_v1 = [float(0 if pd.isna(x) else x) for x in features_v1]
features_v2 = [float(0 if pd.isna(x) else x) for x in features_v2]

print(f"✓ Features v1.0: {len(features_v1)}")
print(f"✓ Features v2.2: {len(features_v2)}")

# Conectar con Vertex AI
print(f"\n[3/3] Obteniendo predicciones...")
aiplatform.init(project=PROJECT_ID, location=REGION)

# Predicción v1.0
try:
    print(f"\n  • Probando modelo v1.0 (endpoint {ENDPOINT_V1})...")
    endpoint_v1 = aiplatform.Endpoint(
        endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_V1}"
    )
    pred_v1 = endpoint_v1.predict(instances=[features_v1])
    prob_default_v1 = pred_v1.predictions[0][1]
    prob_no_default_v1 = pred_v1.predictions[0][0]
    print(f"    ✓ Predicción obtenida")
except Exception as e:
    print(f"    ❌ Error: {e}")
    prob_default_v1 = None
    prob_no_default_v1 = None

# Predicción v2.2
try:
    print(f"\n  • Probando modelo v2.2 (endpoint {ENDPOINT_V2})...")
    endpoint_v2 = aiplatform.Endpoint(
        endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_V2}"
    )
    pred_v2 = endpoint_v2.predict(instances=[features_v2])
    prob_default_v2 = pred_v2.predictions[0][1]
    prob_no_default_v2 = pred_v2.predictions[0][0]
    print(f"    ✓ Predicción obtenida")
except Exception as e:
    print(f"    ❌ Error: {e}")
    prob_default_v2 = None
    prob_no_default_v2 = None

# Mostrar resultados
print("\n" + "=" * 80)
print("📊 RESULTADOS DE LA COMPARACIÓN")
print("=" * 80)

print(f"\n🔷 MODELO v1.0 (Actual en Producción)")
print(f"   Endpoint: {ENDPOINT_V1}")
print(f"   Features: 17 (incluye days_past_due)")
if prob_default_v1 is not None:
    print(f"   • Probabilidad NO Default: {prob_no_default_v1:.3f} ({prob_no_default_v1*100:.1f}%)")
    print(f"   • Probabilidad Default:    {prob_default_v1:.3f} ({prob_default_v1*100:.1f}%)")
    risk_v1 = "Muy Alto" if prob_default_v1 >= 0.6 else "Alto" if prob_default_v1 >= 0.4 else "Medio" if prob_default_v1 >= 0.2 else "Bajo"
    print(f"   • Nivel de Riesgo:         {risk_v1}")
else:
    print(f"   ❌ No disponible")

print(f"\n🔶 MODELO v2.2 (Nuevo con Demografía)")
print(f"   Endpoint: {ENDPOINT_V2}")
print(f"   Features: 22 (sin days_past_due, con demografía)")
if prob_default_v2 is not None:
    print(f"   • Probabilidad NO Default: {prob_no_default_v2:.3f} ({prob_no_default_v2*100:.1f}%)")
    print(f"   • Probabilidad Default:    {prob_default_v2:.3f} ({prob_default_v2*100:.1f}%)")
    risk_v2 = "Muy Alto" if prob_default_v2 >= 0.6 else "Alto" if prob_default_v2 >= 0.4 else "Medio" if prob_default_v2 >= 0.2 else "Bajo"
    print(f"   • Nivel de Riesgo:         {risk_v2}")
else:
    print(f"   ❌ No disponible")

# Comparación
if prob_default_v1 is not None and prob_default_v2 is not None:
    print(f"\n📈 DIFERENCIA:")
    diff = prob_default_v2 - prob_default_v1
    if abs(diff) < 0.05:
        print(f"   Similar: diferencia de {abs(diff)*100:.1f} puntos porcentuales")
    elif diff > 0:
        print(f"   v2.2 predice MAYOR riesgo: +{diff*100:.1f} puntos porcentuales")
    else:
        print(f"   v2.2 predice MENOR riesgo: {diff*100:.1f} puntos porcentuales")

print("\n" + "=" * 80)
print("DATOS DEL CLIENTE:")
print("=" * 80)
print(f"  • Hybrid Score: {cliente.get('hybrid_score', 0):.0f} (Score bajo)")
print(f"  • Edad: {cliente.get('edad', 'N/A')} años (Joven)")
print(f"  • Ciudad: {cliente.get('ciudad_nombre', 'N/A')}")
print(f"  • Créditos vigentes: {cliente.get('creditos_vigentes', 0):.0f}")
print(f"  • Créditos en mora: {cliente.get('creditos_mora', 0):.0f} ⚠️")
print(f"  • Meses como cliente: {cliente.get('months_as_client', 0):.0f} (Nuevo)")
print(f"  • Default real: {'SÍ' if cliente.get('default_flag', 0) == 1 else 'NO'}")

print("\n" + "=" * 80)
