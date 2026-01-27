#!/usr/bin/env python3
"""
PLATAM - Cloud Function para CALCULAR Scores + Descargar HCPN de S3
====================================================================

Esta función:
1. Recibe datos del cliente desde n8n (pagos, préstamos)
2. Descarga HCPN de S3 (solo el archivo específico)
3. Calcula scores PLATAM + Híbrido
4. Llama Vertex AI para predicción ML
5. Retorna scores calculados

Input (POST):
    {
        "cedula": "1116614340",
        "client_data": {
            "months_as_client": 8,
            "ciudad": "Barranquilla"
        },
        "payments": [...],
        "loans": [...]  // Préstamos para calcular créditos vigentes/mora
    }

Output:
    {
        "status": "success",
        "platam_score": 730.5,
        "hybrid_score": 745.2,
        "ml_probability_default": 0.12,
        ...
    }

Autor: PLATAM Data Team
Fecha: Enero 2026
"""

import functions_framework
from flask import jsonify
import pandas as pd
import numpy as np
from google.cloud import aiplatform
import boto3
import json
import os
from datetime import datetime
import time
from typing import Dict, List, Optional

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Vertex AI
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"  # Modelo v2.2 con demografía

# AWS S3 (para HCPN)
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = os.getenv('S3_HCPN_BUCKET', 'fft-analytics-data-lake')
S3_PREFIX = os.getenv('S3_PREFIX', 'ppay/prod/')

# Inicializar Vertex AI
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)

# ============================================================================
# FUNCIONES PARA S3
# ============================================================================

def get_s3_client():
    """Crea cliente S3"""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name='us-east-1'
    )


def download_hcpn_from_s3(cedula: str) -> Optional[Dict]:
    """
    Descarga archivo HCPN específico de S3

    Busca archivos que empiecen con hcpn_{cedula} (pueden tener fecha al final)
    Ej: hcpn_66661722_20240115.json
    """
    s3_client = get_s3_client()

    # Listar archivos que empiecen con hcpn_{cedula}
    prefix_to_search = f'{S3_PREFIX}hcpn_{cedula}'

    try:
        print(f"  Buscando archivos con prefix: s3://{S3_BUCKET}/{prefix_to_search}*")

        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix_to_search
        )

        if 'Contents' not in response or len(response['Contents']) == 0:
            # Intentar sin el prefix ppay/prod/ (por si está en raíz)
            prefix_to_search_root = f'hcpn_{cedula}'
            print(f"  No encontrado, intentando sin prefix: s3://{S3_BUCKET}/{prefix_to_search_root}*")

            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=prefix_to_search_root
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                print(f"  ⚠ No se encontró ningún archivo HCPN para cédula {cedula}")
                return None

        # Tomar el archivo más reciente (por si hay varios)
        files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
        most_recent = files[0]
        key = most_recent['Key']

        print(f"  Encontrado: {key} (modificado: {most_recent['LastModified']})")

        # Descargar el archivo
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        hcpn_data = json.loads(response['Body'].read())

        print(f"  ✓ HCPN descargado exitosamente: {key}")
        return hcpn_data

    except Exception as e:
        print(f"  ⚠ Error descargando HCPN para cédula {cedula}: {e}")
        return None


