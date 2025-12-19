#!/usr/bin/env python3
"""
Calcula PLATAM Internal Credit Score para cada cliente

Este script:
1. Carga el dataset maestro
2. Calcula los 5 componentes del PLATAM Score
3. Asigna rating crediticio (A+ a F)
4. Compara con Experian Score (HCPN)
5. Genera análisis de correlación y diferencias

Usage:
    python scripts/03_calculate_platam_score.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import seaborn as sns

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

def calculate_payment_performance_score(row):
    """
    Componente 1: Payment Performance (400 puntos)

    Basado en:
    - Puntualidad de pagos (DPD)
    - Patrón de pagos
    - Madurez del historial
    """
    if pd.isna(row['has_payment_history']) or not row['has_payment_history']:
        # Sin historial de pagos - score neutro
        return 200  # 50% del máximo

    score = 0

    # 1. Puntualidad (200 puntos)
    # Basado en DPD promedio
    avg_dpd = row.get('days_past_due_mean', 0)

    if pd.isna(avg_dpd):
        timeliness_score = 100
    elif avg_dpd < -15:  # Paga 15+ días antes
        timeliness_score = 200  # Excelente
    elif avg_dpd < 0:  # Paga antes
        timeliness_score = 180
    elif avg_dpd == 0:  # Paga a tiempo
        timeliness_score = 160
    elif avg_dpd <= 5:  # 1-5 días tarde
        timeliness_score = 120
    elif avg_dpd <= 15:  # 6-15 días tarde
        timeliness_score = 80
    elif avg_dpd <= 30:  # 16-30 días tarde
        timeliness_score = 40
    else:  # 30+ días tarde
        timeliness_score = 0

    score += timeliness_score

    # 2. Patrón de pagos (100 puntos)
    # Basado en % de pagos a tiempo/tempranos vs tardíos
    pct_early = row.get('pct_early', 0)
    pct_late = row.get('pct_late', 0)

    if pd.notna(pct_early) and pd.notna(pct_late):
        if pct_early >= 80:  # 80%+ pagos tempranos
            pattern_score = 100
        elif pct_early >= 60:
            pattern_score = 80
        elif pct_late <= 10:  # Bajo % de pagos tardíos
            pattern_score = 70
        elif pct_late <= 30:
            pattern_score = 50
        else:
            pattern_score = 20
    else:
        pattern_score = 50

    score += pattern_score

    # 3. Madurez del historial (100 puntos)
    # Más meses de historial = más confiable
    history_months = row.get('payment_history_months', 0)

    if pd.isna(history_months):
        maturity_score = 20
    elif history_months >= 12:  # 1+ año
        maturity_score = 100
    elif history_months >= 6:  # 6+ meses
        maturity_score = 70
    elif history_months >= 3:  # 3+ meses
        maturity_score = 50
    else:  # < 3 meses
        maturity_score = 30

    score += maturity_score

    return min(score, 400)  # Cap en 400

def calculate_purchase_consistency_score(row):
    """
    Componente 2: Purchase Consistency (200 puntos)

    Basado en:
    - Frecuencia de pagos (proxy para compras)
    - Recency (actividad reciente)
    """
    if pd.isna(row['has_payment_history']) or not row['has_payment_history']:
        return 0  # Sin historial

    score = 0

    # 1. Frecuencia (100 puntos)
    total_payments = row.get('payment_id_count', 0)
    history_months = max(row.get('payment_history_months', 1), 1)

    payments_per_month = total_payments / history_months if history_months > 0 else 0

    if payments_per_month >= 2:  # 2+ pagos/mes
        frequency_score = 100
    elif payments_per_month >= 1:  # 1+ pago/mes
        frequency_score = 80
    elif payments_per_month >= 0.5:  # 1 pago cada 2 meses
        frequency_score = 50
    else:
        frequency_score = 20

    score += frequency_score

    # 2. Recency (100 puntos)
    days_since_last = row.get('days_since_last_payment', 999)

    if pd.isna(days_since_last):
        recency_score = 0
    elif days_since_last <= 30:  # Último pago hace 30 días o menos
        recency_score = 100
    elif days_since_last <= 60:
        recency_score = 70
    elif days_since_last <= 90:
        recency_score = 40
    else:  # 90+ días sin pagar
        recency_score = 10

    score += recency_score

    return min(score, 200)

def calculate_utilization_score(row):
    """
    Componente 3: Utilization Score (150 puntos)

    Basado en:
    - % de utilización del cupo
    - Penaliza volatilidad extrema
    """
    pct_util = row.get('pct_utilization', 0)

    if pd.isna(pct_util):
        return 75  # Score neutro

    # Curva óptima: penalizar muy bajo y muy alto
    if pct_util <= 10:  # Muy baja utilización
        score = 50
    elif pct_util <= 30:  # Óptimo bajo
        score = 120
    elif pct_util <= 50:  # Óptimo
        score = 150
    elif pct_util <= 70:  # Moderado
        score = 130
    elif pct_util <= 85:  # Alto
        score = 90
    elif pct_util <= 95:  # Muy alto
        score = 50
    else:  # Maxed out
        score = 20

    return min(score, 150)

def calculate_payment_plan_score(row):
    """
    Componente 4: Payment Plan History (150 puntos)

    Basado en:
    - Si tiene plan de pago activo (penaliza)
    - Historial de planes de pago
    """
    # Por ahora no tenemos info detallada de payment plans
    # Usar risk_profile y status_plan como proxy

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

def calculate_deterioration_velocity(row):
    """
    Componente 5: Deterioration Velocity (100 puntos)

    Basado en:
    - Comparación de DPD reciente vs histórico
    - Tendencia de deterioro
    """
    if pd.isna(row['has_payment_history']) or not row['has_payment_history']:
        return 50  # Neutro

    # Usar max DPD como proxy para peor momento
    max_dpd = row.get('days_past_due_max', 0)
    avg_dpd = row.get('days_past_due_mean', 0)

    if pd.isna(max_dpd) or pd.isna(avg_dpd):
        return 50

    # Si nunca ha tenido mora severa
    if max_dpd <= 5:
        return 100  # Excelente

    # Velocidad de deterioro = qué tan lejos llegó del promedio
    velocity = max_dpd - avg_dpd

    if velocity <= 10:  # Estable
        score = 100
    elif velocity <= 30:  # Deterioro leve
        score = 70
    elif velocity <= 60:  # Deterioro moderado
        score = 40
    else:  # Deterioro severo
        score = 10

    return min(score, 100)

def get_credit_rating(total_score):
    """
    Asigna rating crediticio basado en score total

    Escala:
    900-1000: A+
    850-899:  A
    800-849:  A-
    750-799:  B+
    700-749:  B
    650-699:  B-
    600-649:  C+
    550-599:  C
    500-549:  C-
    450-499:  D+
    400-449:  D
    0-399:    F
    """
    if total_score >= 900:
        return 'A+'
    elif total_score >= 850:
        return 'A'
    elif total_score >= 800:
        return 'A-'
    elif total_score >= 750:
        return 'B+'
    elif total_score >= 700:
        return 'B'
    elif total_score >= 650:
        return 'B-'
    elif total_score >= 600:
        return 'C+'
    elif total_score >= 550:
        return 'C'
    elif total_score >= 500:
        return 'C-'
    elif total_score >= 450:
        return 'D+'
    elif total_score >= 400:
        return 'D'
    else:
        return 'F'

def normalize_experian_to_1000(experian_score):
    """
    Normaliza Experian Score (0-924) a escala 0-1000
    """
    if pd.isna(experian_score):
        return np.nan

    # Experian va de 0-924, normalizar a 0-1000
    return (experian_score / 924) * 1000

def calculate_scores(df):
    """
    Calcula todos los componentes del PLATAM Score
    """
    logger.info("\n" + "="*80)
    logger.info("CALCULANDO PLATAM SCORES")
    logger.info("="*80)

    # Calcular cada componente
    logger.info("\n1. Calculando Payment Performance (400 pts)...")
    df['score_payment_performance'] = df.apply(calculate_payment_performance_score, axis=1)

    logger.info("2. Calculando Purchase Consistency (200 pts)...")
    df['score_purchase_consistency'] = df.apply(calculate_purchase_consistency_score, axis=1)

    logger.info("3. Calculando Utilization (150 pts)...")
    df['score_utilization'] = df.apply(calculate_utilization_score, axis=1)

    logger.info("4. Calculando Payment Plan History (150 pts)...")
    df['score_payment_plan'] = df.apply(calculate_payment_plan_score, axis=1)

    logger.info("5. Calculando Deterioration Velocity (100 pts)...")
    df['score_deterioration'] = df.apply(calculate_deterioration_velocity, axis=1)

    # Score total
    logger.info("\n6. Calculando score total...")
    df['platam_score'] = (
        df['score_payment_performance'] +
        df['score_purchase_consistency'] +
        df['score_utilization'] +
        df['score_payment_plan'] +
        df['score_deterioration']
    )

    # Rating
    logger.info("7. Asignando credit rating...")
    df['platam_rating'] = df['platam_score'].apply(get_credit_rating)

    # Normalizar Experian para comparación
    logger.info("8. Normalizando Experian Score a escala 0-1000...")
    df['experian_score_normalized'] = df['experian_score'].apply(normalize_experian_to_1000)

    return df

def analyze_scores(df):
    """
    Analiza distribución y estadísticas de scores
    """
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS DE SCORES")
    logger.info("="*80)

    # Estadísticas PLATAM Score
    logger.info("\n--- PLATAM SCORE ---")
    logger.info(f"Promedio: {df['platam_score'].mean():.1f}")
    logger.info(f"Mediana: {df['platam_score'].median():.1f}")
    logger.info(f"Mínimo: {df['platam_score'].min():.1f}")
    logger.info(f"Máximo: {df['platam_score'].max():.1f}")
    logger.info(f"Std Dev: {df['platam_score'].std():.1f}")

    # Distribución por rating
    logger.info("\n--- DISTRIBUCIÓN POR RATING ---")
    rating_dist = df['platam_rating'].value_counts().sort_index()
    for rating, count in rating_dist.items():
        pct = count / len(df) * 100
        logger.info(f"{rating}: {count:4} ({pct:5.1f}%)")

    # Promedios por componente
    logger.info("\n--- PROMEDIO POR COMPONENTE ---")
    logger.info(f"Payment Performance:   {df['score_payment_performance'].mean():6.1f} / 400 ({df['score_payment_performance'].mean()/400*100:.1f}%)")
    logger.info(f"Purchase Consistency:  {df['score_purchase_consistency'].mean():6.1f} / 200 ({df['score_purchase_consistency'].mean()/200*100:.1f}%)")
    logger.info(f"Utilization:           {df['score_utilization'].mean():6.1f} / 150 ({df['score_utilization'].mean()/150*100:.1f}%)")
    logger.info(f"Payment Plan:          {df['score_payment_plan'].mean():6.1f} / 150 ({df['score_payment_plan'].mean()/150*100:.1f}%)")
    logger.info(f"Deterioration:         {df['score_deterioration'].mean():6.1f} / 100 ({df['score_deterioration'].mean()/100*100:.1f}%)")

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
    logger.info(f"{'Métrica':<30} {'PLATAM':<15} {'Experian (norm)':<15}")
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
    logger.info("PLATAM INTERNAL CREDIT SCORE CALCULATOR")
    logger.info("="*80)

    # Cargar dataset maestro
    logger.info(f"\nCargando dataset maestro: {MASTER_DATASET.name}")
    df = pd.read_csv(MASTER_DATASET)
    logger.info(f"✓ Cargados {len(df):,} clientes")

    # Calcular scores
    df = calculate_scores(df)

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
    logger.info("✓ CÁLCULO DE SCORES COMPLETADO")
    logger.info("="*80)
    logger.info(f"\nArchivos generados:")
    logger.info(f"  - {SCORES_OUTPUT}")
    logger.info(f"  - {COMPARISON_OUTPUT}")

    return df

if __name__ == '__main__':
    main()
