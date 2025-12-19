#!/usr/bin/env python3
"""
Análisis del CSV de historial de crédito (HCPN)

Usage:
    python scripts/analyze_hcpn_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
HCPN_CSV = BASE_DIR / 'export-historial_credito-19-12-2025.csv'

def analyze_hcpn():
    """Analiza CSV de historial de crédito"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: HISTORIAL DE CRÉDITO (HCPN)")
    logger.info("="*80)

    df = pd.read_csv(HCPN_CSV)

    logger.info(f"\nTotal registros: {len(df):,}")
    logger.info(f"Columnas: {len(df.columns)}")

    # Tipos de HCPN
    logger.info("\n--- TIPOS DE HCPN ---")
    logger.info(df['hc_type'].value_counts())

    # Campo de identificación
    logger.info("\n--- IDENTIFICACIÓN ---")
    logger.info(f"Registros con cédula: {df['hcpn_id_data_identificacion_numero'].notna().sum()}")
    logger.info(f"Cédulas únicas: {df['hcpn_id_data_identificacion_numero'].nunique()}")

    # Ver algunos ejemplos de cédulas
    cedulas = df['hcpn_id_data_identificacion_numero'].dropna().head(10)
    logger.info("\nEjemplos de cédulas:")
    for cedula in cedulas:
        logger.info(f"  {cedula}")

    # Scores de Experian
    logger.info("\n--- SCORES DE EXPERIAN ---")
    df['hcpn_score_experian_puntaje'] = pd.to_numeric(df['hcpn_score_experian_puntaje'], errors='coerce')
    scores = df['hcpn_score_experian_puntaje'].dropna()

    logger.info(f"Registros con score: {len(scores)}/{len(df)} ({len(scores)/len(df)*100:.1f}%)")
    logger.info(f"Score promedio: {scores.mean():.1f}")
    logger.info(f"Score mínimo: {scores.min():.1f}")
    logger.info(f"Score máximo: {scores.max():.1f}")
    logger.info(f"Score mediana: {scores.median():.1f}")

    # Distribución de scores
    logger.info("\nDistribución de Scores:")
    bins = [0, 300, 500, 650, 750, 850, 1000]
    labels = ['Muy Bajo (0-300)', 'Bajo (300-500)', 'Medio (500-650)', 'Bueno (650-750)', 'Muy Bueno (750-850)', 'Excelente (850+)']
    df['score_category'] = pd.cut(df['hcpn_score_experian_puntaje'], bins=bins, labels=labels)
    logger.info(df['score_category'].value_counts().sort_index())

    # Información financiera
    logger.info("\n--- INFORMACIÓN FINANCIERA ---")

    # Ingresos
    df['hcpn_ingreso'] = pd.to_numeric(df['hcpn_ingreso'], errors='coerce')
    ingresos = df['hcpn_ingreso'].dropna()
    if len(ingresos) > 0:
        logger.info(f"Ingreso promedio: ${ingresos.mean():,.0f}")
        logger.info(f"Ingreso mediana: ${ingresos.median():,.0f}")

    # Cuota total
    df['hcpn_cuota_total'] = pd.to_numeric(df['hcpn_cuota_total'], errors='coerce')
    cuotas = df['hcpn_cuota_total'].dropna()
    if len(cuotas) > 0:
        logger.info(f"Cuota total promedio: ${cuotas.mean():,.0f}")
        logger.info(f"Cuota total mediana: ${cuotas.median():,.0f}")

    # Créditos vigentes
    logger.info("\n--- CRÉDITOS Y COMPORTAMIENTO ---")
    df['hcpn_creditos_principal_credito_vigentes'] = pd.to_numeric(df['hcpn_creditos_principal_credito_vigentes'], errors='coerce')
    df['hcpn_creditos_principal_creditos_cerrados'] = pd.to_numeric(df['hcpn_creditos_principal_creditos_cerrados'], errors='coerce')
    df['hcpn_creditos_principal_creditos_actuales_negativos'] = pd.to_numeric(df['hcpn_creditos_principal_creditos_actuales_negativos'], errors='coerce')

    logger.info(f"Créditos vigentes promedio: {df['hcpn_creditos_principal_credito_vigentes'].mean():.1f}")
    logger.info(f"Créditos cerrados promedio: {df['hcpn_creditos_principal_creditos_cerrados'].mean():.1f}")
    logger.info(f"Créditos con mora promedio: {df['hcpn_creditos_principal_creditos_actuales_negativos'].mean():.1f}")

    # Comportamiento de pago
    logger.info("\n--- COMPORTAMIENTO DE PAGO (Primeros 5 ejemplos) ---")
    comportamiento = df['hcpn_comportamiento'].dropna().head(5)
    for i, comp in enumerate(comportamiento, 1):
        logger.info(f"\nCliente {i}: {comp[:50]}...")  # Primeros 50 caracteres

    # URLs de HCPN completos
    logger.info("\n--- ENLACES A HCPN COMPLETOS EN S3 ---")
    urls = df['hcpn_url'].notna().sum()
    logger.info(f"Registros con URL a S3: {urls}/{len(df)} ({urls/len(df)*100:.1f}%)")

    if urls > 0:
        logger.info("\nEjemplos de URLs:")
        for url in df['hcpn_url'].dropna().head(3):
            logger.info(f"  {url}")

    # Decision
    logger.info("\n--- DECISIÓN DE SCORE ---")
    if 'hcpn_score_decision' in df.columns:
        logger.info(df['hcpn_score_decision'].value_counts())

    # Relación con solicitudes
    logger.info("\n--- RELACIÓN CON SOLICITUDES ---")
    logger.info(f"Registros con id_source: {df['hc_id_source'].notna().sum()}")
    logger.info(f"Registros con id_client: {df['hc_id_client'].notna().sum()}")

    # Mapeo con clientes
    logger.info("\n--- MAPEO CON CLIENTES ---")
    logger.info("Campo clave para merge: hcpn_id_data_identificacion_numero")

    # Campos más importantes para scoring
    logger.info("\n--- CAMPOS CRÍTICOS PARA SCORING ---")
    campos_scoring = {
        'hcpn_score_experian_puntaje': 'Score Experian',
        'hcpn_ingreso': 'Ingreso declarado',
        'hcpn_cuota_total': 'Cuota total de créditos',
        'hcpn_creditos_principal_credito_vigentes': 'Créditos vigentes',
        'hcpn_creditos_principal_creditos_actuales_negativos': 'Créditos en mora',
        'hcpn_creditos_principal_hist_neg_ult_12_meses': 'Historial negativo últimos 12 meses',
        'hcpn_comportamiento': 'Comportamiento de pago histórico',
    }

    for campo, descripcion in campos_scoring.items():
        if campo in df.columns:
            non_null = df[campo].notna().sum()
            pct = non_null / len(df) * 100
            logger.info(f"{descripcion:50} {non_null:4}/{len(df)} ({pct:5.1f}%)")

    return df

def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("ANÁLISIS DE HISTORIAL DE CRÉDITO (HCPN)")
    logger.info("="*80)

    df = analyze_hcpn()

    logger.info("\n" + "="*80)
    logger.info("CONCLUSIÓN")
    logger.info("="*80)
    logger.info("\n✅ Este CSV simplifica ENORMEMENTE el merge:")
    logger.info("   1. Ya tiene scores de Experian parseados")
    logger.info("   2. Tiene número de cédula para hacer join")
    logger.info("   3. Tiene métricas financieras listas")
    logger.info("   4. NO necesitamos descargar JSONs de S3")
    logger.info("\n📌 Próximo paso: Hacer merge con clientes por cédula")

    return df

if __name__ == '__main__':
    main()
