#!/usr/bin/env python3
"""
Visualizaciones comparativas: V2.0 vs Híbrido vs HCPN

Genera gráficos comparativos entre:
- Score PLATAM V2.0 (solo interno)
- Score Híbrido (inteligente con pesos dinámicos)
- Score HCPN (Experian normalizado)

Usage:
    python scripts/09_visualize_hybrid_comparison.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
CHARTS_DIR = BASE_DIR / 'charts'
HYBRID_FILE = PROCESSED_DIR / 'hybrid_scores.csv'

# Crear directorio de gráficos
CHARTS_DIR.mkdir(exist_ok=True)

# Configurar estilo
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10

def create_score_comparison_distributions():
    """Comparación de distribuciones de los 3 scores"""
    df = pd.read_csv(HYBRID_FILE)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Histogramas superpuestos
    ax1 = axes[0, 0]
    ax1.hist(df['platam_score'], bins=30, alpha=0.5, color='#3498db', label='PLATAM V2.0', edgecolor='black')
    ax1.hist(df['hybrid_score'], bins=30, alpha=0.5, color='#2ecc71', label='Híbrido', edgecolor='black')
    ax1.hist(df['experian_score_normalized'].dropna(), bins=30, alpha=0.5, color='#e74c3c', label='HCPN', edgecolor='black')

    ax1.axvline(df['platam_score'].mean(), color='#3498db', linestyle='--', linewidth=2)
    ax1.axvline(df['hybrid_score'].mean(), color='#2ecc71', linestyle='--', linewidth=2)
    ax1.axvline(df['experian_score_normalized'].mean(), color='#e74c3c', linestyle='--', linewidth=2)

    ax1.set_xlabel('Score', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Frecuencia', fontsize=12, fontweight='bold')
    ax1.set_title('Distribución de Scores: PLATAM vs Híbrido vs HCPN', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    # 2. Box plots comparativos
    ax2 = axes[0, 1]
    data_boxplot = [
        df['platam_score'],
        df['hybrid_score'],
        df['experian_score_normalized'].dropna()
    ]
    bp = ax2.boxplot(data_boxplot, labels=['PLATAM\nV2.0', 'Híbrido', 'HCPN'],
                      patch_artist=True, showmeans=True)

    colors = ['#3498db', '#2ecc71', '#e74c3c']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax2.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax2.set_title('Comparación de Rangos y Medianas', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    # 3. Promedios por categoría de madurez
    ax3 = axes[1, 0]
    madurez_order = ['muy_nuevo', 'nuevo', 'intermedio', 'establecido', 'maduro']

    promedios = df.groupby('categoria_madurez').agg({
        'platam_score': 'mean',
        'hybrid_score': 'mean',
        'experian_score_normalized': 'mean'
    }).reindex(madurez_order)

    x = np.arange(len(madurez_order))
    width = 0.25

    ax3.bar(x - width, promedios['platam_score'], width, label='PLATAM V2.0', color='#3498db', alpha=0.8)
    ax3.bar(x, promedios['hybrid_score'], width, label='Híbrido', color='#2ecc71', alpha=0.8)
    ax3.bar(x + width, promedios['experian_score_normalized'], width, label='HCPN', color='#e74c3c', alpha=0.8)

    ax3.set_xlabel('Categoría de Madurez', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Score Promedio', fontsize=12, fontweight='bold')
    ax3.set_title('Scores Promedio por Madurez del Cliente', fontsize=14, fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(madurez_order, rotation=45, ha='right')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    # 4. Estadísticas comparativas (tabla)
    ax4 = axes[1, 1]
    ax4.axis('off')

    stats_data = [
        ['Métrica', 'PLATAM V2.0', 'Híbrido', 'HCPN'],
        ['Promedio', f"{df['platam_score'].mean():.1f}",
         f"{df['hybrid_score'].mean():.1f}",
         f"{df['experian_score_normalized'].mean():.1f}"],
        ['Mediana', f"{df['platam_score'].median():.1f}",
         f"{df['hybrid_score'].median():.1f}",
         f"{df['experian_score_normalized'].median():.1f}"],
        ['Desv. Std', f"{df['platam_score'].std():.1f}",
         f"{df['hybrid_score'].std():.1f}",
         f"{df['experian_score_normalized'].std():.1f}"],
        ['Mínimo', f"{df['platam_score'].min():.1f}",
         f"{df['hybrid_score'].min():.1f}",
         f"{df['experian_score_normalized'].min():.1f}"],
        ['Máximo', f"{df['platam_score'].max():.1f}",
         f"{df['hybrid_score'].max():.1f}",
         f"{df['experian_score_normalized'].max():.1f}"]
    ]

    table = ax4.table(cellText=stats_data, cellLoc='center', loc='center',
                      colWidths=[0.3, 0.23, 0.23, 0.23])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)

    # Estilo de la tabla
    for i in range(len(stats_data)):
        for j in range(4):
            cell = table[(i, j)]
            if i == 0:
                cell.set_facecolor('#34495e')
                cell.set_text_props(weight='bold', color='white')
            elif j == 0:
                cell.set_facecolor('#ecf0f1')
                cell.set_text_props(weight='bold')
            else:
                if j == 1:
                    cell.set_facecolor('#e3f2fd')
                elif j == 2:
                    cell.set_facecolor('#e8f5e9')
                else:
                    cell.set_facecolor('#ffebee')

    ax4.set_title('Estadísticas Comparativas', fontsize=14, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'hybrid_01_comparison_distributions.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/hybrid_01_comparison_distributions.png")
    plt.close()


def create_rating_comparison():
    """Comparación de distribución de ratings"""
    df = pd.read_csv(HYBRID_FILE)

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    rating_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
    colors_ratings = ['#27ae60', '#27ae60', '#27ae60',  # A
                      '#3498db', '#3498db', '#3498db',  # B
                      '#f39c12', '#f39c12', '#f39c12',  # C
                      '#e67e22', '#e74c3c', '#c0392b']  # D, F

    # PLATAM V2.0
    platam_ratings = df['platam_rating'].value_counts().reindex(rating_order, fill_value=0)
    axes[0].bar(platam_ratings.index, platam_ratings.values, color=colors_ratings, alpha=0.8, edgecolor='black')
    axes[0].set_title('PLATAM V2.0', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Cantidad de Clientes', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Rating', fontsize=12, fontweight='bold')
    axes[0].tick_params(axis='x', rotation=45)
    axes[0].grid(True, alpha=0.3, axis='y')

    # Híbrido
    hybrid_ratings = df['hybrid_rating'].value_counts().reindex(rating_order, fill_value=0)
    axes[1].bar(hybrid_ratings.index, hybrid_ratings.values, color=colors_ratings, alpha=0.8, edgecolor='black')
    axes[1].set_title('Híbrido Inteligente', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Cantidad de Clientes', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Rating', fontsize=12, fontweight='bold')
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].grid(True, alpha=0.3, axis='y')

    # HCPN (solo para clientes que lo tienen)
    df_with_hcpn = df[df['experian_score_normalized'].notna()].copy()

    def get_rating_hcpn(score):
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

    df_with_hcpn['hcpn_rating'] = df_with_hcpn['experian_score_normalized'].apply(get_rating_hcpn)
    hcpn_ratings = df_with_hcpn['hcpn_rating'].value_counts().reindex(rating_order, fill_value=0)

    axes[2].bar(hcpn_ratings.index, hcpn_ratings.values, color=colors_ratings, alpha=0.8, edgecolor='black')
    axes[2].set_title(f'HCPN (n={len(df_with_hcpn)})', fontsize=14, fontweight='bold')
    axes[2].set_ylabel('Cantidad de Clientes', fontsize=12, fontweight='bold')
    axes[2].set_xlabel('Rating', fontsize=12, fontweight='bold')
    axes[2].tick_params(axis='x', rotation=45)
    axes[2].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'hybrid_02_rating_comparison.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/hybrid_02_rating_comparison.png")
    plt.close()


def create_weight_analysis():
    """Análisis de pesos dinámicos del híbrido"""
    df = pd.read_csv(HYBRID_FILE)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Scatter: Pesos vs Meses como cliente
    ax1 = axes[0, 0]
    scatter = ax1.scatter(df['months_as_client'], df['peso_platam_usado'],
                         c=df['payment_count'], cmap='viridis', alpha=0.6, s=30)
    ax1.set_xlabel('Meses como Cliente', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Peso PLATAM', fontsize=12, fontweight='bold')
    ax1.set_title('Pesos Dinámicos según Madurez del Cliente', fontsize=14, fontweight='bold')
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, alpha=0.3)

    cbar = plt.colorbar(scatter, ax=ax1)
    cbar.set_label('Cantidad de Pagos', rotation=270, labelpad=20, fontweight='bold')

    # 2. Box plot de pesos por categoría de madurez
    ax2 = axes[0, 1]
    madurez_order = ['muy_nuevo', 'nuevo', 'intermedio', 'establecido', 'maduro']
    peso_data = [df[df['categoria_madurez'] == cat]['peso_platam_usado'].values
                 for cat in madurez_order if cat in df['categoria_madurez'].unique()]

    bp = ax2.boxplot(peso_data, labels=[m for m in madurez_order if m in df['categoria_madurez'].unique()],
                     patch_artist=True, showmeans=True)

    for patch in bp['boxes']:
        patch.set_facecolor('#3498db')
        patch.set_alpha(0.6)

    ax2.set_ylabel('Peso PLATAM', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Categoría de Madurez', fontsize=12, fontweight='bold')
    ax2.set_title('Distribución de Pesos por Categoría', fontsize=14, fontweight='bold')
    ax2.set_xticklabels([m for m in madurez_order if m in df['categoria_madurez'].unique()],
                        rotation=45, ha='right')
    ax2.set_ylim(0, 1.05)
    ax2.grid(True, alpha=0.3, axis='y')

    # 3. Impacto del híbrido: diferencia vs V2.0
    ax3 = axes[1, 0]
    df['hybrid_vs_platam'] = df['hybrid_score'] - df['platam_score']

    ax3.hist(df['hybrid_vs_platam'], bins=50, color='#9b59b6', alpha=0.7, edgecolor='black')
    ax3.axvline(0, color='red', linestyle='--', linewidth=2, label='Sin cambio')
    ax3.axvline(df['hybrid_vs_platam'].mean(), color='green', linestyle='--', linewidth=2,
                label=f'Promedio: {df["hybrid_vs_platam"].mean():.1f}')

    ax3.set_xlabel('Diferencia (Híbrido - PLATAM V2.0)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Frecuencia', fontsize=12, fontweight='bold')
    ax3.set_title('Impacto del Sistema Híbrido', fontsize=14, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Anotaciones
    mejoraron = (df['hybrid_vs_platam'] > 10).sum()
    igual = ((df['hybrid_vs_platam'] >= -10) & (df['hybrid_vs_platam'] <= 10)).sum()
    empeoraron = (df['hybrid_vs_platam'] < -10).sum()

    ax3.text(0.05, 0.95, f'Mejoraron >10pts: {mejoraron} ({mejoraron/len(df)*100:.1f}%)',
             transform=ax3.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='#2ecc71', alpha=0.5))

    ax3.text(0.05, 0.85, f'Similar (±10pts): {igual} ({igual/len(df)*100:.1f}%)',
             transform=ax3.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='#f39c12', alpha=0.5))

    ax3.text(0.05, 0.75, f'Empeoraron <-10pts: {empeoraron} ({empeoraron/len(df)*100:.1f}%)',
             transform=ax3.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='#e74c3c', alpha=0.5))

    # 4. Estrategias más comunes
    ax4 = axes[1, 1]
    ax4.axis('off')

    # Top 10 estrategias
    top_estrategias = df['estrategia_hibrido'].value_counts().head(10)

    estrategias_text = "TOP 10 ESTRATEGIAS MÁS COMUNES\n\n"
    for i, (estrategia, count) in enumerate(top_estrategias.items(), 1):
        pct = count / len(df) * 100
        # Truncar estrategia si es muy larga
        estrategia_corta = estrategia[:45] + '...' if len(estrategia) > 45 else estrategia
        estrategias_text += f"{i}. {estrategia_corta}\n   n={count} ({pct:.1f}%)\n\n"

    ax4.text(0.1, 0.9, estrategias_text, transform=ax4.transAxes, fontsize=9,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#ecf0f1', alpha=0.8))

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'hybrid_03_weight_analysis.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/hybrid_03_weight_analysis.png")
    plt.close()


def create_scatter_comparisons():
    """Scatter plots comparativos"""
    df = pd.read_csv(HYBRID_FILE)
    df_with_hcpn = df[df['experian_score_normalized'].notna()].copy()

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    # 1. PLATAM vs Híbrido
    ax1 = axes[0]
    ax1.scatter(df['platam_score'], df['hybrid_score'], alpha=0.4, s=30, c='#3498db', edgecolors='black', linewidth=0.3)
    ax1.plot([0, 1000], [0, 1000], 'r--', linewidth=2, label='Igualdad')

    corr1 = df['platam_score'].corr(df['hybrid_score'])
    ax1.text(50, 950, f'Correlación: {corr1:.3f}', fontsize=12,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax1.set_xlabel('PLATAM V2.0 Score', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Híbrido Score', fontsize=12, fontweight='bold')
    ax1.set_title('PLATAM V2.0 vs Híbrido', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 1000)
    ax1.set_ylim(0, 1000)

    # 2. HCPN vs Híbrido
    ax2 = axes[1]
    ax2.scatter(df_with_hcpn['experian_score_normalized'], df_with_hcpn['hybrid_score'],
                alpha=0.4, s=30, c='#e74c3c', edgecolors='black', linewidth=0.3)
    ax2.plot([0, 1000], [0, 1000], 'r--', linewidth=2, label='Igualdad')

    corr2 = df_with_hcpn['experian_score_normalized'].corr(df_with_hcpn['hybrid_score'])
    ax2.text(50, 950, f'Correlación: {corr2:.3f}\nn={len(df_with_hcpn)}', fontsize=12,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax2.set_xlabel('HCPN Score (normalizado)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Híbrido Score', fontsize=12, fontweight='bold')
    ax2.set_title('HCPN vs Híbrido', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 1000)
    ax2.set_ylim(0, 1000)

    plt.tight_layout()
    plt.savefig(CHARTS_DIR / 'hybrid_04_scatter_comparisons.png', dpi=300, bbox_inches='tight')
    logger.info(f"✓ Guardado: {CHARTS_DIR}/hybrid_04_scatter_comparisons.png")
    plt.close()


def main():
    logger.info("="*80)
    logger.info("GENERANDO VISUALIZACIONES COMPARATIVAS: V2.0 vs HÍBRIDO vs HCPN")
    logger.info("="*80)

    logger.info("\n1. Comparación de distribuciones...")
    create_score_comparison_distributions()

    logger.info("\n2. Comparación de ratings...")
    create_rating_comparison()

    logger.info("\n3. Análisis de pesos dinámicos...")
    create_weight_analysis()

    logger.info("\n4. Scatter plots comparativos...")
    create_scatter_comparisons()

    logger.info("\n" + "="*80)
    logger.info("✓ VISUALIZACIONES COMPLETADAS")
    logger.info("="*80)
    logger.info(f"\nGráficos guardados en: {CHARTS_DIR.absolute()}")
    logger.info(f"\nArchivos generados:")
    logger.info(f"  • hybrid_01_comparison_distributions.png")
    logger.info(f"  • hybrid_02_rating_comparison.png")
    logger.info(f"  • hybrid_03_weight_analysis.png")
    logger.info(f"  • hybrid_04_scatter_comparisons.png")

if __name__ == '__main__':
    main()
