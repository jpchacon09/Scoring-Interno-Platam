#!/usr/bin/env python3
"""
Agregar Features Demográficas a SCORES_V2_ANALISIS_COMPLETO.csv

Este script:
1. Lee SCORES_V2_ANALISIS_COMPLETO.csv (archivo maestro)
2. Lee hybrid_scores_with_demographics.csv (datos demográficos)
3. Hace merge por cédula
4. AGREGA columnas demográficas AL FINAL (sin tocar las existentes)
5. Guarda backup del original
6. Sobrescribe con versión actualizada

IMPORTANTE: NO modifica columnas existentes (endpoint n8n/Make las usa)

Usage:
    python add_demographics_to_scores_v2.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
import shutil

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
SCORES_V2_FILE = BASE_DIR / 'SCORES_V2_ANALISIS_COMPLETO.csv'
DEMOGRAPHICS_FILE = BASE_DIR / 'data' / 'processed' / 'hybrid_scores_with_demographics.csv'
BACKUP_DIR = BASE_DIR / 'backups'
BACKUP_DIR.mkdir(exist_ok=True)


def create_backup():
    """Crea backup del archivo original"""
    logger.info("\n[1/5] Creando backup del archivo original...")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = BACKUP_DIR / f'SCORES_V2_ANALISIS_COMPLETO_backup_{timestamp}.csv'

    shutil.copy2(SCORES_V2_FILE, backup_file)
    logger.info(f"  ✓ Backup guardado: {backup_file.name}")

    return backup_file


def load_data():
    """Carga archivos"""
    logger.info("\n[2/5] Cargando archivos...")

    # Cargar SCORES_V2 (archivo maestro)
    df_scores = pd.read_csv(SCORES_V2_FILE, encoding='utf-8-sig')
    logger.info(f"  ✓ SCORES_V2: {len(df_scores):,} registros × {len(df_scores.columns)} columnas")

    # Cargar datos demográficos
    df_demo = pd.read_csv(DEMOGRAPHICS_FILE)
    logger.info(f"  ✓ Demografía: {len(df_demo):,} registros × {len(df_demo.columns)} columnas")

    return df_scores, df_demo


def merge_demographics(df_scores, df_demo):
    """Hace merge cuidadoso agregando SOLO nuevas columnas"""
    logger.info("\n[3/5] Agregando columnas demográficas...")

    # Normalizar cédula en ambos DataFrames
    df_scores['cedula'] = df_scores['cedula'].astype(str).str.strip()
    df_demo['cedula'] = df_demo['cedula'].astype(str).str.strip()

    # Columnas originales (preservar orden)
    original_cols = df_scores.columns.tolist()
    logger.info(f"  ✓ Columnas originales: {len(original_cols)}")

    # Nuevas columnas a agregar (SOLO las demográficas)
    new_cols = [
        'genero_encoded',
        'edad',
        'ciudad_encoded',
        'ciudad_nombre',
        'ingresos_smlv',
        'nivel_ingresos_encoded',
        'cuota_mensual',
        'ratio_cuota_ingreso',
        'creditos_vigentes',
        'creditos_mora',
        'hist_neg_12m'
    ]

    # Verificar que existen en df_demo
    available_new_cols = [col for col in new_cols if col in df_demo.columns]
    missing_cols = [col for col in new_cols if col not in df_demo.columns]

    if missing_cols:
        logger.warning(f"  ⚠️  Columnas faltantes en demografía: {missing_cols}")

    logger.info(f"  ✓ Nuevas columnas a agregar: {len(available_new_cols)}")

    # Seleccionar solo cedula + nuevas columnas de df_demo
    df_demo_subset = df_demo[['cedula'] + available_new_cols].copy()

    # Merge LEFT (preserva TODOS los registros de SCORES_V2)
    df_merged = df_scores.merge(
        df_demo_subset,
        on='cedula',
        how='left',
        suffixes=('', '_demo')  # En caso de duplicados
    )

    # Verificar orden de columnas: originales + nuevas
    final_cols = original_cols + available_new_cols
    df_final = df_merged[final_cols].copy()

    # Estadísticas de merge
    matches = df_final[available_new_cols[0]].notna().sum()
    logger.info(f"\n  📊 Resultado del merge:")
    logger.info(f"     • Total registros: {len(df_final):,}")
    logger.info(f"     • Con datos demográficos: {matches:,} ({matches/len(df_final)*100:.1f}%)")
    logger.info(f"     • Sin datos demográficos: {len(df_final) - matches:,}")

    return df_final, available_new_cols


def fill_missing_demographics(df, new_cols):
    """Rellena valores faltantes en nuevas columnas"""
    logger.info("\n[4/5] Rellenando valores faltantes...")

    for col in new_cols:
        missing_count = df[col].isna().sum()

        if missing_count > 0:
            # Categoricas: moda
            if 'encoded' in col or col in ['ciudad_nombre']:
                fill_value = df[col].mode()[0] if len(df[col].mode()) > 0 else 0
                df[col] = df[col].fillna(fill_value)
                logger.info(f"  • {col}: {missing_count} → moda ({fill_value})")

            # Numéricas: mediana
            else:
                fill_value = df[col].median()
                df[col] = df[col].fillna(fill_value)
                logger.info(f"  • {col}: {missing_count} → mediana ({fill_value:.1f})")

    return df


def save_updated_file(df):
    """Guarda archivo actualizado"""
    logger.info("\n[5/5] Guardando archivo actualizado...")

    # Guardar
    df.to_csv(SCORES_V2_FILE, index=False, encoding='utf-8-sig')

    logger.info(f"  ✓ Archivo actualizado: SCORES_V2_ANALISIS_COMPLETO.csv")
    logger.info(f"  ✓ Registros: {len(df):,}")
    logger.info(f"  ✓ Columnas: {len(df.columns)} (antes: 28, nuevas: {len(df.columns) - 28})")

    # Mostrar nuevas columnas agregadas
    logger.info("\n  📋 Nuevas columnas agregadas:")
    for i, col in enumerate(df.columns[28:], 1):
        logger.info(f"     {i}. {col}")


def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("AGREGAR FEATURES DEMOGRÁFICAS A SCORES_V2_ANALISIS_COMPLETO")
    logger.info("="*80)

    # 1. Backup
    backup_file = create_backup()

    # 2. Cargar datos
    df_scores, df_demo = load_data()

    # 3. Merge
    df_merged, new_cols = merge_demographics(df_scores, df_demo)

    # 4. Fill missing
    df_final = fill_missing_demographics(df_merged, new_cols)

    # 5. Guardar
    save_updated_file(df_final)

    logger.info("\n" + "="*80)
    logger.info("✅ PROCESO COMPLETADO")
    logger.info("="*80)
    logger.info(f"\n📁 Archivo actualizado: SCORES_V2_ANALISIS_COMPLETO.csv")
    logger.info(f"📁 Backup guardado en: {backup_file}")
    logger.info("\n⚠️  IMPORTANTE:")
    logger.info("   • Las 28 columnas originales NO fueron modificadas")
    logger.info("   • El endpoint n8n/Make sigue funcionando igual")
    logger.info("   • Solo se AGREGARON nuevas columnas al final")
    logger.info("\n💡 Próximo paso:")
    logger.info("   • Reentrenar modelo con PD anual")
    logger.info("   • Desplegar a Vertex AI")


if __name__ == '__main__':
    main()
