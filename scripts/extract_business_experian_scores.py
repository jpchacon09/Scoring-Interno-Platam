#!/usr/bin/env python3
"""
Extracción Automática de Scores Experian desde PDFs Empresariales

Este script:
1. Lee todos los PDFs de empresas en la carpeta especificada
2. Extrae el NIT y el Score (0-5) de cada PDF
3. Genera un CSV con los resultados
4. Normaliza el score a escala 0-1000

Estructura del PDF DataCrédito:
- Página 1: NIT en el encabezado
- Página 4: Sección "SCORES" con columna "Puntaje" (0-5)

Usage:
    python scripts/extract_business_experian_scores.py
"""

import pdfplumber
import pandas as pd
import re
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PDFS_DIR = Path("/Users/jpchacon/Desktop/PJ Experian")
OUTPUT_CSV = BASE_DIR / "scores_empresas_experian.csv"
OUTPUT_NORMALIZED_CSV = BASE_DIR / "scores_empresas_experian_normalized.csv"


def extract_nit_from_text(text):
    """
    Extrae NIT del texto del PDF

    Busca patrones como:
    - "NIT: 901973300"
    - "NIT 901973300"
    - "Documento 00901973300"
    """
    # Pattern 1: "NIT: 123456789"
    match = re.search(r'NIT:?\s*(\d{9,10})', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: "Documento 00901973300"
    match = re.search(r'Documento\s+0*(\d{9,10})', text, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def extract_score_from_text(text):
    """
    Extrae Score de la sección SCORES del PDF

    Busca el patrón:
    SCORES
    Tipo de Score Evaluación Puntaje Códigos/Razones
    OtorgA 2 2 00099Riesgo Bajo...

    Retorna el valor de la columna "Puntaje"
    """
    # Look for SCORES section
    if 'SCORES' not in text:
        return None

    # Extract text after SCORES keyword
    scores_section = text.split('SCORES', 1)[1]

    # Look for patterns like "OtorgA 2 2" or "OtorgA 1 1"
    # The format is: Tipo Evaluación Puntaje
    match = re.search(r'OtorgA\s+(\d)\s+(\d)', scores_section)
    if match:
        # Return the second number (Puntaje)
        return int(match.group(2))

    # Alternative pattern: Look for "Puntaje" column header
    lines = scores_section.split('\n')
    for i, line in enumerate(lines):
        if 'Puntaje' in line:
            # Next line should have the score
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # Extract single digit (0-5)
                match = re.search(r'(\d)\s+\d{5}', next_line)
                if match:
                    return int(match.group(1))

    return None


def extract_nit_from_filename(filename):
    """
    Extrae NIT del nombre del archivo

    Formato esperado: "PJ-901973300.pdf"
    """
    match = re.search(r'PJ-(\d{9,10})', filename)
    if match:
        return match.group(1)
    return None


def process_pdf(pdf_path):
    """
    Procesa un PDF y extrae NIT y Score

    Returns:
        tuple: (nit, score, status, error_msg)
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # First, try to extract NIT from filename
            nit = extract_nit_from_filename(pdf_path.name)

            # Extract NIT from first page (backup)
            if not nit and len(pdf.pages) > 0:
                first_page_text = pdf.pages[0].extract_text()
                nit = extract_nit_from_text(first_page_text)

            # Extract score from all pages (usually page 4)
            score = None
            for page in pdf.pages:
                page_text = page.extract_text()
                score = extract_score_from_text(page_text)
                if score is not None:
                    break

            if nit and score is not None:
                return (nit, score, 'success', None)
            elif nit:
                return (nit, None, 'score_not_found', 'Score no encontrado en PDF')
            else:
                return (None, score, 'nit_not_found', 'NIT no encontrado')

    except Exception as e:
        return (None, None, 'error', str(e))


def normalize_score(score):
    """
    Normaliza score empresarial Experian (0-5) a escala 0-1000

    Escala inversa: 1=mejor, 5=peor

    Args:
        score: Score Experian (0-5)

    Returns:
        Score normalizado (0-1000)
    """
    if pd.isna(score) or score == 0:
        # Sin información = base conservadora
        return 500

    # Mapeo inverso: 1 → 1000, 5 → 0
    score_map = {
        1: 1000,  # Excelente
        2: 750,   # Bueno
        3: 500,   # Regular
        4: 250,   # Malo
        5: 0      # Muy malo
    }

    return score_map.get(int(score), 500)


def get_rating(score_normalized):
    """Obtiene rating basado en score normalizado"""
    if score_normalized >= 900:
        return 'A+'
    elif score_normalized >= 800:
        return 'A'
    elif score_normalized >= 700:
        return 'B+'
    elif score_normalized >= 600:
        return 'B'
    elif score_normalized >= 500:
        return 'C+'
    elif score_normalized >= 400:
        return 'C'
    else:
        return 'D'


def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("EXTRACCIÓN DE SCORES EXPERIAN EMPRESARIALES DESDE PDFs")
    logger.info("="*80)

    # Check if directory exists
    if not PDFS_DIR.exists():
        logger.error(f"\n❌ Directorio no encontrado: {PDFS_DIR}")
        logger.error("Por favor verifica la ruta de los PDFs")
        return

    # Get all PDF files
    pdf_files = list(PDFS_DIR.glob("*.pdf"))
    logger.info(f"\n📊 Total PDFs encontrados: {len(pdf_files)}")

    if len(pdf_files) == 0:
        logger.error("\n❌ No se encontraron PDFs en el directorio")
        return

    # Process all PDFs
    logger.info("\n🔍 Procesando PDFs...")
    logger.info("-"*80)

    results = []
    success_count = 0
    error_count = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        if i % 20 == 0:
            logger.info(f"  Procesados {i}/{len(pdf_files)}...")

        nit, score, status, error_msg = process_pdf(pdf_path)

        results.append({
            'filename': pdf_path.name,
            'nit': nit,
            'score_experian': score,
            'status': status,
            'error_msg': error_msg
        })

        if status == 'success':
            success_count += 1
        else:
            error_count += 1

    # Create DataFrame
    df = pd.DataFrame(results)

    # Filter successful extractions
    df_success = df[df['status'] == 'success'].copy()

    # Summary
    logger.info("\n" + "="*80)
    logger.info("RESUMEN DE EXTRACCIÓN")
    logger.info("="*80)
    logger.info(f"\n✅ Exitosos: {success_count}/{len(pdf_files)} ({success_count/len(pdf_files)*100:.1f}%)")
    logger.info(f"❌ Errores: {error_count}/{len(pdf_files)} ({error_count/len(pdf_files)*100:.1f}%)")

    if error_count > 0:
        logger.info("\n⚠️  Tipos de errores:")
        error_summary = df[df['status'] != 'success']['status'].value_counts()
        for error_type, count in error_summary.items():
            logger.info(f"   • {error_type}: {count}")

    # Score distribution
    if len(df_success) > 0:
        logger.info("\n📊 Distribución de Scores (0-5):")
        score_dist = df_success['score_experian'].value_counts().sort_index()
        for score, count in score_dist.items():
            pct = count / len(df_success) * 100
            logger.info(f"   Score {int(score)}: {count:3d} empresas ({pct:5.1f}%)")

        logger.info(f"\n📈 Estadísticas:")
        logger.info(f"   • Score promedio: {df_success['score_experian'].mean():.2f}")
        logger.info(f"   • Score mínimo: {df_success['score_experian'].min():.0f}")
        logger.info(f"   • Score máximo: {df_success['score_experian'].max():.0f}")

    # Save raw scores
    output_df = df_success[['nit', 'score_experian']].copy()
    output_df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"\n✅ CSV guardado: {OUTPUT_CSV.name}")
    logger.info(f"   • {len(output_df)} empresas con scores")

    # Normalize scores
    logger.info("\n" + "="*80)
    logger.info("NORMALIZACIÓN DE SCORES (0-5 → 0-1000)")
    logger.info("="*80)

    output_df['score_normalized'] = output_df['score_experian'].apply(normalize_score)
    output_df['rating'] = output_df['score_normalized'].apply(get_rating)

    # Show normalization table
    logger.info("\n📋 Tabla de Conversión:")
    logger.info("─"*70)
    logger.info(f"{'Score Experian':^15} {'Score Normalizado':^20} {'Rating':^10} {'Empresas':^10}")
    logger.info("─"*70)

    for score in sorted(output_df['score_experian'].unique()):
        subset = output_df[output_df['score_experian'] == score]
        norm_score = subset['score_normalized'].iloc[0]
        rating = subset['rating'].iloc[0]
        count = len(subset)
        logger.info(f"{int(score):^15} {int(norm_score):^20} {rating:^10} {count:^10}")

    logger.info("─"*70)

    # Save normalized scores
    output_df.to_csv(OUTPUT_NORMALIZED_CSV, index=False, encoding='utf-8-sig')
    logger.info(f"\n✅ CSV normalizado guardado: {OUTPUT_NORMALIZED_CSV.name}")
    logger.info(f"   • Columnas: NIT, score_experian, score_normalized, rating")

    # Show sample
    logger.info("\n📋 Muestra de resultados (primeras 10 empresas):")
    logger.info(output_df.head(10).to_string(index=False))

    logger.info("\n" + "="*80)
    logger.info("✅ EXTRACCIÓN COMPLETADA")
    logger.info("="*80)
    logger.info(f"\nArchivos generados:")
    logger.info(f"  1. {OUTPUT_CSV} - Scores originales (0-5)")
    logger.info(f"  2. {OUTPUT_NORMALIZED_CSV} - Scores normalizados (0-1000)")

    logger.info("\n💡 Próximos pasos:")
    logger.info("  1. Revisar scores_empresas_experian_normalized.csv")
    logger.info("  2. Ejecutar: python scripts/integrate_business_experian_scores.py")
    logger.info("  3. Recalcular scores híbridos")


if __name__ == '__main__':
    main()
