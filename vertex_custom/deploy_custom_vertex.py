#!/usr/bin/env python3
"""
Desplegar contenedor custom en Vertex AI
"""

from google.cloud import aiplatform
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../key.json"

PROJECT_ID = "platam-analytics"
REGION = "us-central1"
IMAGE_URI = "gcr.io/platam-analytics/platam-scorer-custom:v1"
ENDPOINT_ID = "1160748927884984320"

print("="*80)
print("DESPLEGANDO CONTENEDOR CUSTOM EN VERTEX AI")
print("="*80)

print(f"\n[1/3] Conectando con Vertex AI...")
aiplatform.init(project=PROJECT_ID, location=REGION)

print(f"\n[2/3] Subiendo modelo con contenedor custom...")
print(f"   Imagen: {IMAGE_URI}")

model = aiplatform.Model.upload(
    display_name="platam-custom-final",
    serving_container_image_uri=IMAGE_URI,
    serving_container_predict_route="/predict",
    serving_container_health_route="/health",
    serving_container_ports=[8080]
)

print(f"   ✓ Modelo registrado: {model.resource_name}")

print(f"\n[3/3] Desplegando al endpoint existente...")
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

print(f"   Endpoint: {endpoint.display_name}")
print(f"   ⏳ Desplegando... (esto tarda ~10 minutos)")

model.deploy(
    endpoint=endpoint,
    deployed_model_display_name="platam-custom-final",
    machine_type="n1-standard-2",
    min_replica_count=1,
    max_replica_count=1,
    traffic_percentage=100
)

print("\n" + "="*80)
print("✅ DEPLOYMENT COMPLETADO CON CONTENEDOR CUSTOM!")
print("="*80)
print(f"Endpoint ID: {ENDPOINT_ID}")
print(f"Modelo: Custom container con modelo + scaler incluidos")
print(f"\nAhora puedes enviar datos SIN escalar - Vertex hace todo!")