def extract_hcpn_demographics(hcpn_data: Dict) -> Dict:
    """
    Extrae datos demográficos de HCPN en formato Experian

    Estructura real de HCPN de Experian:
    {
      "Informes": {
        "Informe": {
          "Score": {"@puntaje": 796.0, ...},
          "NaturalNacional": {
            "@genero": 3,
            "Edad": {"@min": 36, "@max": 45},
            "Identificacion": {"@ciudad": "BOGOTA", ...}
          },
          "CuentaCartera": [...],
          "TarjetaCredito": [...],
          ...
        }
      }
    }
    """
    demographics = {}

    try:
        # Navegar a la estructura base
        informe = hcpn_data.get('Informes', {}).get('Informe', {})

        if not informe:
            print("  ⚠ Estructura HCPN inválida: no se encontró 'Informes.Informe'")
            return {
                'experian_score': 0,
                'edad': 35,
                'genero': 'M',
                'ciudad': 'UNKNOWN',
                'cuota_mensual': 0,
                'creditos_vigentes': 0,
                'creditos_mora': 0,
                'hist_neg_12m': 0
            }

        # 1. Score Experian
        score = informe.get('Score', {})
        if '@puntaje' in score:
            demographics['experian_score'] = float(score['@puntaje'])
        else:
            demographics['experian_score'] = 0
            print("  ⚠ No se encontró score en HCPN")

        # 2. Datos de persona natural
        natural = informe.get('NaturalNacional', {})

        # Edad (promedio entre min y max)
        edad_info = natural.get('Edad', {})
        if '@min' in edad_info and '@max' in edad_info:
            edad_min = int(edad_info['@min'])
            edad_max = int(edad_info['@max'])
            demographics['edad'] = int((edad_min + edad_max) / 2)
        else:
            demographics['edad'] = 35
            print("  ⚠ No se encontró edad en HCPN")

        # Género (Experian usa código: 1=M, 2=F, 3=Otro)
        genero_codigo = natural.get('@genero')
        if genero_codigo == '1' or genero_codigo == 1:
            demographics['genero'] = 'M'
        elif genero_codigo == '2' or genero_codigo == 2:
            demographics['genero'] = 'F'
        elif genero_codigo == '3' or genero_codigo == 3:
            demographics['genero'] = 'F'  # Asumimos F por defecto
        else:
            demographics['genero'] = 'M'

        # Ciudad de expedición de la cédula
        identificacion = natural.get('Identificacion', {})
        ciudad = identificacion.get('@ciudad', 'UNKNOWN')
        demographics['ciudad'] = ciudad if ciudad else 'UNKNOWN'

        # 3. Análisis de créditos vigentes y mora
        cuenta_cartera = informe.get('CuentaCartera', [])
        tarjeta_credito = informe.get('TarjetaCredito', [])

        creditos_vigentes = 0
        creditos_mora = 0
        cuota_total = 0
        hist_neg_12m = 0

        # Analizar cuentas de cartera
        for cuenta in cuenta_cartera:
            # Cuenta como vigente si no está cerrada
            estado_cuenta = cuenta.get('@estadoCuenta', '')
            if estado_cuenta != '2':  # 2 = cerrada
                creditos_vigentes += 1

            # Contar mora (calificación > 1 indica mora)
            calificacion = cuenta.get('@calificacion', '0')
            try:
                if int(calificacion) > 1:
                    creditos_mora += 1
            except:
                pass

            # Sumar cuota mensual
            cuota = cuenta.get('@valorCuota', 0)
            try:
                cuota_total += float(cuota)
            except:
                pass

            # Verificar comportamiento últimos 12 meses (últimos 12 caracteres)
            comportamiento = cuenta.get('@comportamiento', '')
            if comportamiento and len(comportamiento) >= 12:
                ultimos_12 = comportamiento[-12:]
                # Si hay alguna letra diferente de 'N' (normal), hay historia negativa
                if any(c not in ['N', ' ', '-'] for c in ultimos_12):
                    hist_neg_12m += 1

        # Analizar tarjetas de crédito
        for tarjeta in tarjeta_credito:
            # Cuenta como vigente si no está cerrada
            estado = tarjeta.get('@estadoCuenta', '')
            if estado != '2':  # 2 = cerrada
                creditos_vigentes += 1

            # Contar mora
            calificacion = tarjeta.get('@calificacion', '0')
            try:
                if int(calificacion) > 1:
                    creditos_mora += 1
            except:
                pass

            # Sumar cuota mínima o pago mensual
            cuota = tarjeta.get('@valorCuota', 0)
            try:
                cuota_total += float(cuota)
            except:
                pass

            # Verificar comportamiento últimos 12 meses
            comportamiento = tarjeta.get('@comportamiento', '')
            if comportamiento and len(comportamiento) >= 12:
                ultimos_12 = comportamiento[-12:]
                if any(c not in ['N', ' ', '-'] for c in ultimos_12):
                    hist_neg_12m += 1

        demographics['cuota_mensual'] = cuota_total
        demographics['creditos_vigentes'] = creditos_vigentes
        demographics['creditos_mora'] = creditos_mora
        demographics['hist_neg_12m'] = hist_neg_12m

        print(f"  ✓ Datos HCPN extraídos: score={demographics['experian_score']}, edad={demographics['edad']}, "
              f"ciudad={demographics['ciudad']}, créditos={creditos_vigentes}, mora={creditos_mora}")

    except Exception as e:
        print(f"  ⚠ Error extrayendo demografía de HCPN: {e}")
        import traceback
        traceback.print_exc()
        # Retornar valores por defecto en caso de error
        demographics = {
            'experian_score': 0,
            'edad': 35,
            'genero': 'M',
            'ciudad': 'UNKNOWN',
            'cuota_mensual': 0,
            'creditos_vigentes': 0,
            'creditos_mora': 0,
            'hist_neg_12m': 0
        }

    return demographics

