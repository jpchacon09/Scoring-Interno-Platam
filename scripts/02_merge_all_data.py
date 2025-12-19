#!/usr/bin/env python3
"""
Merge de todas las tablas limpias en un dataset maestro

Este script:
1. Carga todos los CSVs limpios
2. Calcula due_date y days_past_due para pagos (join con préstamos)
3. Agrega métricas de pagos por cliente
4. Hace merge de clientes + HCPN + pagos + cupo
5. Crea dataset maestro con todas las features para scoring

Usage:
    python scripts/02_merge_all_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'

# Input files (cleaned)
CLIENTES_CLEAN = PROCESSED_DIR / 'clientes_clean.csv'
PAGOS_CLEAN = PROCESSED_DIR / 'pagos_clean.csv'
SOLICITUDES_PRESTAMO_CLEAN = PROCESSED_DIR / 'solicitudes_prestamo_clean.csv'
SOLICITUDES_CUPO_CLEAN = PROCESSED_DIR / 'solicitudes_cupo_clean.csv'
HCPN_CLEAN = PROCESSED_DIR / 'hcpn_clean.csv'

# Output files
PAGOS_ENRICHED = PROCESSED_DIR / 'pagos_enriched.csv'
MASTER_DATASET = PROCESSED_DIR / 'master_dataset.csv'

def enrich_pagos_with_due_dates():
    """
    Enriquece tabla de pagos con due_date y days_past_due
    mediante join con tabla de préstamos
    """
    logger.info("\n" + "="*80)
    logger.info("ENRIQUECIENDO PAGOS CON FECHAS DE VENCIMIENTO")
    logger.info("="*80)

    # Cargar datos
    pagos = pd.read_csv(PAGOS_CLEAN)
    prestamos = pd.read_csv(SOLICITUDES_PRESTAMO_CLEAN)

    logger.info(f"Pagos: {len(pagos):,} registros")
    logger.info(f"Préstamos: {len(prestamos):,} registros")

    # Normalizar tipos
    pagos['cedula'] = pagos['cedula'].astype(str)
    prestamos['cedula'] = prestamos['cedula'].astype(str)

    # Convertir fechas
    pagos['payment_date'] = pd.to_datetime(pagos['payment_date'])
    prestamos['loan_date'] = pd.to_datetime(prestamos['loan_date'])
    prestamos['due_date'] = pd.to_datetime(prestamos['due_date'])

    # Hacer join de pagos con préstamos usando loan_id
    logger.info("\nJoin pagos <- préstamos por loan_id...")
    pagos_merged = pagos.merge(
        prestamos[['loan_id', 'loan_date', 'due_date', 'term_days', 'loan_amount']],
        on='loan_id',
        how='left'
    )

    # Calcular days_past_due
    logger.info("\nCalculando days_past_due...")
    pagos_merged['days_past_due'] = (
        (pagos_merged['payment_date'] - pagos_merged['due_date']).dt.days
    )

    # Clasificar pagos
    pagos_merged['payment_status_cat'] = pd.cut(
        pagos_merged['days_past_due'],
        bins=[-np.inf, 0, 30, 60, 90, np.inf],
        labels=['on_time', '1-30_days', '31-60_days', '61-90_days', '90+_days']
    )

    # Calcular si es pago temprano, a tiempo, o tarde
    pagos_merged['payment_timeliness'] = pagos_merged['days_past_due'].apply(
        lambda x: 'early' if x < 0 else ('on_time' if x == 0 else 'late')
    )

    # Estadísticas
    logger.info("\n--- ESTADÍSTICAS DE PAGOS ---")
    with_due_date = pagos_merged['due_date'].notna().sum()
    logger.info(f"Pagos con due_date: {with_due_date}/{len(pagos_merged)} ({with_due_date/len(pagos_merged)*100:.1f}%)")

    if with_due_date > 0:
        logger.info(f"\nPromedio days_past_due: {pagos_merged['days_past_due'].mean():.1f} días")
        logger.info(f"Mediana days_past_due: {pagos_merged['days_past_due'].median():.1f} días")

        logger.info("\nDistribución de estado de pagos:")
        logger.info(pagos_merged['payment_status_cat'].value_counts().sort_index())

        logger.info("\nDistribución de puntualidad:")
        logger.info(pagos_merged['payment_timeliness'].value_counts())

    # Guardar
    pagos_merged.to_csv(PAGOS_ENRICHED, index=False)
    logger.info(f"\n✓ Guardado: {PAGOS_ENRICHED.name}")

    return pagos_merged

def aggregate_payment_metrics(pagos):
    """
    Agrega métricas de comportamiento de pagos por cliente
    """
    logger.info("\n" + "="*80)
    logger.info("AGREGANDO MÉTRICAS DE PAGOS POR CLIENTE")
    logger.info("="*80)

    # Filtrar solo pagos con due_date
    pagos_valid = pagos[pagos['due_date'].notna()].copy()
    logger.info(f"Pagos válidos para agregar: {len(pagos_valid):,}")

    # Agrupar por cliente
    payment_metrics = pagos_valid.groupby('cedula').agg({
        'payment_id': 'count',  # Total de pagos
        'payment_amount': ['sum', 'mean', 'median'],  # Montos
        'days_past_due': ['mean', 'median', 'max', 'min', 'std'],  # DPD stats
        'payment_date': ['min', 'max']  # Rango de fechas
    }).reset_index()

    # Flatten column names
    payment_metrics.columns = ['_'.join(col).strip('_') for col in payment_metrics.columns.values]
    payment_metrics.rename(columns={'cedula': 'cedula'}, inplace=True)
    payment_metrics['cedula'] = payment_metrics['cedula'].astype(str)

    # Calcular métricas adicionales
    logger.info("\nCalculando métricas adicionales...")

    # Contar pagos por categoría
    payment_categories = pagos_valid.groupby(['cedula', 'payment_status_cat']).size().unstack(fill_value=0)
    payment_categories = payment_categories.add_prefix('payments_')

    # Contar pagos por puntualidad
    payment_timeliness = pagos_valid.groupby(['cedula', 'payment_timeliness']).size().unstack(fill_value=0)
    payment_timeliness = payment_timeliness.add_prefix('payments_')

    # Merge todas las métricas
    payment_metrics = payment_metrics.merge(payment_categories, on='cedula', how='left')
    payment_metrics = payment_metrics.merge(payment_timeliness, on='cedula', how='left')

    # Calcular porcentajes
    total_payments = payment_metrics['payment_id_count']
    payment_metrics['pct_on_time'] = (
        payment_metrics.get('payments_on_time', 0) / total_payments * 100
    )
    payment_metrics['pct_late'] = (
        payment_metrics.get('payments_late', 0) / total_payments * 100
    )
    payment_metrics['pct_early'] = (
        payment_metrics.get('payments_early', 0) / total_payments * 100
    )

    # Calcular recency (días desde último pago)
    reference_date = pd.Timestamp('2025-12-19')
    payment_metrics['payment_date_max'] = pd.to_datetime(payment_metrics['payment_date_max'])
    payment_metrics['days_since_last_payment'] = (
        (reference_date - payment_metrics['payment_date_max']).dt.days
    )

    # Calcular payment history length (meses)
    payment_metrics['payment_date_min'] = pd.to_datetime(payment_metrics['payment_date_min'])
    payment_metrics['payment_history_months'] = (
        (payment_metrics['payment_date_max'] - payment_metrics['payment_date_min']).dt.days / 30.44
    )

    logger.info(f"\n✓ Métricas agregadas para {len(payment_metrics):,} clientes")
    logger.info(f"  Columnas generadas: {len(payment_metrics.columns)}")

    return payment_metrics

def create_master_dataset():
    """
    Crea dataset maestro con todas las features
    """
    logger.info("\n" + "="*80)
    logger.info("CREANDO DATASET MAESTRO")
    logger.info("="*80)

    # 1. Cargar clientes
    logger.info("\n1. Cargando clientes...")
    clientes = pd.read_csv(CLIENTES_CLEAN)
    clientes['cedula'] = clientes['cedula'].astype(str)
    logger.info(f"   {len(clientes):,} clientes")

    # 2. Cargar HCPN
    logger.info("\n2. Cargando HCPN...")
    hcpn = pd.read_csv(HCPN_CLEAN)
    hcpn['cedula'] = hcpn['cedula'].astype(str)
    logger.info(f"   {len(hcpn):,} registros HCPN")

    # 3. Enriquecer pagos
    logger.info("\n3. Enriqueciendo pagos...")
    pagos_enriched = enrich_pagos_with_due_dates()

    # 4. Agregar métricas de pagos
    logger.info("\n4. Agregando métricas de pagos...")
    payment_metrics = aggregate_payment_metrics(pagos_enriched)

    # 5. Cargar solicitudes de cupo
    logger.info("\n5. Cargando solicitudes de cupo...")
    cupo = pd.read_csv(SOLICITUDES_CUPO_CLEAN)

    # Agregar última solicitud de cupo por cliente
    cupo['cedula'] = cupo['cedula'].astype(str)
    cupo_last = cupo.sort_values('request_date', ascending=False).groupby('cedula').first().reset_index()
    cupo_last = cupo_last[['cedula', 'requested_loc', 'credit_study_score', 'credit_study_result', 'risk_profile']]
    cupo_last = cupo_last.add_prefix('last_cupo_')
    cupo_last.rename(columns={'last_cupo_cedula': 'cedula'}, inplace=True)
    cupo_last['cedula'] = cupo_last['cedula'].astype(str)

    logger.info(f"   {len(cupo_last):,} clientes con solicitud de cupo")

    # 6. Merge todo
    logger.info("\n6. Merging todas las tablas...")

    # Empezar con clientes
    master = clientes.copy()
    logger.info(f"   Base: {len(master):,} clientes")

    # Merge con HCPN (left join - no todos tienen HCPN)
    master = master.merge(hcpn, on='cedula', how='left', suffixes=('', '_hcpn'))
    logger.info(f"   + HCPN: {len(master):,} registros")

    # Merge con payment metrics (left join - no todos tienen pagos)
    master = master.merge(payment_metrics, on='cedula', how='left')
    logger.info(f"   + Payment metrics: {len(master):,} registros")

    # Merge con cupo (left join)
    master = master.merge(cupo_last, on='cedula', how='left')
    logger.info(f"   + Cupo: {len(master):,} registros")

    # 7. Limpiar duplicados de columnas
    logger.info("\n7. Limpiando columnas duplicadas...")

    # Resolver client_id duplicado
    if 'client_id_hcpn' in master.columns:
        master['client_id'] = master['client_id'].fillna(master['client_id_hcpn'])
        master.drop(columns=['client_id_hcpn'], inplace=True)

    # 8. Crear flags de disponibilidad de datos
    logger.info("\n8. Creando flags de disponibilidad...")
    master['has_hcpn'] = master['experian_score'].notna()
    master['has_payment_history'] = master['payment_id_count'].notna()
    master['has_cupo_request'] = master['last_cupo_requested_loc'].notna()

    # 9. Estadísticas finales
    logger.info("\n" + "="*80)
    logger.info("ESTADÍSTICAS DEL DATASET MAESTRO")
    logger.info("="*80)

    logger.info(f"\nTotal registros: {len(master):,}")
    logger.info(f"Total columnas: {len(master.columns)}")

    logger.info("\nDisponibilidad de datos:")
    logger.info(f"  Con HCPN: {master['has_hcpn'].sum():,} ({master['has_hcpn'].sum()/len(master)*100:.1f}%)")
    logger.info(f"  Con historial de pagos: {master['has_payment_history'].sum():,} ({master['has_payment_history'].sum()/len(master)*100:.1f}%)")
    logger.info(f"  Con solicitud de cupo: {master['has_cupo_request'].sum():,} ({master['has_cupo_request'].sum()/len(master)*100:.1f}%)")

    logger.info("\nEstadísticas de Experian Score:")
    if master['experian_score'].notna().sum() > 0:
        logger.info(f"  Promedio: {master['experian_score'].mean():.1f}")
        logger.info(f"  Mediana: {master['experian_score'].median():.1f}")
        logger.info(f"  Min: {master['experian_score'].min():.1f}")
        logger.info(f"  Max: {master['experian_score'].max():.1f}")

    logger.info("\nEstadísticas de Pagos:")
    if master['payment_id_count'].notna().sum() > 0:
        logger.info(f"  Promedio pagos por cliente: {master['payment_id_count'].mean():.1f}")
        logger.info(f"  Promedio DPD: {master['days_past_due_mean'].mean():.1f} días")
        logger.info(f"  Promedio % pagos a tiempo: {master['pct_on_time'].mean():.1f}%")

    # 10. Guardar
    master.to_csv(MASTER_DATASET, index=False)
    logger.info(f"\n✓ Dataset maestro guardado: {MASTER_DATASET.name}")
    logger.info(f"  Tamaño: {MASTER_DATASET.stat().st_size / 1024 / 1024:.2f} MB")

    # 11. Guardar resumen de columnas
    logger.info("\n" + "="*80)
    logger.info("COLUMNAS EN DATASET MAESTRO")
    logger.info("="*80)

    column_info = pd.DataFrame({
        'column': master.columns,
        'dtype': master.dtypes.values,
        'non_null': master.notna().sum().values,
        'null_pct': (master.isna().sum() / len(master) * 100).values
    })

    logger.info(f"\n{column_info.to_string(index=False)}")

    return master

def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("MERGE DE DATOS BNPL + HCPN")
    logger.info("="*80)

    # Crear dataset maestro
    master = create_master_dataset()

    logger.info("\n" + "="*80)
    logger.info("✓ MERGE COMPLETADO")
    logger.info("="*80)
    logger.info(f"\nDataset maestro: {MASTER_DATASET.absolute()}")
    logger.info("\nPróximo paso: Ejecutar scripts/03_calculate_platam_score.py")

    return master

if __name__ == '__main__':
    main()
