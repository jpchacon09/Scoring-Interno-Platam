#!/usr/bin/env python3
"""
Inspeccionar estructura del HCPN
"""

import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv('../config/.env')

AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
S3_BUCKET = os.getenv('S3_HCPN_BUCKET', 'fft-analytics-data-lake')
S3_PREFIX = os.getenv('S3_PREFIX', 'ppay/prod/')

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        region_name='us-east-1'
    )

def inspect_hcpn(cedula):
    s3_client = get_s3_client()

    # Buscar archivo
    prefix = f'{S3_PREFIX}hcpn_{cedula}'
    response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

    if 'Contents' not in response:
        print(f"No encontrado: {cedula}")
        return

    key = response['Contents'][0]['Key']
    print(f"\n{'='*70}")
    print(f"Archivo: {key}")
    print(f"{'='*70}\n")

    # Descargar
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
    hcpn = json.loads(response['Body'].read())

    # Mostrar estructura completa (más keys)
    def print_structure(obj, indent=0, max_items=15):
        if isinstance(obj, dict):
            items = list(obj.items())
            print("  " * indent + f"(dict con {len(items)} keys)")
            for k, v in items[:max_items]:
                if isinstance(v, (dict, list)):
                    print("  " * indent + f"├─ {k}: ({type(v).__name__})")
                    if isinstance(v, dict):
                        print_structure(v, indent + 1, max_items=10)
                    elif len(v) > 0:
                        print("  " * (indent + 1) + f"[{len(v)} items]")
                        print_structure(v[0], indent + 2, max_items=10)
                else:
                    print("  " * indent + f"├─ {k}: {v}")
            if len(items) > max_items:
                print("  " * indent + f"└─ ... y {len(items) - max_items} keys más")
        elif isinstance(obj, list) and len(obj) > 0:
            print("  " * indent + f"[Lista con {len(obj)} items]")
            print_structure(obj[0], indent + 1, max_items=10)

    print_structure(hcpn)

    # Buscar datos específicos que necesitamos
    print(f"\n{'='*70}")
    print("Buscando datos demográficos...")
    print(f"{'='*70}\n")

    def find_in_dict(d, path=""):
        """Busca keys específicas recursivamente"""
        findings = {}

        if isinstance(d, dict):
            for k, v in d.items():
                current_path = f"{path}.{k}" if path else k

                # Keys que buscamos
                if k in ['score', 'puntaje', 'edad', 'genero', 'ciudad', 'cuota', 'ingreso', 'credito']:
                    findings[current_path] = v

                if isinstance(v, (dict, list)):
                    findings.update(find_in_dict(v, current_path))

        elif isinstance(d, list) and len(d) > 0:
            findings.update(find_in_dict(d[0], path + "[0]"))

        return findings

    findings = find_in_dict(hcpn)

    if findings:
        for path, value in sorted(findings.items())[:30]:  # Primeros 30
            if isinstance(value, (dict, list)):
                print(f"  {path}: ({type(value).__name__}, {len(value)} items)")
            else:
                print(f"  {path}: {value}")
    else:
        print("  ⚠️  No se encontraron las keys buscadas")
        print("  Keys buscadas: score, puntaje, edad, genero, ciudad, cuota, ingreso, credito")

    # Mostrar TODAS las keys en el primer nivel
    print(f"\n{'='*70}")
    print("Todas las keys en niveles superiores:")
    print(f"{'='*70}\n")

    def show_all_keys(obj, path="", level=0, max_level=3):
        """Muestra todas las keys hasta cierto nivel"""
        if level > max_level:
            return

        if isinstance(obj, dict):
            for k in obj.keys():
                current_path = f"{path}.{k}" if path else k
                print("  " * level + f"• {k}")
                if isinstance(obj[k], (dict, list)) and level < max_level:
                    show_all_keys(obj[k], current_path, level + 1, max_level)
        elif isinstance(obj, list) and len(obj) > 0:
            print("  " * level + f"[Lista con {len(obj)} elementos]")
            show_all_keys(obj[0], path + "[0]", level + 1, max_level)

    show_all_keys(hcpn)

inspect_hcpn('66661722')
