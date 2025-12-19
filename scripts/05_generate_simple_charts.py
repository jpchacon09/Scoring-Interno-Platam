#!/usr/bin/env python3
"""
Genera gráficos simples y claros para comparación PLATAM vs Experian

Usage:
    python scripts/05_generate_simple_charts.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
CHARTS_DIR = BASE_DIR / 'charts'
COMPARISON_FILE = PROCESSED_DIR / 'score_comparison.csv'

# Crear directorio
CHARTS_DIR.mkdir(exist_ok=True)

# Estilo
plt.style.use('default')
sns.set_palette("husl")

# Cargar datos
df = pd.read_csv(COMPARISON_FILE)

print("Generando gráficos simples y claros...\n")

# =============================================================================
# GRÁFICO 1: Scatter Plot con Zonas de Diferencia
# =============================================================================
print("1/6 Generando scatter plot con zonas...")

fig, ax = plt.subplots(figsize=(12, 10))

# Calcular diferencia absoluta para colorear
df['diff_abs'] = (df['platam_score'] - df['experian_score_normalized']).abs()

# Scatter con color según diferencia
scatter = ax.scatter(
    df['experian_score_normalized'],
    df['platam_score'],
    c=df['diff_abs'],
    cmap='RdYlGn_r',  # Rojo=mucha diferencia, Verde=poca diferencia
    s=60,
    alpha=0.6,
    edgecolors='black',
    linewidth=0.5
)

# Línea de igualdad perfecta
ax.plot([0, 1000], [0, 1000], 'k--', linewidth=2, label='Igualdad perfecta\n(ambos scores iguales)', alpha=0.7)

# Bandas de "cercanía aceptable" (±100 puntos)
ax.fill_between([0, 1000], [-100, 900], [100, 1100], alpha=0.1, color='green',
                 label='Zona aceptable\n(diferencia ±100 pts)')

# Colorbar
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Diferencia absoluta (puntos)', fontsize=12, fontweight='bold')

# Anotaciones de zonas
ax.text(850, 250, 'PLATAM más\nESTRICTO', fontsize=14, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='#e74c3c', alpha=0.3), ha='center')
ax.text(250, 850, 'PLATAM más\nGENEROSO', fontsize=14, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='#2ecc71', alpha=0.3), ha='center')

# Estadísticas
corr = df['platam_score'].corr(df['experian_score_normalized'])
ax.text(50, 950, f'Correlación: {corr:.3f}\n(Baja = miden cosas diferentes)',
        fontsize=12, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

ax.set_xlabel('Score Experian (normalizado 0-1000)', fontsize=14, fontweight='bold')
ax.set_ylabel('Score PLATAM Interno', fontsize=14, fontweight='bold')
ax.set_title('Comparación Score PLATAM vs Experian\nCada punto = 1 cliente',
             fontsize=16, fontweight='bold', pad=20)
ax.legend(loc='lower right', fontsize=11)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 1000)
ax.set_ylim(0, 1000)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '01_scatter_zonas.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Guardado: 01_scatter_zonas.png")
plt.close()

# =============================================================================
# GRÁFICO 2: Promedios por Rating - Comparación Visual
# =============================================================================
print("2/6 Generando comparación por rating...")

rating_summary = df.groupby('platam_rating').agg({
    'platam_score': 'mean',
    'experian_score_normalized': 'mean',
    'cedula': 'count'
}).reset_index()
rating_summary.columns = ['Rating', 'PLATAM Promedio', 'Experian Promedio', 'Cantidad']

# Ordenar ratings
rating_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'F']
rating_summary['Rating'] = pd.Categorical(rating_summary['Rating'], categories=rating_order, ordered=True)
rating_summary = rating_summary.sort_values('Rating')

fig, ax = plt.subplots(figsize=(14, 8))

x = np.arange(len(rating_summary))
width = 0.35

bars1 = ax.bar(x - width/2, rating_summary['PLATAM Promedio'], width,
               label='PLATAM Interno', color='#3498db', edgecolor='black', linewidth=1.5)
bars2 = ax.bar(x + width/2, rating_summary['Experian Promedio'], width,
               label='Experian', color='#e74c3c', edgecolor='black', linewidth=1.5)

# Agregar valores en las barras
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}',
                ha='center', va='bottom', fontsize=9, fontweight='bold')

# Agregar cantidad de clientes en cada rating
for i, row in rating_summary.iterrows():
    ax.text(i, -80, f'n={row["Cantidad"]}', ha='center', fontsize=9, style='italic')

ax.set_xlabel('Rating PLATAM', fontsize=14, fontweight='bold')
ax.set_ylabel('Score Promedio', fontsize=14, fontweight='bold')
ax.set_title('Comparación de Scores Promedio por Rating PLATAM\n¿Qué score tiene Experian para clientes de cada rating PLATAM?',
             fontsize=15, fontweight='bold', pad=20)
ax.set_xticks(x)
ax.set_xticklabels(rating_summary['Rating'], fontsize=12, fontweight='bold')
ax.legend(fontsize=12)
ax.grid(True, axis='y', alpha=0.3)
ax.set_ylim(-100, 1000)

# Línea de referencia
ax.axhline(y=700, color='orange', linestyle='--', alpha=0.5, linewidth=2, label='Score "Bueno" (700)')

plt.tight_layout()
plt.savefig(CHARTS_DIR / '02_promedios_por_rating.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Guardado: 02_promedios_por_rating.png")
plt.close()

# =============================================================================
# GRÁFICO 3: Histograma de Diferencias - ¿Quién es más estricto?
# =============================================================================
print("3/6 Generando histograma de diferencias...")

fig, ax = plt.subplots(figsize=(14, 8))

# Calcular diferencia
diff = df['platam_score'] - df['experian_score_normalized']

# Crear histograma con colores
n, bins, patches = ax.hist(diff, bins=50, edgecolor='black', linewidth=1)

# Colorear barras
for i, patch in enumerate(patches):
    if bins[i] < -100:
        patch.set_facecolor('#e74c3c')  # Rojo - PLATAM mucho más bajo
    elif bins[i] < 0:
        patch.set_facecolor('#f39c12')  # Naranja - PLATAM más bajo
    elif bins[i] < 100:
        patch.set_facecolor('#2ecc71')  # Verde - Similar
    else:
        patch.set_facecolor('#3498db')  # Azul - PLATAM más alto

# Líneas de referencia
ax.axvline(0, color='black', linestyle='--', linewidth=3, label='Sin diferencia', alpha=0.8)
ax.axvline(diff.mean(), color='red', linestyle='--', linewidth=2,
           label=f'Promedio: {diff.mean():.1f} pts', alpha=0.8)

# Estadísticas
platam_mas_bajo = (diff < -100).sum()
similar = ((diff >= -100) & (diff <= 100)).sum()
platam_mas_alto = (diff > 100).sum()

# Texto explicativo
info_text = f"""
PLATAM más bajo que Experian (-100 o menos): {platam_mas_bajo} clientes ({platam_mas_bajo/len(diff)*100:.1f}%)
Similar (diferencia entre -100 y +100): {similar} clientes ({similar/len(diff)*100:.1f}%)
PLATAM más alto que Experian (+100 o más): {platam_mas_alto} clientes ({platam_mas_alto/len(diff)*100:.1f}%)
"""

ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

ax.set_xlabel('Diferencia de Scores (PLATAM - Experian)', fontsize=14, fontweight='bold')
ax.set_ylabel('Cantidad de Clientes', fontsize=14, fontweight='bold')
ax.set_title('¿Quién es más estricto? PLATAM vs Experian\nNegativo = PLATAM más estricto | Positivo = PLATAM más generoso',
             fontsize=15, fontweight='bold', pad=20)
ax.legend(fontsize=12)
ax.grid(True, axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '03_diferencias_histogram.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Guardado: 03_diferencias_histogram.png")
plt.close()

# =============================================================================
# GRÁFICO 4: Boxplot - Distribuciones Comparadas
# =============================================================================
print("4/6 Generando boxplot comparativo...")

fig, ax = plt.subplots(figsize=(10, 8))

data_to_plot = [df['platam_score'], df['experian_score_normalized']]
positions = [1, 2]

bp = ax.boxplot(data_to_plot, positions=positions, widths=0.6, patch_artist=True,
                showmeans=True, meanline=True,
                boxprops=dict(linewidth=2, edgecolor='black'),
                whiskerprops=dict(linewidth=2),
                capprops=dict(linewidth=2),
                medianprops=dict(linewidth=3, color='red'),
                meanprops=dict(linewidth=3, color='green', linestyle='--'))

# Colorear cajas
colors = ['#3498db', '#e74c3c']
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)

# Estadísticas
stats_platam = f"Media: {df['platam_score'].mean():.0f}\nMediana: {df['platam_score'].median():.0f}"
stats_experian = f"Media: {df['experian_score_normalized'].mean():.0f}\nMediana: {df['experian_score_normalized'].median():.0f}"

ax.text(1, df['platam_score'].min() - 80, stats_platam, ha='center', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='#3498db', alpha=0.3))
ax.text(2, df['experian_score_normalized'].min() - 80, stats_experian, ha='center', fontsize=10,
        bbox=dict(boxstyle='round', facecolor='#e74c3c', alpha=0.3))

ax.set_ylabel('Score (0-1000)', fontsize=14, fontweight='bold')
ax.set_title('Distribución de Scores: PLATAM vs Experian\nLínea roja = mediana | Línea verde = media',
             fontsize=15, fontweight='bold', pad=20)
ax.set_xticks(positions)
ax.set_xticklabels(['PLATAM Interno', 'Experian'], fontsize=13, fontweight='bold')
ax.grid(True, axis='y', alpha=0.3)
ax.set_ylim(-150, 1050)

plt.tight_layout()
plt.savefig(CHARTS_DIR / '04_boxplot_comparativo.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Guardado: 04_boxplot_comparativo.png")
plt.close()

# =============================================================================
# GRÁFICO 5: Top 10 Mayores Diferencias en Cada Dirección
# =============================================================================
print("5/6 Generando casos extremos...")

# Top 10 donde PLATAM es mucho más bajo que Experian
platam_mas_bajo_top = df.nsmallest(10, 'score_diff')[['cedula', 'platam_score', 'experian_score_normalized', 'score_diff']].copy()
platam_mas_bajo_top['tipo'] = 'PLATAM más bajo'

# Top 10 donde PLATAM es mucho más alto que Experian
platam_mas_alto_top = df.nlargest(10, 'score_diff')[['cedula', 'platam_score', 'experian_score_normalized', 'score_diff']].copy()
platam_mas_alto_top['tipo'] = 'PLATAM más alto'

# Combinar
casos_extremos = pd.concat([platam_mas_bajo_top, platam_mas_alto_top])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

# Izquierda: PLATAM más bajo
for idx, row in platam_mas_bajo_top.iterrows():
    ax1.barh(platam_mas_bajo_top.index.tolist().index(idx), row['experian_score_normalized'],
             color='#e74c3c', alpha=0.7, edgecolor='black', linewidth=1.5, label='Experian' if idx == platam_mas_bajo_top.index[0] else '')
    ax1.barh(platam_mas_bajo_top.index.tolist().index(idx), row['platam_score'],
             color='#3498db', alpha=0.7, edgecolor='black', linewidth=1.5, label='PLATAM' if idx == platam_mas_bajo_top.index[0] else '')

    # Texto con diferencia
    ax1.text(row['experian_score_normalized'] + 20, platam_mas_bajo_top.index.tolist().index(idx),
             f'Δ={row["score_diff"]:.0f}', fontsize=10, fontweight='bold', va='center')

ax1.set_xlabel('Score', fontsize=12, fontweight='bold')
ax1.set_ylabel('Clientes (anónimos)', fontsize=12, fontweight='bold')
ax1.set_title('Top 10: PLATAM mucho MÁS BAJO que Experian\n(PLATAM más estricto)',
              fontsize=13, fontweight='bold', color='#c0392b')
ax1.legend(fontsize=10)
ax1.grid(True, axis='x', alpha=0.3)
ax1.set_yticks(range(10))
ax1.set_yticklabels([f'Cliente {i+1}' for i in range(10)])
ax1.invert_yaxis()

# Derecha: PLATAM más alto
for idx, row in platam_mas_alto_top.iterrows():
    ax2.barh(platam_mas_alto_top.index.tolist().index(idx), row['experian_score_normalized'],
             color='#e74c3c', alpha=0.7, edgecolor='black', linewidth=1.5, label='Experian' if idx == platam_mas_alto_top.index[0] else '')
    ax2.barh(platam_mas_alto_top.index.tolist().index(idx), row['platam_score'],
             color='#3498db', alpha=0.7, edgecolor='black', linewidth=1.5, label='PLATAM' if idx == platam_mas_alto_top.index[0] else '')

    # Texto con diferencia
    ax2.text(row['platam_score'] + 20, platam_mas_alto_top.index.tolist().index(idx),
             f'Δ=+{row["score_diff"]:.0f}', fontsize=10, fontweight='bold', va='center')

ax2.set_xlabel('Score', fontsize=12, fontweight='bold')
ax2.set_ylabel('Clientes (anónimos)', fontsize=12, fontweight='bold')
ax2.set_title('Top 10: PLATAM mucho MÁS ALTO que Experian\n(PLATAM más generoso)',
              fontsize=13, fontweight='bold', color='#27ae60')
ax2.legend(fontsize=10)
ax2.grid(True, axis='x', alpha=0.3)
ax2.set_yticks(range(10))
ax2.set_yticklabels([f'Cliente {i+1}' for i in range(10)])
ax2.invert_yaxis()

plt.tight_layout()
plt.savefig(CHARTS_DIR / '05_casos_extremos.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Guardado: 05_casos_extremos.png")
plt.close()

# =============================================================================
# GRÁFICO 6: Mapa de Calor - Categorización
# =============================================================================
print("6/6 Generando mapa de categorización...")

# Crear categorías para ambos scores
def categorize_score(score):
    if score >= 800:
        return 'Excelente\n(800+)'
    elif score >= 650:
        return 'Bueno\n(650-799)'
    elif score >= 500:
        return 'Regular\n(500-649)'
    else:
        return 'Malo\n(<500)'

df['platam_cat'] = df['platam_score'].apply(categorize_score)
df['experian_cat'] = df['experian_score_normalized'].apply(categorize_score)

# Tabla de contingencia
contingency = pd.crosstab(df['platam_cat'], df['experian_cat'], margins=True, margins_name='TOTAL')

# Reordenar
cat_order = ['Excelente\n(800+)', 'Bueno\n(650-799)', 'Regular\n(500-649)', 'Malo\n(<500)', 'TOTAL']
contingency = contingency.reindex(index=cat_order, columns=cat_order)

fig, ax = plt.subplots(figsize=(12, 10))

sns.heatmap(contingency.iloc[:-1, :-1], annot=True, fmt='d', cmap='YlOrRd',
            cbar_kws={'label': 'Cantidad de Clientes'},
            linewidths=2, linecolor='black', ax=ax, vmin=0, vmax=500,
            annot_kws={'fontsize': 14, 'fontweight': 'bold'})

ax.set_xlabel('Categoría según Experian', fontsize=14, fontweight='bold')
ax.set_ylabel('Categoría según PLATAM', fontsize=14, fontweight='bold')
ax.set_title('¿Coinciden las Categorías? PLATAM vs Experian\nDiagonal = Coincidencia perfecta',
             fontsize=16, fontweight='bold', pad=20)

# Resaltar diagonal
for i in range(4):
    ax.add_patch(plt.Rectangle((i, i), 1, 1, fill=False, edgecolor='blue', lw=4))

# Texto explicativo
coinciden = sum([contingency.iloc[i, i] for i in range(4)])
total = contingency.iloc[-1, -1]
ax.text(0.02, 0.98, f'Clientes en diagonal (coinciden): {coinciden:.0f} ({coinciden/total*100:.1f}%)',
        transform=ax.transAxes, fontsize=12, fontweight='bold',
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

plt.tight_layout()
plt.savefig(CHARTS_DIR / '06_mapa_categorizacion.png', dpi=300, bbox_inches='tight')
print(f"   ✓ Guardado: 06_mapa_categorizacion.png")
plt.close()

print("\n" + "="*80)
print("✓ TODOS LOS GRÁFICOS GENERADOS")
print("="*80)
print(f"\nUbicación: {CHARTS_DIR.absolute()}\n")
