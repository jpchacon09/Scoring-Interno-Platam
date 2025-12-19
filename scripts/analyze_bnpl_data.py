#!/usr/bin/env python3
"""
Análisis profundo de los datos BNPL para entender estructura y crear estrategia de merge

Usage:
    python scripts/analyze_bnpl_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
CLIENTES_CSV = BASE_DIR / 'export-clientes-19-12-2025.csv'
PAGOS_CSV = BASE_DIR / 'export-pagos-19-12-2025.csv'
SOLICITUDES_CUPO_CSV = BASE_DIR / 'export-solicitudes_cupo-19-12-2025.csv'
SOLICITUDES_PRESTAMO_CSV = BASE_DIR / 'export-solicitud_prestamo-19-12-2025.csv'

def analyze_clientes():
    """Analiza tabla de clientes"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: CLIENTES")
    logger.info("="*80)

    df = pd.read_csv(CLIENTES_CSV)

    logger.info(f"\nTotal registros: {len(df):,}")
    logger.info(f"Columnas: {len(df.columns)}")

    # Campos clave para identificación
    logger.info("\n--- CAMPOS DE IDENTIFICACIÓN ---")
    logger.info(f"_ID (client_id): {df['_ID'].nunique()} únicos")
    logger.info(f"cl_doc_number (cédula): {df['cl_doc_number'].nunique()} únicos")
    logger.info(f"cl_email: {df['cl_email'].nunique()} únicos")

    # Duplicados
    dup_doc = df['cl_doc_number'].duplicated().sum()
    if dup_doc > 0:
        logger.warning(f"⚠️  {dup_doc} cédulas duplicadas")
        dups = df[df['cl_doc_number'].duplicated(keep=False)]['cl_doc_number'].value_counts()
        logger.warning(f"   Primeras duplicadas: {dups.head()}")

    # Estados
    logger.info("\n--- ESTADOS DE CLIENTES ---")
    logger.info(df['cl_estado'].value_counts())

    # Cupos
    logger.info("\n--- ESTADÍSTICAS DE CUPO ---")
    logger.info(f"Cupo total otorgado: ${df['cl_cupo'].sum():,.0f}")
    logger.info(f"Cupo disponible: ${df['cl_cupo_disponible'].sum():,.0f}")
    logger.info(f"Promedio cupo: ${df['cl_cupo'].mean():,.0f}")
    logger.info(f"Mediana cupo: ${df['cl_cupo'].median():,.0f}")

    # Tipos de clientes
    logger.info("\n--- TIPOS DE CLIENTES ---")
    logger.info(df['cl_type'].value_counts())

    # Tipos de negocio
    logger.info("\n--- TIPOS DE NEGOCIO (Top 10) ---")
    if 'cl_bus_type' in df.columns:
        logger.info(df['cl_bus_type'].value_counts().head(10))

    # Ciudades
    logger.info("\n--- CIUDADES (Top 10) ---")
    logger.info(df['cl_city'].value_counts().head(10))

    # Campos relevantes para scoring
    logger.info("\n--- CAMPOS PARA SCORING ---")
    scoring_fields = {
        'cl_cupo': 'Cupo total',
        'cl_cupo_disponible': 'Cupo disponible',
        'cl_collection_priority_score': 'Score de prioridad de cobranza',
        'cl_risk_profile': 'Perfil de riesgo',
        'cl_payment_probability_score': 'Score de probabilidad de pago',
        'cl_status_plan': 'Estado de plan de pago',
    }

    for field, desc in scoring_fields.items():
        if field in df.columns:
            non_null = df[field].notna().sum()
            logger.info(f"{desc}: {non_null}/{len(df)} ({non_null/len(df)*100:.1f}%)")

    return df

