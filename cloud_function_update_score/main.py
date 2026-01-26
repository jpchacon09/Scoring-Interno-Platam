#!/usr/bin/env python3
"""
PLATAM - Cloud Function para Actualización Individual de Scores
================================================================

Recibe triggers de eventos de negocio y actualiza el score de UN cliente específico.

Input (POST):
    {
        "client_id": "1120",  // ID interno de MySQL (wp_jet_cct_clientes._ID)
        "trigger": "late_7"   // Tipo de evento
    }

Output:
    {
        "status": "success",
        "client_id": "1120",
        "cedula": "128282",
        "platam_score": 730.5,
        "hybrid_score": 745.2,
        "ml_probability_default": 0.12,
        "ml_risk_level": "Bajo",
        "processing_time_ms": 2847,
        "trigger": "late_7"
    }

Autor: PLATAM Data Team
Fecha: Enero 2026
"""

import functions_framework
from flask import jsonify
import pymysql
import pandas as pd
import numpy as np
from google.cloud import aiplatform
from datetime import datetime, timedelta
import json
import time
import os
from typing import Dict, Optional, List

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Vertex AI
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"  # Modelo v2.2 con demografía

# MySQL - Usar variables de entorno en producción
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'TU_HOST_MYSQL'),  # Configura en deployment
    'user': os.getenv('MYSQL_USER', 'TU_USUARIO'),
    'password': os.getenv('MYSQL_PASSWORD', 'TU_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE', 'platam_db'),
    'charset': 'utf8mb4'
}

# Inicializar Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

# ============================================================================
# FUNCIONES DE SCORING REUTILIZADAS (simplificadas)
# ============================================================================

def calculate_payment_performance(payments_df: pd.DataFrame, months_as_client: int) -> Dict:
    """Calcula Payment Performance Score (600 pts)"""

    if len(payments_df) < 3:
        return {
            'timeliness_score': 50,
            'pattern_score': 50,
            'total': 300,
            'payment_count': len(payments_df)
        }

    # Calcular score de timeliness
    payments_df['payment_quality'] = payments_df['days_past_due'].apply(
        lambda dpd: 100 if dpd <= 0 else max(0, 100 - dpd * 3)
    )
    timeliness_score = payments_df['payment_quality'].mean()

    # Pattern score (consistencia)
    recent_6mo = payments_df.head(min(6, len(payments_df)))
    pattern_score = max(0, 100 - recent_6mo['days_past_due'].std() * 2) if len(recent_6mo) > 0 else 50

    # Pesos según madurez
    if months_as_client < 6:
        timeliness_weight, pattern_weight = 0.85, 0.15
    elif months_as_client < 12:
        timeliness_weight, pattern_weight = 0.70, 0.30
    else:
        timeliness_weight, pattern_weight = 0.50, 0.50

    total = (timeliness_score * timeliness_weight + pattern_score * pattern_weight) * 6

    return {
        'timeliness_score': round(timeliness_score, 1),
        'pattern_score': round(pattern_score, 1),
        'total': round(total, 1),
        'payment_count': len(payments_df)
    }


def calculate_payment_plan_score(payment_plans_df: pd.DataFrame) -> Dict:
    """Calcula Payment Plan History Score (150 pts)"""

    if len(payment_plans_df) == 0:
        return {'total': 150, 'active_plans': 0, 'defaulted_plans': 0}

    score = 150
    active = len(payment_plans_df[payment_plans_df['plan_status'] == 'active'])
    completed = len(payment_plans_df[payment_plans_df['plan_status'] == 'completed'])
    defaulted = len(payment_plans_df[payment_plans_df['plan_status'] == 'defaulted'])

    score -= (active * 50) + (defaulted * 100) - (completed * 30)
    score = max(0, min(150, score))

    return {
        'total': round(score, 1),
        'active_plans': active,
        'defaulted_plans': defaulted
    }


