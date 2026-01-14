#!/usr/bin/env python3
"""
Script de Prueba del Endpoint de Vertex AI
Modelo v2.2 con 22 features (sin income features)

Usage:
    python test_vertex_endpoint.py
"""

import json
from google.cloud import aiplatform
import os

# Configuración
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"

def test_endpoint():
    """Prueba el endpoint con datos de ejemplo"""

    print("=" * 80)
    print("PRUEBA DE ENDPOINT VERTEX AI - MODELO v2.2")
    print("=" * 80)

    # Conectar con Vertex AI
    print(f"\n[1/3] Conectando con Vertex AI...")
    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
    )
    print(f"✓ Conectado al endpoint: {ENDPOINT_ID}")

    # Datos de prueba (22 features)
    print(f"\n[2/3] Preparando datos de prueba...")
    test_instance = [
        # 15 features originales (sin days_past_due)
        750,    # platam_score
        715,    # experian_score_normalized
        680,    # score_payment_performance
        600,    # score_payment_plan
        700,    # score_deterioration
        50,     # payment_count
        24,     # months_as_client
        0.1,    # pct_early
        0.05,   # pct_late
        0.6,    # peso_platam_usado
        0.4,    # peso_hcpn_usado
        0,      # tiene_plan_activo
        0,      # tiene_plan_default
        0,      # tiene_plan_pendiente
        0,      # num_planes

        # 7 features demográficas CONFIABLES (sin income)
        0,      # genero_encoded
        35,     # edad
        0,      # ciudad_encoded
        1500000,  # cuota_mensual
        5,      # creditos_vigentes
        0,      # creditos_mora
        0       # hist_neg_12m
    ]

    print(f"✓ Features preparadas: {len(test_instance)} (esperadas: 22)")

    # Hacer predicción
    print(f"\n[3/3] Enviando request al modelo...")
    prediction = endpoint.predict(instances=[test_instance])

    # Procesar resultado
    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

    print(f"\n{'=' * 80}")
    print("✅ PREDICCIÓN EXITOSA")
    print(f"{'=' * 80}")
    print(f"\n📊 Resultados:")
    print(f"   • Probabilidad NO Default: {prob_no_default:.3f} ({prob_no_default*100:.1f}%)")
    print(f"   • Probabilidad Default:    {prob_default:.3f} ({prob_default*100:.1f}%)")

    # Categorizar riesgo
    if prob_default < 0.10:
        risk_level = "Muy Bajo"
    elif prob_default < 0.20:
        risk_level = "Bajo"
    elif prob_default < 0.40:
        risk_level = "Medio"
    elif prob_default < 0.60:
        risk_level = "Alto"
    else:
        risk_level = "Muy Alto"

    print(f"   • Nivel de Riesgo:         {risk_level}")
    print(f"\n{'=' * 80}")
    print("✅ ENDPOINT FUNCIONANDO CORRECTAMENTE")
    print(f"{'=' * 80}\n")

    return True

if __name__ == "__main__":
    try:
        test_endpoint()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
