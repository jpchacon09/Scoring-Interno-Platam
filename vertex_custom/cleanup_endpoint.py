#!/usr/bin/env python3
"""
Limpiar endpoint: eliminar deployments antiguos y dejar solo platam-custom-final
"""

from google.cloud import aiplatform
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../key.json"

PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "1160748927884984320"

print("="*80)
print("LIMPIEZA DE ENDPOINT - ELIMINAR DEPLOYMENTS ANTIGUOS")
print("="*80)

aiplatform.init(project=PROJECT_ID, location=REGION)

# Obtener endpoint
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

print(f"\nEndpoint: {endpoint.display_name}")
print(f"ID: {ENDPOINT_ID}\n")

# Listar modelos desplegados
deployed_models = endpoint.gca_resource.deployed_models

print(f"Modelos desplegados actualmente: {len(deployed_models)}\n")

for i, deployed_model in enumerate(deployed_models, 1):
    print(f"{i}. Deployed Model ID: {deployed_model.id}")
    print(f"   Display Name: {deployed_model.display_name}")
    print(f"   Model: {deployed_model.model}")
    print(f"   Traffic: {deployed_model.traffic_split if hasattr(deployed_model, 'traffic_split') else 'N/A'}")
    print()

# Identificar cuál es el modelo custom
custom_model = None
models_to_undeploy = []

for deployed_model in deployed_models:
    if "custom" in deployed_model.display_name.lower():
        custom_model = deployed_model.id
        print(f"✓ Modelo a MANTENER: {deployed_model.display_name} ({deployed_model.id})")
    else:
        models_to_undeploy.append(deployed_model.id)
        print(f"✗ Modelo a ELIMINAR: {deployed_model.display_name} ({deployed_model.id})")

print("\n" + "="*60)
print(f"Modelos a mantener: 1")
print(f"Modelos a eliminar: {len(models_to_undeploy)}")
print("="*60)

if not models_to_undeploy:
    print("\n✅ No hay modelos antiguos para eliminar. El endpoint está limpio.")
    exit(0)

# Confirmar eliminación
print(f"\n⚠️  Se eliminarán {len(models_to_undeploy)} deployment(s) del endpoint.")
print("   El modelo custom-final seguirá funcionando.\n")

# Eliminar deployments antiguos
for deployed_model_id in models_to_undeploy:
    try:
        print(f"🗑️  Eliminando deployment {deployed_model_id}...")
        endpoint.undeploy(deployed_model_id=deployed_model_id)
        print(f"   ✓ Eliminado exitosamente")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "="*80)
print("✅ LIMPIEZA DEL ENDPOINT COMPLETADA")
print("="*80)
print("\nAhora puedes ejecutar cleanup_old_models.py para eliminar los modelos del registry.")
