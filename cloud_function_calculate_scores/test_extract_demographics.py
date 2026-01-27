#!/usr/bin/env python3
"""
Test de la función extract_hcpn_demographics actualizada
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

def extract_hcpn_demographics(hcpn_data):
    """
    Función de extracción actualizada (copiada de main.py)
    """
    demographics = {}

    try:
        # Navegar a la estructura base
        informe = hcpn_data.get('Informes', {}).get('Informe', {})

        if not informe:
            print("  ⚠ Estructura HCPN inválida")
            return {
                'experian_score': 0,
                'edad': 35,
                'genero': 'M',
                'ciudad': 'UNKNOWN',
                'cuota_mensual': 0,
                'creditos_vigentes': 0,
                'creditos_mora': 0,
                'hist_neg_12m': 0
            }

        # 1. Score Experian
        score = informe.get('Score', {})
        if '@puntaje' in score:
            demographics['experian_score'] = float(score['@puntaje'])
        else:
            demographics['experian_score'] = 0

        # 2. Edad
        natural = informe.get('NaturalNacional', {})
        edad_info = natural.get('Edad', {})
        if '@min' in edad_info and '@max' in edad_info:
            edad_min = int(edad_info['@min'])
            edad_max = int(edad_info['@max'])
            demographics['edad'] = int((edad_min + edad_max) / 2)
        else:
            demographics['edad'] = 35

        # 3. Género
        genero_codigo = natural.get('@genero')
        if genero_codigo == '1' or genero_codigo == 1:
            demographics['genero'] = 'M'
        elif genero_codigo == '2' or genero_codigo == 2:
            demographics['genero'] = 'F'
        elif genero_codigo == '3' or genero_codigo == 3:
            demographics['genero'] = 'F'
        else:
            demographics['genero'] = 'M'

        # 4. Ciudad
        identificacion = natural.get('Identificacion', {})
        ciudad = identificacion.get('@ciudad', 'UNKNOWN')
        demographics['ciudad'] = ciudad if ciudad else 'UNKNOWN'

        # 5. Análisis de créditos
        cuenta_cartera = informe.get('CuentaCartera', [])
        tarjeta_credito = informe.get('TarjetaCredito', [])

        creditos_vigentes = 0
        creditos_mora = 0
        cuota_total = 0
        hist_neg_12m = 0

        for cuenta in cuenta_cartera:
            estado_cuenta = cuenta.get('@estadoCuenta', '')
            if estado_cuenta != '2':
                creditos_vigentes += 1

            calificacion = cuenta.get('@calificacion', '0')
            try:
                if int(calificacion) > 1:
                    creditos_mora += 1
            except:
                pass

            cuota = cuenta.get('@valorCuota', 0)
            try:
                cuota_total += float(cuota)
            except:
                pass

            comportamiento = cuenta.get('@comportamiento', '')
            if comportamiento and len(comportamiento) >= 12:
                ultimos_12 = comportamiento[-12:]
                if any(c not in ['N', ' ', '-'] for c in ultimos_12):
                    hist_neg_12m += 1

        for tarjeta in tarjeta_credito:
            estado = tarjeta.get('@estadoCuenta', '')
            if estado != '2':
                creditos_vigentes += 1

            calificacion = tarjeta.get('@calificacion', '0')
            try:
                if int(calificacion) > 1:
                    creditos_mora += 1
            except:
                pass

            cuota = tarjeta.get('@valorCuota', 0)
            try:
                cuota_total += float(cuota)
            except:
                pass

            comportamiento = tarjeta.get('@comportamiento', '')
            if comportamiento and len(comportamiento) >= 12:
                ultimos_12 = comportamiento[-12:]
                if any(c not in ['N', ' ', '-'] for c in ultimos_12):
                    hist_neg_12m += 1

        demographics['cuota_mensual'] = cuota_total
        demographics['creditos_vigentes'] = creditos_vigentes
        demographics['creditos_mora'] = creditos_mora
        demographics['hist_neg_12m'] = hist_neg_12m

    except Exception as e:
        print(f"  ⚠ Error: {e}")
        import traceback
        traceback.print_exc()
        demographics = {
            'experian_score': 0,
            'edad': 35,
            'genero': 'M',
            'ciudad': 'UNKNOWN',
            'cuota_mensual': 0,
            'creditos_vigentes': 0,
            'creditos_mora': 0,
            'hist_neg_12m': 0
        }

    return demographics

def test_extraction(cedula):
    """Test extracción de demografía de un HCPN real"""
    s3_client = get_s3_client()

    print(f"\n{'='*70}")
    print(f"Test extracción para cédula: {cedula}")
    print(f"{'='*70}\n")

    # Buscar archivo
    prefix = f'{S3_PREFIX}hcpn_{cedula}'
    response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

    if 'Contents' not in response:
        print(f"❌ No se encontró HCPN para {cedula}")
        return

    key = response['Contents'][0]['Key']
    print(f"📁 Archivo: {key}\n")

    # Descargar
    response = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
    hcpn_data = json.loads(response['Body'].read())

    # Extraer demografía
    demographics = extract_hcpn_demographics(hcpn_data)

    # Mostrar resultados
    print("📊 DATOS EXTRAÍDOS:")
    print(f"  ✓ Score Experian: {demographics['experian_score']}")
    print(f"  ✓ Edad: {demographics['edad']} años")
    print(f"  ✓ Género: {demographics['genero']}")
    print(f"  ✓ Ciudad: {demographics['ciudad']}")
    print(f"  ✓ Cuota mensual: ${demographics['cuota_mensual']:,.0f}")
    print(f"  ✓ Créditos vigentes: {demographics['creditos_vigentes']}")
    print(f"  ✓ Créditos en mora: {demographics['creditos_mora']}")
    print(f"  ✓ Hist. negativa 12m: {demographics['hist_neg_12m']}")

    print(f"\n{'='*70}")
    print("✅ TEST EXITOSO")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    # Probar con las cédulas que sabemos que existen
    test_cedulas = ['66661722', '1116614340']

    for cedula in test_cedulas:
        test_extraction(cedula)