# ============================================================================
# FUNCIONES DE SCORING (iguales que antes)
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

    recent_dpds = [p.get('days_past_due', 0) for p in payments[:min(6, len(payments))]]
    pattern_score = max(0, 100 - np.std(recent_dpds) * 2) if len(recent_dpds) > 1 else 50

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

    pesos = {
        'muy_nuevo': 0.30,
        'nuevo': 0.40,
        'intermedio': 0.50,
        'establecido': 0.60,
        'maduro': 0.70
    }

    if hcpn_score is None or pd.isna(hcpn_score) or hcpn_score == 0:
        peso_platam = 1.0
        peso_hcpn = 0.0
        hybrid_score = platam_score
    else:
        peso_platam = pesos[categoria]

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


def get_ml_prediction(client_data: Dict, scores: Dict, hcpn_demographics: Dict) -> Dict:
    """Llama a Vertex AI para obtener predicción ML (modelo v2.2: 22 features)"""

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

    ciudad_map = {
        'Bogotá': 0, 'Medellín': 1, 'Cali': 2, 'Barranquilla': 3,
        'Cartagena': 4, 'Bucaramanga': 5, 'Manizales': 6, 'MANI': 6
    }

    instance = []
    for feature in feature_order:
        if feature == 'genero_encoded':
            value = 1 if hcpn_demographics.get('genero', '').upper() == 'M' else 0
        elif feature == 'ciudad_encoded':
            ciudad = client_data.get('ciudad', '')
            value = ciudad_map.get(ciudad, 0)
        elif feature in hcpn_demographics:
            value = hcpn_demographics[feature]
        elif feature in scores:
            value = scores[feature]
        elif feature in client_data:
            value = client_data[feature]
        else:
            value = 0

        if isinstance(value, bool):
            value = int(value)

        instance.append(float(value))

    prediction = endpoint.predict(instances=[instance])

    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

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
# FUNCIÓN PRINCIPAL
# ============================================================================

