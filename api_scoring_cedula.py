#!/usr/bin/env python3
"""
API de Scoring Completo - Búsqueda por Cédula/NIT
Carga CSV con datos precalculados + llama a Vertex AI

Input: {"cedula": "1006157869"}
Output: Score híbrido + Probabilidad ML + Recomendación
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import aiplatform
import os
import pandas as pd
from typing import Optional
from datetime import datetime

app = FastAPI(
    title="PLATAM Scoring API - Por Cédula",
    description="Scoring completo: Busca por cédula/NIT y retorna evaluación 360°",
    version="1.0"
)

# ================== CONFIGURACIÓN ==================

# Configurar Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "1160748927884984320"

# Ruta al CSV con datos
CSV_PATH = "data/processed/hybrid_scores.csv"

# ================== DATOS EN MEMORIA ==================

# Cargar CSV al iniciar la API
print("="*80)
print("🚀 INICIANDO API DE SCORING")
print("="*80)
print(f"\n📂 Cargando datos desde: {CSV_PATH}")

try:
    # Cargar CSV
    df_clientes = pd.read_csv(CSV_PATH)

    # Limpiar nombres de columnas (por si hay BOM)
    df_clientes.columns = df_clientes.columns.str.strip()

    # Convertir cédula a string para búsqueda
    df_clientes['cedula'] = df_clientes['cedula'].astype(str)

    print(f"✅ Cargados {len(df_clientes)} clientes")
    print(f"📊 Columnas disponibles: {len(df_clientes.columns)}")
    print(f"\n📋 Primeras cédulas: {df_clientes['cedula'].head(3).tolist()}")

except Exception as e:
    print(f"❌ Error al cargar CSV: {e}")
    df_clientes = None

# Conectar con Vertex AI
print(f"\n🌐 Conectando con Vertex AI...")
try:
    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
    )
    print(f"✅ Conectado al endpoint: {ENDPOINT_ID}")
except Exception as e:
    print(f"❌ Error al conectar con Vertex AI: {e}")
    endpoint = None

print("\n" + "="*80)
print("✅ API LISTA PARA RECIBIR REQUESTS")
print("="*80)
print("📍 Endpoints disponibles:")
print("   • GET  /health")
print("   • POST /predict")
print("   • GET  /stats")
print("\n🌐 Docs interactivas: http://localhost:8000/docs")
print("="*80 + "\n")

# ================== MODELOS DE DATOS ==================

class ClientRequest(BaseModel):
    cedula: str  # O NIT

class ScoringData(BaseModel):
    platam_score: float
    experian_score: float
    hybrid_score: float
    hybrid_category: str
    peso_platam: float
    peso_experian: float

class MLPrediction(BaseModel):
    probability_default: float
    probability_no_default: float
    risk_level: str
    attention_level: str  # Nivel de atención requerido

class Recommendation(BaseModel):
    action_plan: str  # Plan de acción sugerido
    priority: str  # Prioridad de atención
    reason: str
    requires_follow_up: bool  # Requiere seguimiento
    flags: list

class ClientInfo(BaseModel):
    cedula: str
    client_name: Optional[str]
    months_as_client: int
    payment_count: int
    has_payment_history: bool

class CompleteResponse(BaseModel):
    client_info: ClientInfo
    timestamp: str
    scoring: ScoringData
    ml_prediction: MLPrediction
    recommendation: Recommendation

# ================== FUNCIONES AUXILIARES ==================

def get_client_by_cedula(cedula: str) -> Optional[dict]:
    """Busca cliente por cédula en el CSV cargado"""
    if df_clientes is None:
        raise HTTPException(status_code=503, detail="Datos no cargados")

    # Buscar por cédula (convertir a string)
    cedula_str = str(cedula).strip()
    cliente = df_clientes[df_clientes['cedula'] == cedula_str]

    if cliente.empty:
        return None

    # Retornar primera coincidencia como dict
    return cliente.iloc[0].to_dict()

def get_ml_prediction(client_data: dict) -> tuple:
    """Obtiene predicción del modelo ML en Vertex AI"""

    # Features en el orden correcto para el modelo
    feature_order = [
        'platam_score', 'experian_score_normalized',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'payment_count', 'months_as_client',
        'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late',
        'peso_platam_usado', 'peso_hcpn_usado',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]

    # Preparar instancia (manejar NaN)
    instance = []
    for feature in feature_order:
        value = client_data.get(feature, 0)
        # Reemplazar NaN con 0
        if pd.isna(value):
            value = 0
        # Convertir booleanos a enteros
        if isinstance(value, bool):
            value = int(value)
        instance.append(float(value))

    # Llamar a Vertex AI
    prediction = endpoint.predict(instances=[instance])

    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

    return prob_default, prob_no_default

def calculate_risk_level(prob_default: float) -> str:
    """Categoriza el nivel de riesgo"""
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

def get_attention_level(prob_default: float) -> str:
    """Determina el nivel de atención según probabilidad de default"""
    if prob_default >= 0.60:
        return "Alerta crítica"
    elif prob_default >= 0.40:
        return "Seguimiento cercano"
    elif prob_default >= 0.20:
        return "Atención moderada"
    else:
        return "Monitoreo normal"

def categorize_hybrid_score(score: float) -> str:
    """Categoriza el score híbrido"""
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

def generate_recommendation(client_data: dict, ml_data: dict) -> dict:
    """Genera recomendación de seguimiento y cobranza combinando scoring + ML"""

    hybrid_score = client_data['hybrid_score']
    prob_default = ml_data['probability_default']
    attention_level = ml_data['attention_level']

    # Categorizar score
    if pd.isna(hybrid_score):
        hybrid_score = 500  # Default si no hay score

    hybrid_category = categorize_hybrid_score(hybrid_score)

    flags = []

    # Analizar flags
    if prob_default >= 0.70:
        flags.append(f"🔴 Probabilidad de default muy alta ({prob_default*100:.0f}%)")

    if hybrid_score < 500:
        flags.append(f"⚠️ Score híbrido bajo ({hybrid_score:.0f})")

    days_past_due = client_data.get('days_past_due_mean', 0)
    if not pd.isna(days_past_due) and days_past_due > 15:
        flags.append(f"⏰ Mora promedio alta ({days_past_due:.0f} días)")

    if client_data.get('tiene_plan_default', False):
        flags.append("❌ Tiene planes de pago en default")

    months_as_client = client_data.get('months_as_client', 0)
    if pd.isna(months_as_client) or months_as_client < 3:
        flags.append("🆕 Cliente muy nuevo (<3 meses)")

    # PLAN DE ACCIÓN SEGÚN RIESGO
    if prob_default >= 0.60:
        # Alto riesgo de incumplimiento
        if hybrid_score >= 750 and prob_default < 0.70:
            action_plan = "Contacto preventivo - Verificar situación actual"
            priority = "Alta"
            reason = f"Score excelente ({hybrid_score:.0f}) pero riesgo elevado ({prob_default*100:.1f}%)"
            requires_follow_up = True
        else:
            action_plan = "Cobranza inmediata - Restringir nuevos créditos"
            priority = "Crítica"
            reason = f"Alta probabilidad de incumplimiento ({prob_default*100:.1f}%) con score {hybrid_category.lower()}"
            requires_follow_up = True

    elif prob_default < 0.20:
        # Bajo riesgo
        if hybrid_score < 500:
            action_plan = "Monitoreo rutinario - Revisar score bajo"
            priority = "Baja"
            reason = f"Riesgo bajo ({prob_default*100:.1f}%) pero score híbrido bajo ({hybrid_score:.0f})"
            requires_follow_up = False
        else:
            action_plan = "Sin acción - Cliente confiable"
            priority = "Ninguna"
            reason = f"Riesgo muy bajo ({prob_default*100:.1f}%) y score {hybrid_category.lower()}"
            requires_follow_up = False

    elif prob_default < 0.40:
        # Riesgo moderado-bajo
        if hybrid_score >= 700:
            action_plan = "Monitoreo rutinario - Buen desempeño"
            priority = "Baja"
            reason = f"Score alto ({hybrid_score:.0f}) y riesgo moderado ({prob_default*100:.1f}%)"
            requires_follow_up = False
        else:
            action_plan = "Recordatorio preventivo - Seguimiento mensual"
            priority = "Media"
            reason = f"Riesgo moderado ({prob_default*100:.1f}%) con score {hybrid_category.lower()}"
            requires_follow_up = True

    else:
        # Riesgo moderado-alto (40-60%)
        if hybrid_score >= 700:
            action_plan = "Contacto preventivo - Evaluar refinanciación"
            priority = "Media"
            reason = f"Score bueno ({hybrid_score:.0f}) pero riesgo moderado-alto ({prob_default*100:.1f}%)"
            requires_follow_up = True
        else:
            action_plan = "Seguimiento cercano - Limitar exposición"
            priority = "Alta"
            reason = f"Indicadores mixtos: score {hybrid_category.lower()} y riesgo {prob_default*100:.1f}%"
            requires_follow_up = True

    return {
        'action_plan': action_plan,
        'priority': priority,
        'reason': reason,
        'requires_follow_up': requires_follow_up,
        'flags': flags
    }

# ================== ENDPOINTS ==================

@app.get("/")
def root():
    return {
        "service": "PLATAM Scoring API",
        "version": "1.0 - Búsqueda por Cédula",
        "status": "online",
        "clientes_cargados": len(df_clientes) if df_clientes is not None else 0,
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "stats": "/stats",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "data_loaded": df_clientes is not None,
        "vertex_ai": "connected" if endpoint else "disconnected",
        "model": "platam-custom-final",
        "clientes": len(df_clientes) if df_clientes is not None else 0
    }

@app.get("/stats")
def stats():
    """Estadísticas de los datos cargados"""
    if df_clientes is None:
        raise HTTPException(status_code=503, detail="Datos no cargados")

    return {
        "total_clientes": len(df_clientes),
        "score_promedio": float(df_clientes['hybrid_score'].mean()),
        "score_min": float(df_clientes['hybrid_score'].min()),
        "score_max": float(df_clientes['hybrid_score'].max()),
        "clientes_con_historial": int(df_clientes['has_payment_history'].sum()),
        "meses_promedio": float(df_clientes['months_as_client'].mean())
    }

@app.post("/predict", response_model=CompleteResponse)
async def predict_by_cedula(request: ClientRequest):
    """
    Endpoint principal: Busca cliente por cédula y retorna evaluación completa
    """
    try:
        # 1. Buscar cliente por cédula
        client_data = get_client_by_cedula(request.cedula)

        if not client_data:
            raise HTTPException(
                status_code=404,
                detail=f"Cliente con cédula {request.cedula} no encontrado"
            )

        # 2. Extraer datos de scoring
        scoring_data = {
            'platam_score': float(client_data.get('platam_score', 0)),
            'experian_score': float(client_data.get('experian_score_normalized', 0)),
            'hybrid_score': float(client_data.get('hybrid_score', 0)),
            'hybrid_category': categorize_hybrid_score(client_data.get('hybrid_score', 0)),
            'peso_platam': float(client_data.get('peso_platam_usado', 0)),
            'peso_experian': float(client_data.get('peso_hcpn_usado', 0))
        }

        # 3. Obtener predicción ML
        prob_default, prob_no_default = get_ml_prediction(client_data)

        ml_data = {
            'probability_default': prob_default,
            'probability_no_default': prob_no_default,
            'risk_level': calculate_risk_level(prob_default),
            'attention_level': get_attention_level(prob_default)
        }

        # 4. Generar recomendación
        recommendation = generate_recommendation(client_data, ml_data)

        # 5. Información del cliente
        client_name = client_data.get('client_name', 'N/A')
        if pd.isna(client_name):
            client_name = 'N/A'

        client_info = {
            'cedula': str(client_data['cedula']),
            'client_name': str(client_name),
            'months_as_client': int(client_data.get('months_as_client', 0) if not pd.isna(client_data.get('months_as_client', 0)) else 0),
            'payment_count': int(client_data.get('payment_count', 0) if not pd.isna(client_data.get('payment_count', 0)) else 0),
            'has_payment_history': bool(client_data.get('has_payment_history', False))
        }

        # 6. Construir respuesta
        return CompleteResponse(
            client_info=ClientInfo(**client_info),
            timestamp=datetime.now().isoformat(),
            scoring=ScoringData(**scoring_data),
            ml_prediction=MLPrediction(**ml_data),
            recommendation=Recommendation(**recommendation)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
