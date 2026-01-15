#!/usr/bin/env python3
"""
Script para generar gráficas actualizadas del modelo v2.2
Incluye feature importance, distribuciones, análisis por ciudad, y más
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from google.cloud import aiplatform
import pickle
import os
from sklearn.metrics import roc_curve, auc, confusion_matrix, classification_report
import warnings
warnings.filterwarnings('ignore')

# Configuración
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "platam-analytics"
REGION = "us-central1"
ENDPOINT_ID = "7891061911641391104"  # Modelo v2.2

# Paths
CSV_PATH = "SCORES_V2_ANALISIS_COMPLETO.csv"
MODEL_PATH = "models/vertex_ai_final/model.pkl"
OUTPUT_DIR = "charts"

# Features del modelo v2.2 (22 features)
FEATURE_ORDER = [
    'platam_score', 'experian_score_normalized',
    'score_payment_performance', 'score_payment_plan', 'score_deterioration',
    'payment_count', 'months_as_client',
    'pct_early', 'pct_late',
    'peso_platam_usado', 'peso_hcpn_usado',
    'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes',
    'genero_encoded', 'edad', 'ciudad_encoded',
    'cuota_mensual', 'creditos_vigentes', 'creditos_mora', 'hist_neg_12m'
]

print("="*80)
print("📊 GENERANDO GRÁFICAS ACTUALIZADAS - MODELO v2.2")
print("="*80)

# ============================================
# 1. CARGAR DATOS
# ============================================
print("\n📂 Cargando datos...")
df = pd.read_csv(CSV_PATH)
print(f"✅ Cargados {len(df)} clientes con {len(df.columns)} columnas")

# ============================================
# 2. CONECTAR CON VERTEX AI
# ============================================
print("\n🌐 Conectando con Vertex AI endpoint v2.2...")
aiplatform.init(project=PROJECT_ID, location=REGION)
endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
)
print(f"✅ Conectado al endpoint: {ENDPOINT_ID}")

# ============================================
# 3. GENERAR PREDICCIONES
# ============================================
print("\n🤖 Generando predicciones con modelo v2.2...")

def prepare_instance(row):
    """Prepara una instancia para predicción"""
    instance = []
    for feature in FEATURE_ORDER:
        value = row.get(feature, 0)
        if pd.isna(value) or value is None:
            if feature == 'edad':
                value = 35
            elif feature in ['genero_encoded', 'ciudad_encoded']:
                value = 0
            else:
                value = 0
        if isinstance(value, bool):
            value = int(value)
        instance.append(float(value))
    return instance

# Generar predicciones (batch)
predictions = []
print("Generando predicciones para todos los clientes...")
for idx, row in df.iterrows():
    if idx % 100 == 0:
        print(f"  Procesados {idx}/{len(df)} clientes...")

    instance = prepare_instance(row)
    pred = endpoint.predict(instances=[instance])
    prob_default = pred.predictions[0][1]
    predictions.append(prob_default)

df['ml_prob_default_v2.2'] = predictions
print(f"✅ Predicciones generadas para {len(df)} clientes")

# ============================================
# 4. CARGAR MODELO LOCAL PARA FEATURE IMPORTANCE
# ============================================
print("\n📊 Cargando modelo local para feature importance...")
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)

# XGBClassifier usa feature_importances_ (no get_score)
feature_importances = model.feature_importances_
importance_df = pd.DataFrame({
    'feature': FEATURE_ORDER,
    'importance': feature_importances
})
importance_df = importance_df.sort_values('importance', ascending=False)

# Mapear nombres de features a nombres legibles
feature_names_map = {
    'platam_score': 'Score PLATAM',
    'experian_score_normalized': 'Score Experian',
    'score_payment_performance': 'Performance de Pago',
    'score_payment_plan': 'Score Plan de Pago',
    'score_deterioration': 'Deterioro',
    'payment_count': 'Cantidad de Pagos',
    'months_as_client': 'Meses como Cliente',
    'pct_early': '% Pagos Tempranos',
    'pct_late': '% Pagos Tardíos',
    'peso_platam_usado': 'Peso PLATAM',
    'peso_hcpn_usado': 'Peso HCPN',
    'tiene_plan_activo': 'Plan Activo',
    'tiene_plan_default': 'Plan Default',
    'tiene_plan_pendiente': 'Plan Pendiente',
    'num_planes': 'Num Planes',
    'genero_encoded': 'Género',
    'edad': 'Edad',
    'ciudad_encoded': 'Ciudad',
    'cuota_mensual': 'Cuota Mensual',
    'creditos_vigentes': 'Créditos Vigentes',
    'creditos_mora': 'Créditos en Mora',
    'hist_neg_12m': 'Historial Negativo 12m'
}

importance_df['feature_name'] = importance_df['feature'].map(feature_names_map)

# ============================================
# 5. GENERAR GRÁFICAS
# ============================================
print("\n🎨 Generando gráficas...")

# Configurar estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)

# GRÁFICA 1: Feature Importance
print("  📊 1/6 - Feature Importance...")
fig, ax = plt.subplots(figsize=(14, 10))
colors = sns.color_palette("viridis", len(importance_df))
bars = ax.barh(importance_df['feature_name'], importance_df['importance'], color=colors)
ax.set_xlabel('Importancia (Gain)', fontsize=12, fontweight='bold')
ax.set_title('Feature Importance - Modelo v2.2 (22 Features con Demografía)',
             fontsize=14, fontweight='bold', pad=20)
ax.invert_yaxis()
for i, (bar, val) in enumerate(zip(bars, importance_df['importance'])):
    ax.text(val, bar.get_y() + bar.get_height()/2,
            f' {val:.1f}',
            va='center', fontsize=9, fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/v2.2_feature_importance.png', dpi=300, bbox_inches='tight')
plt.close()
print("    ✅ Guardada: v2.2_feature_importance.png")

# GRÁFICA 2: Distribución de Probabilidades de Default
print("  📊 2/6 - Distribución de Probabilidades...")
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Histograma
ax1.hist(df['ml_prob_default_v2.2'], bins=50, color='steelblue', edgecolor='black', alpha=0.7)
ax1.axvline(df['ml_prob_default_v2.2'].mean(), color='red', linestyle='--', linewidth=2, label=f'Media: {df["ml_prob_default_v2.2"].mean():.2%}')
ax1.axvline(df['ml_prob_default_v2.2'].median(), color='orange', linestyle='--', linewidth=2, label=f'Mediana: {df["ml_prob_default_v2.2"].median():.2%}')
ax1.set_xlabel('Probabilidad de Default', fontsize=12)
ax1.set_ylabel('Frecuencia', fontsize=12)
ax1.set_title('Distribución de Probabilidades de Default\nModelo v2.2', fontsize=13, fontweight='bold')
ax1.legend()
ax1.grid(alpha=0.3)

# Boxplot
box = ax2.boxplot(df['ml_prob_default_v2.2'], vert=True, patch_artist=True)
box['boxes'][0].set_facecolor('lightblue')
ax2.set_ylabel('Probabilidad de Default', fontsize=12)
ax2.set_title('Boxplot de Probabilidades', fontsize=13, fontweight='bold')
ax2.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/v2.2_distribucion_probabilidades.png', dpi=300, bbox_inches='tight')
plt.close()
print("    ✅ Guardada: v2.2_distribucion_probabilidades.png")

# GRÁFICA 3: Análisis por Ciudad
print("  📊 3/6 - Análisis por Ciudad...")
if 'ciudad' in df.columns:
    ciudad_stats = df.groupby('ciudad').agg({
        'ml_prob_default_v2.2': ['mean', 'count'],
        'hybrid_score': 'mean'
    }).round(3)

    ciudad_stats.columns = ['prob_default_mean', 'count', 'score_mean']
    ciudad_stats = ciudad_stats[ciudad_stats['count'] >= 10].sort_values('prob_default_mean', ascending=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # Probabilidad de default por ciudad
    colors = ['red' if x > 0.30 else 'orange' if x > 0.20 else 'green'
              for x in ciudad_stats['prob_default_mean']]
    bars = ax1.barh(ciudad_stats.index, ciudad_stats['prob_default_mean'] * 100, color=colors, alpha=0.7)
    ax1.set_xlabel('Probabilidad de Default (%)', fontsize=12)
    ax1.set_title('Probabilidad de Default por Ciudad\n(Modelo v2.2 con Geografía)',
                  fontsize=13, fontweight='bold')
    for i, (bar, val, count) in enumerate(zip(bars, ciudad_stats['prob_default_mean'], ciudad_stats['count'])):
        ax1.text(val * 100, bar.get_y() + bar.get_height()/2,
                f' {val*100:.1f}% (n={int(count)})',
                va='center', fontsize=9)
    ax1.axvline(df['ml_prob_default_v2.2'].mean() * 100, color='blue',
                linestyle='--', linewidth=2, label='Promedio Nacional')
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Score híbrido por ciudad
    colors2 = ['green' if x > 650 else 'orange' if x > 550 else 'red'
               for x in ciudad_stats['score_mean']]
    bars2 = ax2.barh(ciudad_stats.index, ciudad_stats['score_mean'], color=colors2, alpha=0.7)
    ax2.set_xlabel('Score Híbrido Promedio', fontsize=12)
    ax2.set_title('Score Híbrido por Ciudad', fontsize=13, fontweight='bold')
    for bar, val in zip(bars2, ciudad_stats['score_mean']):
        ax2.text(val, bar.get_y() + bar.get_height()/2,
                f' {val:.0f}',
                va='center', fontsize=9)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(f'{OUTPUT_DIR}/v2.2_analisis_por_ciudad.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("    ✅ Guardada: v2.2_analisis_por_ciudad.png")

# GRÁFICA 4: Scatter Probabilidad vs Score Híbrido
print("  📊 4/6 - Scatter Probabilidad vs Score...")
fig, ax = plt.subplots(figsize=(14, 9))
scatter = ax.scatter(df['hybrid_score'], df['ml_prob_default_v2.2'] * 100,
                     c=df['ml_prob_default_v2.2'], cmap='RdYlGn_r',
                     alpha=0.6, s=50, edgecolors='black', linewidth=0.5)
ax.set_xlabel('Score Híbrido', fontsize=12, fontweight='bold')
ax.set_ylabel('Probabilidad de Default (%)', fontsize=12, fontweight='bold')
ax.set_title('Relación Score Híbrido vs Probabilidad de Default\nModelo v2.2 con Features Demográficas',
             fontsize=14, fontweight='bold', pad=20)
ax.axhline(20, color='orange', linestyle='--', linewidth=2, label='Umbral Riesgo Medio (20%)')
ax.axhline(40, color='red', linestyle='--', linewidth=2, label='Umbral Riesgo Alto (40%)')
ax.axvline(550, color='blue', linestyle='--', linewidth=2, label='Score Mínimo Bueno (550)')
cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Probabilidad de Default', fontsize=11)
ax.legend(loc='upper right')
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/v2.2_scatter_score_vs_prob.png', dpi=300, bbox_inches='tight')
plt.close()
print("    ✅ Guardada: v2.2_scatter_score_vs_prob.png")

# GRÁFICA 5: Distribución por Nivel de Riesgo
print("  📊 5/6 - Distribución por Nivel de Riesgo...")
def classify_risk(prob):
    if prob < 0.10:
        return "Muy Bajo"
    elif prob < 0.20:
        return "Bajo"
    elif prob < 0.40:
        return "Medio"
    elif prob < 0.60:
        return "Alto"
    else:
        return "Muy Alto"

df['risk_level'] = df['ml_prob_default_v2.2'].apply(classify_risk)
risk_counts = df['risk_level'].value_counts()
risk_order = ["Muy Bajo", "Bajo", "Medio", "Alto", "Muy Alto"]
risk_counts = risk_counts.reindex(risk_order)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Barras
colors_risk = ['darkgreen', 'green', 'orange', 'orangered', 'red']
bars = ax1.bar(risk_counts.index, risk_counts.values, color=colors_risk, alpha=0.8, edgecolor='black')
ax1.set_ylabel('Cantidad de Clientes', fontsize=12)
ax1.set_title('Distribución de Clientes por Nivel de Riesgo\nModelo v2.2',
              fontsize=13, fontweight='bold')
for bar, val in zip(bars, risk_counts.values):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(val)}\n({val/len(df)*100:.1f}%)',
            ha='center', va='bottom', fontsize=10, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)

# Pie chart
ax2.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%',
        colors=colors_risk, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
ax2.set_title('Proporción de Niveles de Riesgo', fontsize=13, fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/v2.2_distribucion_niveles_riesgo.png', dpi=300, bbox_inches='tight')
plt.close()
print("    ✅ Guardada: v2.2_distribucion_niveles_riesgo.png")

# GRÁFICA 6: Top Features Demográficas
print("  📊 6/6 - Análisis de Features Demográficas...")
demographic_features = ['edad', 'ciudad_encoded', 'cuota_mensual', 'creditos_vigentes',
                        'creditos_mora', 'hist_neg_12m', 'genero_encoded']
demo_importance = importance_df[importance_df['feature'].isin(demographic_features)].copy()

fig, ax = plt.subplots(figsize=(12, 6))
colors = sns.color_palette("rocket", len(demo_importance))
bars = ax.barh(demo_importance['feature_name'], demo_importance['importance'], color=colors)
ax.set_xlabel('Importancia (Gain)', fontsize=12, fontweight='bold')
ax.set_title('Importancia de Features Demográficas\nNuevas en Modelo v2.2',
             fontsize=14, fontweight='bold', pad=20)
ax.invert_yaxis()
for bar, val in zip(bars, demo_importance['importance']):
    ax.text(val, bar.get_y() + bar.get_height()/2,
            f' {val:.1f}',
            va='center', fontsize=10, fontweight='bold')
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/v2.2_features_demograficas.png', dpi=300, bbox_inches='tight')
plt.close()
print("    ✅ Guardada: v2.2_features_demograficas.png")

# ============================================
# 6. GUARDAR DATOS ACTUALIZADOS
# ============================================
print("\n💾 Guardando CSV con predicciones actualizadas...")
output_csv = "SCORES_V2_CON_PREDICCIONES_V2.2.csv"
df.to_csv(output_csv, index=False)
print(f"✅ Guardado: {output_csv}")

# ============================================
# 7. RESUMEN
# ============================================
print("\n" + "="*80)
print("✅ GENERACIÓN COMPLETADA")
print("="*80)
print(f"\n📊 Estadísticas del Modelo v2.2:")
print(f"   • Total clientes analizados: {len(df):,}")
print(f"   • Probabilidad de default promedio: {df['ml_prob_default_v2.2'].mean():.2%}")
print(f"   • Probabilidad de default mediana: {df['ml_prob_default_v2.2'].median():.2%}")
print(f"\n🎯 Distribución por nivel de riesgo:")
for level in risk_order:
    count = risk_counts.get(level, 0)
    pct = count / len(df) * 100
    print(f"   • {level:12s}: {count:4d} clientes ({pct:5.1f}%)")

print(f"\n📈 Gráficas generadas en '{OUTPUT_DIR}/':")
print(f"   1. v2.2_feature_importance.png")
print(f"   2. v2.2_distribucion_probabilidades.png")
print(f"   3. v2.2_analisis_por_ciudad.png")
print(f"   4. v2.2_scatter_score_vs_prob.png")
print(f"   5. v2.2_distribucion_niveles_riesgo.png")
print(f"   6. v2.2_features_demograficas.png")

print("\n" + "="*80)