def calculate_deterioration_velocity(payments_df: pd.DataFrame) -> Dict:
    """Calcula Deterioration Velocity Score (250 pts)"""

    if len(payments_df) < 3:
        return {'total': 125, 'dpd_1mo': 0, 'dpd_6mo': 0, 'trend_delta': 0}

    # Últimos 1 mes vs últimos 6 meses
    payments_1mo = payments_df.head(min(1, len(payments_df)))
    payments_6mo = payments_df.head(min(6, len(payments_df)))

    dpd_1mo = payments_1mo['days_past_due'].mean() if len(payments_1mo) > 0 else 0
    dpd_6mo = payments_6mo['days_past_due'].mean() if len(payments_6mo) > 0 else 0

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
    if hcpn_score is None or pd.isna(hcpn_score):
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

# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def get_db_connection():
    """Crea conexión a MySQL"""
    return pymysql.connect(**MYSQL_CONFIG)


def get_client_data(client_id: str) -> Optional[Dict]:
    """
    Obtiene datos del cliente desde MySQL
    Tabla: wp_jet_cct_clientes
    """
    conn = get_db_connection()
    try:
        query = f"""
        SELECT
            _ID as client_id,
            cl_cedula as cedula,
            cl_nombre as client_name,
            cl_email as email,
            cl_ciudad as ciudad,
            cl_genero as genero,
            cl_edad as edad,
            cl_cuota_mensual as cuota_mensual,
            cl_creditos_vigentes as creditos_vigentes,
            cl_creditos_mora as creditos_mora,
            cl_hist_neg_12m as hist_neg_12m,
            cl_platam_score as platam_score_anterior,
            cl_hybrid_score as hybrid_score_anterior,
            cl_experian_score as experian_score_normalized,
            cl_months_as_client as months_as_client
        FROM wp_jet_cct_clientes
        WHERE _ID = {client_id}
        LIMIT 1
        """

        df = pd.read_sql(query, conn)

        if df.empty:
            return None

        return df.iloc[0].to_dict()

    finally:
        conn.close()


def get_payments_history(cedula: str, limit: int = 100) -> pd.DataFrame:
    """
    Obtiene historial de pagos del cliente
    Tabla: wp_pagos (ajusta según tu estructura)
    """
    conn = get_db_connection()
    try:
        query = f"""
        SELECT
            payment_id,
            payment_date,
            due_date,
            DATEDIFF(payment_date, due_date) as days_past_due,
            payment_amount,
            payment_status
        FROM wp_pagos
        WHERE client_cedula = '{cedula}'
        ORDER BY payment_date DESC
        LIMIT {limit}
        """

        df = pd.read_sql(query, conn)
        return df

    finally:
        conn.close()


def get_payment_plans(cedula: str) -> pd.DataFrame:
    """
    Obtiene planes de pago del cliente
    Tabla: wp_payment_plans (ajusta según tu estructura)
    """
    conn = get_db_connection()
    try:
        query = f"""
        SELECT
            plan_id,
            plan_start_date,
            plan_end_date,
            plan_status,
            plan_amount
        FROM wp_payment_plans
        WHERE client_cedula = '{cedula}'
        ORDER BY plan_start_date DESC
        """

        df = pd.read_sql(query, conn)
        return df

    finally:
        conn.close()


