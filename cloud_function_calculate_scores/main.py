#!/usr/bin/env python3
"""
PLATAM - Cloud Function para CALCULAR Scores (sin acceso a MySQL)
==================================================================

Esta función SOLO calcula scores. NO accede a MySQL.
n8n le envía los datos y ella retorna los scores calculados.

Input (POST):
    {
        "client_data": {
            "cedula": "128282",
            "months_as_client": 8,
            "experian_score": 715,
            "edad": 32,
            "ciudad": "Barranquilla",
            "genero": "M",
            "cuota_mensual": 450000,
            "creditos_vigentes": 5,
            "creditos_mora": 1,
            "hist_neg_12m": 0
        },
        "payments": [
            {"payment_date": "2026-01-20", "days_past_due": 7},
            {"payment_date": "2025-12-15", "days_past_due": 2},
            ...
        ],
        "payment_plans": [
            {"plan_status": "active", "plan_start_date": "2025-11-01"},
            ...
        ]
    }

Output:
    {
        "status": "success",
        "platam_score": 730.5,
        "hybrid_score": 745.2,
        "ml_probability_default": 0.12,
        "ml_probability_no_default": 0.88,
        "ml_risk_level": "Bajo",
        "peso_platam": 0.6,
        "peso_hcpn": 0.4,
        "score_payment_performance": 450.0,
        "score_payment_plan": 150.0,
        "score_deterioration": 130.5,
        "processing_time_ms": 1847
    }

Autor: PLATAM Data Team
Fecha: Enero 2026
"""

import functions_framework
from flask import jsonify
import pandas as pd
import numpy as np
from google.cloud import aiplatform
from datetime import datetime
import time
from typing import Dict, List, Optional

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"  # Modelo v2.2 con demografía

# Inicializar Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

# ============================================================================
# FUNCIONES DE SCORING (simplificadas)
# ============================================================================

def calculate_payment_performance(payments: List[Dict], months_as_client: int) -> Dict:
    """Calcula Payment Performance Score (600 pts)"""

    if len(payments) < 3:
        return {
            'timeliness_score': 50,
            'pattern_score': 50,
            'total': 300,
            'payment_count': len(payments),
            'pct_early': 0,
            'pct_late': 0
        }

    # Calcular scores de calidad por pago
    payment_scores = []
    early_count = 0
    late_count = 0

    for payment in payments:
        dpd = payment.get('days_past_due', 0)

        if dpd <= 0:
            score = 100
            early_count += 1
        elif dpd <= 15:
            score = max(0, 100 - dpd * 3)
            late_count += 1
        elif dpd <= 30:
            score = max(0, 55 - dpd * 2)
            late_count += 1
        else:
            score = 0
            late_count += 1

        payment_scores.append(score)

    timeliness_score = np.mean(payment_scores) if payment_scores else 50

    # Pattern score (consistencia)
    recent_dpds = [p.get('days_past_due', 0) for p in payments[:min(6, len(payments))]]
    pattern_score = max(0, 100 - np.std(recent_dpds) * 2) if len(recent_dpds) > 1 else 50

    # Pesos según madurez
    if months_as_client < 6:
        timeliness_weight, pattern_weight = 0.85, 0.15
    elif months_as_client < 12:
        timeliness_weight, pattern_weight = 0.70, 0.30
    else:
        timeliness_weight, pattern_weight = 0.50, 0.50

    total = (timeliness_score * timeliness_weight + pattern_score * pattern_weight) * 6

    total_payments = len(payments)
    pct_early = round(early_count / total_payments, 3) if total_payments > 0 else 0
    pct_late = round(late_count / total_payments, 3) if total_payments > 0 else 0

    return {
        'timeliness_score': round(timeliness_score, 1),
        'pattern_score': round(pattern_score, 1),
        'total': round(total, 1),
        'payment_count': len(payments),
        'pct_early': pct_early,
        'pct_late': pct_late
    }


def calculate_payment_plan_score(payment_plans: List[Dict]) -> Dict:
    """Calcula Payment Plan History Score (150 pts)"""

    if len(payment_plans) == 0:
        return {
            'total': 150,
            'active_plans': 0,
            'defaulted_plans': 0,
            'pending_plans': 0,
            'num_planes': 0,
            'tiene_plan_activo': False,
            'tiene_plan_default': False,
            'tiene_plan_pendiente': False
        }

    score = 150
    active = sum(1 for p in payment_plans if p.get('plan_status') == 'active')
    completed = sum(1 for p in payment_plans if p.get('plan_status') == 'completed')
    defaulted = sum(1 for p in payment_plans if p.get('plan_status') == 'defaulted')
    pending = sum(1 for p in payment_plans if p.get('plan_status') == 'pending')

    score -= (active * 50) + (defaulted * 100) - (completed * 30)
    score = max(0, min(150, score))

    return {
        'total': round(score, 1),
        'active_plans': active,
        'defaulted_plans': defaulted,
        'pending_plans': pending,
        'num_planes': len(payment_plans),
        'tiene_plan_activo': active > 0,
        'tiene_plan_default': defaulted > 0,
        'tiene_plan_pendiente': pending > 0
    }


