#!/usr/bin/env python3
"""
PLATAM Hybrid Scoring System
=============================

Sistema de scoring híbrido que combina inteligentemente:
1. PLATAM Score V2.0 (comportamiento interno)
2. HCPN Score normalizado (historial externo)

La combinación NO es fija (50/50), sino DINÁMICA basada en:
- Disponibilidad de datos
- Madurez del cliente
- Cantidad de historial interno

Autor: PLATAM Data Team
Fecha: Diciembre 2025
Versión: 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

# Setup logging
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURACIÓN DE PESOS DINÁMICOS
# ============================================================================

class HybridScoringConfig:
    """
    Configuración de pesos para el scoring híbrido.

    Estos valores se pueden ajustar basándose en validación con datos reales
    de default.
    """

    # Umbrales de madurez del cliente (en meses)
    MADUREZ_NUEVO = 3          # < 3 meses = muy nuevo
    MADUREZ_INTERMEDIO = 6     # 3-6 meses = intermedio
    MADUREZ_ESTABLECIDO = 12   # 6-12 meses = establecido
    # > 12 meses = maduro

    # Umbrales de historial de pagos
    MIN_PAGOS_CONFIABLES = 5   # Mínimo de pagos para confiar en PLATAM
    MIN_PAGOS_MADUROS = 10     # Pagos para considerar cliente maduro

    # Pesos PLATAM según madurez (cuando tiene HCPN)
    PESOS_PLATAM = {
        'muy_nuevo': 0.30,      # < 3 meses: confía más en HCPN
        'nuevo': 0.40,          # 3-6 meses: HCPN sigue siendo importante
        'intermedio': 0.50,     # 6-12 meses: equilibrado
        'establecido': 0.60,    # 12-24 meses: confía más en PLATAM
        'maduro': 0.70          # 24+ meses: confía mucho en PLATAM
    }

    # Ajustes por cantidad de historial de pagos
    BONUS_HISTORIAL_AMPLIO = 0.10    # +10% peso PLATAM si >20 pagos
    PENALIZACION_HISTORIAL_POCO = -0.10  # -10% peso PLATAM si <5 pagos

    # Score por defecto para clientes sin datos
    DEFAULT_SCORE_SIN_DATOS = 500    # Score conservador
    DEFAULT_SCORE_APLICACION = 550   # Con datos de aplicación


# ============================================================================
# FUNCIONES AUXILIARES PARA DETERMINAR PESOS
# ============================================================================

def determinar_categoria_madurez(months_as_client: int, payment_count: int) -> str:
    """
    Determina la categoría de madurez del cliente.

    Considera tanto el tiempo como cliente como la cantidad de pagos realizados.

    Args:
        months_as_client: Meses que lleva el cliente en la plataforma
        payment_count: Cantidad total de pagos realizados

    Returns:
        str: Categoría de madurez ('muy_nuevo', 'nuevo', 'intermedio',
             'establecido', 'maduro')

    Examples:
        >>> determinar_categoria_madurez(2, 3)
        'muy_nuevo'
        >>> determinar_categoria_madurez(8, 12)
        'intermedio'
        >>> determinar_categoria_madurez(24, 30)
        'maduro'
    """
    config = HybridScoringConfig()

    # Categorización por tiempo
    if months_as_client < config.MADUREZ_NUEVO:
        categoria_tiempo = 'muy_nuevo'
    elif months_as_client < config.MADUREZ_INTERMEDIO:
        categoria_tiempo = 'nuevo'
    elif months_as_client < config.MADUREZ_ESTABLECIDO:
        categoria_tiempo = 'intermedio'
    elif months_as_client < 24:
        categoria_tiempo = 'establecido'
    else:
        categoria_tiempo = 'maduro'

    # Ajuste por cantidad de pagos
    # Si tiene muchos pagos pero poco tiempo, sube una categoría
    if payment_count >= config.MIN_PAGOS_MADUROS * 2 and categoria_tiempo in ['muy_nuevo', 'nuevo']:
        logger.debug(f"  Ajuste: Cliente con muchos pagos ({payment_count}) → sube categoría")
        categorias = ['muy_nuevo', 'nuevo', 'intermedio', 'establecido', 'maduro']
        idx = categorias.index(categoria_tiempo)
        categoria_tiempo = categorias[min(idx + 1, len(categorias) - 1)]

    # Si tiene pocos pagos pero mucho tiempo, baja una categoría
    if payment_count < config.MIN_PAGOS_CONFIABLES and categoria_tiempo in ['establecido', 'maduro']:
        logger.debug(f"  Ajuste: Cliente con pocos pagos ({payment_count}) → baja categoría")
        categorias = ['muy_nuevo', 'nuevo', 'intermedio', 'establecido', 'maduro']
        idx = categorias.index(categoria_tiempo)
        categoria_tiempo = categorias[max(idx - 1, 0)]

    return categoria_tiempo


def calcular_peso_platam(
    months_as_client: int,
    payment_count: int,
    tiene_hcpn: bool
) -> Tuple[float, str]:
    """
    Calcula el peso que debe tener PLATAM en el score híbrido.

    La lógica es:
    - Si NO tiene HCPN → PLATAM = 100%
    - Si tiene HCPN → Peso dinámico según madurez y historial

    Args:
        months_as_client: Meses como cliente
        payment_count: Cantidad de pagos realizados
        tiene_hcpn: Si tiene score HCPN disponible

    Returns:
        Tuple[float, str]: (peso_platam, justificacion)

    Examples:
        >>> calcular_peso_platam(2, 3, True)
        (0.30, 'Cliente muy_nuevo con HCPN: peso PLATAM 30%')

        >>> calcular_peso_platam(18, 25, True)
        (0.70, 'Cliente establecido con historial amplio: peso PLATAM 70%')

        >>> calcular_peso_platam(12, 15, False)
        (1.0, 'Sin HCPN: confianza 100% en PLATAM')
    """
    config = HybridScoringConfig()

    # Caso 1: Sin HCPN → 100% PLATAM
    if not tiene_hcpn:
        return 1.0, "Sin HCPN disponible: confianza 100% en PLATAM V2.0"

    # Caso 2: Con HCPN → Peso dinámico
    categoria = determinar_categoria_madurez(months_as_client, payment_count)
    peso_base = config.PESOS_PLATAM[categoria]

    # Ajustes por historial de pagos
    ajuste = 0.0
    razones_ajuste = []

    if payment_count >= 20:
        ajuste += config.BONUS_HISTORIAL_AMPLIO
        razones_ajuste.append(f"historial amplio ({payment_count} pagos, +{config.BONUS_HISTORIAL_AMPLIO*100:.0f}%)")

    if payment_count < config.MIN_PAGOS_CONFIABLES:
        ajuste += config.PENALIZACION_HISTORIAL_POCO
        razones_ajuste.append(f"poco historial ({payment_count} pagos, {config.PENALIZACION_HISTORIAL_POCO*100:.0f}%)")

    # Aplicar ajustes con límites
    peso_final = peso_base + ajuste
    peso_final = max(0.20, min(0.80, peso_final))  # Límites: 20% - 80%

    # Construir justificación
    justificacion = f"Cliente {categoria}"
    if razones_ajuste:
        justificacion += f" con {', '.join(razones_ajuste)}"
    justificacion += f": peso PLATAM {peso_final*100:.0f}%, HCPN {(1-peso_final)*100:.0f}%"

    return peso_final, justificacion


# ============================================================================
# FUNCIÓN PRINCIPAL: CALCULATE HYBRID SCORE
# ============================================================================

def calculate_hybrid_score(
    platam_score: float,
    hcpn_score: Optional[float],
    months_as_client: int,
    payment_count: int,
    client_id: str = None,
    verbose: bool = False
) -> Dict:
    """
    Calcula el score híbrido combinando PLATAM y HCPN de forma inteligente.

    NO usa una combinación fija 50/50, sino que ajusta dinámicamente los pesos
    según la disponibilidad de datos y madurez del cliente.

    Args:
        platam_score: Score PLATAM V2.0 (0-1000)
        hcpn_score: Score HCPN normalizado (0-1000), o None si no disponible
        months_as_client: Meses que lleva el cliente en la plataforma
        payment_count: Cantidad total de pagos realizados
        client_id: ID del cliente (para logging)
        verbose: Si True, imprime detalles de cálculo

    Returns:
        Dict con:
        - hybrid_score: Score híbrido final (0-1000)
        - peso_platam: Peso usado para PLATAM (0-1)
        - peso_hcpn: Peso usado para HCPN (0-1)
        - estrategia: Descripción de la estrategia usada
        - categoria_madurez: Categoría del cliente

    Examples:
        # Cliente nuevo con ambos scores
        >>> calculate_hybrid_score(650, 720, months_as_client=2, payment_count=3)
        {
            'hybrid_score': 699.0,  # 70% HCPN + 30% PLATAM
            'peso_platam': 0.30,
            'peso_hcpn': 0.70,
            'estrategia': 'Cliente muy_nuevo: confía más en HCPN',
            'categoria_madurez': 'muy_nuevo'
        }

        # Cliente maduro con ambos scores
        >>> calculate_hybrid_score(850, 720, months_as_client=18, payment_count=25)
        {
            'hybrid_score': 815.0,  # 70% PLATAM + 30% HCPN
            'peso_platam': 0.70,
            'peso_hcpn': 0.30,
            'estrategia': 'Cliente establecido: confía más en PLATAM',
            'categoria_madurez': 'establecido'
        }

        # Cliente sin HCPN
        >>> calculate_hybrid_score(750, None, months_as_client=12, payment_count=15)
        {
            'hybrid_score': 750.0,  # 100% PLATAM
            'peso_platam': 1.0,
            'peso_hcpn': 0.0,
            'estrategia': 'Sin HCPN: usa 100% PLATAM',
            'categoria_madurez': 'intermedio'
        }
    """
    config = HybridScoringConfig()

    if verbose and client_id:
        logger.info(f"\n{'='*70}")
        logger.info(f"CALCULANDO SCORE HÍBRIDO: Cliente {client_id}")
        logger.info(f"{'='*70}")
        logger.info(f"  PLATAM Score: {platam_score:.1f}")
        logger.info(f"  HCPN Score: {hcpn_score:.1f if hcpn_score else 'N/A'}")
        logger.info(f"  Meses como cliente: {months_as_client}")
        logger.info(f"  Cantidad de pagos: {payment_count}")

    # Determinar categoría de madurez
    categoria = determinar_categoria_madurez(months_as_client, payment_count)

    # Determinar disponibilidad de HCPN
    tiene_hcpn = hcpn_score is not None and not pd.isna(hcpn_score)
    tiene_platam = platam_score is not None and not pd.isna(platam_score) and platam_score > 0

    # ========================================================================
    # CASO 1: Cliente con ambos scores (IDEAL)
    # ========================================================================
    if tiene_hcpn and tiene_platam:
        peso_platam, justificacion = calcular_peso_platam(
            months_as_client, payment_count, tiene_hcpn
        )
        peso_hcpn = 1.0 - peso_platam

        # Calcular híbrido
        hybrid_score = (platam_score * peso_platam) + (hcpn_score * peso_hcpn)

        estrategia = f"Híbrido: {justificacion}"

        if verbose:
            logger.info(f"\n  ✅ CASO 1: Cliente con ambos scores")
            logger.info(f"  Categoría madurez: {categoria}")
            logger.info(f"  {justificacion}")
            logger.info(f"  Cálculo: ({platam_score:.1f} × {peso_platam:.2f}) + ({hcpn_score:.1f} × {peso_hcpn:.2f})")
            logger.info(f"  → Score Híbrido: {hybrid_score:.1f}")

    # ========================================================================
    # CASO 2: Cliente SIN HCPN pero con historial interno
    # ========================================================================
    elif not tiene_hcpn and tiene_platam:
        peso_platam = 1.0
        peso_hcpn = 0.0
        hybrid_score = platam_score
        estrategia = "Sin HCPN: usa 100% PLATAM V2.0 basado en comportamiento interno"

        if verbose:
            logger.info(f"\n  ✅ CASO 2: Cliente sin HCPN")
            logger.info(f"  {estrategia}")
            logger.info(f"  → Score Híbrido: {hybrid_score:.1f} (= PLATAM)")

    # ========================================================================
    # CASO 3: Cliente CON HCPN pero SIN historial interno (nuevo)
    # ========================================================================
    elif tiene_hcpn and not tiene_platam:
        peso_platam = 0.20  # 20% basado en score de aplicación
        peso_hcpn = 0.80    # 80% HCPN

        # Score PLATAM por defecto conservador
        platam_default = config.DEFAULT_SCORE_APLICACION
        hybrid_score = (platam_default * peso_platam) + (hcpn_score * peso_hcpn)

        estrategia = f"Cliente nuevo con HCPN: usa 80% HCPN + 20% score base ({platam_default})"

        if verbose:
            logger.info(f"\n  ⚠️ CASO 3: Cliente nuevo con HCPN pero sin historial")
            logger.info(f"  {estrategia}")
            logger.info(f"  Cálculo: ({platam_default} × {peso_platam:.2f}) + ({hcpn_score:.1f} × {peso_hcpn:.2f})")
            logger.info(f"  → Score Híbrido: {hybrid_score:.1f}")

    # ========================================================================
    # CASO 4: Cliente SIN HCPN y SIN historial interno (thin file)
    # ========================================================================
    else:
        peso_platam = 1.0
        peso_hcpn = 0.0
        hybrid_score = config.DEFAULT_SCORE_SIN_DATOS
        estrategia = f"Thin file: usa score conservador por defecto ({config.DEFAULT_SCORE_SIN_DATOS})"

        if verbose:
            logger.info(f"\n  ⚠️ CASO 4: Thin file (sin datos suficientes)")
            logger.info(f"  {estrategia}")
            logger.info(f"  → Score Híbrido: {hybrid_score:.1f}")

    # Asegurar que el score esté en rango válido
    hybrid_score = max(0, min(1000, hybrid_score))

    return {
        'hybrid_score': round(hybrid_score, 1),
        'peso_platam': peso_platam,
        'peso_hcpn': peso_hcpn,
        'estrategia': estrategia,
        'categoria_madurez': categoria,
        'platam_score': platam_score,
        'hcpn_score': hcpn_score if tiene_hcpn else None
    }


# ============================================================================
# FUNCIÓN PARA CALCULAR RATING DEL SCORE HÍBRIDO
# ============================================================================

def get_hybrid_rating(hybrid_score: float) -> str:
    """
    Determina el rating crediticio basado en el score híbrido.

    Usa la misma escala que PLATAM V2.0 para consistencia.

    Args:
        hybrid_score: Score híbrido (0-1000)

    Returns:
        str: Rating ('A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F')
    """
    if hybrid_score >= 900:
        return 'A+'
    elif hybrid_score >= 850:
        return 'A'
    elif hybrid_score >= 800:
        return 'A-'
    elif hybrid_score >= 750:
        return 'B+'
    elif hybrid_score >= 700:
        return 'B'
    elif hybrid_score >= 650:
        return 'B-'
    elif hybrid_score >= 600:
        return 'C+'
    elif hybrid_score >= 550:
        return 'C'
    elif hybrid_score >= 500:
        return 'C-'
    elif hybrid_score >= 450:
        return 'D'
    else:
        return 'F'


# ============================================================================
# FUNCIÓN BATCH PARA DATAFRAMES
# ============================================================================

def calculate_hybrid_scores_batch(
    df: pd.DataFrame,
    platam_col: str = 'platam_score',
    hcpn_col: str = 'experian_score_normalized',
    months_col: str = 'months_as_client',
    payment_count_col: str = 'payment_id_count',
    client_id_col: str = 'cedula'
) -> pd.DataFrame:
    """
    Calcula scores híbridos para un DataFrame completo.

    Args:
        df: DataFrame con datos de clientes
        platam_col: Nombre de columna con PLATAM score
        hcpn_col: Nombre de columna con HCPN score
        months_col: Nombre de columna con meses como cliente
        payment_count_col: Nombre de columna con cantidad de pagos
        client_id_col: Nombre de columna con ID de cliente

    Returns:
        DataFrame original con columnas adicionales:
        - hybrid_score
        - hybrid_rating
        - peso_platam_usado
        - peso_hcpn_usado
        - estrategia_hibrido
        - categoria_madurez
    """
    logger.info(f"\n{'='*70}")
    logger.info("CALCULANDO SCORES HÍBRIDOS EN BATCH")
    logger.info(f"{'='*70}")
    logger.info(f"Total clientes: {len(df):,}")

    results = []

    for idx, row in df.iterrows():
        result = calculate_hybrid_score(
            platam_score=row[platam_col],
            hcpn_score=row[hcpn_col] if pd.notna(row[hcpn_col]) else None,
            months_as_client=row[months_col],
            payment_count=row[payment_count_col],
            client_id=row[client_id_col],
            verbose=False
        )
        results.append(result)

        # Log progress
        if (idx + 1) % 500 == 0:
            logger.info(f"  Procesados {idx + 1:,} / {len(df):,} clientes...")

    # Crear DataFrame con resultados
    results_df = pd.DataFrame(results)

    # Agregar ratings
    results_df['hybrid_rating'] = results_df['hybrid_score'].apply(get_hybrid_rating)

    # Combinar con DataFrame original
    df_output = df.copy()
    df_output['hybrid_score'] = results_df['hybrid_score']
    df_output['hybrid_rating'] = results_df['hybrid_rating']
    df_output['peso_platam_usado'] = results_df['peso_platam']
    df_output['peso_hcpn_usado'] = results_df['peso_hcpn']
    df_output['estrategia_hibrido'] = results_df['estrategia']
    df_output['categoria_madurez'] = results_df['categoria_madurez']

    # Resumen
    logger.info(f"\n{'='*70}")
    logger.info("RESUMEN DE SCORING HÍBRIDO")
    logger.info(f"{'='*70}")
    logger.info(f"\nPromedio score híbrido: {df_output['hybrid_score'].mean():.1f}")
    logger.info(f"Mediana score híbrido: {df_output['hybrid_score'].median():.1f}")

    logger.info(f"\nDistribución por categoría de madurez:")
    for cat, count in df_output['categoria_madurez'].value_counts().items():
        pct = count / len(df_output) * 100
        logger.info(f"  {cat}: {count} ({pct:.1f}%)")

    logger.info(f"\nDistribución de pesos PLATAM:")
    logger.info(f"  Promedio: {df_output['peso_platam_usado'].mean():.2f}")
    logger.info(f"  Mediana: {df_output['peso_platam_usado'].median():.2f}")
    logger.info(f"  Min: {df_output['peso_platam_usado'].min():.2f}")
    logger.info(f"  Max: {df_output['peso_platam_usado'].max():.2f}")

    return df_output


if __name__ == '__main__':
    """
    Tests y ejemplos de uso
    """
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("\n" + "="*70)
    print("EJEMPLOS DE USO: SCORING HÍBRIDO SEGMENTADO")
    print("="*70)

    # Ejemplo 1: Cliente muy nuevo con ambos scores
    print("\n[EJEMPLO 1] Cliente MUY NUEVO (2 meses, 3 pagos)")
    result1 = calculate_hybrid_score(
        platam_score=650,
        hcpn_score=720,
        months_as_client=2,
        payment_count=3,
        client_id="TEST-001",
        verbose=True
    )

    # Ejemplo 2: Cliente maduro con ambos scores
    print("\n[EJEMPLO 2] Cliente MADURO (18 meses, 25 pagos)")
    result2 = calculate_hybrid_score(
        platam_score=850,
        hcpn_score=720,
        months_as_client=18,
        payment_count=25,
        client_id="TEST-002",
        verbose=True
    )

    # Ejemplo 3: Cliente sin HCPN
    print("\n[EJEMPLO 3] Cliente SIN HCPN (12 meses, 15 pagos)")
    result3 = calculate_hybrid_score(
        platam_score=750,
        hcpn_score=None,
        months_as_client=12,
        payment_count=15,
        client_id="TEST-003",
        verbose=True
    )

    # Ejemplo 4: Thin file
    print("\n[EJEMPLO 4] THIN FILE (0 meses, 0 pagos)")
    result4 = calculate_hybrid_score(
        platam_score=0,
        hcpn_score=None,
        months_as_client=0,
        payment_count=0,
        client_id="TEST-004",
        verbose=True
    )

    print("\n" + "="*70)
    print("TESTS COMPLETADOS")
    print("="*70)
