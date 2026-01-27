#!/usr/bin/env python3
"""
Test de búsqueda de archivos HCPN en S3
"""

import boto3
import os
from dotenv import load_dotenv

# Cargar credenciales del .env
load_dotenv('../config/.env')

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = os.getenv('S3_HCPN_BUCKET', 'fft-analytics-data-lake')
S3_PREFIX = os.getenv('S3_PREFIX', 'ppay/prod/')

def get_s3_client():
    """Crea cliente S3"""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name='us-east-1'
    )

def test_find_hcpn(cedula: str):
    """
    Prueba buscar archivo HCPN para una cédula
    """
    s3_client = get_s3_client()

    print(f"\n{'='*70}")
    print(f"🔍 Buscando HCPN para cédula: {cedula}")
    print(f"{'='*70}\n")

    # Listar archivos que empiecen con hcpn_{cedula}
    prefix_to_search = f'{S3_PREFIX}hcpn_{cedula}'

    print(f"📂 Bucket: {S3_BUCKET}")
    print(f"🔎 Prefix: {prefix_to_search}*")
    print()

    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=prefix_to_search
        )

        if 'Contents' not in response or len(response['Contents']) == 0:
            print(f"⚠️  No se encontraron archivos con prefix: {prefix_to_search}")
            print()

            # Intentar sin el prefix ppay/prod/
            prefix_to_search_root = f'hcpn_{cedula}'
            print(f"🔄 Intentando sin prefix: {prefix_to_search_root}*")

            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix=prefix_to_search_root
            )

            if 'Contents' not in response or len(response['Contents']) == 0:
                print(f"❌ No se encontró ningún archivo HCPN para cédula {cedula}")
                return None

        # Mostrar todos los archivos encontrados
        files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)

        print(f"✅ Encontrados {len(files)} archivo(s):\n")

        for i, file in enumerate(files, 1):
            print(f"  {i}. {file['Key']}")
            print(f"     Tamaño: {file['Size']} bytes")
            print(f"     Modificado: {file['LastModified']}")
            print()

        # Tomar el más reciente
        most_recent = files[0]
        key = most_recent['Key']

        print(f"⭐ Seleccionado (más reciente): {key}")
        print()

        # Descargar el archivo
        print("📥 Descargando archivo...")
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
        hcpn_data = response['Body'].read()

        print(f"✅ Archivo descargado exitosamente")
        print(f"   Tamaño: {len(hcpn_data)} bytes")
        print()

        # Parsear JSON
        import json
        hcpn_json = json.loads(hcpn_data)

        print("📊 Estructura del HCPN:")
        print(f"   Keys en el JSON: {list(hcpn_json.keys())[:10]}")

        # Mostrar score si existe
        if 'score' in hcpn_json:
            if 'puntaje' in hcpn_json['score']:
                print(f"   Score Experian: {hcpn_json['score']['puntaje']}")
        elif 'score_experian' in hcpn_json:
            if 'puntaje' in hcpn_json['score_experian']:
                print(f"   Score Experian: {hcpn_json['score_experian']['puntaje']}")

        # Mostrar edad si existe
        if 'id_data' in hcpn_json and 'edad' in hcpn_json['id_data']:
            print(f"   Edad: {hcpn_json['id_data']['edad']}")
        elif 'edad' in hcpn_json:
            print(f"   Edad: {hcpn_json['edad']}")

        print()
        print("="*70)
        print("✅ TEST EXITOSO")
        print("="*70)

        return hcpn_json

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Probar con varias cédulas
    test_cedulas = [
        '66661722',      # La que mencionó el usuario
        '1116614340',    # La de los ejemplos
        '1192925596',    # Otra de los ejemplos
    ]

    for cedula in test_cedulas:
        result = test_find_hcpn(cedula)
        if result:
            print(f"\n✅ HCPN encontrado para {cedula}")
        else:
            print(f"\n❌ HCPN NO encontrado para {cedula}")
        print("\n" + "="*70 + "\n")
