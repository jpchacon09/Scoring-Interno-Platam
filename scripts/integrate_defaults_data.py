#!/usr/bin/env python3
"""
Integración de Datos de Defaults al Sistema

Este script:
1. Lee Defaults.csv con información de préstamos en default
2. Identifica clientes que cayeron en default (l_status = "Default")
3. Crea variable default_flag (0 o 1) para cada cliente
4. Actualiza todos los datasets con la información de defaults
5. Genera estadísticas sobre defaults y su relación con scores

Criterios de Default:
- Cliente tiene al menos UN préstamo con l_status = "Default", O
- Cliente tiene mora > 180 días en algún préstamo

Usage:
    python scripts/integrate_defaults_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
DEFAULTS_CSV = BASE_DIR / "Defaults.csv"
MASTER_DATASET = BASE_DIR / "data" / "processed" / "master_dataset.csv"
SCORES_V2 = BASE_DIR / "SCORES_V2_ANALISIS_COMPLETO.csv"
OUTPUT_ML_DATASET = BASE_DIR / "ml_training_data.csv"


def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("INTEGRACIÓN DE DATOS DE DEFAULTS")
    logger.info("="*80)

    # 1. Cargar defaults
    logger.info("\n[1/7] Cargando datos de defaults...")
    defaults_df = pd.read_csv(DEFAULTS_CSV)
    logger.info(f"   ✓ {len(defaults_df):,} préstamos cargados")
    logger.info(f"   ✓ {defaults_df['l_cl_doc_number'].nunique():,} clientes únicos")

    # Analizar estados
    status_counts = defaults_df['l_status'].value_counts()
    logger.info(f"\n   Distribución de estados:")
    for status, count in status_counts.items():
        pct = count / len(defaults_df) * 100
        logger.info(f"      {status}: {count:,} ({pct:.1f}%)")

    # 2. Identificar clientes en default
    logger.info("\n[2/7] Identificando clientes en default...")

    # Criterio 1: l_status = "Default"
    defaults_by_status = defaults_df[defaults_df['l_status'] == 'Default']['l_cl_doc_number'].unique()
    logger.info(f"   • Por status 'Default': {len(defaults_by_status)} clientes")

    # Criterio 2: Mora > 180 días
    defaults_df['l_due_days'] = pd.to_numeric(defaults_df['l_due_days'], errors='coerce')
    defaults_by_days = defaults_df[defaults_df['l_due_days'] > 180]['l_cl_doc_number'].unique()
    logger.info(f"   • Por mora >180 días: {len(defaults_by_days)} clientes")

    # Criterio 3: l_status = "Tarde" (opcional, para considerar)
    late_clients = defaults_df[defaults_df['l_status'] == 'Tarde']['l_cl_doc_number'].unique()
    logger.info(f"   • Status 'Tarde': {len(late_clients)} clientes")

    # Combinar criterios (Default OR mora >180 días)
    default_clients = set(defaults_by_status) | set(defaults_by_days)
    logger.info(f"\n   ✅ Total clientes en DEFAULT: {len(default_clients)}")

    # Crear DataFrame de defaults
    defaults_summary = pd.DataFrame({
        'cedula': list(default_clients),
        'default_flag': 1
    })

    # Añadir información adicional
    # Máxima mora por cliente
    max_days_per_client = defaults_df.groupby('l_cl_doc_number')['l_due_days'].max().reset_index()
    max_days_per_client.columns = ['cedula', 'max_days_past_due']

    # Número de préstamos en default por cliente
    defaults_count = defaults_df[defaults_df['l_status'] == 'Default'].groupby('l_cl_doc_number').size().reset_index()
    defaults_count.columns = ['cedula', 'num_defaults']

    # Balance total pendiente en defaults
    balance_defaults = defaults_df[defaults_df['l_status'] == 'Default'].groupby('l_cl_doc_number')['l_balance_total'].sum().reset_index()
    balance_defaults.columns = ['cedula', 'balance_default_total']

    # Merge con información adicional
    defaults_summary = defaults_summary.merge(max_days_per_client, on='cedula', how='left')
    defaults_summary = defaults_summary.merge(defaults_count, on='cedula', how='left')
    defaults_summary = defaults_summary.merge(balance_defaults, on='cedula', how='left')

    # Fill NaN
    defaults_summary['num_defaults'] = defaults_summary['num_defaults'].fillna(0).astype(int)
    defaults_summary['balance_default_total'] = defaults_summary['balance_default_total'].fillna(0)

    # 3. Cargar master_dataset
    logger.info("\n[3/7] Cargando master_dataset...")
    master_df = pd.read_csv(MASTER_DATASET)
    master_df['cedula'] = pd.to_numeric(master_df['cedula'], errors='coerce')
    defaults_summary['cedula'] = pd.to_numeric(defaults_summary['cedula'], errors='coerce')

    logger.info(f"   ✓ {len(master_df)} clientes en master_dataset")

    # 4. Hacer merge
    logger.info("\n[4/7] Integrando información de defaults...")

    # Remove existing default columns if any
    cols_to_drop = ['default_flag', 'max_days_past_due', 'num_defaults', 'balance_default_total']
    for col in cols_to_drop:
        if col in master_df.columns:
            master_df = master_df.drop(col, axis=1)

    # Merge
    master_df = master_df.merge(
        defaults_summary,
        on='cedula',
        how='left'
    )

    # Fill NaN para clientes sin defaults
    master_df['default_flag'] = master_df['default_flag'].fillna(0).astype(int)
    master_df['max_days_past_due'] = master_df['max_days_past_due'].fillna(0)
    master_df['num_defaults'] = master_df['num_defaults'].fillna(0).astype(int)
    master_df['balance_default_total'] = master_df['balance_default_total'].fillna(0)

    # Contar matches
    defaults_matched = master_df[master_df['default_flag'] == 1]
    logger.info(f"   ✓ {len(defaults_matched)} clientes marcados con default_flag = 1")
    logger.info(f"   ✓ {len(master_df) - len(defaults_matched)} clientes sin default (default_flag = 0)")

    # Estadísticas
    pct_defaults = len(defaults_matched) / len(master_df) * 100
    logger.info(f"\n   📊 Tasa de default: {pct_defaults:.2f}%")

    # 5. Guardar master_dataset actualizado
    logger.info("\n[5/7] Guardando master_dataset actualizado...")
    master_df.to_csv(MASTER_DATASET, index=False)
    logger.info(f"   ✓ Guardado: {MASTER_DATASET.name}")

    # 6. Actualizar SCORES_V2_ANALISIS_COMPLETO
    logger.info("\n[6/7] Actualizando SCORES_V2_ANALISIS_COMPLETO.csv...")
    scores_df = pd.read_csv(SCORES_V2, encoding='utf-8-sig')
    scores_df['cedula'] = pd.to_numeric(scores_df['cedula'], errors='coerce')

    # Remove existing default columns
    for col in cols_to_drop:
        if col in scores_df.columns:
            scores_df = scores_df.drop(col, axis=1)

    # Merge
    scores_df = scores_df.merge(
        defaults_summary,
        on='cedula',
        how='left'
    )

    # Fill NaN
    scores_df['default_flag'] = scores_df['default_flag'].fillna(0).astype(int)
    scores_df['max_days_past_due'] = scores_df['max_days_past_due'].fillna(0)
    scores_df['num_defaults'] = scores_df['num_defaults'].fillna(0).astype(int)
    scores_df['balance_default_total'] = scores_df['balance_default_total'].fillna(0)

    scores_df.to_csv(SCORES_V2, index=False, encoding='utf-8-sig')
    logger.info(f"   ✓ Guardado: {SCORES_V2.name}")

    # 7. Crear ML training dataset
    logger.info("\n[7/7] Creando dataset para Machine Learning...")

    # Seleccionar columnas relevantes para ML
    ml_features = [
        # Identificación
        'cedula', 'client_type',

        # Target
        'default_flag',

        # Scores
        'platam_score', 'experian_score_normalized', 'hybrid_score',
        'platam_rating', 'hybrid_rating',

        # Componentes PLATAM
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',

        # Comportamiento de pago
        'payment_count', 'months_as_client',
        'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late',

        # Pesos híbridos
        'peso_platam_usado', 'peso_hcpn_usado', 'categoria_madurez',

        # Información de defaults
        'max_days_past_due', 'num_defaults', 'balance_default_total',

        # Planes de pago
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]

    # Seleccionar columnas que existen
    available_cols = [col for col in ml_features if col in scores_df.columns]
    ml_df = scores_df[available_cols].copy()

    # Guardar
    ml_df.to_csv(OUTPUT_ML_DATASET, index=False, encoding='utf-8-sig')
    logger.info(f"   ✓ Guardado: {OUTPUT_ML_DATASET.name}")
    logger.info(f"   • {len(ml_df)} clientes")
    logger.info(f"   • {len(ml_df.columns)} features")

    # Análisis de defaults vs scores
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: DEFAULTS vs SCORES")
    logger.info("="*80)

    # Comparar scores entre defaults y no-defaults
    with_default = ml_df[ml_df['default_flag'] == 1]
    without_default = ml_df[ml_df['default_flag'] == 0]

    logger.info(f"\n📊 Comparación de Scores Promedio:")
    logger.info(f"{'Métrica':<30} {'Sin Default':>15} {'Con Default':>15} {'Diferencia':>15}")
    logger.info("-" * 75)

    metrics = ['platam_score', 'experian_score_normalized', 'hybrid_score']
    for metric in metrics:
        if metric in ml_df.columns:
            avg_no_default = without_default[metric].mean()
            avg_default = with_default[metric].mean()
            diff = avg_default - avg_no_default
            logger.info(f"{metric:<30} {avg_no_default:>15.1f} {avg_default:>15.1f} {diff:>15.1f}")

    # Distribución de ratings en defaults
    if len(with_default) > 0:
        logger.info(f"\n🏆 Distribución de Ratings en Clientes con Default:")
        rating_dist = with_default['platam_rating'].value_counts().sort_index()
        for rating, count in rating_dist.items():
            pct = count / len(with_default) * 100
            logger.info(f"   {rating}: {count:3d} ({pct:5.1f}%)")

    # Distribución de ratings en no-defaults
    if len(without_default) > 0:
        logger.info(f"\n✅ Distribución de Ratings en Clientes SIN Default:")
        rating_dist = without_default['platam_rating'].value_counts().sort_index()
        for rating, count in rating_dist.items():
            pct = count / len(without_default) * 100
            logger.info(f"   {rating}: {count:3d} ({pct:5.1f}%)")

    # Tasa de default por rating
    logger.info(f"\n📉 Tasa de Default por Rating:")
    for rating in sorted(ml_df['platam_rating'].unique()):
        subset = ml_df[ml_df['platam_rating'] == rating]
        default_rate = (subset['default_flag'].sum() / len(subset)) * 100
        logger.info(f"   {rating}: {default_rate:5.1f}% ({subset['default_flag'].sum()}/{len(subset)})")

    # Summary
    logger.info("\n" + "="*80)
    logger.info("RESUMEN FINAL")
    logger.info("="*80)

    logger.info(f"\n📊 Datos de Defaults:")
    logger.info(f"   • Total clientes en default: {len(defaults_matched)}")
    logger.info(f"   • Tasa de default: {pct_defaults:.2f}%")
    logger.info(f"   • Máximo días de mora: {master_df['max_days_past_due'].max():.0f} días")
    logger.info(f"   • Balance total en default: ${master_df['balance_default_total'].sum():,.0f}")

    logger.info(f"\n✅ Archivos actualizados:")
    logger.info(f"   1. {MASTER_DATASET.name} - Con default_flag y métricas de default")
    logger.info(f"   2. {SCORES_V2.name} - Con default_flag")
    logger.info(f"   3. {OUTPUT_ML_DATASET.name} - Dataset listo para ML")

    logger.info(f"\n🎯 Balance de Clases (para ML):")
    logger.info(f"   • No-Default (0): {len(without_default)} ({len(without_default)/len(ml_df)*100:.1f}%)")
    logger.info(f"   • Default (1): {len(with_default)} ({len(with_default)/len(ml_df)*100:.1f}%)")

    if len(with_default) / len(ml_df) < 0.05:
        logger.info(f"\n⚠️  ADVERTENCIA: Clases desbalanceadas (<5% defaults)")
        logger.info(f"   Recomendación: Usar class_weight o SMOTE en entrenamiento")

    logger.info(f"\n💡 Siguiente paso:")
    logger.info(f"   • Dataset listo: ml_training_data.csv ({len(ml_df)} clientes, {len(ml_df.columns)} features)")
    logger.info(f"   • ¡Podemos empezar con ML!")


if __name__ == '__main__':
    main()