@functions_framework.http
def calculate_scores(request):
    """Cloud Function principal"""
    start_time = time.time()

    # CORS
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    if request.method != 'POST':
        return jsonify({'error': 'Only POST method supported'}), 405, headers

    try:
        request_json = request.get_json(silent=True)

        if not request_json:
            return jsonify({'error': 'Request body must be JSON'}), 400, headers

        cedula = request_json.get('cedula')
        client_data = request_json.get('client_data', {})
        payments = request_json.get('payments', [])
        payment_plans = request_json.get('payment_plans', [])

        if not cedula:
            return jsonify({'error': 'cedula is required'}), 400, headers

        print(f"\n{'='*70}")
        print(f"🧮 CALCULANDO SCORES PARA CÉDULA: {cedula}")
        print(f"{'='*70}\n")

        # 1. Descargar HCPN de S3
        print("📥 1. Descargando HCPN de S3...")
        hcpn_data = download_hcpn_from_s3(cedula)

        if hcpn_data:
            hcpn_demographics = extract_hcpn_demographics(hcpn_data)
        else:
            print("  ⚠ Usando valores por defecto para demografía")
            hcpn_demographics = {
                'experian_score': 0,
                'edad': 35,
                'genero': 'M',
                'cuota_mensual': 0,
                'creditos_vigentes': 0,
                'creditos_mora': 0,
                'hist_neg_12m': 0
            }

        # 2. Calcular scores PLATAM
        print(f"\n🧮 2. Calculando scores PLATAM...")
        print(f"   • Pagos recibidos: {len(payments)}")
        print(f"   • Planes de pago: {len(payment_plans)}")

        months_as_client = client_data.get('months_as_client', 0)

        payment_perf = calculate_payment_performance(payments, months_as_client)
        payment_plan = calculate_payment_plan_score(payment_plans)
        deterioration = calculate_deterioration_velocity(payments)

        platam_score = (
            payment_perf['total'] +
            payment_plan['total'] +
            deterioration['total']
        )

        print(f"\n   ✓ PLATAM Score: {platam_score:.1f}")
        print(f"      • Payment Performance: {payment_perf['total']:.1f}/600")
        print(f"      • Payment Plan: {payment_plan['total']:.1f}/150")
        print(f"      • Deterioration: {deterioration['total']:.1f}/250")

        # 3. Calcular híbrido
        print(f"\n🔀 3. Calculando score híbrido...")
        hybrid_result = calculate_hybrid_score(
            platam_score,
            hcpn_demographics.get('experian_score'),
            months_as_client,
            payment_perf['payment_count']
        )

        print(f"   ✓ Hybrid Score: {hybrid_result['hybrid_score']:.1f}")
        print(f"      • Peso PLATAM: {hybrid_result['peso_platam']*100:.0f}%")
        print(f"      • Peso HCPN: {hybrid_result['peso_hcpn']*100:.0f}%")

        # 4. Predicción ML
        print(f"\n🤖 4. Obteniendo predicción ML...")

        scores_for_ml = {
            'platam_score': platam_score,
            'experian_score': hcpn_demographics.get('experian_score', 0),
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

        ml_prediction = get_ml_prediction(client_data, scores_for_ml, hcpn_demographics)

        print(f"   ✓ Probabilidad Default: {ml_prediction['probability_default']*100:.1f}%")
        print(f"   ✓ Nivel de Riesgo: {ml_prediction['risk_level']}")

        processing_time_ms = int((time.time() - start_time) * 1000)

        print(f"\n{'='*70}")
        print(f"✅ CÁLCULO COMPLETADO EN {processing_time_ms}ms")
        print(f"{'='*70}\n")

        # Respuesta
        response = {
            'status': 'success',
            'cedula': cedula,
            'platam_score': round(platam_score, 1),
            'hybrid_score': hybrid_result['hybrid_score'],
            'ml_probability_default': ml_prediction['probability_default'],
            'ml_probability_no_default': ml_prediction['probability_no_default'],
            'ml_risk_level': ml_prediction['risk_level'],
            'peso_platam': hybrid_result['peso_platam'],
            'peso_hcpn': hybrid_result['peso_hcpn'],
            'score_payment_performance': payment_perf['total'],
            'score_payment_plan': payment_plan['total'],
            'score_deterioration': deterioration['total'],
            'payment_count': payment_perf['payment_count'],
            'pct_early': payment_perf['pct_early'],
            'pct_late': payment_perf['pct_late'],
            'tiene_plan_activo': payment_plan['tiene_plan_activo'],
            'tiene_plan_default': payment_plan['tiene_plan_default'],
            'tiene_plan_pendiente': payment_plan['tiene_plan_pendiente'],
            'num_planes': payment_plan['num_planes'],
            'processing_time_ms': processing_time_ms,
            'timestamp': datetime.now().isoformat(),
            'hcpn_found': hcpn_data is not None
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
