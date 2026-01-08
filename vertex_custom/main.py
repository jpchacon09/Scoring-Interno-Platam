from fastapi import FastAPI, Request
import pickle
import pandas as pd
import os

app = FastAPI()

# Cargar modelos al iniciar
print("Cargando modelos...")
with open("scaler_final.pkl", "rb") as f:
    scaler = pickle.load(f)
with open("xgboost_model_final.pkl", "rb") as f:
    model = pickle.load(f)
print("✅ Modelos cargados en memoria")

@app.get("/health")
def health_check():
    return {"status": "alive"}

@app.post("/predict")
async def predict(request: Request):
    body = await request.json()

    # Vertex envía los datos en formato {"instances": [[...], [...]]}
    instances = body["instances"]

    # Nombres de columnas esperados (IMPORTANTE: Mismo orden que entrenamiento)
    columns = [
        'platam_score', 'experian_score_normalized', 'score_payment_performance',
        'score_payment_plan', 'score_deterioration', 'payment_count',
        'months_as_client', 'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late', 'peso_platam_usado', 'peso_hcpn_usado',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]

    # 1. Crear DataFrame
    df = pd.DataFrame(instances, columns=columns)

    # 2. ESCALAR (Ahora ocurre DENTRO de Vertex)
    scaled_data = scaler.transform(df)

    # 3. PREDECIR (retornar probabilidades)
    predictions_proba = model.predict_proba(scaled_data)

    # 4. Devolver respuesta estándar de Vertex (probabilidades para ambas clases)
    return {"predictions": predictions_proba.tolist()}
