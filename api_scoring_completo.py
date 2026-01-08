#!/usr/bin/env python3
"""
API de Scoring Completo para n8n
Combina: Scoring Híbrido + Probabilidad de Default ML

Endpoint: POST /predict
Input: {"client_id": "12345"}
Output: Scoring completo + Probabilidad ML + Recomendación
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import aiplatform
import os
import pandas as pd
from typing import Optional, Dict
from datetime import datetime

app = FastAPI(
    title="PLATAM Scoring API",
    description="API completa: Scoring Híbrido + Probabilidad de Default ML",
    version="1.0"
)

# Configurar Vertex AI
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "1160748927884984320"

aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

# ================== MODELOS DE DATOS ==================

class ClientRequest(BaseModel):
    client_id: str

class ScoringData(BaseModel):
    platam_score: int
    experian_score: int
    hybrid_score: int
    hybrid_category: str
    peso_platam: float
    peso_experian: float

class MLPrediction(BaseModel):
    probability_default: float
    probability_no_default: float
    risk_level: str
    ml_decision: str

class Recommendation(BaseModel):
    final_decision: str
    confidence: str
    reason: str
    should_review_manually: bool
    flags: list

class CompleteResponse(BaseModel):
    client_id: str
    timestamp: str
    scoring: ScoringData
    ml_prediction: MLPrediction
    recommendation: Recommendation

# ================== FUNCIONES AUXILIARES ==================

def get_client_data(client_id: str) -> Dict:
    """
    REEMPLAZA ESTO con tu consulta real a BigQuery/PostgreSQL/etc

    Debe retornar los datos del cliente con todas las features necesarias
    """
    # TODO: Implementar consulta a tu base de datos
    # Ejemplo:
    # from google.cloud import bigquery
    # client = bigquery.Client()
    # query = f"SELECT * FROM `platam.clientes` WHERE client_id = '{client_id}'"
    # result = client.query(query).to_dataframe()

    # Por ahora, datos de ejemplo:
    return {
        'client_id': client_id,
        # Scores base
        'platam_score': 650,
        'experian_score_normalized': 700,

        # Features de comportamiento
        'score_payment_performance': 400,
        'score_payment_plan': 150,
        'score_deterioration': 150,
        'payment_count': 18,
        'months_as_client': 14,
        'days_past_due_mean': 8.5,
        'days_past_due_max': 25,
        'pct_early': 0.3,
        'pct_late': 0.25,

        # Features de uso
        'peso_platam_usado': 0.6,
        'peso_hcpn_usado': 0.4,

        # Features de planes de pago
        'tiene_plan_activo': 0,
        'tiene_plan_default': 0,
        'tiene_plan_pendiente': 0,
        'num_planes': 0
    }

def calculate_hybrid_score(platam_score: int, experian_score: int,
                          peso_platam: float, peso_experian: float) -> tuple:
    """
    Calcula el scoring híbrido usando los pesos dinámicos
    Retorna: (hybrid_score, category)
    """
    # Normalizar experian a escala 300-850 si está en otra escala
    if experian_score > 850:
        experian_score = min(850, max(300, experian_score))

    # Calcular score híbrido
    hybrid_score = int(
        (platam_score * peso_platam) +
        (experian_score * peso_experian)
    )

    # Categorizar
    if hybrid_score >= 750:
        category = "Excelente"
    elif hybrid_score >= 650:
        category = "Bueno"
    elif hybrid_score >= 550:
        category = "Medio"
    elif hybrid_score >= 450:
        category = "Regular"
    else:
        category = "Bajo"

    return hybrid_score, category

def get_ml_prediction(client_data: Dict) -> tuple:
    """
    Obtiene la predicción del modelo ML en Vertex AI
    Retorna: (prob_default, prob_no_default)
    """
    # Preparar features en el orden correcto
    feature_order = [
        'platam_score', 'experian_score_normalized',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'payment_count', 'months_as_client',
        'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late',
        'peso_platam_usado', 'peso_hcpn_usado',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]

    instance = [[client_data[f] for f in feature_order]]

    # Llamar a Vertex AI
    prediction = endpoint.predict(instances=instance)

    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

    return prob_default, prob_no_default

def calculate_risk_level(prob_default: float) -> str:
    """Categoriza el nivel de riesgo según la probabilidad"""
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

def get_ml_decision(prob_default: float) -> str:
    """Decisión basada solo en el modelo ML"""
    if prob_default >= 0.60:
        return "RECHAZAR"
    elif prob_default >= 0.40:
        return "REVISAR"
    else:
        return "APROBAR"

def generate_recommendation(scoring_data: Dict, ml_data: Dict) -> Dict:
    """
    Combina scoring híbrido + ML para dar recomendación final

    Lógica de decisión:
    1. Si ML dice RECHAZAR (>60%) → RECHAZAR (salvo score excelente)
    2. Si ML dice APROBAR (<40%) → APROBAR (salvo score bajo)
    3. Si ML dice REVISAR (40-60%) → Depende del score híbrido
    """
    hybrid_score = scoring_data['hybrid_score']
    hybrid_category = scoring_data['hybrid_category']
    prob_default = ml_data['probability_default']
    ml_decision = ml_data['ml_decision']

    flags = []

    # Análisis de flags
    if prob_default >= 0.70:
        flags.append("⚠️ Probabilidad de default muy alta (>70%)")

    if hybrid_score < 500:
        flags.append("⚠️ Score híbrido bajo (<500)")

    if scoring_data.get('days_past_due_mean', 0) > 15:
        flags.append("⚠️ Mora promedio alta (>15 días)")

    if scoring_data.get('tiene_plan_default', 0) == 1:
        flags.append("⚠️ Tiene planes de pago en default")

    # DECISIÓN FINAL
    if prob_default >= 0.60:
        # ML recomienda rechazar
        if hybrid_score >= 750 and prob_default < 0.70:
            # Excepción: score excelente y probabilidad no tan alta
            final_decision = "REVISAR MANUALMENTE"
            confidence = "Media"
            reason = f"Score híbrido excelente ({hybrid_score}) pero probabilidad de default moderada ({prob_default*100:.1f}%)"
            should_review = True
        else:
            final_decision = "RECHAZAR"
            confidence = "Alta"
            reason = f"Alta probabilidad de default ({prob_default*100:.1f}%) con score {hybrid_category.lower()}"
            should_review = False

    elif prob_default < 0.40:
        # ML recomienda aprobar
        if hybrid_score < 500:
            # Excepción: score híbrido muy bajo
            final_decision = "REVISAR MANUALMENTE"
            confidence = "Media"
            reason = f"Baja probabilidad de default ({prob_default*100:.1f}%) pero score híbrido bajo ({hybrid_score})"
            should_review = True
        else:
            final_decision = "APROBAR"
            confidence = "Alta"
            reason = f"Baja probabilidad de default ({prob_default*100:.1f}%) y score {hybrid_category.lower()}"
            should_review = False

    else:
        # ML recomienda revisar (40-60%)
        if hybrid_score >= 700:
            final_decision = "APROBAR CON CONDICIONES"
            confidence = "Media"
            reason = f"Score híbrido bueno ({hybrid_score}) pero probabilidad de default moderada ({prob_default*100:.1f}%)"
            should_review = True
        elif hybrid_score >= 550:
            final_decision = "REVISAR MANUALMENTE"
            confidence = "Baja"
            reason = f"Indicadores mixtos: score {hybrid_category.lower()} y probabilidad de default {prob_default*100:.1f}%"
            should_review = True
        else:
            final_decision = "RECHAZAR"
            confidence = "Media"
            reason = f"Score híbrido bajo ({hybrid_score}) y probabilidad de default moderada ({prob_default*100:.1f}%)"
            should_review = False

    return {
        'final_decision': final_decision,
        'confidence': confidence,
        'reason': reason,
        'should_review_manually': should_review,
        'flags': flags
    }

# ================== ENDPOINTS ==================

@app.get("/")
def root():
    return {
        "service": "PLATAM Scoring API",
        "version": "1.0",
        "status": "online",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "vertex_ai": "connected",
        "model": "platam-custom-final"
    }

@app.post("/predict", response_model=CompleteResponse)
async def predict_complete(request: ClientRequest):
    """
    Endpoint principal: Retorna scoring completo para un cliente

    Combina:
    1. Scoring híbrido (PLATAM + Experian)
    2. Predicción ML (Probabilidad de default)
    3. Recomendación final (Combina ambos)
    """
    try:
        # 1. Obtener datos del cliente
        client_data = get_client_data(request.client_id)

        if not client_data:
            raise HTTPException(status_code=404, detail=f"Cliente {request.client_id} no encontrado")

        # 2. Calcular scoring híbrido
        hybrid_score, hybrid_category = calculate_hybrid_score(
            platam_score=client_data['platam_score'],
            experian_score=client_data['experian_score_normalized'],
            peso_platam=client_data['peso_platam_usado'],
            peso_experian=client_data['peso_hcpn_usado']
        )

        scoring_data = {
            'platam_score': client_data['platam_score'],
            'experian_score': client_data['experian_score_normalized'],
            'hybrid_score': hybrid_score,
            'hybrid_category': hybrid_category,
            'peso_platam': client_data['peso_platam_usado'],
            'peso_experian': client_data['peso_hcpn_usado']
        }

        # 3. Obtener predicción ML
        prob_default, prob_no_default = get_ml_prediction(client_data)

        risk_level = calculate_risk_level(prob_default)
        ml_decision = get_ml_decision(prob_default)

        ml_data = {
            'probability_default': prob_default,
            'probability_no_default': prob_no_default,
            'risk_level': risk_level,
            'ml_decision': ml_decision
        }

        # 4. Generar recomendación final
        recommendation = generate_recommendation(
            {**scoring_data, **client_data},
            ml_data
        )

        # 5. Construir respuesta completa
        return CompleteResponse(
            client_id=request.client_id,
            timestamp=datetime.now().isoformat(),
            scoring=ScoringData(**scoring_data),
            ml_prediction=MLPrediction(**ml_data),
            recommendation=Recommendation(**recommendation)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")

# ================== ENDPOINTS AUXILIARES ==================

@app.post("/predict/scoring-only")
async def predict_scoring_only(request: ClientRequest):
    """Solo scoring híbrido (sin ML)"""
    client_data = get_client_data(request.client_id)

    hybrid_score, hybrid_category = calculate_hybrid_score(
        platam_score=client_data['platam_score'],
        experian_score=client_data['experian_score_normalized'],
        peso_platam=client_data['peso_platam_usado'],
        peso_experian=client_data['peso_hcpn_usado']
    )

    return {
        'client_id': request.client_id,
        'platam_score': client_data['platam_score'],
        'experian_score': client_data['experian_score_normalized'],
        'hybrid_score': hybrid_score,
        'hybrid_category': hybrid_category
    }

@app.post("/predict/ml-only")
async def predict_ml_only(request: ClientRequest):
    """Solo predicción ML (sin scoring)"""
    client_data = get_client_data(request.client_id)

    prob_default, prob_no_default = get_ml_prediction(client_data)
    risk_level = calculate_risk_level(prob_default)
    ml_decision = get_ml_decision(prob_default)

    return {
        'client_id': request.client_id,
        'probability_default': round(prob_default, 4),
        'probability_no_default': round(prob_no_default, 4),
        'risk_level': risk_level,
        'decision': ml_decision
    }

if __name__ == "__main__":
    import uvicorn
    print("="*80)
    print("🚀 PLATAM Scoring API - Completa")
    print("="*80)
    print("Endpoints disponibles:")
    print("  • POST /predict - Scoring completo (híbrido + ML + recomendación)")
    print("  • POST /predict/scoring-only - Solo scoring híbrido")
    print("  • POST /predict/ml-only - Solo predicción ML")
    print("\nDocs interactivas: http://localhost:8000/docs")
    print("="*80)
    uvicorn.run(app, host="0.0.0.0", port=8000)
