#!/usr/bin/env python3
"""
Integración de Scores Experian Empresariales al Sistema

Este script:
1. Lee scores_empresas_experian_normalized.csv (scores 0-1000)
2. Actualiza master_dataset.csv con scores empresariales
3. Actualiza platam_scores.csv
4. Recalcula scores híbridos (PLATAM + Experian)
5. Regenera SCORES_V2_ANALISIS_COMPLETO.csv

Las empresas ahora tendrán:
- experian_score: score original 0-5
- experian_score_normalized: score normalizado 0-1000
- Scores híbridos con pesos dinámicos (igual que personas naturales)

Usage:
    python scripts/integrate_business_experian_scores.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
BUSINESS_SCORES_CSV = BASE_DIR / "scores_empresas_experian_normalized.csv"
MASTER_DATASET = BASE_DIR / "data" / "processed" / "master_dataset.csv"
PLATAM_SCORES = BASE_DIR / "data" / "processed" / "platam_scores.csv"
HYBRID_SCORES = BASE_DIR / "data" / "processed" / "hybrid_scores.csv"


def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("INTEGRACIÓN DE SCORES EXPERIAN EMPRESARIALES")
    logger.info("="*80)

    # 1. Cargar scores empresariales
    logger.info("\n[1/6] Cargando scores empresariales...")
    business_scores = pd.read_csv(BUSINESS_SCORES_CSV, encoding='utf-8-sig')
    business_scores['nit'] = pd.to_numeric(business_scores['nit'], errors='coerce').astype('Int64')
    logger.info(f"   ✓ {len(business_scores)} empresas con scores Experian")
    logger.info(f"   • Score promedio (0-5): {business_scores['score_experian'].mean():.2f}")
    logger.info(f"   • Score normalizado promedio (0-1000): {business_scores['score_normalized'].mean():.1f}")

    # 2. Cargar master dataset
    logger.info("\n[2/6] Cargando master dataset...")
    master_df = pd.read_csv(MASTER_DATASET)
    master_df['cedula'] = pd.to_numeric(master_df['cedula'], errors='coerce').astype('Int64')

    empresas_master = master_df[master_df['client_type'] == 'Empresa'].copy()
    logger.info(f"   ✓ {len(master_df)} clientes totales")
    logger.info(f"   ✓ {len(empresas_master)} empresas en master dataset")

    # 3. Hacer merge
    logger.info("\n[3/6] Integrando scores empresariales...")

    # Crear diccionario de scores
    score_dict = dict(zip(business_scores['nit'], business_scores['score_experian']))
    score_norm_dict = dict(zip(business_scores['nit'], business_scores['score_normalized']))

    # Actualizar solo empresas
    empresas_mask = master_df['client_type'] == 'Empresa'

    # Mapear scores
    master_df.loc[empresas_mask, 'experian_score'] = master_df.loc[empresas_mask, 'cedula'].map(score_dict)
    master_df.loc[empresas_mask, 'experian_score_normalized'] = master_df.loc[empresas_mask, 'cedula'].map(score_norm_dict)

    # Contar actualizaciones
    empresas_actualizadas = master_df[empresas_mask & master_df['experian_score'].notna()]
    logger.info(f"   ✓ {len(empresas_actualizadas)} empresas actualizadas con scores Experian")
    logger.info(f"   • {len(empresas_master) - len(empresas_actualizadas)} empresas sin score (usarán base 500)")

    # 4. Guardar master dataset actualizado
    logger.info("\n[4/6] Guardando master dataset actualizado...")
    master_df.to_csv(MASTER_DATASET, index=False)
    logger.info(f"   ✓ Guardado: {MASTER_DATASET.name}")

    # 5. Actualizar platam_scores.csv
    logger.info("\n[5/6] Actualizando platam_scores.csv...")
    platam_df = pd.read_csv(PLATAM_SCORES)
    platam_df['cedula'] = pd.to_numeric(platam_df['cedula'], errors='coerce').astype('Int64')

    # Mapear scores a platam_scores
    platam_df['experian_score'] = platam_df['cedula'].map(score_dict).fillna(platam_df['experian_score'])
    platam_df['experian_score_normalized'] = platam_df['cedula'].map(score_norm_dict).fillna(platam_df['experian_score_normalized'])

    platam_df.to_csv(PLATAM_SCORES, index=False)
    logger.info(f"   ✓ Guardado: {PLATAM_SCORES.name}")

    # 6. Recalcular scores híbridos
    logger.info("\n[6/6] Recalculando scores híbridos...")
    logger.info("   (Ejecutando script 08_calculate_hybrid_scores.py...)")

    # Call the hybrid scoring script using subprocess
    import subprocess
    result = subprocess.run(
        ['python', 'scripts/08_calculate_hybrid_scores.py'],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        logger.error(f"   ❌ Error ejecutando script híbrido:")
        logger.error(result.stderr)
        return

    logger.info(f"   ✓ Scores híbridos recalculados")

    # Reload hybrid scores
    hybrid_df = pd.read_csv(HYBRID_SCORES, encoding='utf-8-sig')
    hybrid_df['cedula'] = pd.to_numeric(hybrid_df['cedula'], errors='coerce').astype('Int64')

    # Summary
    logger.info("\n" + "="*80)
    logger.info("RESUMEN FINAL")
    logger.info("="*80)

    # Compare before/after for empresas
    empresas_con_experian = hybrid_df[
        (hybrid_df['cedula'].isin(empresas_actualizadas['cedula'])) &
        (hybrid_df['experian_score_normalized'].notna())
    ]

    if len(empresas_con_experian) > 0:
        logger.info(f"\n📊 Empresas con Score Experian: {len(empresas_con_experian)}")
        logger.info(f"   • PLATAM promedio: {empresas_con_experian['platam_score'].mean():.1f}")
        logger.info(f"   • Experian promedio: {empresas_con_experian['experian_score_normalized'].mean():.1f}")
        logger.info(f"   • Híbrido promedio: {empresas_con_experian['hybrid_score'].mean():.1f}")

        logger.info(f"\n🏆 Distribución de Ratings Híbridos (Empresas con Experian):")
        rating_dist = empresas_con_experian['hybrid_rating'].value_counts().sort_index()
        for rating, count in rating_dist.items():
            pct = count / len(empresas_con_experian) * 100
            logger.info(f"   {rating}: {count:3d} ({pct:5.1f}%)")

    # Empresas sin Experian
    empresas_sin_experian = hybrid_df[
        (hybrid_df['cedula'].isin(empresas_master['cedula'])) &
        (hybrid_df['experian_score_normalized'].isna())
    ]

    if len(empresas_sin_experian) > 0:
        logger.info(f"\n⚠️  Empresas sin Score Experian: {len(empresas_sin_experian)}")
        logger.info(f"   • Usan 100% PLATAM score")
        logger.info(f"   • PLATAM promedio: {empresas_sin_experian['platam_score'].mean():.1f}")

    logger.info("\n" + "="*80)
    logger.info("✅ INTEGRACIÓN COMPLETADA")
    logger.info("="*80)

    logger.info(f"\nArchivos actualizados:")
    logger.info(f"  1. {MASTER_DATASET.name} - Con scores empresariales")
    logger.info(f"  2. {PLATAM_SCORES.name} - Con scores empresariales")
    logger.info(f"  3. {HYBRID_SCORES.name} - Scores híbridos recalculados")

    logger.info(f"\n💡 Próximo paso:")
    logger.info(f"  python scripts/fix_payment_plans_and_recalculate.py")
    logger.info(f"  (Para regenerar SCORES_V2_ANALISIS_COMPLETO.csv)")


if __name__ == '__main__':
    main()
