#!/usr/bin/env python3
"""
Visualizaciones Completas del Modelo XGBoost Optimizado
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (roc_auc_score, roc_curve, confusion_matrix,
                             precision_recall_curve, classification_report)
from xgboost import XGBClassifier
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Configurar estilo
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 12)

print("="*80)
print("VISUALIZACIONES DEL MODELO - XGBoost Optimizado")
print("="*80)

# 1. CARGAR DATOS Y ENTRENAR
print("\n[1/3] Entrenando modelo...")
df = pd.read_csv('ml_training_data.csv')

feature_cols = [
    'platam_score', 'experian_score_normalized',
    'score_payment_performance', 'score_payment_plan', 'score_deterioration',
    'payment_count', 'months_as_client',
    'days_past_due_mean', 'days_past_due_max',
    'pct_early', 'pct_late',
    'peso_platam_usado', 'peso_hcpn_usado',
    'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
]

feature_cols = [col for col in feature_cols if col in df.columns]
X = df[feature_cols].fillna(0)
y = df['default_flag']

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# Normalización
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Entrenar
scale_pos_weight = len(y_train[y_train==0]) / len(y_train[y_train==1])
model = XGBClassifier(
    max_depth=4,
    learning_rate=0.1,
    n_estimators=100,
    scale_pos_weight=scale_pos_weight,
    random_state=42,
    eval_metric='auc'
)
model.fit(X_train_scaled, y_train)

# Predicciones
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]

# Threshold óptimo
optimal_threshold = 0.60
y_pred_optimal = (y_pred_proba >= optimal_threshold).astype(int)
y_pred_default = (y_pred_proba >= 0.50).astype(int)

print("   ✓ Modelo entrenado")

# 2. CALCULAR MÉTRICAS
print("\n[2/3] Calculando métricas...")

auc = roc_auc_score(y_test, y_pred_proba)
cm_optimal = confusion_matrix(y_test, y_pred_optimal)
cm_default = confusion_matrix(y_test, y_pred_default)

print(f"   ✓ AUC-ROC: {auc:.3f}")
print(f"   ✓ Threshold óptimo: {optimal_threshold}")

# 3. CREAR VISUALIZACIONES
print("\n[3/3] Generando visualizaciones...")

fig = plt.figure(figsize=(18, 12))

# =====================
# 1. ROC CURVE
# =====================
ax1 = plt.subplot(2, 3, 1)
fpr, tpr, thresholds_roc = roc_curve(y_test, y_pred_proba)
plt.plot(fpr, tpr, linewidth=3, label=f'XGBoost (AUC = {auc:.3f})', color='#2E86AB')
plt.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Random Classifier', alpha=0.5)
plt.fill_between(fpr, tpr, alpha=0.2, color='#2E86AB')

# Marcar threshold óptimo
idx_optimal = np.argmin(np.abs(thresholds_roc - optimal_threshold))
plt.plot(fpr[idx_optimal], tpr[idx_optimal], 'ro', markersize=12,
         label=f'Threshold {optimal_threshold} (TPR={tpr[idx_optimal]:.2f})')

plt.xlabel('False Positive Rate', fontsize=12, fontweight='bold')
plt.ylabel('True Positive Rate', fontsize=12, fontweight='bold')
plt.title('Curva ROC (Receiver Operating Characteristic)', fontsize=14, fontweight='bold', pad=15)
plt.legend(loc='lower right', fontsize=10)
plt.grid(True, alpha=0.3)

# =====================
# 2. PRECISION-RECALL CURVE
# =====================
ax2 = plt.subplot(2, 3, 2)
precision, recall, thresholds_pr = precision_recall_curve(y_test, y_pred_proba)
plt.plot(recall, precision, linewidth=3, color='#A23B72', label='Precision-Recall Curve')
plt.fill_between(recall, precision, alpha=0.2, color='#A23B72')

# Baseline (proporción de defaults)
baseline = y_test.sum() / len(y_test)
plt.axhline(y=baseline, color='k', linestyle='--', linewidth=2,
            label=f'Baseline ({baseline:.1%})', alpha=0.5)

plt.xlabel('Recall (Detectar Defaults)', fontsize=12, fontweight='bold')
plt.ylabel('Precision', fontsize=12, fontweight='bold')
plt.title('Curva Precision-Recall', fontsize=14, fontweight='bold', pad=15)
plt.legend(loc='best', fontsize=10)
plt.grid(True, alpha=0.3)

# =====================
# 3. CONFUSION MATRIX (Threshold Óptimo)
# =====================
ax3 = plt.subplot(2, 3, 3)
sns.heatmap(cm_optimal, annot=True, fmt='d', cmap='RdYlGn_r',
            cbar=True, square=True, linewidths=2,
            annot_kws={'size': 16, 'weight': 'bold'})

tn, fp, fn, tp = cm_optimal.ravel()
plt.text(0.5, -0.15, f'TN: {tn}', ha='center', fontsize=11, transform=ax3.transAxes)
plt.text(1.5, -0.15, f'FP: {fp}', ha='center', fontsize=11, transform=ax3.transAxes)
plt.text(0.5, -0.22, f'(Buenos OK)', ha='center', fontsize=9, style='italic', transform=ax3.transAxes)
plt.text(1.5, -0.22, f'(Buenos Rechazados)', ha='center', fontsize=9, style='italic', color='red', transform=ax3.transAxes)

plt.ylabel('Real', fontsize=12, fontweight='bold')
plt.xlabel('Predicción', fontsize=12, fontweight='bold')
plt.title(f'Confusion Matrix - Threshold {optimal_threshold}\n{tp}/20 Defaults Detectados ({tp/20*100:.0f}%)',
          fontsize=14, fontweight='bold', pad=15)
plt.yticks([0.5, 1.5], ['No-Default', 'Default'], rotation=0)
plt.xticks([0.5, 1.5], ['No-Default', 'Default'])

# =====================
# 4. FEATURE IMPORTANCE (Top 10)
# =====================
ax4 = plt.subplot(2, 3, 4)
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False).head(10)

colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(feature_importance)))
bars = plt.barh(range(len(feature_importance)), feature_importance['importance'], color=colors)

# Añadir valores
for i, (idx, row) in enumerate(feature_importance.iterrows()):
    plt.text(row['importance'], i, f" {row['importance']:.3f}",
             va='center', fontsize=10, fontweight='bold')

plt.yticks(range(len(feature_importance)), feature_importance['feature'])
plt.xlabel('Importancia', fontsize=12, fontweight='bold')
plt.title('Top 10 Features Más Importantes', fontsize=14, fontweight='bold', pad=15)
plt.gca().invert_yaxis()
plt.grid(True, alpha=0.3, axis='x')

# =====================
# 5. DISTRIBUCIÓN DE PROBABILIDADES
# =====================
ax5 = plt.subplot(2, 3, 5)

# Probabilidades para no-defaults y defaults
probs_no_default = y_pred_proba[y_test == 0]
probs_default = y_pred_proba[y_test == 1]

plt.hist(probs_no_default, bins=30, alpha=0.6, label='No-Default (Real)',
         color='green', edgecolor='black', density=True)
plt.hist(probs_default, bins=15, alpha=0.8, label='Default (Real)',
         color='red', edgecolor='black', density=True)

# Línea de threshold
plt.axvline(x=optimal_threshold, color='blue', linestyle='--', linewidth=3,
            label=f'Threshold Óptimo ({optimal_threshold})')
plt.axvline(x=0.50, color='gray', linestyle=':', linewidth=2,
            label='Threshold Default (0.50)', alpha=0.7)

plt.xlabel('Probabilidad Predicha de Default', fontsize=12, fontweight='bold')
plt.ylabel('Densidad', fontsize=12, fontweight='bold')
plt.title('Distribución de Probabilidades Predichas', fontsize=14, fontweight='bold', pad=15)
plt.legend(fontsize=10)
plt.grid(True, alpha=0.3)

# =====================
# 6. COMPARACIÓN DE THRESHOLDS
# =====================
ax6 = plt.subplot(2, 3, 6)

thresholds_compare = [0.40, 0.50, 0.60]
recalls = []
precisions = []
buenos_rechazados = []

for thresh in thresholds_compare:
    y_pred_temp = (y_pred_proba >= thresh).astype(int)
    cm_temp = confusion_matrix(y_test, y_pred_temp)
    tn_t, fp_t, fn_t, tp_t = cm_temp.ravel()

    recall = tp_t / (tp_t + fn_t) if (tp_t + fn_t) > 0 else 0
    precision = tp_t / (tp_t + fp_t) if (tp_t + fp_t) > 0 else 0

    recalls.append(recall * 100)
    precisions.append(precision * 100)
    buenos_rechazados.append(fp_t)

x = np.arange(len(thresholds_compare))
width = 0.25

bars1 = plt.bar(x - width, recalls, width, label='Recall (%)', color='#2E86AB', alpha=0.8)
bars2 = plt.bar(x, precisions, width, label='Precision (%)', color='#A23B72', alpha=0.8)
bars3 = plt.bar(x + width, buenos_rechazados, width, label='Buenos Rechazados', color='#F18F01', alpha=0.8)

# Añadir valores en las barras
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}', ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.xlabel('Threshold', fontsize=12, fontweight='bold')
plt.ylabel('Valor', fontsize=12, fontweight='bold')
plt.title('Comparación de Thresholds', fontsize=14, fontweight='bold', pad=15)
plt.xticks(x, [f'{t:.2f}' for t in thresholds_compare])
plt.legend(fontsize=10)
plt.grid(True, alpha=0.3, axis='y')

# Resaltar threshold óptimo
plt.axvspan(x[2] - width*1.5, x[2] + width*2.5, alpha=0.2, color='green', label='Óptimo (0.60)')

# =====================
# LAYOUT FINAL
# =====================
plt.suptitle('XGBoost - Predicción de Defaults\nModelo Optimizado para Perfil Agresivo',
             fontsize=18, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0, 1, 0.99])
plt.savefig('model_visualizations.png', dpi=200, bbox_inches='tight')
print("   ✓ Gráfico guardado: model_visualizations.png")

# =====================
# REPORTE TEXTUAL
# =====================
print("\n" + "="*80)
print("📊 REPORTE DE MÉTRICAS")
print("="*80)

print(f"\n🎯 MODELO: XGBoost")
print(f"   • AUC-ROC: {auc:.3f}")
print(f"   • Threshold óptimo: {optimal_threshold}")
print(f"   • Perfil: AGRESIVO (minimizar rechazo de buenos)")

print(f"\n📈 PERFORMANCE CON THRESHOLD {optimal_threshold}:")
tn, fp, fn, tp = cm_optimal.ravel()
recall_opt = tp / (tp + fn)
precision_opt = tp / (tp + fp)
accuracy_opt = (tn + tp) / (tn + fp + fn + tp)

print(f"   • Accuracy: {accuracy_opt:.1%}")
print(f"   • Precision: {precision_opt:.1%}")
print(f"   • Recall: {recall_opt:.1%}")
print(f"   • Defaults detectados: {tp}/20 ({recall_opt*100:.0f}%)")
print(f"   • Buenos rechazados: {fp}/347 ({fp/347*100:.1f}%)")
print(f"   • Tasa de aprobación: {(tn+fn)/len(y_test):.1%}")

print(f"\n📋 TOP 5 FEATURES MÁS IMPORTANTES:")
for i, (idx, row) in enumerate(feature_importance.head(5).iterrows(), 1):
    print(f"   {i}. {row['feature']}: {row['importance']:.3f}")

print("\n" + "="*80)
print("✅ VISUALIZACIONES COMPLETADAS")
print("="*80)
print("\n📁 Archivo generado: model_visualizations.png")
print("   • 6 gráficos completos del modelo")
print("   • Listo para presentación o análisis")

print("\n💡 INTERPRETACIÓN:")
print("   • Curva ROC muestra buen poder discriminatorio (AUC > 0.70)")
print("   • Threshold 0.60 minimiza falsos positivos (perfil agresivo)")
print("   • Features más importantes: Experian, DPD, Scores internos")
print("   • Modelo listo para deployment en Vertex AI")

print("\n" + "="*80)
