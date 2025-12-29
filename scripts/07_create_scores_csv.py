#!/usr/bin/env python3
"""
Crea CSV con comparación de scores y score híbrido

Genera archivo CSV con:
- ID cliente (cédula)
- Score PLATAM interno
- Score HCPN (Experian)
- Desviación entre scores
- Score híbrido (50% HCPN + 50% PLATAM)
- Rating del score híbrido

Usage:
    python scripts/07_create_scores_csv.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
SCORES_FILE = PROCESSED_DIR / 'platam_scores.csv'
OUTPUT_CSV = BASE_DIR / 'SCORES_COMPARACION.csv'

def get_credit_rating(score):
    """Asigna rating crediticio según score"""
    if pd.isna(score):
        return 'N/A'
    if score >= 900:
        return 'A+'
    elif score >= 850:
        return 'A'
    elif score >= 800:
        return 'A-'
    elif score >= 750:
        return 'B+'
    elif score >= 700:
        return 'B'
    elif score >= 650:
        return 'B-'
    elif score >= 600:
        return 'C+'
    elif score >= 550:
        return 'C'
    elif score >= 500:
        return 'C-'
    elif score >= 450:
        return 'D+'
    elif score >= 400:
        return 'D'
    else:
        return 'F'

def create_scores_csv():
    """Crea archivo CSV con comparación de scores"""

    logger.info("="*80)
    logger.info("CREANDO CSV DE COMPARACIÓN DE SCORES")
    logger.info("="*80)

    # Cargar datos
    logger.info(f"\nCargando scores desde: {SCORES_FILE.name}")
    df = pd.read_csv(SCORES_FILE)
    logger.info(f"✓ Cargados {len(df):,} clientes")

    # Crear DataFrame para CSV
    logger.info("\nPreparando datos para CSV...")

    csv_data = pd.DataFrame()

    # 1. ID Cliente (cédula)
    csv_data['id_cliente'] = df['cedula']

    # 2. Información básica del cliente
    csv_data['nombre'] = df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
    csv_data['email'] = df['email']
    csv_data['estado'] = df['estado']

    # 3. Score PLATAM Interno
    csv_data['score_platam'] = df['platam_score'].round(0)
    csv_data['rating_platam'] = df['platam_rating']

    # 4. Score HCPN (Experian normalizado a 0-1000)
    csv_data['score_hcpn_normalizado'] = df['experian_score_normalized'].round(0)

    # 5. Score HCPN Original (0-924)
    csv_data['score_hcpn_original'] = df['experian_score'].round(0)

    # 6. Desviación (PLATAM - HCPN)
    csv_data['desviacion_scores'] = (df['platam_score'] - df['experian_score_normalized']).round(0)

    # 7. Score Híbrido (50% PLATAM + 50% HCPN)
    logger.info("\nCalculando score híbrido (50% PLATAM + 50% HCPN)...")

    # Para clientes sin HCPN, usar 100% PLATAM
    csv_data['score_calculado_hcpn'] = np.where(
        df['experian_score_normalized'].notna(),
        (df['platam_score'] * 0.5 + df['experian_score_normalized'] * 0.5).round(0),
        df['platam_score'].round(0)
    )

    # 8. Rating del score híbrido
    csv_data['rating_score_calculado'] = csv_data['score_calculado_hcpn'].apply(get_credit_rating)

    # 9. Componentes del score PLATAM
    # Componentes del score PLATAM V2.0 (3 componentes)
    csv_data['componente_payment_performance_600pts'] = df['score_payment_performance'].round(0)
    csv_data['componente_payment_plan_history_150pts'] = df['score_payment_plan'].round(0)
    csv_data['componente_deterioration_velocity_250pts'] = df['score_deterioration'].round(0)

    # 10. Información financiera
    csv_data['cupo_total'] = df['cupo_total']
    csv_data['cupo_disponible'] = df['cupo_disponible']
    csv_data['pct_utilizacion'] = df['pct_utilization'].round(1)

    # 11. Datos de HCPN
    csv_data['hcpn_ingreso_declarado'] = df['declared_income']
    csv_data['hcpn_cuota_total_mensual'] = df['total_monthly_payment']
    csv_data['hcpn_creditos_activos'] = df['active_credits']
    csv_data['hcpn_creditos_en_mora'] = df['credits_in_default']

    # 12. Métricas de pagos
    csv_data['total_pagos'] = df['payment_id_count']
    csv_data['promedio_dpd'] = df['days_past_due_mean'].round(1)
    csv_data['pct_pagos_a_tiempo'] = df['pct_on_time'].round(1)
    csv_data['dias_desde_ultimo_pago'] = df['days_since_last_payment']

    # 13. Flags
    csv_data['tiene_hcpn'] = df['has_hcpn']
    csv_data['tiene_historial_pagos'] = df['has_payment_history']

    # 14. Categorización de diferencia
    csv_data['categoria_diferencia'] = pd.cut(
        csv_data['desviacion_scores'].abs(),
        bins=[0, 50, 100, 150, 200, np.inf],
        labels=['Muy Similar (0-50)', 'Similar (50-100)', 'Moderada (100-150)',
                'Alta (150-200)', 'Muy Alta (200+)']
    )

    # 15. Interpretación de desviación
    def interpretar_desviacion(dev):
        if pd.isna(dev):
            return 'Sin HCPN'
        elif dev < -150:
            return 'PLATAM mucho más bajo'
        elif dev < -50:
            return 'PLATAM más bajo'
        elif dev <= 50:
            return 'Similares'
        elif dev <= 150:
            return 'PLATAM más alto'
        else:
            return 'PLATAM mucho más alto'

    csv_data['interpretacion_diferencia'] = csv_data['desviacion_scores'].apply(interpretar_desviacion)

    # Ordenar por score híbrido descendente
    csv_data = csv_data.sort_values('score_calculado_hcpn', ascending=False)

    # Estadísticas
    logger.info("\n" + "="*80)
    logger.info("ESTADÍSTICAS DEL SCORE CALCULADO + HCPN")
    logger.info("="*80)
    logger.info(f"\nPromedio: {csv_data['score_calculado_hcpn'].mean():.1f}")
    logger.info(f"Mediana: {csv_data['score_calculado_hcpn'].median():.1f}")
    logger.info(f"Mínimo: {csv_data['score_calculado_hcpn'].min():.1f}")
    logger.info(f"Máximo: {csv_data['score_calculado_hcpn'].max():.1f}")

    logger.info("\nDistribución por Rating:")
    rating_dist = csv_data['rating_score_calculado'].value_counts().sort_index()
    for rating, count in rating_dist.items():
        pct = count / len(csv_data) * 100
        logger.info(f"  {rating}: {count:4} ({pct:5.1f}%)")

    # Guardar CSV
    logger.info("\n" + "="*80)
    logger.info("GUARDANDO CSV")
    logger.info("="*80)

    csv_data.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

    logger.info(f"\n✓ CSV guardado exitosamente:")
    logger.info(f"  {OUTPUT_CSV.absolute()}")
    logger.info(f"  Tamaño: {OUTPUT_CSV.stat().st_size / 1024 / 1024:.2f} MB")
    logger.info(f"  Registros: {len(csv_data):,}")
    logger.info(f"  Columnas: {len(csv_data.columns)}")

    logger.info("\n" + "="*80)
    logger.info("COLUMNAS PRINCIPALES DEL CSV")
    logger.info("="*80)
    logger.info("\n✅ COLUMNAS CLAVE:")
    logger.info("  • id_cliente - Cédula del cliente")
    logger.info("  • score_platam - Score interno (0-1000)")
    logger.info("  • score_hcpn_normalizado - Score Experian normalizado (0-1000)")
    logger.info("  • desviacion_scores - PLATAM - HCPN")
    logger.info("  • score_calculado_hcpn - 50% PLATAM + 50% HCPN ⭐")
    logger.info("  • rating_score_calculado - Rating del score híbrido")

    logger.info("\n" + "="*80)
    logger.info("✓ CSV CREADO EXITOSAMENTE")
    logger.info("="*80)
    logger.info(f"\nPuedes descargar el archivo desde:")
    logger.info(f"{OUTPUT_CSV.name}")

    return csv_data

if __name__ == '__main__':
    create_scores_csv()
