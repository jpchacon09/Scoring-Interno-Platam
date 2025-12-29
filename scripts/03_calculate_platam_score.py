#!/usr/bin/env python3
"""
Calcula PLATAM Internal Credit Score para cada cliente

Este script:
1. Carga el dataset maestro
2. Calcula los 3 componentes del PLATAM Score
3. Asigna rating crediticio (A+ a F)
4. Compara con Experian Score (HCPN)
5. Genera análisis de correlación y diferencias

Sistema actualizado V2.0 (3 componentes):
- Payment Performance: 600 pts (60%)
- Payment Plan History: 150 pts (15%)
- Deterioration Velocity: 250 pts (25%)

Cambios desde V1.0:
- Eliminados: Purchase Consistency y Utilization (componentes débiles)
- Payment Performance: aumentado de 400 a 600 pts
- Deterioration Velocity: aumentado de 100 a 250 pts

Usage:
    python scripts/03_calculate_platam_score.py
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

# Add parent dir to path to import internal_credit_score
sys.path.append(str(Path(__file__).parent.parent))
from internal_credit_score import (
    calculate_payment_performance,
    calculate_payment_plan_score,
    calculate_deterioration_velocity,
    get_credit_rating,
    calculate_credit_score
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
MASTER_DATASET = PROCESSED_DIR / 'master_dataset.csv'
SCORES_OUTPUT = PROCESSED_DIR / 'platam_scores.csv'
COMPARISON_OUTPUT = PROCESSED_DIR / 'score_comparison.csv'

# Reference date
REFERENCE_DATE = pd.Timestamp('2025-12-19')


def normalize_experian_to_1000(experian_score):
    """
    Normaliza Experian Score (0-924) a escala 0-1000
    """
    if pd.isna(experian_score):
        return np.nan

    # Experian va de 0-924, normalizar a 0-1000
    return (experian_score / 924) * 1000


def calculate_scores_from_master_dataset(df):
    """
    Calcula todos los componentes del PLATAM Score usando el dataset maestro

    El dataset maestro ya tiene features agregadas, pero el nuevo sistema
    requiere data transaccional para cálculos más precisos.

    Esta función adapta los datos del master dataset al formato requerido
    por las funciones de internal_credit_score.py
    """
    logger.info("\n" + "="*80)
    logger.info("CALCULANDO PLATAM SCORES V2.0")
    logger.info("Sistema de 3 componentes")
    logger.info("="*80)

    results = []

    # Preparar datos de pagos si existen
    # El master dataset tiene features agregadas, pero necesitamos
    # simular o reconstruir datos transaccionales si es posible

    logger.info("\n⚠️  NOTA IMPORTANTE:")
    logger.info("Este script usa features agregadas del master dataset.")
    logger.info("Para cálculos precisos del nuevo sistema, se recomienda usar")
    logger.info("scripts/calculate_scores.py con datos transaccionales.")
    logger.info("")

    logger.info(f"Calculando scores para {len(df)} clientes...")

    for idx, row in df.iterrows():
        if idx % 100 == 0:
            logger.info(f"  Procesando cliente {idx+1}/{len(df)}...")

        try:
            client_id = row['cedula']

            # Calcular componentes usando features agregadas
            # Esto es una aproximación basada en el master dataset

            # 1. Payment Performance (600 pts) - basado en features existentes
            score_payment_perf = calculate_payment_performance_from_features(row)

            # 2. Payment Plan History (150 pts)
            score_payment_plan = calculate_payment_plan_from_features(row)

            # 3. Deterioration Velocity (250 pts)
            score_deterioration = calculate_deterioration_from_features(row)

            # Score total
            platam_score = score_payment_perf + score_payment_plan + score_deterioration

            # Rating
            platam_rating = get_credit_rating(platam_score)

            # Normalizar Experian
            experian_norm = normalize_experian_to_1000(row.get('experian_score'))

            result = {
                'cedula': client_id,
                'client_name': row.get('client_name', ''),
                'calculation_date': REFERENCE_DATE.date(),

                # Component scores (3 componentes)
                'score_payment_performance': score_payment_perf,
                'score_payment_plan': score_payment_plan,
                'score_deterioration': score_deterioration,

                # Total
                'platam_score': round(platam_score, 1),
                'platam_rating': platam_rating,

                # Experian comparison
                'experian_score': row.get('experian_score'),
                'experian_score_normalized': experian_norm,

                # Key features from master dataset
                'has_payment_history': row.get('has_payment_history', False),
                'payment_history_months': row.get('payment_history_months', 0),
                'payment_id_count': row.get('payment_id_count', 0),
                'days_past_due_mean': row.get('days_past_due_mean', 0),
                'days_past_due_max': row.get('days_past_due_max', 0),
                'pct_early': row.get('pct_early', 0),
                'pct_late': row.get('pct_late', 0),
                'days_since_last_payment': row.get('days_since_last_payment'),
                'cupo_total': row.get('cupo_total', 0),
                'pct_utilization': row.get('pct_utilization', 0),
                'status_plan': row.get('status_plan'),
                'risk_profile': row.get('risk_profile', ''),
            }

            results.append(result)

        except Exception as e:
            logger.error(f"Error procesando cliente {row.get('cedula')}: {e}")
            continue

    return pd.DataFrame(results)


def calculate_payment_performance_from_features(row):
    """
    Calcula Payment Performance Score (600 pts) usando features agregadas

    Adaptación del componente más importante del nuevo sistema
    """
    if pd.isna(row.get('has_payment_history')) or not row['has_payment_history']:
        return 300  # 50% del máximo si no hay historial

    score = 0

    # 1. Timeliness basado en DPD promedio (300 pts)
    avg_dpd = row.get('days_past_due_mean', 0)

    if pd.isna(avg_dpd):
        timeliness_score = 150
    elif avg_dpd < -15:  # Paga 15+ días antes
        timeliness_score = 300
    elif avg_dpd < 0:  # Paga antes
        timeliness_score = 270
    elif avg_dpd == 0:  # Paga a tiempo
        timeliness_score = 240
    elif avg_dpd <= 5:  # 1-5 días tarde
        timeliness_score = 180
    elif avg_dpd <= 15:  # 6-15 días tarde
        timeliness_score = 120
    elif avg_dpd <= 30:  # 16-30 días tarde
        timeliness_score = 60
    else:  # 30+ días tarde
        timeliness_score = 0

    score += timeliness_score

    # 2. Pattern basado en % de pagos tempranos/tardíos (200 pts)
    pct_early = row.get('pct_early', 0)
    pct_late = row.get('pct_late', 0)

    if pd.notna(pct_early) and pd.notna(pct_late):
        if pct_early >= 80:  # 80%+ pagos tempranos
            pattern_score = 200
        elif pct_early >= 60:
            pattern_score = 160
        elif pct_late <= 10:  # Bajo % de pagos tardíos
            pattern_score = 140
        elif pct_late <= 30:
            pattern_score = 100
        else:
            pattern_score = 40
    else:
        pattern_score = 100

    score += pattern_score

    # 3. Maturity del historial (100 pts)
    history_months = row.get('payment_history_months', 0)

    if pd.isna(history_months):
        maturity_score = 30
    elif history_months >= 12:  # 1+ año
        maturity_score = 100
    elif history_months >= 6:  # 6+ meses
        maturity_score = 70
    elif history_months >= 3:  # 3+ meses
        maturity_score = 50
    else:  # < 3 meses
        maturity_score = 30

    score += maturity_score

    return min(score, 600)  # Cap en 600


def calculate_payment_plan_from_features(row):
    """
    Calcula Payment Plan History Score (150 pts) usando features agregadas
    """
    status_plan = row.get('status_plan')
    risk_profile = row.get('risk_profile', '')

    # Si tiene plan de pago activo, penalizar
    if pd.notna(status_plan):
        return 50  # Penalización por tener plan activo

    # Basarse en risk_profile
    if pd.isna(risk_profile) or risk_profile == '':
        return 100  # Neutro

    risk_lower = str(risk_profile).lower()

    if 'bajo' in risk_lower or 'low' in risk_lower:
        return 150  # Excelente
    elif 'medio' in risk_lower or 'medium' in risk_lower:
        return 100
    elif 'alto' in risk_lower or 'high' in risk_lower:
        return 50
    else:
        return 100


def calculate_deterioration_from_features(row):
    """
    Calcula Deterioration Velocity Score (250 pts) usando features agregadas

    Basado en comparación de DPD máximo vs promedio como proxy
    """
    if pd.isna(row.get('has_payment_history')) or not row['has_payment_history']:
        return 125  # 50% neutro

    max_dpd = row.get('days_past_due_max', 0)
    avg_dpd = row.get('days_past_due_mean', 0)

    if pd.isna(max_dpd) or pd.isna(avg_dpd):
        return 125

    # Si nunca ha tenido mora severa
    if max_dpd <= 5:
        return 250  # Excelente

    # Velocidad de deterioro = qué tan lejos llegó del promedio
    velocity = max_dpd - avg_dpd

    if velocity <= 10:  # Estable
        score = 250
    elif velocity <= 30:  # Deterioro leve
        score = 175
    elif velocity <= 60:  # Deterioro moderado
        score = 100
    else:  # Deterioro severo
        score = 25

    return min(score, 250)


def analyze_scores(df):
    """
    Analiza distribución y estadísticas de scores
    """
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS DE SCORES")
    logger.info("="*80)

    # Estadísticas PLATAM Score
    logger.info("\n--- PLATAM SCORE V2.0 ---")
    logger.info(f"Promedio: {df['platam_score'].mean():.1f}")
    logger.info(f"Mediana: {df['platam_score'].median():.1f}")
    logger.info(f"Mínimo: {df['platam_score'].min():.1f}")
    logger.info(f"Máximo: {df['platam_score'].max():.1f}")
    logger.info(f"Std Dev: {df['platam_score'].std():.1f}")

    # Distribución por rating
    logger.info("\n--- DISTRIBUCIÓN POR RATING ---")
    rating_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D/F']
    rating_counts = df['platam_rating'].value_counts()
    for rating in rating_order:
        if rating in rating_counts.index:
            count = rating_counts[rating]
            pct = count / len(df) * 100
            logger.info(f"{rating}: {count:4} ({pct:5.1f}%)")

    # Promedios por componente (3 componentes)
    logger.info("\n--- PROMEDIO POR COMPONENTE (Sistema V2.0) ---")
    logger.info(f"Payment Performance:    {df['score_payment_performance'].mean():6.1f} / 600 ({df['score_payment_performance'].mean()/600*100:.1f}%)")
    logger.info(f"Payment Plan History:   {df['score_payment_plan'].mean():6.1f} / 150 ({df['score_payment_plan'].mean()/150*100:.1f}%)")
    logger.info(f"Deterioration Velocity: {df['score_deterioration'].mean():6.1f} / 250 ({df['score_deterioration'].mean()/250*100:.1f}%)")

    return df


def compare_with_experian(df):
    """
    Compara PLATAM Score con Experian Score
    """
    logger.info("\n" + "="*80)
    logger.info("COMPARACIÓN PLATAM vs EXPERIAN")
    logger.info("="*80)

    # Filtrar solo clientes con ambos scores
    comparison = df[df['experian_score'].notna()].copy()
    logger.info(f"\nClientes con ambos scores: {len(comparison):,}")

    if len(comparison) == 0:
        logger.warning("No hay clientes con ambos scores para comparar")
        return df

    # Estadísticas comparativas
    logger.info("\n--- ESTADÍSTICAS COMPARATIVAS ---")
    logger.info(f"{'Métrica':<30} {'PLATAM V2.0':<15} {'Experian (norm)':<15}")
    logger.info("-" * 60)
    logger.info(f"{'Promedio':<30} {comparison['platam_score'].mean():>14.1f} {comparison['experian_score_normalized'].mean():>14.1f}")
    logger.info(f"{'Mediana':<30} {comparison['platam_score'].median():>14.1f} {comparison['experian_score_normalized'].median():>14.1f}")
    logger.info(f"{'Mínimo':<30} {comparison['platam_score'].min():>14.1f} {comparison['experian_score_normalized'].min():>14.1f}")
    logger.info(f"{'Máximo':<30} {comparison['platam_score'].max():>14.1f} {comparison['experian_score_normalized'].max():>14.1f}")
    logger.info(f"{'Std Dev':<30} {comparison['platam_score'].std():>14.1f} {comparison['experian_score_normalized'].std():>14.1f}")

    # Diferencia
    comparison['score_diff'] = comparison['platam_score'] - comparison['experian_score_normalized']
    comparison['score_diff_abs'] = comparison['score_diff'].abs()

    logger.info("\n--- DIFERENCIAS (PLATAM - Experian) ---")
    logger.info(f"Diferencia promedio: {comparison['score_diff'].mean():+.1f} puntos")
    logger.info(f"Diferencia mediana: {comparison['score_diff'].median():+.1f} puntos")
    logger.info(f"Diferencia absoluta promedio: {comparison['score_diff_abs'].mean():.1f} puntos")
    logger.info(f"Diferencia máxima: {comparison['score_diff_abs'].max():.1f} puntos")

    # Correlación
    correlation = comparison['platam_score'].corr(comparison['experian_score_normalized'])
    logger.info(f"\nCorrelación (Pearson): {correlation:.3f}")

    # Categorías de diferencia
    logger.info("\n--- CATEGORIZACIÓN DE DIFERENCIAS ---")
    comparison['diff_category'] = pd.cut(
        comparison['score_diff_abs'],
        bins=[0, 50, 100, 150, 200, np.inf],
        labels=['Muy Similar (0-50)', 'Similar (50-100)', 'Moderada (100-150)', 'Alta (150-200)', 'Muy Alta (200+)']
    )

    diff_dist = comparison['diff_category'].value_counts().sort_index()
    for cat, count in diff_dist.items():
        pct = count / len(comparison) * 100
        logger.info(f"{cat}: {count:4} ({pct:5.1f}%)")

    # Casos donde PLATAM es mucho mejor que Experian
    much_better = comparison[comparison['score_diff'] > 150]
    logger.info(f"\nCasos PLATAM >> Experian (+150): {len(much_better)} ({len(much_better)/len(comparison)*100:.1f}%)")

    # Casos donde PLATAM es mucho peor que Experian
    much_worse = comparison[comparison['score_diff'] < -150]
    logger.info(f"Casos PLATAM << Experian (-150): {len(much_worse)} ({len(much_worse)/len(comparison)*100:.1f}%)")

    # Guardar comparación
    comparison_file = COMPARISON_OUTPUT
    comparison.to_csv(comparison_file, index=False)
    logger.info(f"\n✓ Comparación guardada en: {comparison_file.name}")

    return df


def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("PLATAM INTERNAL CREDIT SCORE CALCULATOR V2.0")
    logger.info("Sistema de 3 componentes")
    logger.info("="*80)

    # Cargar dataset maestro
    logger.info(f"\nCargando dataset maestro: {MASTER_DATASET.name}")
    df = pd.read_csv(MASTER_DATASET)
    logger.info(f"✓ Cargados {len(df):,} clientes")

    # Calcular scores
    df = calculate_scores_from_master_dataset(df)

    # Analizar scores
    df = analyze_scores(df)

    # Comparar con Experian
    df = compare_with_experian(df)

    # Guardar resultados
    logger.info("\n" + "="*80)
    logger.info("GUARDANDO RESULTADOS")
    logger.info("="*80)

    # Guardar scores completos
    df.to_csv(SCORES_OUTPUT, index=False)
    logger.info(f"✓ Scores guardados en: {SCORES_OUTPUT.name}")
    logger.info(f"  Tamaño: {SCORES_OUTPUT.stat().st_size / 1024 / 1024:.2f} MB")

    # Crear resumen por rating
    summary = df.groupby('platam_rating').agg({
        'platam_score': ['count', 'mean', 'min', 'max'],
        'experian_score': 'mean',
        'cupo_total': 'mean',
        'pct_utilization': 'mean'
    }).round(1)

    logger.info("\n--- RESUMEN POR RATING ---")
    logger.info(summary.to_string())

    logger.info("\n" + "="*80)
    logger.info("✅ CÁLCULO DE SCORES COMPLETADO")
    logger.info("="*80)
    logger.info(f"\nArchivos generados:")
    logger.info(f"  - {SCORES_OUTPUT}")
    logger.info(f"  - {COMPARISON_OUTPUT}")

    logger.info("\n💡 Cambios del sistema V2.0:")
    logger.info("  ✅ Eliminados: Purchase Consistency y Utilization")
    logger.info("  ✅ Payment Performance: 400 → 600 pts (+50%)")
    logger.info("  ✅ Deterioration Velocity: 100 → 250 pts (+150%)")
    logger.info("  ✅ Payment Plan History: 150 pts (sin cambios)")

    return df


if __name__ == '__main__':
    main()