def analyze_pagos():
    """Analiza tabla de pagos"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: PAGOS")
    logger.info("="*80)

    df = pd.read_csv(PAGOS_CSV)

    logger.info(f"\nTotal pagos: {len(df):,}")
    logger.info(f"Columnas: {len(df.columns)}")

    # Clientes únicos con pagos
    logger.info(f"Clientes únicos con pagos: {df['p_cl_doc_number'].nunique()}")

    # Tipos de pagos
    logger.info("\n--- TIPOS DE PAGOS ---")
    logger.info(df['p_type'].value_counts().head(10))

    # Estados de pagos
    logger.info("\n--- ESTADOS DE PAGOS ---")
    logger.info(df['p_status'].value_counts())

    # Montos
    logger.info("\n--- ESTADÍSTICAS DE MONTOS ---")
    logger.info(f"Total pagado: ${df['p_payment_amount'].astype(float).sum():,.0f}")
    logger.info(f"Promedio pago: ${df['p_payment_amount'].astype(float).mean():,.0f}")
    logger.info(f"Mediana pago: ${df['p_payment_amount'].astype(float).median():,.0f}")

    # Fechas
    logger.info("\n--- RANGO DE FECHAS ---")
    df['p_payment_date'] = pd.to_datetime(df['p_payment_date'], format='%d/%m/%Y', errors='coerce')
    logger.info(f"Primer pago: {df['p_payment_date'].min()}")
    logger.info(f"Último pago: {df['p_payment_date'].max()}")

    # Pagos por mes
    logger.info("\n--- PAGOS POR MES (últimos 6 meses) ---")
    df['month'] = df['p_payment_date'].dt.to_period('M')
    monthly = df.groupby('month').size().tail(6)
    for month, count in monthly.items():
        logger.info(f"{month}: {count:,} pagos")

    return df

def analyze_solicitudes_cupo():
    """Analiza solicitudes de cupo (LOC requests)"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: SOLICITUDES DE CUPO")
    logger.info("="*80)

    df = pd.read_csv(SOLICITUDES_CUPO_CSV)

    logger.info(f"\nTotal solicitudes: {len(df):,}")
    logger.info(f"Columnas: {len(df.columns)}")

    # Estados
    logger.info("\n--- ESTADOS DE SOLICITUDES ---")
    logger.info(df['clr_status'].value_counts())

    # Cupos solicitados
    logger.info("\n--- CUPOS SOLICITADOS ---")
    if 'clr_requested_loc' in df.columns:
        df['clr_requested_loc'] = pd.to_numeric(df['clr_requested_loc'], errors='coerce')
        logger.info(f"Total solicitado: ${df['clr_requested_loc'].sum():,.0f}")
        logger.info(f"Promedio: ${df['clr_requested_loc'].mean():,.0f}")

    # Estudios de crédito
    logger.info("\n--- ESTUDIOS DE CRÉDITO ---")
    if 'clr_credit_study_result' in df.columns:
        logger.info(df['clr_credit_study_result'].value_counts())

    if 'clr_credit_study_score' in df.columns:
        df['clr_credit_study_score'] = pd.to_numeric(df['clr_credit_study_score'], errors='coerce')
        logger.info(f"\nScore promedio: {df['clr_credit_study_score'].mean():.1f}")
        logger.info(f"Score mínimo: {df['clr_credit_study_score'].min():.1f}")
        logger.info(f"Score máximo: {df['clr_credit_study_score'].max():.1f}")

    # Perfiles de riesgo
    logger.info("\n--- PERFILES DE RIESGO ---")
    if 'clr_risk_profile' in df.columns:
        logger.info(df['clr_risk_profile'].value_counts())

    return df

