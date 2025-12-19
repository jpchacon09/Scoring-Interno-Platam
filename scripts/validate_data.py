#!/usr/bin/env python3
"""
Script para validar que los CSVs tengan la estructura correcta

Usage:
    python scripts/validate_data.py
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
RAW_DIR = Path('data/raw')

# Esquemas esperados
SCHEMAS = {
    'clients': {
        'required_columns': ['client_id', 'client_name', 'tax_id', 'months_as_client',
                            'current_credit_limit', 'current_outstanding'],
        'optional_columns': ['registration_date', 'industry', 'account_status'],
        'date_columns': ['registration_date'],
        'numeric_columns': ['months_as_client', 'current_credit_limit', 'current_outstanding'],
    },
    'payments': {
        'required_columns': ['client_id', 'payment_date', 'due_date',
                            'days_past_due', 'payment_amount'],
        'optional_columns': ['payment_id', 'invoice_id', 'payment_method'],
        'date_columns': ['payment_date', 'due_date'],
        'numeric_columns': ['days_past_due', 'payment_amount'],
    },
    'orders': {
        'required_columns': ['client_id', 'order_date', 'order_value'],
        'optional_columns': ['order_id', 'order_status'],
        'date_columns': ['order_date'],
        'numeric_columns': ['order_value'],
    },
    'utilization': {
        'required_columns': ['client_id', 'month', 'avg_outstanding',
                            'credit_limit', 'utilization_pct'],
        'optional_columns': ['id', 'max_outstanding'],
        'date_columns': ['month'],
        'numeric_columns': ['avg_outstanding', 'credit_limit', 'utilization_pct'],
    },
    'payment_plans': {
        'required_columns': ['client_id', 'plan_start_date', 'plan_status'],
        'optional_columns': ['plan_id', 'plan_end_date', 'original_amount', 'completion_date'],
        'date_columns': ['plan_start_date', 'plan_end_date', 'completion_date'],
        'numeric_columns': ['original_amount'],
    }
}

class DataValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.dataframes = {}

    def validate_all(self):
        """Valida todos los CSVs"""
        logger.info("="*60)
        logger.info("PLATAM - Validación de Datos")
        logger.info("="*60)

        # Validar cada tipo de archivo
        for table_name, schema in SCHEMAS.items():
            logger.info(f"\n[{table_name.upper()}]")
            logger.info("-"*60)

            folder = RAW_DIR / table_name
            if not folder.exists():
                self.warnings.append(f"Carpeta {folder} no existe")
                logger.warning(f"⚠ Carpeta no encontrada: {folder}")
                continue

            # Buscar archivos CSV
            csv_files = list(folder.glob('*.csv'))

            if not csv_files:
                if table_name == 'payment_plans':
                    logger.info("  ℹ No hay archivos CSV (opcional)")
                    continue
                else:
                    self.errors.append(f"No se encontraron CSVs en {folder}")
                    logger.error(f"  ❌ No se encontraron archivos CSV")
                    continue

            logger.info(f"  Archivos encontrados: {len(csv_files)}")

            # Leer y concatenar todos los CSVs
            dfs = []
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    dfs.append(df)
                    logger.info(f"    ✓ {csv_file.name}: {len(df)} filas")
                except Exception as e:
                    self.errors.append(f"Error leyendo {csv_file}: {e}")
                    logger.error(f"    ❌ Error: {e}")

            if not dfs:
                continue

            # Concatenar
            df = pd.concat(dfs, ignore_index=True)
            self.dataframes[table_name] = df

            # Validar estructura
            self.validate_structure(table_name, df, schema)

            # Validar datos
            self.validate_data_quality(table_name, df, schema)

        # Validar relaciones entre tablas
        logger.info("\n[RELACIONES ENTRE TABLAS]")
        logger.info("-"*60)
        self.validate_relationships()

        # Reporte final
        self.print_summary()

    def validate_structure(self, table_name, df, schema):
        """Valida estructura de columnas"""
        # Verificar columnas requeridas
        missing_cols = [col for col in schema['required_columns']
                       if col not in df.columns]

        if missing_cols:
            self.errors.append(f"{table_name}: Columnas faltantes: {missing_cols}")
            logger.error(f"  ❌ Columnas faltantes: {missing_cols}")
        else:
            logger.info(f"  ✓ Todas las columnas requeridas presentes")

        # Informar columnas extra (no es error, solo info)
        expected_cols = set(schema['required_columns'] + schema['optional_columns'])
        extra_cols = [col for col in df.columns if col not in expected_cols]

        if extra_cols:
            logger.info(f"  ℹ Columnas adicionales: {extra_cols}")

    def validate_data_quality(self, table_name, df, schema):
        """Valida calidad de los datos"""
        # Verificar valores nulos en columnas requeridas
        for col in schema['required_columns']:
            if col not in df.columns:
                continue

            null_count = df[col].isna().sum()
            if null_count > 0:
                pct = (null_count / len(df)) * 100
                self.warnings.append(
                    f"{table_name}.{col}: {null_count} valores nulos ({pct:.1f}%)"
                )
                logger.warning(f"  ⚠ {col}: {null_count} nulos ({pct:.1f}%)")

        # Validar columnas de fecha
        for col in schema.get('date_columns', []):
            if col not in df.columns or df[col].isna().all():
                continue

            try:
                # Intentar parsear fechas
                df[col] = pd.to_datetime(df[col], errors='coerce')
                invalid_dates = df[col].isna().sum()

                if invalid_dates > 0:
                    self.warnings.append(
                        f"{table_name}.{col}: {invalid_dates} fechas inválidas"
                    )
                    logger.warning(f"  ⚠ {col}: {invalid_dates} fechas inválidas")
                else:
                    logger.info(f"  ✓ {col}: formato de fecha válido")

            except Exception as e:
                self.errors.append(f"{table_name}.{col}: Error parseando fechas: {e}")
                logger.error(f"  ❌ {col}: {e}")

        # Validar columnas numéricas
        for col in schema.get('numeric_columns', []):
            if col not in df.columns or df[col].isna().all():
                continue

            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                invalid_nums = df[col].isna().sum()

                if invalid_nums > 0:
                    self.warnings.append(
                        f"{table_name}.{col}: {invalid_nums} valores no numéricos"
                    )
                    logger.warning(f"  ⚠ {col}: {invalid_nums} no numéricos")

                # Verificar valores negativos donde no deberían
                if col in ['payment_amount', 'order_value', 'credit_limit', 'current_credit_limit']:
                    negative_count = (df[col] < 0).sum()
                    if negative_count > 0:
                        self.warnings.append(
                            f"{table_name}.{col}: {negative_count} valores negativos"
                        )
                        logger.warning(f"  ⚠ {col}: {negative_count} negativos")

            except Exception as e:
                self.errors.append(f"{table_name}.{col}: Error validando numéricos: {e}")

        # Verificar duplicados en client_id para tabla clients
        if table_name == 'clients' and 'client_id' in df.columns:
            duplicates = df['client_id'].duplicated().sum()
            if duplicates > 0:
                self.errors.append(f"clients: {duplicates} client_id duplicados")
                logger.error(f"  ❌ {duplicates} client_id duplicados")
            else:
                logger.info(f"  ✓ No hay client_id duplicados")

    def validate_relationships(self):
        """Valida relaciones entre tablas"""
        if 'clients' not in self.dataframes:
            logger.error("  ❌ No se puede validar relaciones sin tabla clients")
            return

        client_ids = set(self.dataframes['clients']['client_id'].unique())
        logger.info(f"  Clientes en tabla principal: {len(client_ids)}")

        # Validar que todos los client_id en otras tablas existan en clients
        for table_name in ['payments', 'orders', 'utilization', 'payment_plans']:
            if table_name not in self.dataframes:
                continue

            df = self.dataframes[table_name]
            if 'client_id' not in df.columns:
                continue

            table_client_ids = set(df['client_id'].unique())
            orphan_ids = table_client_ids - client_ids

            if orphan_ids:
                self.warnings.append(
                    f"{table_name}: {len(orphan_ids)} client_id no existen en tabla clients"
                )
                logger.warning(
                    f"  ⚠ {table_name}: {len(orphan_ids)} client_id huérfanos"
                )
                if len(orphan_ids) <= 5:
                    logger.warning(f"    IDs: {list(orphan_ids)}")
            else:
                logger.info(f"  ✓ {table_name}: Todos los client_id válidos")

        # Verificar cobertura de datos por cliente
        logger.info("\n  Cobertura de datos por cliente:")
        for table_name in ['payments', 'orders', 'utilization']:
            if table_name not in self.dataframes:
                continue

            df = self.dataframes[table_name]
            table_client_ids = set(df['client_id'].unique())
            coverage = (len(table_client_ids) / len(client_ids)) * 100

            logger.info(f"    {table_name}: {len(table_client_ids)}/{len(client_ids)} clientes ({coverage:.1f}%)")

            if coverage < 50:
                self.warnings.append(
                    f"{table_name}: Solo {coverage:.1f}% de clientes tienen datos"
                )

    def print_summary(self):
        """Imprime resumen de validación"""
        logger.info("\n" + "="*60)
        logger.info("RESUMEN DE VALIDACIÓN")
        logger.info("="*60)

        logger.info(f"\nTablas cargadas: {len(self.dataframes)}")
        for table_name, df in self.dataframes.items():
            logger.info(f"  - {table_name}: {len(df):,} filas")

        if self.errors:
            logger.error(f"\n❌ ERRORES CRÍTICOS: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  - {error}")
        else:
            logger.info("\n✓ No se encontraron errores críticos")

        if self.warnings:
            logger.warning(f"\n⚠ ADVERTENCIAS: {len(self.warnings)}")
            for warning in self.warnings[:10]:  # Mostrar solo primeras 10
                logger.warning(f"  - {warning}")
            if len(self.warnings) > 10:
                logger.warning(f"  ... y {len(self.warnings) - 10} más")
        else:
            logger.info("✓ No se encontraron advertencias")

        # Resultado final
        logger.info("\n" + "="*60)
        if self.errors:
            logger.error("❌ VALIDACIÓN FALLIDA")
            logger.error("Por favor corrige los errores antes de continuar")
            sys.exit(1)
        elif self.warnings:
            logger.warning("⚠ VALIDACIÓN CON ADVERTENCIAS")
            logger.warning("Puedes continuar, pero revisa las advertencias")
        else:
            logger.info("✓ VALIDACIÓN EXITOSA")
            logger.info("Los datos están listos para calcular scoring")

def main():
    validator = DataValidator()
    validator.validate_all()

if __name__ == '__main__':
    main()