def update_client_scores(client_id: str, scores: Dict, trigger: str):
    """Actualiza scores en MySQL"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        update_query = f"""
        UPDATE wp_jet_cct_clientes
        SET
            cl_platam_score = {scores['platam_score']},
            cl_hybrid_score = {scores['hybrid_score']},
            cl_ml_probability_default = {scores['ml_probability_default']},
            cl_ml_risk_level = '{scores['ml_risk_level']}',
            cl_score_payment_performance = {scores.get('score_payment_performance', 0)},
            cl_score_payment_plan = {scores.get('score_payment_plan', 0)},
            cl_score_deterioration = {scores.get('score_deterioration', 0)},
            cl_peso_platam = {scores.get('peso_platam', 0)},
            cl_peso_experian = {scores.get('peso_hcpn', 0)},
            cl_last_update_trigger = '{trigger}',
            cl_modified = NOW()
        WHERE _ID = {client_id}
        """

        cursor.execute(update_query)
        conn.commit()

        print(f"✅ Scores actualizados en MySQL para client_id={client_id}")

    finally:
        conn.close()

# ============================================================================
# PREDICCIÓN ML CON VERTEX AI
# ============================================================================

def get_ml_prediction(client_data: Dict, scores: Dict) -> Dict:
    """
    Llama a Vertex AI para obtener predicción ML
    Modelo v2.2: 22 features
    """

    # Preparar features en el orden correcto
    feature_order = [
        'platam_score', 'experian_score_normalized',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'payment_count', 'months_as_client',
        'pct_early', 'pct_late',
        'peso_platam', 'peso_hcpn',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes',
        'genero_encoded', 'edad', 'ciudad_encoded',
        'cuota_mensual', 'creditos_vigentes', 'creditos_mora', 'hist_neg_12m'
    ]

    # Mapeo de valores
    data_map = {
        'platam_score': scores.get('platam_score', 0),
        'experian_score_normalized': client_data.get('experian_score_normalized', 0),
        'score_payment_performance': scores.get('score_payment_performance', 0),
        'score_payment_plan': scores.get('score_payment_plan', 0),
        'score_deterioration': scores.get('score_deterioration', 0),
        'payment_count': scores.get('payment_count', 0),
        'months_as_client': client_data.get('months_as_client', 0),
        'pct_early': scores.get('pct_early', 0),
        'pct_late': scores.get('pct_late', 0),
        'peso_platam': scores.get('peso_platam', 0),
        'peso_hcpn': scores.get('peso_hcpn', 0),
        'tiene_plan_activo': scores.get('tiene_plan_activo', 0),
        'tiene_plan_default': scores.get('tiene_plan_default', 0),
        'tiene_plan_pendiente': scores.get('tiene_plan_pendiente', 0),
        'num_planes': scores.get('num_planes', 0),
        'genero_encoded': 1 if client_data.get('genero') == 'M' else 0,
        'edad': client_data.get('edad', 35),
        'ciudad_encoded': hash(str(client_data.get('ciudad', ''))) % 100,  # Simplificado
        'cuota_mensual': client_data.get('cuota_mensual', 0),
        'creditos_vigentes': client_data.get('creditos_vigentes', 0),
        'creditos_mora': client_data.get('creditos_mora', 0),
        'hist_neg_12m': client_data.get('hist_neg_12m', 0)
    }

    # Construir instancia
    instance = []
    for feature in feature_order:
        value = data_map.get(feature, 0)
        if pd.isna(value) or value is None:
            value = 0
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
def update_client_score(request):
    """
    Cloud Function principal

    Recibe:
        POST {"client_id": "1120", "trigger": "late_7"}

    Retorna:
        {"status": "success", ...}
    """
    start_time = time.time()

    # Parse request
    if request.method != 'POST':
        return jsonify({'error': 'Only POST method supported'}), 405

    try:
        request_json = request.get_json(silent=True)

        if not request_json:
            return jsonify({'error': 'Request body must be JSON'}), 400

        client_id = request_json.get('client_id')
        trigger = request_json.get('trigger', 'manual')

        if not client_id:
            return jsonify({'error': 'client_id is required'}), 400

        print(f"\n{'='*70}")
        print(f"🔄 RECALCULANDO SCORE PARA CLIENT_ID: {client_id}")
        print(f"📌 Trigger: {trigger}")
        print(f"{'='*70}\n")

        # 1. Obtener datos del cliente
        print("📊 1. Consultando datos del cliente...")
        client_data = get_client_data(client_id)

        if not client_data:
            return jsonify({'error': f'Client {client_id} not found'}), 404

        cedula = client_data['cedula']
        print(f"   ✓ Cliente encontrado: {cedula}")

        # 2. Obtener historial de pagos
        print("💳 2. Consultando historial de pagos...")
        payments_df = get_payments_history(cedula)
        print(f"   ✓ {len(payments_df)} pagos encontrados")

        # 3. Obtener planes de pago
        print("📋 3. Consultando planes de pago...")
        payment_plans_df = get_payment_plans(cedula)
        print(f"   ✓ {len(payment_plans_df)} planes encontrados")

        # 4. Recalcular scores PLATAM
        print("🧮 4. Recalculando scores PLATAM...")

        payment_perf = calculate_payment_performance(
            payments_df,
            client_data['months_as_client']
        )
        payment_plan = calculate_payment_plan_score(payment_plans_df)
        deterioration = calculate_deterioration_velocity(payments_df)

        platam_score = (
            payment_perf['total'] +
            payment_plan['total'] +
            deterioration['total']
        )

        print(f"   ✓ PLATAM Score: {platam_score:.1f}")
        print(f"      • Payment Performance: {payment_perf['total']:.1f}/600")
        print(f"      • Payment Plan: {payment_plan['total']:.1f}/150")
        print(f"      • Deterioration: {deterioration['total']:.1f}/250")

        # 5. Calcular score híbrido
        print("🔀 5. Calculando score híbrido...")

        hybrid_result = calculate_hybrid_score(
            platam_score,
            client_data.get('experian_score_normalized'),
            client_data['months_as_client'],
            payment_perf['payment_count']
        )

        print(f"   ✓ Hybrid Score: {hybrid_result['hybrid_score']:.1f}")
        print(f"      • Peso PLATAM: {hybrid_result['peso_platam']*100:.0f}%")
        print(f"      • Peso HCPN: {hybrid_result['peso_hcpn']*100:.0f}%")

        # 6. Obtener predicción ML
        print("🤖 6. Obteniendo predicción ML de Vertex AI...")

        # Preparar scores completos para ML
        scores_for_ml = {
            'platam_score': platam_score,
            'score_payment_performance': payment_perf['total'],
            'score_payment_plan': payment_plan['total'],
            'score_deterioration': deterioration['total'],
            'payment_count': payment_perf['payment_count'],
            'peso_platam': hybrid_result['peso_platam'],
            'peso_hcpn': hybrid_result['peso_hcpn'],
            'tiene_plan_activo': payment_plan['active_plans'] > 0,
            'tiene_plan_default': payment_plan['defaulted_plans'] > 0,
            'tiene_plan_pendiente': 0,
            'num_planes': len(payment_plans_df),
            'pct_early': 0,  # Calcular si tienes datos
            'pct_late': 0
        }

        ml_prediction = get_ml_prediction(client_data, scores_for_ml)

        print(f"   ✓ Probabilidad Default: {ml_prediction['probability_default']*100:.1f}%")
        print(f"   ✓ Nivel de Riesgo: {ml_prediction['risk_level']}")

        # 7. Actualizar MySQL
        print("💾 7. Actualizando MySQL...")

        final_scores = {
            'platam_score': platam_score,
            'hybrid_score': hybrid_result['hybrid_score'],
            'ml_probability_default': ml_prediction['probability_default'],
            'ml_risk_level': ml_prediction['risk_level'],
            'score_payment_performance': payment_perf['total'],
            'score_payment_plan': payment_plan['total'],
            'score_deterioration': deterioration['total'],
            'peso_platam': hybrid_result['peso_platam'],
            'peso_hcpn': hybrid_result['peso_hcpn']
        }

        update_client_scores(client_id, final_scores, trigger)

        processing_time_ms = int((time.time() - start_time) * 1000)

        print(f"\n{'='*70}")
        print(f"✅ ACTUALIZACIÓN COMPLETADA EN {processing_time_ms}ms")
        print(f"{'='*70}\n")

        # Respuesta
        return jsonify({
            'status': 'success',
            'client_id': client_id,
            'cedula': cedula,
            'platam_score': round(platam_score, 1),
            'hybrid_score': hybrid_result['hybrid_score'],
            'ml_probability_default': ml_prediction['probability_default'],
            'ml_probability_no_default': ml_prediction['probability_no_default'],
            'ml_risk_level': ml_prediction['risk_level'],
            'peso_platam': hybrid_result['peso_platam'],
            'peso_hcpn': hybrid_result['peso_hcpn'],
            'trigger': trigger,
            'processing_time_ms': processing_time_ms,
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
