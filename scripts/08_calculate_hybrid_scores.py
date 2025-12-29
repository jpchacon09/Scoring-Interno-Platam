#!/usr/bin/env python3
"""
Calcula scores híbridos para todos los clientes

Este script toma los scores PLATAM V2.0 ya calculados y los combina
inteligentemente con los scores HCPN (Experian) usando pesos dinámicos
basados en la madurez del cliente.

NO usa una combinación fija 50/50, sino que ajusta los pesos según:
- Meses como cliente
- Cantidad de pagos realizados
- Disponibilidad de datos

Usage:
    python scripts/08_calculate_hybrid_scores.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import sys

# Añadir path raíz al sys.path para importar módulos
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from hybrid_scoring import calculate_hybrid_scores_batch, HybridScoringConfig
from internal_credit_score import get_credit_rating

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
SCORES_FILE = PROCESSED_DIR / 'platam_scores.csv'
OUTPUT_FILE = PROCESSED_DIR / 'hybrid_scores.csv'

def calculate_hybrid_scores():
    """Calcula scores híbridos para todos los clientes"""

    logger.info("="*80)
    logger.info("CÁLCULO DE SCORES HÍBRIDOS")
    logger.info("="*80)

    # Cargar scores V2.0
    logger.info(f"\n1. Cargando scores PLATAM V2.0...")
    logger.info(f"   Archivo: {SCORES_FILE.name}")

    df = pd.read_csv(SCORES_FILE)
    logger.info(f"   ✓ Cargados {len(df):,} clientes")

    # Calcular meses como cliente (basado en fecha de creación)
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        reference_date = pd.Timestamp.now()
        df['months_as_client'] = ((reference_date - df['created_at']).dt.days / 30.44).fillna(0).astype(int)
    else:
        # Usar días desde último pago como proxy si no hay created_at
        logger.warning("   ⚠️  Columna 'created_at' no encontrada, usando proxy")
        df['months_as_client'] = (df['days_since_last_payment'].fillna(0) / 30.44).astype(int)

    # Asegurar que payment_count existe
    if 'payment_id_count' in df.columns:
        df['payment_count'] = df['payment_id_count'].fillna(0).astype(int)
    else:
        df['payment_count'] = 0
        logger.warning("   ⚠️  Columna 'payment_id_count' no encontrada, usando 0")

    # Calcular scores híbridos en batch
    logger.info(f"\n2. Calculando scores híbridos...")
    logger.info(f"   Configuración:")
    logger.info(f"   - Cliente muy nuevo: < {HybridScoringConfig.MADUREZ_NUEVO} meses")
    logger.info(f"   - Cliente nuevo: {HybridScoringConfig.MADUREZ_NUEVO}-{HybridScoringConfig.MADUREZ_INTERMEDIO} meses")
    logger.info(f"   - Cliente intermedio: {HybridScoringConfig.MADUREZ_INTERMEDIO}-{HybridScoringConfig.MADUREZ_ESTABLECIDO} meses")
    logger.info(f"   - Cliente establecido: {HybridScoringConfig.MADUREZ_ESTABLECIDO}-24 meses")
    logger.info(f"   - Cliente maduro: > 24 meses")

    df_hybrid = calculate_hybrid_scores_batch(
        df=df,
        platam_col='platam_score',
        hcpn_col='experian_score_normalized',
        months_col='months_as_client',
        payment_count_col='payment_count'
    )

    # Calcular rating del score híbrido
    df_hybrid['hybrid_rating'] = df_hybrid['hybrid_score'].apply(get_credit_rating)

    # Estadísticas
    logger.info("\n" + "="*80)
    logger.info("ESTADÍSTICAS DE SCORES HÍBRIDOS")
    logger.info("="*80)

    logger.info(f"\n📊 Estadísticas Generales:")
    logger.info(f"   Promedio Score Híbrido: {df_hybrid['hybrid_score'].mean():.1f}")
    logger.info(f"   Mediana Score Híbrido: {df_hybrid['hybrid_score'].median():.1f}")
    logger.info(f"   Mínimo: {df_hybrid['hybrid_score'].min():.1f}")
    logger.info(f"   Máximo: {df_hybrid['hybrid_score'].max():.1f}")
    logger.info(f"   Desviación Estándar: {df_hybrid['hybrid_score'].std():.1f}")

    logger.info(f"\n🎯 Comparación de Promedios:")
    logger.info(f"   PLATAM V2.0: {df_hybrid['platam_score'].mean():.1f}")
    logger.info(f"   HCPN: {df_hybrid['experian_score_normalized'].mean():.1f}")
    logger.info(f"   Híbrido: {df_hybrid['hybrid_score'].mean():.1f}")

    # Distribución por estrategia
    logger.info(f"\n📋 Distribución por Estrategia:")
    estrategia_dist = df_hybrid['estrategia_hibrido'].value_counts()
    for estrategia, count in estrategia_dist.items():
        pct = count / len(df_hybrid) * 100
        logger.info(f"   {estrategia[:50]}: {count:4} ({pct:5.1f}%)")

    # Distribución por categoría de madurez
    logger.info(f"\n📈 Distribución por Madurez:")
    madurez_dist = df_hybrid['categoria_madurez'].value_counts()
    for cat, count in madurez_dist.items():
        pct = count / len(df_hybrid) * 100
        avg_peso = df_hybrid[df_hybrid['categoria_madurez'] == cat]['peso_platam_usado'].mean()
        logger.info(f"   {cat}: {count:4} ({pct:5.1f}%) - Peso PLATAM promedio: {avg_peso:.1%}")

    # Distribución por rating híbrido
    logger.info(f"\n🏆 Distribución por Rating Híbrido:")
    rating_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
    rating_dist = df_hybrid['hybrid_rating'].value_counts().reindex(rating_order, fill_value=0)

    for rating, count in rating_dist.items():
        if count > 0:
            pct = count / len(df_hybrid) * 100
            logger.info(f"   {rating}: {count:4} ({pct:5.1f}%)")

    # Comparación de ratings
    logger.info(f"\n🔄 Cambios de Rating (PLATAM → Híbrido):")
    rating_cambios = pd.crosstab(df_hybrid['platam_rating'], df_hybrid['hybrid_rating'])

    # Clientes que mejoraron
    mejoraron = 0
    empeoraron = 0
    igual = 0

    rating_values = {'A+': 12, 'A': 11, 'A-': 10, 'B+': 9, 'B': 8, 'B-': 7,
                     'C+': 6, 'C': 5, 'C-': 4, 'D+': 3, 'D': 2, 'F': 1}

    for idx, row in df_hybrid.iterrows():
        platam_val = rating_values.get(row['platam_rating'], 0)
        hybrid_val = rating_values.get(row['hybrid_rating'], 0)

        if hybrid_val > platam_val:
            mejoraron += 1
        elif hybrid_val < platam_val:
            empeoraron += 1
        else:
            igual += 1

    logger.info(f"   Mejoraron: {mejoraron:4} ({mejoraron/len(df_hybrid)*100:5.1f}%)")
    logger.info(f"   Igual: {igual:4} ({igual/len(df_hybrid)*100:5.1f}%)")
    logger.info(f"   Empeoraron: {empeoraron:4} ({empeoraron/len(df_hybrid)*100:5.1f}%)")

    # Guardar resultados
    logger.info("\n" + "="*80)
    logger.info("GUARDANDO RESULTADOS")
    logger.info("="*80)

    df_hybrid.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    logger.info(f"\n✓ Archivo guardado exitosamente:")
    logger.info(f"  {OUTPUT_FILE.absolute()}")
    logger.info(f"  Tamaño: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    logger.info(f"  Registros: {len(df_hybrid):,}")
    logger.info(f"  Columnas: {len(df_hybrid.columns)}")

    logger.info("\n" + "="*80)
    logger.info("COLUMNAS PRINCIPALES")
    logger.info("="*80)
    logger.info("\n✅ SCORES:")
    logger.info("  • platam_score - Score PLATAM V2.0 (0-1000)")
    logger.info("  • experian_score_normalized - Score HCPN normalizado (0-1000)")
    logger.info("  • hybrid_score - Score híbrido inteligente (0-1000) ⭐")
    logger.info("  • hybrid_rating - Rating del score híbrido")

    logger.info("\n✅ INFORMACIÓN DE CÁLCULO:")
    logger.info("  • peso_platam_usado - Peso usado para PLATAM (0-1)")
    logger.info("  • peso_hcpn_usado - Peso usado para HCPN (0-1)")
    logger.info("  • estrategia_hibrido - Estrategia de cálculo aplicada")
    logger.info("  • categoria_madurez - Categoría del cliente")

    logger.info("\n" + "="*80)
    logger.info("✓ CÁLCULO COMPLETADO EXITOSAMENTE")
    logger.info("="*80)

    return df_hybrid

if __name__ == '__main__':
    calculate_hybrid_scores()
