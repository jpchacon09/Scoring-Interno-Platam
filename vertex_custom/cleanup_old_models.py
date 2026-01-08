#!/usr/bin/env python3
"""
Limpiar modelos antiguos de Vertex AI Model Registry
IMPORTANTE: Solo elimina modelos que NO están desplegados
"""

from google.cloud import aiplatform
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../key.json"

PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "1160748927884984320"

print("="*80)
print("LIMPIEZA DE MODELOS ANTIGUOS EN VERTEX AI")
print("="*80)

aiplatform.init(project=PROJECT_ID, location=REGION)

# 1. Obtener el modelo actualmente desplegado
print("\n[1/3] Verificando modelo desplegado...")
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

deployed_models = endpoint.list_models()
deployed_model_ids = [model.id for model in deployed_models]
print(f"   ✓ Modelos desplegados (NO se eliminarán): {deployed_model_ids}")

# 2. Listar todos los modelos
print("\n[2/3] Listando todos los modelos...")
all_models = aiplatform.Model.list(
    filter='',
    order_by='create_time desc'
)

print(f"\n   Total de modelos encontrados: {len(all_models)}")
print("\n   Modelos en el registry:")
for i, model in enumerate(all_models, 1):
    # Extraer el ID numérico del modelo
    model_id = model.resource_name.split('/')[-1].split('@')[0]
    is_deployed = model_id in deployed_model_ids
    status = "🟢 DESPLEGADO (NO eliminar)" if is_deployed else "⚪ No desplegado"
    print(f"   {i}. {model.display_name} | ID: {model_id} | {status}")

# 3. Eliminar modelos no desplegados
print("\n[3/3] Eliminando modelos antiguos...")
deleted_count = 0

for model in all_models:
    model_id = model.resource_name.split('/')[-1].split('@')[0]

    # NO eliminar si está desplegado
    if model_id in deployed_model_ids:
        print(f"   ⏭️  Saltando {model.display_name} (está desplegado)")
        continue

    # NO eliminar si es el modelo custom final (por si acaso)
    if "custom-final" in model.display_name.lower():
        print(f"   ⏭️  Saltando {model.display_name} (modelo custom principal)")
        continue

    # Eliminar modelos antiguos/fallidos
    try:
        print(f"   🗑️  Eliminando: {model.display_name}...")
        model.delete()
        deleted_count += 1
        print(f"      ✓ Eliminado exitosamente")
    except Exception as e:
        print(f"      ❌ Error al eliminar: {e}")

print("\n" + "="*80)
print(f"✅ LIMPIEZA COMPLETADA")
print("="*80)
print(f"Modelos eliminados: {deleted_count}")
print(f"Modelos conservados: {len(all_models) - deleted_count}")
print("\nModelos conservados son los que están actualmente desplegados.")
