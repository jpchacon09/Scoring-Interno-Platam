#!/usr/bin/env python3
"""
Script para descargar archivos HCPN de S3 basado en tax_id de clientes

Usage:
    python scripts/download_hcpn.py
"""

import os
import sys
import json
import pandas as pd
import boto3
from pathlib import Path
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(env_path)

# Configuration
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
S3_HCPN_BUCKET = os.getenv('S3_HCPN_BUCKET', 'fft-analytics-data-lake')
S3_PREFIX = os.getenv('S3_PREFIX', 'ppay/prod/')
HCPN_DIR = Path(os.getenv('HCPN_DIR', 'data/hcpn'))
CLIENTS_CSV = Path(os.getenv('RAW_DIR', 'data/raw')) / 'clients' / 'clients.csv'

def check_config():
    """Verifica que las credenciales estén configuradas"""
    if not AWS_ACCESS_KEY or not AWS_SECRET_KEY:
        logger.error("❌ AWS credentials no configuradas")
        logger.error("Por favor edita config/.env con tus credenciales")
        sys.exit(1)

    if not CLIENTS_CSV.exists():
        logger.error(f"❌ Archivo {CLIENTS_CSV} no encontrado")
        logger.error("Primero debes subir clients.csv a data/raw/clients/")
        sys.exit(1)

def get_s3_client():
    """Crea cliente S3 con credenciales"""
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY,
            region_name=AWS_REGION
        )
        # Test connection
        s3_client.list_buckets()
        logger.info("✓ Conexión a AWS S3 exitosa")
        return s3_client
    except Exception as e:
        logger.error(f"❌ Error conectando a AWS S3: {e}")
        sys.exit(1)

def load_clients():
    """Carga lista de clientes desde CSV"""
    try:
        df = pd.read_csv(CLIENTS_CSV)

        # Verificar que tenga columnas necesarias
        required_cols = ['client_id', 'tax_id']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            logger.error(f"❌ Columnas faltantes en clients.csv: {missing_cols}")
            sys.exit(1)

        # Remover duplicados y NaN
        df = df[['client_id', 'tax_id']].drop_duplicates()
        df = df.dropna(subset=['tax_id'])

        logger.info(f"✓ Cargados {len(df)} clientes desde {CLIENTS_CSV}")
        return df

    except Exception as e:
        logger.error(f"❌ Error leyendo {CLIENTS_CSV}: {e}")
        sys.exit(1)

def download_hcpn(s3_client, tax_id, client_id):
    """
    Descarga archivo HCPN de S3

    Intenta múltiples formatos de nombre con el prefix configurado
    """
    possible_keys = [
        f'{S3_PREFIX}hcpn_{tax_id}.json',
        f'{S3_PREFIX}{tax_id}.json',
        f'{S3_PREFIX}HCPN_{tax_id}.json',
        f'hcpn_{tax_id}.json',  # Sin prefix
        f'{tax_id}.json',  # Sin prefix
        f'HCPN_{tax_id}.json',  # Sin prefix
    ]

    for key in possible_keys:
        try:
            # Intentar descargar
            response = s3_client.get_object(Bucket=S3_HCPN_BUCKET, Key=key)
            hcpn_data = response['Body'].read()

            # Guardar localmente
            output_file = HCPN_DIR / f'hcpn_{client_id}.json'
            with open(output_file, 'wb') as f:
                f.write(hcpn_data)

            logger.info(f"  ✓ Descargado: {key} → {output_file.name}")
            return True

        except s3_client.exceptions.NoSuchKey:
            continue
        except Exception as e:
            logger.warning(f"  ⚠ Error descargando {key}: {e}")
            continue

    logger.warning(f"  ⚠ No se encontró HCPN para tax_id={tax_id} (probados: {len(possible_keys)} formatos)")
    return False

def main():
    """Función principal"""
    logger.info("="*60)
    logger.info("PLATAM - Descarga de HCPN desde S3")
    logger.info("="*60)

    # 1. Verificar configuración
    logger.info("\n[1/4] Verificando configuración...")
    check_config()

    # 2. Conectar a S3
    logger.info("\n[2/4] Conectando a AWS S3...")
    s3_client = get_s3_client()

    # 3. Cargar clientes
    logger.info("\n[3/4] Cargando lista de clientes...")
    clients_df = load_clients()

    # 4. Crear directorio de destino
    HCPN_DIR.mkdir(parents=True, exist_ok=True)

    # 5. Descargar HCPN para cada cliente
    logger.info(f"\n[4/4] Descargando HCPNs de S3")
    logger.info(f"  Bucket: {S3_HCPN_BUCKET}")
    logger.info(f"  Prefix: {S3_PREFIX}")
    logger.info("-"*60)

    results = {
        'downloaded': 0,
        'not_found': 0,
        'errors': 0
    }

    for idx, row in clients_df.iterrows():
        client_id = row['client_id']
        tax_id = str(row['tax_id']).strip()

        logger.info(f"[{idx+1}/{len(clients_df)}] {client_id} (tax_id: {tax_id})")

        success = download_hcpn(s3_client, tax_id, client_id)

        if success:
            results['downloaded'] += 1
        else:
            results['not_found'] += 1

    # 6. Resumen
    logger.info("\n" + "="*60)
    logger.info("RESUMEN")
    logger.info("="*60)
    logger.info(f"✓ Descargados:    {results['downloaded']}")
    logger.info(f"⚠ No encontrados: {results['not_found']}")
    logger.info(f"❌ Errores:        {results['errors']}")
    logger.info(f"\nArchivos guardados en: {HCPN_DIR.absolute()}")

    if results['downloaded'] == 0:
        logger.warning("\n⚠ WARNING: No se descargó ningún HCPN")
        logger.warning("Verifica:")
        logger.warning("  1. Que el bucket S3 tenga los archivos correctos")
        logger.warning("  2. Que los tax_id en clients.csv coincidan con los nombres en S3")
        logger.warning("  3. Que tengas permisos de lectura en el bucket")

    logger.info("\n✓ Proceso completado")

if __name__ == '__main__':
    main()
