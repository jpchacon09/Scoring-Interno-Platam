#!/usr/bin/env python3
"""
Genera visualizaciones de comparación de scores

Usage:
    python scripts/04_visualize_scores.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
CHARTS_DIR = BASE_DIR / 'charts'
COMPARISON_FILE = PROCESSED_DIR / 'score_comparison.csv'

# Crear directorio de gráficos
CHARTS_DIR.mkdir(exist_ok=True)

# Configurar estilo
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)

def create_score_distribution():
    """Distribución de scores PLATAM vs Experian"""
    df = pd.read_csv(COMPARISON_FILE)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # PLATAM
    axes[0].hist(df['platam_score'], bins=30, color='#3498db', alpha=0.7, edgecolor='black')
    axes[0].axvline(df['platam_score'].mean(), color='red', linestyle='--', linewidth=2, label=f'Promedio: {df["platam_score"].mean():.1f}')
    axes[0].axvline(df['platam_score'].median(), color='green', linestyle='--', linewidth=2, label=f'Mediana: {df["platam_score"].median():.1f}')
    axes[0].set_xlabel('Score', fontsize=12)
    axes[0].set_ylabel('Frecuencia', fontsize=12)
    axes[0].set_title('Distribución PLATAM Score', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Experian
    axes[1].hist(df['experian_score_normalized'], bins=30, color='#e74c3c', alpha=0.7, edgecolor='black')
    axes[1].axvline(df['experian_score_normalized'].mean(), color='red', linestyle='--', linewidth=2, label=f'Promedio: {df["experian_score_normalized"].mean():.1f}')
    axes[1].axvline(df['experian_score_normalized'].median(), color='green', linestyle='--', linewidth=2, label=f'Mediana: {df["experian_score_normalized"].median():.1f}')
    axes[1].set_xlabel('Score (normalizado 0-1000)', fontsize=12)
    axes[1].set_ylabel('Frecuencia', fontsize=12)
    axes[1].set_title('Distribución Experian Score', fontsize=14, fontweight='bold')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'score_distribution.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/score_distribution.png")
    plt.close()

def create_scatter_plot():
    """Scatter plot PLATAM vs Experian"""
    df = pd.read_csv(COMPARISON_FILE)

    plt.figure(figsize=(10, 10))

    # Scatter
    plt.scatter(df['experian_score_normalized'], df['platam_score'],
                alpha=0.5, s=50, c='#3498db', edgecolors='black', linewidth=0.5)

    # Línea de igualdad
    plt.plot([0, 1000], [0, 1000], 'r--', linewidth=2, label='Igualdad (PLATAM = Experian)')

    # Correlación
    corr = df['platam_score'].corr(df['experian_score_normalized'])
    plt.text(50, 950, f'Correlación: {corr:.3f}', fontsize=14,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.xlabel('Experian Score (normalizado 0-1000)', fontsize=12)
    plt.ylabel('PLATAM Score', fontsize=12)
    plt.title('Comparación PLATAM vs Experian Score', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 1000)
    plt.ylim(0, 1000)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'platam_vs_experian_scatter.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/platam_vs_experian_scatter.png")
    plt.close()

def create_difference_distribution():
    """Distribución de diferencias"""
    df = pd.read_csv(COMPARISON_FILE)

    plt.figure(figsize=(12, 6))

    # Histograma de diferencias
    plt.hist(df['score_diff'], bins=50, color='#9b59b6', alpha=0.7, edgecolor='black')
    plt.axvline(0, color='red', linestyle='--', linewidth=2, label='Sin diferencia')
    plt.axvline(df['score_diff'].mean(), color='green', linestyle='--', linewidth=2,
                label=f'Promedio: {df["score_diff"].mean():.1f}')

    plt.xlabel('Diferencia (PLATAM - Experian)', fontsize=12)
    plt.ylabel('Frecuencia', fontsize=12)
    plt.title('Distribución de Diferencias entre Scores', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)

    # Anotaciones
    plt.text(df['score_diff'].min() + 50, plt.ylim()[1] * 0.9,
             f'PLATAM más bajo\n({(df["score_diff"] < 0).sum()} clientes, {(df["score_diff"] < 0).sum()/len(df)*100:.1f}%)',
             fontsize=10, bbox=dict(boxstyle='round', facecolor='#e74c3c', alpha=0.5))

    plt.text(df['score_diff'].max() - 150, plt.ylim()[1] * 0.9,
             f'PLATAM más alto\n({(df["score_diff"] > 0).sum()} clientes, {(df["score_diff"] > 0).sum()/len(df)*100:.1f}%)',
             fontsize=10, bbox=dict(boxstyle='round', facecolor='#2ecc71', alpha=0.5))

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'score_difference_distribution.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/score_difference_distribution.png")
    plt.close()

def create_rating_distribution():
    """Distribución por rating PLATAM"""
    df = pd.read_csv(COMPARISON_FILE)

    rating_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
    rating_counts = df['platam_rating'].value_counts().reindex(rating_order, fill_value=0)

    plt.figure(figsize=(12, 6))
    bars = plt.bar(rating_counts.index, rating_counts.values,
                    color=['#27ae60', '#27ae60', '#27ae60',  # A
                           '#3498db', '#3498db', '#3498db',  # B
                           '#f39c12', '#f39c12', '#f39c12',  # C
                           '#e67e22', '#e74c3c', '#c0392b'],  # D, F
                    edgecolor='black', linewidth=1.5, alpha=0.8)

    # Agregar valores en las barras
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}\n({height/len(df)*100:.1f}%)',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    plt.xlabel('Rating Crediticio', fontsize=12)
    plt.ylabel('Cantidad de Clientes', fontsize=12)
    plt.title('Distribución de Clientes por Rating PLATAM', fontsize=14, fontweight='bold')
    plt.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'rating_distribution.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/rating_distribution.png")
    plt.close()

def create_component_analysis():
    """Análisis de componentes del score V2.0 (3 componentes)"""
    df = pd.read_csv(PROCESSED_DIR / 'platam_scores.csv')

    # Sistema V2.0: 3 componentes
    components = {
        'Payment\nPerformance': ('score_payment_performance', 600),
        'Payment Plan\nHistory': ('score_payment_plan', 150),
        'Deterioration\nVelocity': ('score_deterioration', 250)
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Promedios absolutos
    names = list(components.keys())
    values = [df[col].mean() for col, _ in components.values()]
    maxes = [max_val for _, max_val in components.values()]

    bars1 = axes[0].bar(names, values, color='#3498db', alpha=0.7, edgecolor='black', linewidth=1.5, label='Promedio obtenido')
    axes[0].bar(names, maxes, color='lightgray', alpha=0.3, edgecolor='black', linewidth=1, label='Máximo posible')

    # Agregar valores
    for i, (bar, val, max_val) in enumerate(zip(bars1, values, maxes)):
        axes[0].text(bar.get_x() + bar.get_width()/2., val + 5,
                    f'{val:.1f}\n({val/max_val*100:.1f}%)',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    axes[0].set_ylabel('Puntos', fontsize=12)
    axes[0].set_title('Sistema V2.0: Promedio por Componente (3 componentes)', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, axis='y', alpha=0.3)

    # Porcentajes del máximo
    percentages = [(df[col].mean() / max_val * 100) for col, max_val in components.values()]
    colors = ['#27ae60' if p >= 70 else '#f39c12' if p >= 50 else '#e74c3c' for p in percentages]

    bars2 = axes[1].bar(names, percentages, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    axes[1].axhline(70, color='green', linestyle='--', alpha=0.5, label='Bueno (70%+)')
    axes[1].axhline(50, color='orange', linestyle='--', alpha=0.5, label='Regular (50%+)')

    # Agregar valores
    for bar, pct in zip(bars2, percentages):
        axes[1].text(bar.get_x() + bar.get_width()/2., pct + 1,
                    f'{pct:.1f}%',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    axes[1].set_ylabel('% del Máximo', fontsize=12)
    axes[1].set_title('Sistema V2.0: Desempeño por Componente', fontsize=12, fontweight='bold')
    axes[1].set_ylim(0, 100)
    axes[1].legend()
    axes[1].grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'component_analysis_v2.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/component_analysis_v2.png")
    plt.close()

def main():
    logger.info("="*80)
    logger.info("GENERANDO VISUALIZACIONES DE SCORES")
    logger.info("="*80)

    logger.info("\n1. Distribución de scores...")
    create_score_distribution()

    logger.info("\n2. Scatter plot PLATAM vs Experian...")
    create_scatter_plot()

    logger.info("\n3. Distribución de diferencias...")
    create_difference_distribution()

    logger.info("\n4. Distribución por rating...")
    create_rating_distribution()

    logger.info("\n5. Análisis de componentes...")
    create_component_analysis()

    logger.info("\n" + "="*80)
    logger.info("✓ VISUALIZACIONES COMPLETADAS")
    logger.info("="*80)
    logger.info(f"\nGráficos guardados en: {CHARTS_DIR.absolute()}")

if __name__ == '__main__':
    main()
