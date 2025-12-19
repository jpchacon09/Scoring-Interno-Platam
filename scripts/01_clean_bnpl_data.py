#!/usr/bin/env python3
"""
Limpieza y normalización de datos BNPL + HCPN

Este script:
1. Limpia y normaliza los 5 CSVs exportados
2. Convierte formatos de fecha a YYYY-MM-DD
3. Calcula campos faltantes (due_date, days_past_due)
4. Normaliza identificadores (cedula)
5. Filtra registros inválidos
6. Guarda datos limpios en data/processed/

Usage:
    python scripts/01_clean_bnpl_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'

# Input files
CLIENTES_CSV = BASE_DIR / 'export-clientes-19-12-2025.csv'
PAGOS_CSV = BASE_DIR / 'export-pagos-19-12-2025.csv'
SOLICITUDES_CUPO_CSV = BASE_DIR / 'export-solicitudes_cupo-19-12-2025.csv'
SOLICITUDES_PRESTAMO_CSV = BASE_DIR / 'export-solicitud_prestamo-19-12-2025.csv'
HCPN_CSV = BASE_DIR / 'export-historial_credito-19-12-2025.csv'

# Output files
CLIENTES_CLEAN = PROCESSED_DIR / 'clientes_clean.csv'
PAGOS_CLEAN = PROCESSED_DIR / 'pagos_clean.csv'
SOLICITUDES_CUPO_CLEAN = PROCESSED_DIR / 'solicitudes_cupo_clean.csv'
SOLICITUDES_PRESTAMO_CLEAN = PROCESSED_DIR / 'solicitudes_prestamo_clean.csv'
HCPN_CLEAN = PROCESSED_DIR / 'hcpn_clean.csv'

def convert_date_column(df, col_name, date_format='%d/%m/%Y'):
    """
    Convierte columna de fecha a formato YYYY-MM-DD

    Args:
        df: DataFrame
        col_name: Nombre de la columna
        date_format: Formato de entrada (default: dd/mm/yyyy)

    Returns:
        Series con fechas convertidas
    """
    if col_name not in df.columns:
        logger.warning(f"Columna {col_name} no encontrada")
        return None

    # Intentar múltiples formatos
    formats_to_try = [
        '%d/%m/%Y',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S'
    ]

    result = None
    for fmt in formats_to_try:
        try:
            result = pd.to_datetime(df[col_name], format=fmt, errors='coerce')
            non_null = result.notna().sum()
            if non_null > 0:
                logger.info(f"  ✓ Convertidos {non_null} registros con formato {fmt}")
                break
        except:
            continue

    if result is None:
        # Último intento sin formato específico
        result = pd.to_datetime(df[col_name], errors='coerce')

    return result

def normalize_cedula(cedula):
    """
    Normaliza número de cédula removiendo espacios, guiones, etc.
    """
    if pd.isna(cedula):
        return None

    cedula_str = str(cedula).strip()
    # Remover puntos, guiones, espacios
    cedula_str = cedula_str.replace('.', '').replace('-', '').replace(' ', '')
    # Remover decimales si es que vienen (.0)
    if '.' in cedula_str:
        cedula_str = cedula_str.split('.')[0]

    return cedula_str if cedula_str else None

def clean_clientes():
    """Limpia tabla de clientes"""
    logger.info("\n" + "="*80)
    logger.info("LIMPIANDO: CLIENTES")
    logger.info("="*80)

    df = pd.read_csv(CLIENTES_CSV)
    original_count = len(df)
    logger.info(f"Registros originales: {original_count:,}")

    # Normalizar cédula
    logger.info("\n1. Normalizando cédulas...")
    df['cedula'] = df['cl_doc_number'].apply(normalize_cedula)

    # Remover duplicados por cédula (quedarnos con el más reciente)
    logger.info("\n2. Removiendo duplicados...")
    duplicated_before = df['cedula'].duplicated().sum()
    if duplicated_before > 0:
        logger.warning(f"  ⚠️  Encontrados {duplicated_before} duplicados")
        # Convertir fecha de creación
        if 'cl_date_created' in df.columns:
            df['date_created'] = convert_date_column(df, 'cl_date_created')
            df = df.sort_values('date_created', ascending=False)
        df = df.drop_duplicates(subset=['cedula'], keep='first')
        logger.info(f"  ✓ Removidos {duplicated_before} duplicados")

    # Convertir fechas
    logger.info("\n3. Convirtiendo fechas...")
    date_columns = ['cl_date_created', 'cl_date_modified', 'cl_date_activated']
    for col in date_columns:
        if col in df.columns:
            df[col] = convert_date_column(df, col)

    # Convertir campos numéricos
    logger.info("\n4. Convirtiendo campos numéricos...")
    numeric_columns = [
        'cl_cupo', 'cl_cupo_disponible', 'cl_collection_priority_score',
        'cl_payment_probability_score'
    ]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Crear campos derivados
    logger.info("\n5. Creando campos derivados...")
    df['cupo_utilizado'] = df['cl_cupo'] - df['cl_cupo_disponible']
    df['pct_utilization'] = (df['cupo_utilizado'] / df['cl_cupo'] * 100).fillna(0)

    # Calcular antiguedad en meses
    if 'cl_date_created' in df.columns:
        reference_date = pd.Timestamp('2025-12-19')
        df['months_as_client'] = ((reference_date - df['cl_date_created']).dt.days / 30.44).fillna(0).astype(int)

    # Seleccionar y renombrar columnas clave
    columns_to_keep = {
        '_ID': 'client_id',
        'cedula': 'cedula',
        'cl_email': 'email',
        'cl_phone': 'phone',
        'cl_first_name': 'first_name',
        'cl_last_name': 'last_name',
        'cl_type': 'client_type',
        'cl_estado': 'estado',
        'cl_cupo': 'cupo_total',
        'cl_cupo_disponible': 'cupo_disponible',
        'cupo_utilizado': 'cupo_utilizado',
        'pct_utilization': 'pct_utilization',
        'cl_city': 'city',
        'cl_bus_type': 'business_type',
        'cl_date_created': 'date_created',
        'cl_date_activated': 'date_activated',
        'months_as_client': 'months_as_client',
        'cl_collection_priority_score': 'collection_score',
        'cl_payment_probability_score': 'payment_probability_score',
        'cl_risk_profile': 'risk_profile',
        'cl_status_plan': 'status_plan'
    }

    # Mantener solo columnas que existan
    rename_dict = {k: v for k, v in columns_to_keep.items() if k in df.columns}
    df_clean = df[list(rename_dict.keys())].rename(columns=rename_dict)

    # Filtrar clientes válidos (con cédula)
    df_clean = df_clean[df_clean['cedula'].notna()]

    logger.info(f"\n✓ Limpieza completada: {len(df_clean):,} registros")
    logger.info(f"  Removidos: {original_count - len(df_clean):,}")

    return df_clean

def clean_pagos():
    """Limpia tabla de pagos"""
    logger.info("\n" + "="*80)
    logger.info("LIMPIANDO: PAGOS")
    logger.info("="*80)

    df = pd.read_csv(PAGOS_CSV)
    original_count = len(df)
    logger.info(f"Registros originales: {original_count:,}")

    # Normalizar cédula
    logger.info("\n1. Normalizando cédulas...")
    df['cedula'] = df['p_cl_doc_number'].apply(normalize_cedula)

    # Convertir fechas
    logger.info("\n2. Convirtiendo fechas...")
    df['payment_date'] = convert_date_column(df, 'p_payment_date')

    # Convertir montos
    logger.info("\n3. Convirtiendo montos...")
    df['payment_amount'] = pd.to_numeric(df['p_payment_amount'], errors='coerce')

    # Filtrar pagos válidos
    logger.info("\n4. Filtrando pagos válidos...")

    # Remover pagos sin fecha o monto
    df = df[df['payment_date'].notna()]
    df = df[df['payment_amount'].notna()]
    df = df[df['payment_amount'] > 0]

    # Filtrar por tipo de pago (excluir ajustes, castigos, etc.)
    if 'p_type' in df.columns:
        # Excluir write-offs y ajustes
        tipos_excluir = ['write off', 'ajuste']
        df = df[~df['p_type'].str.lower().str.contains('|'.join(tipos_excluir), na=False)]

    # Filtrar por estado (solo pagos confirmados)
    if 'p_status' in df.columns:
        # Estados válidos observados en la data
        estados_validos = ['Registrado', 'account_credited']
        df = df[df['p_status'].isin(estados_validos)]

    # Seleccionar y renombrar columnas
    columns_to_keep = {
        '_ID': 'payment_id',
        'cedula': 'cedula',
        'p_cl_id': 'client_id',
        'p_l_id': 'loan_id',
        'payment_date': 'payment_date',
        'payment_amount': 'payment_amount',
        'p_type': 'payment_type',
        'p_status': 'payment_status',
        'p_payment_method': 'payment_method'
    }

    rename_dict = {k: v for k, v in columns_to_keep.items() if k in df.columns}
    df_clean = df[list(rename_dict.keys())].rename(columns=rename_dict)

    # Filtrar registros con cédula
    df_clean = df_clean[df_clean['cedula'].notna()]

    logger.info(f"\n✓ Limpieza completada: {len(df_clean):,} registros")
    logger.info(f"  Removidos: {original_count - len(df_clean):,}")
    logger.info(f"  Total pagado: ${df_clean['payment_amount'].sum():,.0f}")

    return df_clean

def clean_solicitudes_prestamo():
    """Limpia tabla de solicitudes de préstamo"""
    logger.info("\n" + "="*80)
    logger.info("LIMPIANDO: SOLICITUDES DE PRÉSTAMO")
    logger.info("="*80)

    df = pd.read_csv(SOLICITUDES_PRESTAMO_CSV)
    original_count = len(df)
    logger.info(f"Registros originales: {original_count:,}")

    # Normalizar cédula
    logger.info("\n1. Normalizando cédulas...")
    df['cedula'] = df['lr_doc_number'].apply(normalize_cedula)

    # Convertir fechas
    logger.info("\n2. Convirtiendo fechas...")
    df['loan_date'] = convert_date_column(df, 'lr_timestamp')

    # Convertir campos numéricos
    logger.info("\n3. Convirtiendo campos numéricos...")
    df['order_value'] = pd.to_numeric(df['lr_order_value'], errors='coerce')
    df['term_days'] = pd.to_numeric(df['lr_cp_term'], errors='coerce')

    # Calcular due_date
    logger.info("\n4. Calculando fechas de vencimiento...")
    df['due_date'] = df.apply(
        lambda row: row['loan_date'] + timedelta(days=row['term_days'])
        if pd.notna(row['loan_date']) and pd.notna(row['term_days'])
        else None,
        axis=1
    )

    calculated = df['due_date'].notna().sum()
    logger.info(f"  ✓ Calculadas {calculated:,} fechas de vencimiento")

    # Seleccionar y renombrar columnas
    columns_to_keep = {
        '_ID': 'loan_id',
        'cedula': 'cedula',
        'lr_cl_id': 'client_id',
        'loan_date': 'loan_date',
        'due_date': 'due_date',
        'order_value': 'loan_amount',
        'term_days': 'term_days',
        'lr_status': 'loan_status',
        'lr_partner_id': 'partner_id',
        'lr_shop_name': 'shop_name'
    }

    rename_dict = {k: v for k, v in columns_to_keep.items() if k in df.columns}
    df_clean = df[list(rename_dict.keys())].rename(columns=rename_dict)

    # Filtrar válidos
    df_clean = df_clean[df_clean['cedula'].notna()]
    df_clean = df_clean[df_clean['loan_date'].notna()]

    logger.info(f"\n✓ Limpieza completada: {len(df_clean):,} registros")
    logger.info(f"  Removidos: {original_count - len(df_clean):,}")

    return df_clean

def clean_solicitudes_cupo():
    """Limpia tabla de solicitudes de cupo"""
    logger.info("\n" + "="*80)
    logger.info("LIMPIANDO: SOLICITUDES DE CUPO")
    logger.info("="*80)

    df = pd.read_csv(SOLICITUDES_CUPO_CSV)
    original_count = len(df)
    logger.info(f"Registros originales: {original_count:,}")

    # Normalizar cédula
    logger.info("\n1. Normalizando cédulas...")
    df['cedula'] = df['clr_doc_number'].apply(normalize_cedula)

    # Convertir fechas
    logger.info("\n2. Convirtiendo fechas...")
    df['request_date'] = convert_date_column(df, 'clr_date_created')

    # Convertir campos numéricos
    logger.info("\n3. Convirtiendo campos numéricos...")
    df['requested_loc'] = pd.to_numeric(df['clr_requested_loc'], errors='coerce')
    df['credit_study_score'] = pd.to_numeric(df['clr_credit_study_score'], errors='coerce')

    # Seleccionar y renombrar columnas
    columns_to_keep = {
        '_ID': 'request_id',
        'cedula': 'cedula',
        'clr_cl_id': 'client_id',
        'request_date': 'request_date',
        'requested_loc': 'requested_loc',
        'clr_status': 'request_status',
        'credit_study_score': 'credit_study_score',
        'clr_credit_study_result': 'credit_study_result',
        'clr_risk_profile': 'risk_profile'
    }

    rename_dict = {k: v for k, v in columns_to_keep.items() if k in df.columns}
    df_clean = df[list(rename_dict.keys())].rename(columns=rename_dict)

    # Filtrar válidos
    df_clean = df_clean[df_clean['cedula'].notna()]

    logger.info(f"\n✓ Limpieza completada: {len(df_clean):,} registros")
    logger.info(f"  Removidos: {original_count - len(df_clean):,}")

    return df_clean

def clean_hcpn():
    """Limpia tabla de historial de crédito (HCPN)"""
    logger.info("\n" + "="*80)
    logger.info("LIMPIANDO: HISTORIAL DE CRÉDITO (HCPN)")
    logger.info("="*80)

    df = pd.read_csv(HCPN_CSV)
    original_count = len(df)
    logger.info(f"Registros originales: {original_count:,}")

    # Normalizar cédula
    logger.info("\n1. Normalizando cédulas...")
    df['cedula'] = df['hcpn_id_data_identificacion_numero'].apply(normalize_cedula)

    # Convertir campos numéricos clave
    logger.info("\n2. Convirtiendo campos numéricos...")
    numeric_fields = {
        'hcpn_score_experian_puntaje': 'experian_score',
        'hcpn_ingreso': 'income',
        'hcpn_cuota_total': 'total_monthly_payment',
        'hcpn_creditos_principal_credito_vigentes': 'active_credits',
        'hcpn_creditos_principal_creditos_cerrados': 'closed_credits',
        'hcpn_creditos_principal_creditos_actuales_negativos': 'credits_in_default',
        'hcpn_creditos_principal_hist_neg_ult_12_meses': 'negative_history_12m'
    }

    for old_col, new_col in numeric_fields.items():
        if old_col in df.columns:
            df[new_col] = pd.to_numeric(df[old_col], errors='coerce')

    # Extraer información de comportamiento
    logger.info("\n3. Procesando comportamiento de pago...")
    if 'hcpn_comportamiento' in df.columns:
        df['comportamiento'] = df['hcpn_comportamiento']
        # Contar pagos al día (C) vs morosos (números 1-5)
        df['pct_current_payments'] = df['comportamiento'].apply(
            lambda x: (str(x).count('C') / len(str(x)) * 100) if pd.notna(x) and len(str(x)) > 0 else None
        )

    # Seleccionar columnas finales
    columns_to_keep = {
        '_ID': 'hcpn_id',
        'cedula': 'cedula',
        'hc_id_client': 'client_id',
        'hc_type': 'hcpn_type',
        'experian_score': 'experian_score',
        'income': 'declared_income',
        'total_monthly_payment': 'total_monthly_payment',
        'active_credits': 'active_credits',
        'closed_credits': 'closed_credits',
        'credits_in_default': 'credits_in_default',
        'negative_history_12m': 'negative_history_12m',
        'comportamiento': 'payment_behavior',
        'pct_current_payments': 'pct_current_payments',
        'hcpn_score_decision': 'score_decision',
        'hcpn_url': 'hcpn_url'
    }

    rename_dict = {k: v for k, v in columns_to_keep.items() if k in df.columns}
    df_clean = df[list(rename_dict.keys())].rename(columns=rename_dict)

    # Filtrar válidos (con cédula y score)
    df_clean = df_clean[df_clean['cedula'].notna()]
    df_clean = df_clean[df_clean['experian_score'].notna()]

    # Remover duplicados (quedarnos con el más reciente)
    duplicated = df_clean['cedula'].duplicated().sum()
    if duplicated > 0:
        logger.warning(f"  ⚠️  Encontrados {duplicated} HCPNs duplicados por cédula")
        df_clean = df_clean.drop_duplicates(subset=['cedula'], keep='last')
        logger.info(f"  ✓ Removidos duplicados, quedando con el más reciente")

    logger.info(f"\n✓ Limpieza completada: {len(df_clean):,} registros")
    logger.info(f"  Removidos: {original_count - len(df_clean):,}")
    logger.info(f"  Score promedio: {df_clean['experian_score'].mean():.1f}")

    return df_clean

def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("LIMPIEZA DE DATOS BNPL + HCPN")
    logger.info("="*80)

    # Crear directorio de salida
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Limpiar cada tabla
    clientes_clean = clean_clientes()
    pagos_clean = clean_pagos()
    prestamos_clean = clean_solicitudes_prestamo()
    cupo_clean = clean_solicitudes_cupo()
    hcpn_clean = clean_hcpn()

    # Guardar datos limpios
    logger.info("\n" + "="*80)
    logger.info("GUARDANDO DATOS LIMPIOS")
    logger.info("="*80)

    clientes_clean.to_csv(CLIENTES_CLEAN, index=False)
    logger.info(f"✓ {CLIENTES_CLEAN.name}: {len(clientes_clean):,} registros")

    pagos_clean.to_csv(PAGOS_CLEAN, index=False)
    logger.info(f"✓ {PAGOS_CLEAN.name}: {len(pagos_clean):,} registros")

    prestamos_clean.to_csv(SOLICITUDES_PRESTAMO_CLEAN, index=False)
    logger.info(f"✓ {SOLICITUDES_PRESTAMO_CLEAN.name}: {len(prestamos_clean):,} registros")

    cupo_clean.to_csv(SOLICITUDES_CUPO_CLEAN, index=False)
    logger.info(f"✓ {SOLICITUDES_CUPO_CLEAN.name}: {len(cupo_clean):,} registros")

    hcpn_clean.to_csv(HCPN_CLEAN, index=False)
    logger.info(f"✓ {HCPN_CLEAN.name}: {len(hcpn_clean):,} registros")

    # Resumen de validación
    logger.info("\n" + "="*80)
    logger.info("VALIDACIÓN DE MERGE")
    logger.info("="*80)

    cedulas_clientes = set(clientes_clean['cedula'].dropna())
    cedulas_pagos = set(pagos_clean['cedula'].dropna())
    cedulas_prestamos = set(prestamos_clean['cedula'].dropna())
    cedulas_cupo = set(cupo_clean['cedula'].dropna())
    cedulas_hcpn = set(hcpn_clean['cedula'].dropna())

    logger.info(f"\nCédulas únicas por tabla:")
    logger.info(f"  Clientes:    {len(cedulas_clientes):,}")
    logger.info(f"  Pagos:       {len(cedulas_pagos):,}")
    logger.info(f"  Préstamos:   {len(cedulas_prestamos):,}")
    logger.info(f"  Cupo:        {len(cedulas_cupo):,}")
    logger.info(f"  HCPN:        {len(cedulas_hcpn):,}")

    logger.info(f"\nOverlap con clientes:")
    logger.info(f"  Pagos:       {len(cedulas_clientes & cedulas_pagos):,} ({len(cedulas_clientes & cedulas_pagos)/len(cedulas_clientes)*100:.1f}%)")
    logger.info(f"  Préstamos:   {len(cedulas_clientes & cedulas_prestamos):,} ({len(cedulas_clientes & cedulas_prestamos)/len(cedulas_clientes)*100:.1f}%)")
    logger.info(f"  Cupo:        {len(cedulas_clientes & cedulas_cupo):,} ({len(cedulas_clientes & cedulas_cupo)/len(cedulas_clientes)*100:.1f}%)")
    logger.info(f"  HCPN:        {len(cedulas_clientes & cedulas_hcpn):,} ({len(cedulas_clientes & cedulas_hcpn)/len(cedulas_clientes)*100:.1f}%)")

    logger.info("\n" + "="*80)
    logger.info("✓ LIMPIEZA COMPLETADA")
    logger.info("="*80)
    logger.info(f"\nArchivos guardados en: {PROCESSED_DIR.absolute()}")
    logger.info("\nPróximo paso: Ejecutar scripts/02_merge_all_data.py")

if __name__ == '__main__':
    main()
