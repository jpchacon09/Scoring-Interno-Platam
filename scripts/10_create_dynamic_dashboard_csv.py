#!/usr/bin/env python3
"""
Crea CSV dinámico enriquecido para análisis de dashboard

Este CSV permite iterar sobre variables para ver cómo varían los scores.
Perfecto para análisis en Excel, Google Sheets, Power BI, Tableau, etc.

Incluye:
- Todos los scores (PLATAM, HCPN, Híbrido)
- Componentes individuales detallados
- Variables de input que afectan el scoring
- Segmentaciones múltiples para análisis
- Métricas calculadas para insights

Usage:
    python scripts/10_create_dynamic_dashboard_csv.py
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
HYBRID_FILE = PROCESSED_DIR / 'hybrid_scores.csv'
OUTPUT_FILE = BASE_DIR / 'DASHBOARD_SCORING_DINAMICO.csv'

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

def categorize_dpd(dpd):
    """Categoriza días de mora"""
    if pd.isna(dpd):
        return 'Sin Datos'
    elif dpd == 0:
        return '0 - Al Día'
    elif dpd <= 15:
        return '1-15 días'
    elif dpd <= 30:
        return '16-30 días'
    elif dpd <= 60:
        return '31-60 días'
    elif dpd <= 90:
        return '61-90 días'
    else:
        return '90+ días (Severo)'

def categorize_payment_count(count):
    """Categoriza cantidad de pagos"""
    if pd.isna(count) or count == 0:
        return '0 - Sin Pagos'
    elif count <= 3:
        return '1-3 pagos'
    elif count <= 10:
        return '4-10 pagos'
    elif count <= 20:
        return '11-20 pagos'
    else:
        return '20+ pagos'

def categorize_utilization(pct):
    """Categoriza porcentaje de utilización"""
    if pd.isna(pct):
        return 'Sin Datos'
    elif pct == 0:
        return '0% - Sin Uso'
    elif pct <= 25:
        return '1-25% - Bajo'
    elif pct <= 50:
        return '26-50% - Moderado'
    elif pct <= 75:
        return '51-75% - Alto'
    else:
        return '76-100% - Muy Alto'

def categorize_income(income):
    """Categoriza ingreso declarado"""
    if pd.isna(income) or income == 0:
        return 'Sin Datos'
    elif income < 500000:
        return '< $500K'
    elif income < 1000000:
        return '$500K - $1M'
    elif income < 2000000:
        return '$1M - $2M'
    elif income < 3000000:
        return '$2M - $3M'
    else:
        return '$3M+'

def create_dynamic_dashboard_csv():
    """Crea CSV enriquecido para dashboard dinámico"""

    logger.info("="*80)
    logger.info("CREANDO CSV DINÁMICO PARA DASHBOARD")
    logger.info("="*80)

    # Cargar datos híbridos
    logger.info(f"\n1. Cargando datos híbridos...")
    df = pd.read_csv(HYBRID_FILE)
    logger.info(f"   ✓ Cargados {len(df):,} clientes")

    # Crear DataFrame para dashboard
    logger.info(f"\n2. Preparando datos para dashboard...")
    dashboard = pd.DataFrame()

    # ========================================================================
    # SECCIÓN 1: IDENTIFICACIÓN DEL CLIENTE
    # ========================================================================
    logger.info("   • Sección: Identificación del Cliente")
    dashboard['cliente_id'] = df['cedula']
    dashboard['nombre'] = df['client_name'] if 'client_name' in df.columns else 'N/A'
    dashboard['email'] = df['email'] if 'email' in df.columns else 'N/A'
    dashboard['estado'] = df['estado'] if 'estado' in df.columns else 'Activo'

    # ========================================================================
    # SECCIÓN 2: SCORES PRINCIPALES
    # ========================================================================
    logger.info("   • Sección: Scores Principales")
    dashboard['score_platam_v2'] = df['platam_score'].round(0)
    dashboard['score_hcpn_normalizado'] = df['experian_score_normalized'].round(0)
    dashboard['score_hibrido'] = df['hybrid_score'].round(0)

    # Ratings
    dashboard['rating_platam'] = df['platam_rating']
    dashboard['rating_hcpn'] = df['experian_score_normalized'].apply(get_credit_rating)
    dashboard['rating_hibrido'] = df['hybrid_rating']

    # ========================================================================
    # SECCIÓN 3: COMPONENTES DEL SCORE PLATAM V2.0
    # ========================================================================
    logger.info("   • Sección: Componentes PLATAM V2.0")

    # Componentes absolutos (puntos)
    dashboard['comp1_payment_performance_pts'] = df['score_payment_performance'].round(0)
    dashboard['comp2_payment_plan_pts'] = df['score_payment_plan'].round(0)
    dashboard['comp3_deterioration_velocity_pts'] = df['score_deterioration'].round(0)

    # Componentes porcentuales (% del máximo)
    dashboard['comp1_payment_performance_pct'] = (df['score_payment_performance'] / 600 * 100).round(1)
    dashboard['comp2_payment_plan_pct'] = (df['score_payment_plan'] / 150 * 100).round(1)
    dashboard['comp3_deterioration_velocity_pct'] = (df['score_deterioration'] / 250 * 100).round(1)

    # ========================================================================
    # SECCIÓN 4: INFORMACIÓN DEL SCORING HÍBRIDO
    # ========================================================================
    logger.info("   • Sección: Información Híbrido")
    dashboard['hibrido_peso_platam'] = (df['peso_platam_usado'] * 100).round(1)
    dashboard['hibrido_peso_hcpn'] = (df['peso_hcpn_usado'] * 100).round(1)
    dashboard['hibrido_estrategia'] = df['estrategia_hibrido']
    dashboard['hibrido_categoria_madurez'] = df['categoria_madurez']

    # ========================================================================
    # SECCIÓN 5: VARIABLES DE COMPORTAMIENTO DE PAGO
    # ========================================================================
    logger.info("   • Sección: Variables de Pago")

    # Métricas de pago
    dashboard['pagos_total'] = df['payment_id_count'].fillna(0).astype(int)
    dashboard['pagos_categoria'] = df['payment_id_count'].apply(categorize_payment_count)

    dashboard['dpd_promedio'] = df['days_past_due_mean'].round(1)
    dashboard['dpd_categoria'] = df['days_past_due_mean'].apply(categorize_dpd)

    dashboard['dpd_max'] = df['days_past_due_max'].round(1) if 'days_past_due_max' in df.columns else 0
    dashboard['pct_early'] = df['pct_early'].round(1) if 'pct_early' in df.columns else 0
    dashboard['pct_late'] = df['pct_late'].round(1) if 'pct_late' in df.columns else 0

    # Calcular % pagos a tiempo (100 - %late)
    dashboard['pct_pagos_a_tiempo'] = (100 - df['pct_late']).round(1) if 'pct_late' in df.columns else 100
    dashboard['dias_desde_ultimo_pago'] = df['days_since_last_payment'].fillna(0).astype(int)

    # Tiempo como cliente
    dashboard['meses_como_cliente'] = df['months_as_client'].fillna(0).astype(int)

    # Categorización de madurez manual
    def cat_meses(m):
        if m < 3:
            return '< 3 meses (Muy Nuevo)'
        elif m < 6:
            return '3-6 meses (Nuevo)'
        elif m < 12:
            return '6-12 meses (Intermedio)'
        elif m < 24:
            return '12-24 meses (Establecido)'
        else:
            return '24+ meses (Maduro)'

    dashboard['meses_categoria'] = df['months_as_client'].apply(cat_meses)

    # ========================================================================
    # SECCIÓN 6: INFORMACIÓN FINANCIERA
    # ========================================================================
    logger.info("   • Sección: Información Financiera")

    # Cupos
    dashboard['cupo_total'] = df['cupo_total'].fillna(0).round(0).astype(int)
    dashboard['cupo_disponible'] = 0  # No disponible en datos
    dashboard['cupo_utilizado'] = (df['cupo_total'] * df['pct_utilization'] / 100).fillna(0).round(0).astype(int)

    # Utilización
    dashboard['utilizacion_pct'] = df['pct_utilization'].round(1)
    dashboard['utilizacion_categoria'] = df['pct_utilization'].apply(categorize_utilization)

    # ========================================================================
    # SECCIÓN 7: DATOS HCPN (EXPERIAN)
    # ========================================================================
    logger.info("   • Sección: Datos HCPN")

    dashboard['hcpn_score_original'] = df['experian_score'].fillna(0).round(0)
    dashboard['hcpn_score_normalizado'] = df['experian_score_normalized'].fillna(0).round(0)
    dashboard['tiene_hcpn'] = df['experian_score'].notna()

    # ========================================================================
    # SECCIÓN 8: COMPARACIONES Y DIFERENCIAS
    # ========================================================================
    logger.info("   • Sección: Comparaciones")

    # Diferencias absolutas
    dashboard['diff_hibrido_vs_platam'] = (df['hybrid_score'] - df['platam_score']).round(0)
    dashboard['diff_hibrido_vs_hcpn'] = (df['hybrid_score'] - df['experian_score_normalized']).round(0)
    dashboard['diff_platam_vs_hcpn'] = (df['platam_score'] - df['experian_score_normalized']).round(0)

    # Diferencias porcentuales
    dashboard['diff_hibrido_vs_platam_pct'] = (
        (df['hybrid_score'] - df['platam_score']) / df['platam_score'] * 100
    ).round(1)

    # Categorización de diferencias
    def cat_diff(diff):
        if pd.isna(diff):
            return 'Sin Comparación'
        elif diff < -100:
            return 'Mucho Menor (<-100)'
        elif diff < -50:
            return 'Menor (-100 a -50)'
        elif diff < -10:
            return 'Ligeramente Menor (-50 a -10)'
        elif diff <= 10:
            return 'Similar (±10)'
        elif diff <= 50:
            return 'Ligeramente Mayor (10 a 50)'
        elif diff <= 100:
            return 'Mayor (50 a 100)'
        else:
            return 'Mucho Mayor (>100)'

    dashboard['diff_hibrido_vs_platam_categoria'] = dashboard['diff_hibrido_vs_platam'].apply(cat_diff)

    # ========================================================================
    # SECCIÓN 9: SEGMENTACIONES PARA ANÁLISIS
    # ========================================================================
    logger.info("   • Sección: Segmentaciones")

    # Segmentación por score híbrido
    def segment_score(score):
        if pd.isna(score):
            return 'Sin Score'
        elif score >= 800:
            return 'Excelente (800+)'
        elif score >= 700:
            return 'Muy Bueno (700-799)'
        elif score >= 600:
            return 'Bueno (600-699)'
        elif score >= 500:
            return 'Regular (500-599)'
        else:
            return 'Malo (<500)'

    dashboard['segmento_score_hibrido'] = df['hybrid_score'].apply(segment_score)
    dashboard['segmento_score_platam'] = df['platam_score'].apply(segment_score)

    # Segmentación por riesgo
    def risk_segment(rating):
        if rating in ['A+', 'A', 'A-']:
            return 'Bajo Riesgo'
        elif rating in ['B+', 'B', 'B-']:
            return 'Riesgo Moderado'
        elif rating in ['C+', 'C', 'C-']:
            return 'Riesgo Medio-Alto'
        else:
            return 'Alto Riesgo'

    dashboard['segmento_riesgo_hibrido'] = df['hybrid_rating'].apply(risk_segment)

    # Segmentación por comportamiento
    def behavior_segment(pct_late, dpd_mean):
        if pd.isna(pct_late) or pd.isna(dpd_mean):
            return 'Sin Datos'
        pct_on_time = 100 - pct_late
        if pct_on_time >= 90 and dpd_mean <= 5:
            return 'Excelente Pagador'
        elif pct_on_time >= 75 and dpd_mean <= 15:
            return 'Buen Pagador'
        elif pct_on_time >= 50 and dpd_mean <= 30:
            return 'Pagador Regular'
        else:
            return 'Pagador Irregular'

    dashboard['segmento_comportamiento'] = df.apply(
        lambda row: behavior_segment(row['pct_late'] if 'pct_late' in df.columns else np.nan, row['days_past_due_mean']),
        axis=1
    )

    # ========================================================================
    # SECCIÓN 10: FLAGS Y INDICADORES
    # ========================================================================
    logger.info("   • Sección: Flags e Indicadores")

    # Flags binarios
    dashboard['tiene_historial_pagos'] = df['has_payment_history'].fillna(False)

    # Flags de alerta
    dashboard['flag_alta_utilizacion'] = df['pct_utilization'] > 80
    dashboard['flag_mora_actual'] = df['days_past_due_mean'] > 0
    dashboard['flag_mora_severa'] = df['days_past_due_max'] > 60
    dashboard['flag_sin_pagos_recientes'] = df['days_since_last_payment'] > 90
    dashboard['flag_pago_irregular'] = df['pct_late'] > 25

    # Indicador de cambio de rating
    dashboard['cambio_rating_hibrido_vs_platam'] = np.where(
        df['hybrid_rating'] != df['platam_rating'],
        'Cambió',
        'Sin Cambio'
    )

    # ========================================================================
    # SECCIÓN 11: MÉTRICAS CALCULADAS
    # ========================================================================
    logger.info("   • Sección: Métricas Calculadas")

    # Score normalizado 0-100
    dashboard['score_hibrido_normalizado_0_100'] = (df['hybrid_score'] / 10).round(1)

    # Probabilidad de default estimada (simplificada)
    # Fórmula: PD = 1 / (1 + exp((score - 500) / 100))
    dashboard['prob_default_estimada_pct'] = (
        1 / (1 + np.exp((df['hybrid_score'] - 500) / 100)) * 100
    ).round(2)

    # Índice de calidad de pago (combina DPD y % late)
    pct_on_time = 100 - df['pct_late']
    dashboard['indice_calidad_pago'] = np.where(
        pct_on_time.notna() & df['days_past_due_mean'].notna(),
        (pct_on_time - df['days_past_due_mean']).round(1),
        np.nan
    )

    # Plan de pago activo
    dashboard['tiene_plan_pago_activo'] = df['status_plan'].notna() if 'status_plan' in df.columns else False
    dashboard['perfil_riesgo_plan'] = df['risk_profile'] if 'risk_profile' in df.columns else 'N/A'

    # ========================================================================
    # SECCIÓN 12: METADATA
    # ========================================================================
    logger.info("   • Sección: Metadata")

    dashboard['fecha_calculo'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    dashboard['version_scoring'] = 'V2.0 + Híbrido'

    # Ordenar por score híbrido descendente
    dashboard = dashboard.sort_values('score_hibrido', ascending=False)

    # Estadísticas
    logger.info("\n" + "="*80)
    logger.info("ESTADÍSTICAS DEL CSV DINÁMICO")
    logger.info("="*80)

    logger.info(f"\n📊 Resumen:")
    logger.info(f"   Total clientes: {len(dashboard):,}")
    logger.info(f"   Total columnas: {len(dashboard.columns)}")
    logger.info(f"   Con HCPN: {dashboard['tiene_hcpn'].sum():,} ({dashboard['tiene_hcpn'].sum()/len(dashboard)*100:.1f}%)")
    logger.info(f"   Con historial pagos: {dashboard['tiene_historial_pagos'].sum():,} ({dashboard['tiene_historial_pagos'].sum()/len(dashboard)*100:.1f}%)")

    logger.info(f"\n📈 Distribución por Segmento de Score:")
    for seg, count in dashboard['segmento_score_hibrido'].value_counts().items():
        pct = count / len(dashboard) * 100
        logger.info(f"   {seg}: {count:,} ({pct:.1f}%)")

    logger.info(f"\n⚠️  Flags de Alerta:")
    logger.info(f"   Alta utilización (>80%): {dashboard['flag_alta_utilizacion'].sum():,}")
    logger.info(f"   Mora actual: {dashboard['flag_mora_actual'].sum():,}")
    logger.info(f"   Mora severa (>60d): {dashboard['flag_mora_severa'].sum():,}")
    logger.info(f"   Sin pagos recientes (>90d): {dashboard['flag_sin_pagos_recientes'].sum():,}")
    logger.info(f"   Pago irregular (>25% late): {dashboard['flag_pago_irregular'].sum():,}")

    # Guardar CSV
    logger.info("\n" + "="*80)
    logger.info("GUARDANDO CSV")
    logger.info("="*80)

    dashboard.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    logger.info(f"\n✓ CSV guardado exitosamente:")
    logger.info(f"  {OUTPUT_FILE.absolute()}")
    logger.info(f"  Tamaño: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")
    logger.info(f"  Registros: {len(dashboard):,}")
    logger.info(f"  Columnas: {len(dashboard.columns)}")

    logger.info("\n" + "="*80)
    logger.info("SECCIONES DEL CSV")
    logger.info("="*80)
    logger.info("\n1. IDENTIFICACIÓN DEL CLIENTE (4 columnas)")
    logger.info("   • cliente_id, nombre, email, estado")

    logger.info("\n2. SCORES PRINCIPALES (6 columnas)")
    logger.info("   • score_platam_v2, score_hcpn_normalizado, score_hibrido")
    logger.info("   • rating_platam, rating_hcpn, rating_hibrido")

    logger.info("\n3. COMPONENTES PLATAM V2.0 (6 columnas)")
    logger.info("   • Puntos: comp1_payment_performance_pts, comp2_payment_plan_pts, comp3_deterioration_velocity_pts")
    logger.info("   • Porcentajes: comp1/2/3_*_pct")

    logger.info("\n4. INFORMACIÓN HÍBRIDO (4 columnas)")
    logger.info("   • hibrido_peso_platam, hibrido_peso_hcpn")
    logger.info("   • hibrido_estrategia, hibrido_categoria_madurez")

    logger.info("\n5. VARIABLES DE PAGO (9 columnas)")
    logger.info("   • pagos_total, dpd_promedio, pct_pagos_a_tiempo")
    logger.info("   • meses_como_cliente, dias_desde_ultimo_pago")
    logger.info("   • Categorizaciones para análisis")

    logger.info("\n6. INFORMACIÓN FINANCIERA (5 columnas)")
    logger.info("   • cupo_total, cupo_disponible, cupo_utilizado")
    logger.info("   • utilizacion_pct, utilizacion_categoria")

    logger.info("\n7. DATOS HCPN (7 columnas)")
    logger.info("   • hcpn_ingreso_declarado, hcpn_cuota_mensual")
    logger.info("   • hcpn_creditos_activos, hcpn_creditos_en_mora")
    logger.info("   • hcpn_ratio_cuota_ingreso")

    logger.info("\n8. COMPARACIONES (5 columnas)")
    logger.info("   • diff_hibrido_vs_platam, diff_hibrido_vs_hcpn")
    logger.info("   • Diferencias en pts y %")

    logger.info("\n9. SEGMENTACIONES (4 columnas)")
    logger.info("   • segmento_score_hibrido, segmento_riesgo_hibrido")
    logger.info("   • segmento_comportamiento")

    logger.info("\n10. FLAGS E INDICADORES (7 columnas)")
    logger.info("   • tiene_historial_pagos, tiene_plan_pago_activo")
    logger.info("   • 5 flags de alerta (alta_utilizacion, mora, etc.)")

    logger.info("\n11. MÉTRICAS CALCULADAS (5 columnas)")
    logger.info("   • prob_default_estimada_pct")
    logger.info("   • indice_calidad_pago")
    logger.info("   • perfil_riesgo_plan")

    logger.info("\n" + "="*80)
    logger.info("USO RECOMENDADO")
    logger.info("="*80)
    logger.info("\n✅ En Excel/Google Sheets:")
    logger.info("   1. Crear tabla dinámica para análisis interactivo")
    logger.info("   2. Filtrar por categorías y segmentos")
    logger.info("   3. Crear gráficos dinámicos")
    logger.info("   4. Analizar correlaciones entre variables")

    logger.info("\n✅ Variables clave para iterar:")
    logger.info("   • meses_categoria → Ver cómo varía score por madurez")
    logger.info("   • pagos_categoria → Impacto de cantidad de pagos")
    logger.info("   • dpd_categoria → Efecto de mora en score")
    logger.info("   • utilizacion_categoria → Relación utilización-score")
    logger.info("   • hcpn_ingreso_categoria → Score por nivel de ingreso")

    logger.info("\n" + "="*80)
    logger.info("✓ CSV DINÁMICO CREADO EXITOSAMENTE")
    logger.info("="*80)

    return dashboard

if __name__ == '__main__':
    create_dynamic_dashboard_csv()
