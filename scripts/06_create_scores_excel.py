#!/usr/bin/env python3
"""
Crea Excel con comparación de scores y score híbrido

Genera archivo Excel con:
- ID cliente (cédula)
- Score PLATAM interno
- Score HCPN (Experian)
- Desviación entre scores
- Score híbrido (50% HCPN + 50% PLATAM)
- Rating del score híbrido

Usage:
    python scripts/06_create_scores_excel.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
SCORES_FILE = PROCESSED_DIR / 'platam_scores.csv'
OUTPUT_EXCEL = BASE_DIR / 'SCORES_COMPARACION.xlsx'

def get_credit_rating(score):
    """Asigna rating crediticio según score"""
    if pd.isna(score):
        return 'N/A'
    if score >= 900:
        return 'A+'
    elif score >= 850:
        return 'A'
    elif score >= 800:
        return 'A-'
    elif score >= 750:
        return 'B+'
    elif score >= 700:
        return 'B'
    elif score >= 650:
        return 'B-'
    elif score >= 600:
        return 'C+'
    elif score >= 550:
        return 'C'
    elif score >= 500:
        return 'C-'
    elif score >= 450:
        return 'D+'
    elif score >= 400:
        return 'D'
    else:
        return 'F'

def create_scores_excel():
    """Crea archivo Excel con comparación de scores"""

    logger.info("="*80)
    logger.info("CREANDO EXCEL DE COMPARACIÓN DE SCORES")
    logger.info("="*80)

    # Cargar datos
    logger.info(f"\nCargando scores desde: {SCORES_FILE.name}")
    df = pd.read_csv(SCORES_FILE)
    logger.info(f"✓ Cargados {len(df):,} clientes")

    # Crear DataFrame para Excel
    logger.info("\nPreparando datos para Excel...")

    excel_data = pd.DataFrame()

    # 1. ID Cliente (cédula)
    excel_data['ID_Cliente'] = df['cedula']

    # 2. Información básica del cliente
    excel_data['Nombre'] = df['first_name'].fillna('') + ' ' + df['last_name'].fillna('')
    excel_data['Email'] = df['email']
    excel_data['Estado'] = df['estado']

    # 3. Score PLATAM Interno
    excel_data['Score_PLATAM'] = df['platam_score'].round(0)
    excel_data['Rating_PLATAM'] = df['platam_rating']

    # 4. Score HCPN (Experian normalizado a 0-1000)
    excel_data['Score_HCPN_Experian'] = df['experian_score_normalized'].round(0)

    # 5. Score HCPN Original (0-924)
    excel_data['Score_HCPN_Original'] = df['experian_score'].round(0)

    # 6. Desviación (PLATAM - HCPN)
    excel_data['Desviacion_Scores'] = (df['platam_score'] - df['experian_score_normalized']).round(0)

    # 7. Score Híbrido (50% PLATAM + 50% HCPN)
    logger.info("\nCalculando score híbrido (50% PLATAM + 50% HCPN)...")

    # Para clientes sin HCPN, usar 100% PLATAM
    excel_data['Score_Hibrido_50_50'] = np.where(
        df['experian_score_normalized'].notna(),
        (df['platam_score'] * 0.5 + df['experian_score_normalized'] * 0.5).round(0),
        df['platam_score'].round(0)
    )

    # 8. Rating del score híbrido
    excel_data['Rating_Hibrido'] = excel_data['Score_Hibrido_50_50'].apply(get_credit_rating)

    # 9. Componentes del score PLATAM V2.0 (3 componentes)
    excel_data['Payment_Performance_600pts'] = df['score_payment_performance'].round(0)
    excel_data['Payment_Plan_History_150pts'] = df['score_payment_plan'].round(0)
    excel_data['Deterioration_Velocity_250pts'] = df['score_deterioration'].round(0)

    # 10. Información financiera
    excel_data['Cupo_Total'] = df['cupo_total']
    excel_data['Cupo_Disponible'] = df['cupo_disponible']
    excel_data['Pct_Utilizacion'] = df['pct_utilization'].round(1)

    # 11. Datos de HCPN
    excel_data['HCPN_Ingreso_Declarado'] = df['declared_income']
    excel_data['HCPN_Cuota_Total_Mensual'] = df['total_monthly_payment']
    excel_data['HCPN_Creditos_Activos'] = df['active_credits']
    excel_data['HCPN_Creditos_en_Mora'] = df['credits_in_default']

    # 12. Métricas de pagos
    excel_data['Total_Pagos'] = df['payment_id_count']
    excel_data['Promedio_DPD'] = df['days_past_due_mean'].round(1)
    excel_data['Pct_Pagos_a_Tiempo'] = df['pct_on_time'].round(1)
    excel_data['Dias_Desde_Ultimo_Pago'] = df['days_since_last_payment']

    # 13. Flags
    excel_data['Tiene_HCPN'] = df['has_hcpn']
    excel_data['Tiene_Historial_Pagos'] = df['has_payment_history']

    # 14. Categorización de diferencia
    excel_data['Categoria_Diferencia'] = pd.cut(
        excel_data['Desviacion_Scores'].abs(),
        bins=[0, 50, 100, 150, 200, np.inf],
        labels=['Muy Similar (0-50)', 'Similar (50-100)', 'Moderada (100-150)',
                'Alta (150-200)', 'Muy Alta (200+)']
    )

    # 15. Interpretación de desviación
    def interpretar_desviacion(dev):
        if pd.isna(dev):
            return 'Sin HCPN'
        elif dev < -150:
            return 'PLATAM mucho más bajo'
        elif dev < -50:
            return 'PLATAM más bajo'
        elif dev <= 50:
            return 'Similares'
        elif dev <= 150:
            return 'PLATAM más alto'
        else:
            return 'PLATAM mucho más alto'

    excel_data['Interpretacion'] = excel_data['Desviacion_Scores'].apply(interpretar_desviacion)

    # Ordenar por score híbrido descendente
    excel_data = excel_data.sort_values('Score_Hibrido_50_50', ascending=False)

    # Estadísticas
    logger.info("\n" + "="*80)
    logger.info("ESTADÍSTICAS DEL SCORE HÍBRIDO")
    logger.info("="*80)
    logger.info(f"\nPromedio Score Híbrido: {excel_data['Score_Hibrido_50_50'].mean():.1f}")
    logger.info(f"Mediana Score Híbrido: {excel_data['Score_Hibrido_50_50'].median():.1f}")
    logger.info(f"Mínimo: {excel_data['Score_Hibrido_50_50'].min():.1f}")
    logger.info(f"Máximo: {excel_data['Score_Hibrido_50_50'].max():.1f}")

    logger.info("\nDistribución por Rating Híbrido:")
    rating_dist = excel_data['Rating_Hibrido'].value_counts().sort_index()
    for rating, count in rating_dist.items():
        pct = count / len(excel_data) * 100
        logger.info(f"  {rating}: {count:4} ({pct:5.1f}%)")

    # Guardar a Excel
    logger.info("\n" + "="*80)
    logger.info("GUARDANDO EXCEL")
    logger.info("="*80)

    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
        # Hoja 1: Datos completos
        excel_data.to_excel(writer, sheet_name='Scores Completos', index=False)

        # Hoja 2: Resumen por Rating Híbrido
        resumen_rating = excel_data.groupby('Rating_Hibrido').agg({
            'ID_Cliente': 'count',
            'Score_PLATAM': 'mean',
            'Score_HCPN_Experian': 'mean',
            'Score_Hibrido_50_50': 'mean',
            'Desviacion_Scores': 'mean',
            'Cupo_Total': 'mean'
        }).round(1)
        resumen_rating.columns = ['Cantidad', 'PLATAM Promedio', 'HCPN Promedio',
                                   'Híbrido Promedio', 'Desviación Promedio', 'Cupo Promedio']
        resumen_rating = resumen_rating.sort_index()
        resumen_rating.to_excel(writer, sheet_name='Resumen por Rating')

        # Hoja 3: Top 100 mejores scores híbridos
        top_100 = excel_data.head(100)[['ID_Cliente', 'Nombre', 'Score_Hibrido_50_50',
                                         'Rating_Hibrido', 'Score_PLATAM', 'Score_HCPN_Experian',
                                         'Cupo_Total', 'Estado']]
        top_100.to_excel(writer, sheet_name='Top 100 Mejores', index=False)

        # Hoja 4: Clientes con mayor desviación
        mayor_desviacion = excel_data.nlargest(50, 'Desviacion_Scores')[
            ['ID_Cliente', 'Nombre', 'Score_PLATAM', 'Score_HCPN_Experian',
             'Desviacion_Scores', 'Interpretacion', 'Estado']
        ]
        mayor_desviacion.to_excel(writer, sheet_name='PLATAM Mucho Mayor', index=False)

        menor_desviacion = excel_data.nsmallest(50, 'Desviacion_Scores')[
            ['ID_Cliente', 'Nombre', 'Score_PLATAM', 'Score_HCPN_Experian',
             'Desviacion_Scores', 'Interpretacion', 'Estado']
        ]
        menor_desviacion.to_excel(writer, sheet_name='PLATAM Mucho Menor', index=False)

        # Hoja 5: Estadísticas generales
        stats_data = {
            'Métrica': [
                'Total Clientes',
                'Con HCPN',
                'Sin HCPN',
                'Score PLATAM Promedio',
                'Score HCPN Promedio',
                'Score Híbrido Promedio',
                'Desviación Promedio',
                'Correlación PLATAM-HCPN'
            ],
            'Valor': [
                len(excel_data),
                excel_data['Tiene_HCPN'].sum(),
                (~excel_data['Tiene_HCPN']).sum(),
                f"{excel_data['Score_PLATAM'].mean():.1f}",
                f"{excel_data['Score_HCPN_Experian'].mean():.1f}",
                f"{excel_data['Score_Hibrido_50_50'].mean():.1f}",
                f"{excel_data['Desviacion_Scores'].mean():.1f}",
                f"{excel_data['Score_PLATAM'].corr(excel_data['Score_HCPN_Experian']):.3f}"
            ]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Estadísticas', index=False)

    logger.info(f"\n✓ Excel guardado exitosamente:")
    logger.info(f"  {OUTPUT_EXCEL.absolute()}")
    logger.info(f"  Tamaño: {OUTPUT_EXCEL.stat().st_size / 1024 / 1024:.2f} MB")

    logger.info("\n" + "="*80)
    logger.info("HOJAS DEL EXCEL")
    logger.info("="*80)
    logger.info("\n1. 'Scores Completos' - Todos los clientes con todas las columnas")
    logger.info("2. 'Resumen por Rating' - Estadísticas agrupadas por rating híbrido")
    logger.info("3. 'Top 100 Mejores' - Los 100 clientes con mejor score híbrido")
    logger.info("4. 'PLATAM Mucho Mayor' - Top 50 donde PLATAM >> HCPN")
    logger.info("5. 'PLATAM Mucho Menor' - Top 50 donde PLATAM << HCPN")
    logger.info("6. 'Estadísticas' - Resumen general del análisis")

    logger.info("\n" + "="*80)
    logger.info("✓ EXCEL CREADO EXITOSAMENTE")
    logger.info("="*80)

    return excel_data

if __name__ == '__main__':
    create_scores_excel()