def calculate_deterioration_velocity(payments: List[Dict]) -> Dict:
    """Calcula Deterioration Velocity Score (250 pts)"""

    if len(payments) < 3:
        return {'total': 125, 'dpd_1mo': 0, 'dpd_6mo': 0, 'trend_delta': 0}

    # Últimos 1 mes vs últimos 6 meses
    payments_1mo = payments[:min(1, len(payments))]
    payments_6mo = payments[:min(6, len(payments))]

    dpd_1mo = np.mean([p.get('days_past_due', 0) for p in payments_1mo]) if payments_1mo else 0
    dpd_6mo = np.mean([p.get('days_past_due', 0) for p in payments_6mo]) if payments_6mo else 0

    trend_delta = dpd_1mo - dpd_6mo
    base_score = max(0, min(100, 100 - (trend_delta * 3)))
    score = base_score * 2.5

    return {
        'total': round(score, 1),
        'dpd_1mo': round(dpd_1mo, 1),
        'dpd_6mo': round(dpd_6mo, 1),
        'trend_delta': round(trend_delta, 1)
    }


def calculate_hybrid_score(platam_score: float, hcpn_score: Optional[float],
                          months_as_client: int, payment_count: int) -> Dict:
    """Calcula score híbrido con pesos dinámicos"""

    # Determinar categoría de madurez
    if months_as_client < 3:
        categoria = 'muy_nuevo'
    elif months_as_client < 6:
        categoria = 'nuevo'
    elif months_as_client < 12:
        categoria = 'intermedio'
    elif months_as_client < 24:
        categoria = 'establecido'
    else:
        categoria = 'maduro'

    # Pesos base
    pesos = {
        'muy_nuevo': 0.30,
        'nuevo': 0.40,
        'intermedio': 0.50,
        'establecido': 0.60,
        'maduro': 0.70
    }

    # Si no tiene HCPN, 100% PLATAM
    if hcpn_score is None or pd.isna(hcpn_score) or hcpn_score == 0:
        peso_platam = 1.0
        peso_hcpn = 0.0
        hybrid_score = platam_score
    else:
        peso_platam = pesos[categoria]

        # Ajuste por historial
        if payment_count >= 20:
            peso_platam += 0.10
        elif payment_count < 5:
            peso_platam -= 0.10

        peso_platam = max(0.20, min(0.80, peso_platam))
        peso_hcpn = 1.0 - peso_platam

        hybrid_score = (platam_score * peso_platam) + (hcpn_score * peso_hcpn)

    return {
        'hybrid_score': round(hybrid_score, 1),
        'peso_platam': peso_platam,
        'peso_hcpn': peso_hcpn,
        'categoria': categoria
    }


def get_ml_prediction(client_data: Dict, scores: Dict) -> Dict:
    """
    Llama a Vertex AI para obtener predicción ML
    Modelo v2.2: 22 features
    """

    # Preparar features en el orden correcto
    feature_order = [
        'platam_score', 'experian_score',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'payment_count', 'months_as_client',
        'pct_early', 'pct_late',
        'peso_platam', 'peso_hcpn',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes',
        'genero_encoded', 'edad', 'ciudad_encoded',
        'cuota_mensual', 'creditos_vigentes', 'creditos_mora', 'hist_neg_12m'
    ]

    # Mapeo de ciudades a códigos (simplificado)
    ciudad_map = {
        'Bogotá': 0, 'Medellín': 1, 'Cali': 2, 'Barranquilla': 3,
        'Cartagena': 4, 'Bucaramanga': 5, 'Manizales': 6
    }

    # Construir instancia
    instance = []
    for feature in feature_order:
        if feature == 'genero_encoded':
            value = 1 if client_data.get('genero', '').upper() == 'M' else 0
        elif feature == 'ciudad_encoded':
            ciudad = client_data.get('ciudad', '')
            value = ciudad_map.get(ciudad, 0)
        elif feature in scores:
            value = scores[feature]
        elif feature in client_data:
            value = client_data[feature]
        else:
            value = 0

        # Convertir booleanos a int
        if isinstance(value, bool):
            value = int(value)

        instance.append(float(value))

    # Llamar a Vertex AI
    prediction = endpoint.predict(instances=[instance])

    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

    # Determinar nivel de riesgo
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

    return {
        'probability_default': round(prob_default, 4),
        'probability_no_default': round(prob_no_default, 4),
        'risk_level': risk_level
    }


# ============================================================================
# FUNCIÓN PRINCIPAL DE LA CLOUD FUNCTION
# ============================================================================

