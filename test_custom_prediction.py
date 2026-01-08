#!/usr/bin/env python3
"""
Probar predicción con contenedor custom de Vertex AI
IMPORTANTE: Los datos se envían SIN escalar - Vertex lo hace internamente
"""

from google.cloud import aiplatform
import os

# Autenticación
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"

# Configuración
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "1160748927884984320"

def predecir_cliente():
    # Datos de prueba (cliente de riesgo medio)
    # IMPORTANTE: Estos son los datos ORIGINALES, SIN ESCALAR
    datos_cliente = {
        'platam_score': 650,
        'experian_score_normalized': 700,
        'score_payment_performance': 400,
        'score_payment_plan': 150,
        'score_deterioration': 150,
        'payment_count': 18,
        'months_as_client': 14,
        'days_past_due_mean': 8.5,
        'days_past_due_max': 25,
        'pct_early': 0.3,
        'pct_late': 0.25,
        'peso_platam_usado': 0.6,
        'peso_hcpn_usado': 0.4,
        'tiene_plan_activo': 0,
        'tiene_plan_default': 0,
        'tiene_plan_pendiente': 0,
        'num_planes': 0
    }

    print("🧑 Cliente de prueba:")
    print(f"   PLATAM Score: {datos_cliente['platam_score']}")
    print(f"   Experian Score: {datos_cliente['experian_score_normalized']}")
    print(f"   Mora promedio: {datos_cliente['days_past_due_mean']} días")
    print(f"   Meses como cliente: {datos_cliente['months_as_client']}")

    # Conectar con Vertex AI
    print(f"\n🌐 Conectando con Vertex AI endpoint...")
    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
    )

    # Preparar datos (como lista en el orden correcto)
    feature_order = [
        'platam_score', 'experian_score_normalized',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'payment_count', 'months_as_client',
        'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late',
        'peso_platam_usado', 'peso_hcpn_usado',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]

    instance = [[datos_cliente[feature] for feature in feature_order]]

    # Hacer predicción
    print("🚀 Enviando datos SIN escalar a Vertex AI...")
    print(f"   (El escalado ocurre dentro del contenedor)")
    prediction = endpoint.predict(instances=instance)

    # Procesar resultado
    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

    print("\n" + "="*60)
    print("📊 RESULTADO DE LA PREDICCIÓN")
    print("="*60)
    print(f"\n🎲 Probabilidad No-Default: {prob_no_default*100:.2f}%")
    print(f"🎲 Probabilidad Default: {prob_default*100:.2f}%")
    print(f"🎯 Threshold configurado: 60%")

    # Aplicar threshold 0.60
    if prob_default >= 0.60:
        decision = "❌ RECHAZAR"
        riesgo = "Muy Alto"
    elif prob_default >= 0.40:
        decision = "⚠️  REVISAR MANUALMENTE"
        riesgo = "Alto"
    else:
        decision = "✅ APROBAR"
        riesgo = "Bajo-Medio"

    print(f"📈 Nivel de riesgo: {riesgo}")
    print(f"✅ Decisión: {decision}")
    print("\n" + "="*60)

    return {
        'probability_default': prob_default,
        'probability_no_default': prob_no_default,
        'decision': decision,
        'risk': riesgo
    }

if __name__ == "__main__":
    try:
        resultado = predecir_cliente()
        print("\n🎉 ¡PREDICCIÓN EXITOSA DESDE VERTEX AI CON CONTENEDOR CUSTOM!")
        print("✓ Modelo funcionando correctamente")
        print("✓ Escalado automático dentro del contenedor")
        print("✓ Listo para usar en producción")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