def analyze_solicitudes_prestamo():
    """Analiza solicitudes de préstamo (loan requests)"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: SOLICITUDES DE PRÉSTAMO")
    logger.info("="*80)

    df = pd.read_csv(SOLICITUDES_PRESTAMO_CSV)

    logger.info(f"\nTotal solicitudes: {len(df):,}")
    logger.info(f"Columnas: {len(df.columns)}")

    # Estados
    logger.info("\n--- ESTADOS DE SOLICITUDES ---")
    logger.info(df['lr_status'].value_counts().head(10))

    # Montos
    logger.info("\n--- MONTOS SOLICITADOS ---")
    df['lr_order_value'] = pd.to_numeric(df['lr_order_value'], errors='coerce')
    logger.info(f"Total solicitado: ${df['lr_order_value'].sum():,.0f}")
    logger.info(f"Promedio: ${df['lr_order_value'].mean():,.0f}")
    logger.info(f"Mediana: ${df['lr_order_value'].median():,.0f}")

    # Por partner
    logger.info("\n--- TOP 10 PARTNERS ---")
    partner_stats = df.groupby('lr_partner_id').agg({
        'lr_order_value': ['count', 'sum']
    }).round(0)
    logger.info(partner_stats.head(10))

    return df

def analyze_relationships():
    """Analiza relaciones entre tablas"""
    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS: RELACIONES ENTRE TABLAS")
    logger.info("="*80)

    # Cargar datos
    clientes = pd.read_csv(CLIENTES_CSV)
    pagos = pd.read_csv(PAGOS_CSV)
    sol_cupo = pd.read_csv(SOLICITUDES_CUPO_CSV)
    sol_prestamo = pd.read_csv(SOLICITUDES_PRESTAMO_CSV)

    # Clientes en cada tabla
    logger.info("\n--- OVERLAP DE CLIENTES ---")

    clientes_ids = set(clientes['_ID'].astype(str))
    clientes_docs = set(clientes['cl_doc_number'].dropna().astype(str))

    pagos_docs = set(pagos['p_cl_doc_number'].dropna().astype(str))
    sol_cupo_docs = set(sol_cupo['clr_doc_number'].dropna().astype(str))
    sol_prestamo_docs = set(sol_prestamo['lr_doc_number'].dropna().astype(str))

    logger.info(f"Clientes totales: {len(clientes)}")
    logger.info(f"  Con pagos: {len(clientes_docs & pagos_docs)} ({len(clientes_docs & pagos_docs)/len(clientes)*100:.1f}%)")
    logger.info(f"  Con solicitud de cupo: {len(clientes_docs & sol_cupo_docs)} ({len(clientes_docs & sol_cupo_docs)/len(clientes)*100:.1f}%)")
    logger.info(f"  Con solicitud de préstamo: {len(clientes_docs & sol_prestamo_docs)} ({len(clientes_docs & sol_prestamo_docs)/len(clientes)*100:.1f}%)")

    # Clientes sin pagos
    sin_pagos = clientes_docs - pagos_docs
    logger.info(f"\nClientes SIN pagos registrados: {len(sin_pagos)}")

    # Campos de join
    logger.info("\n--- CAMPOS PARA JOIN ---")
    logger.info("Clientes:")
    logger.info("  - _ID (primary key)")
    logger.info("  - cl_doc_number (cédula)")
    logger.info("  - cl_clr_id (link a solicitud de cupo)")

    logger.info("\nPagos:")
    logger.info("  - p_cl_id (link a cliente por _ID)")
    logger.info("  - p_cl_doc_number (link por cédula)")
    logger.info("  - p_l_id (link a préstamo)")

    logger.info("\nSolicitudes Cupo:")
    logger.info("  - clr_cl_id (link a cliente)")
    logger.info("  - clr_doc_number (cédula)")

    logger.info("\nSolicitudes Préstamo:")
    logger.info("  - lr_cl_id (link a cliente)")
    logger.info("  - lr_doc_number (cédula)")

def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("ANÁLISIS COMPLETO DE DATOS BNPL")
    logger.info("="*80)

    # Analizar cada tabla
    clientes_df = analyze_clientes()
    pagos_df = analyze_pagos()
    sol_cupo_df = analyze_solicitudes_cupo()
    sol_prestamo_df = analyze_solicitudes_prestamo()

    # Analizar relaciones
    analyze_relationships()

    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS COMPLETADO")
    logger.info("="*80)

    return {
        'clientes': clientes_df,
        'pagos': pagos_df,
        'solicitudes_cupo': sol_cupo_df,
        'solicitudes_prestamo': sol_prestamo_df
    }

if __name__ == '__main__':
    main()