@functions_framework.http
def calculate_scores(request):
    """
    Cloud Function principal

    Recibe datos del cliente desde n8n, calcula scores, retorna JSON
    """
    start_time = time.time()

    # CORS headers
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    if request.method != 'POST':
        return jsonify({'error': 'Only POST method supported'}), 405, headers

    try:
        request_json = request.get_json(silent=True)

        if not request_json:
            return jsonify({'error': 'Request body must be JSON'}), 400, headers

        client_data = request_json.get('client_data', {})
        payments = request_json.get('payments', [])
        payment_plans = request_json.get('payment_plans', [])

        if not client_data:
            return jsonify({'error': 'client_data is required'}), 400, headers

        print(f"\n{'='*70}")
        print(f"🧮 CALCULANDO SCORES")
        print(f"📊 Cliente: {client_data.get('cedula', 'N/A')}")
        print(f"💳 Pagos: {len(payments)}")
        print(f"📋 Planes: {len(payment_plans)}")
        print(f"{'='*70}\n")

        # 1. Calcular componentes PLATAM
        months_as_client = client_data.get('months_as_client', 0)

        payment_perf = calculate_payment_performance(payments, months_as_client)
        payment_plan = calculate_payment_plan_score(payment_plans)
        deterioration = calculate_deterioration_velocity(payments)

        platam_score = (
            payment_perf['total'] +
            payment_plan['total'] +
            deterioration['total']
        )

        print(f"✓ PLATAM Score: {platam_score:.1f}")
        print(f"  • Payment Performance: {payment_perf['total']:.1f}/600")
        print(f"  • Payment Plan: {payment_plan['total']:.1f}/150")
        print(f"  • Deterioration: {deterioration['total']:.1f}/250")

        # 2. Calcular score híbrido
        hybrid_result = calculate_hybrid_score(
            platam_score,
            client_data.get('experian_score'),
            months_as_client,
            payment_perf['payment_count']
        )

        print(f"\n✓ Hybrid Score: {hybrid_result['hybrid_score']:.1f}")
        print(f"  • Peso PLATAM: {hybrid_result['peso_platam']*100:.0f}%")
        print(f"  • Peso HCPN: {hybrid_result['peso_hcpn']*100:.0f}%")

        # 3. Preparar scores completos para ML
        scores_for_ml = {
            'platam_score': platam_score,
            'experian_score': client_data.get('experian_score', 0),
            'score_payment_performance': payment_perf['total'],
            'score_payment_plan': payment_plan['total'],
            'score_deterioration': deterioration['total'],
            'payment_count': payment_perf['payment_count'],
            'months_as_client': months_as_client,
            'pct_early': payment_perf['pct_early'],
            'pct_late': payment_perf['pct_late'],
            'peso_platam': hybrid_result['peso_platam'],
            'peso_hcpn': hybrid_result['peso_hcpn'],
            'tiene_plan_activo': payment_plan['tiene_plan_activo'],
            'tiene_plan_default': payment_plan['tiene_plan_default'],
            'tiene_plan_pendiente': payment_plan['tiene_plan_pendiente'],
            'num_planes': payment_plan['num_planes']
        }

        # 4. Predicción ML
        ml_prediction = get_ml_prediction(client_data, scores_for_ml)

        print(f"\n✓ ML Prediction:")
        print(f"  • Prob Default: {ml_prediction['probability_default']*100:.1f}%")
        print(f"  • Risk Level: {ml_prediction['risk_level']}")

        processing_time_ms = int((time.time() - start_time) * 1000)

        print(f"\n{'='*70}")
        print(f"✅ CÁLCULO COMPLETADO EN {processing_time_ms}ms")
        print(f"{'='*70}\n")

        # Respuesta
        response = {
            'status': 'success',
            'platam_score': round(platam_score, 1),
            'hybrid_score': hybrid_result['hybrid_score'],
            'ml_probability_default': ml_prediction['probability_default'],
            'ml_probability_no_default': ml_prediction['probability_no_default'],
            'ml_risk_level': ml_prediction['risk_level'],
            'peso_platam': hybrid_result['peso_platam'],
            'peso_hcpn': hybrid_result['peso_hcpn'],

            # Componentes
            'score_payment_performance': payment_perf['total'],
            'score_payment_plan': payment_plan['total'],
            'score_deterioration': deterioration['total'],

            # Features adicionales para ML
            'payment_count': payment_perf['payment_count'],
            'pct_early': payment_perf['pct_early'],
            'pct_late': payment_perf['pct_late'],
            'tiene_plan_activo': payment_plan['tiene_plan_activo'],
            'tiene_plan_default': payment_plan['tiene_plan_default'],
            'tiene_plan_pendiente': payment_plan['tiene_plan_pendiente'],
            'num_planes': payment_plan['num_planes'],

            'processing_time_ms': processing_time_ms,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(response), 200, headers

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500, headers
