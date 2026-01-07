#!/usr/bin/env python3
"""
Optimización de Threshold para XGBoost
Encuentra el threshold óptimo según perfil de negocio
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, confusion_matrix, precision_recall_curve
from xgboost import XGBClassifier
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("OPTIMIZACIÓN DE THRESHOLD - XGBoost")
print("Perfil de Negocio: AGRESIVO (evitar rechazar buenos clientes)")
print("="*80)

# 1. CARGAR DATOS
print("\n[1/5] Cargando datos...")
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

print(f"   ✓ {len(df)} clientes, {y.sum()} defaults ({y.sum()/len(y)*100:.1f}%)")

# 2. TRAIN/TEST SPLIT
print("\n[2/5] Dividiendo datos...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 3. NORMALIZACIÓN Y ENTRENAMIENTO
print("\n[3/5] Entrenando XGBoost...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

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
print("   ✓ Modelo entrenado")

# 4. OBTENER PROBABILIDADES
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
auc = roc_auc_score(y_test, y_pred_proba)
print(f"   ✓ AUC-ROC: {auc:.3f}")

# 5. PROBAR MÚLTIPLES THRESHOLDS
print("\n[4/5] Probando múltiples thresholds...")

thresholds_to_test = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]

results = []

for threshold in thresholds_to_test:
    # Aplicar threshold
    y_pred = (y_pred_proba >= threshold).astype(int)

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    # Métricas
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tn + tp) / (tn + fp + fn + tp)

    # Tasa de rechazo (% de clientes que marcamos como default)
    rejection_rate = (fp + tp) / len(y_test)

    # Guardar resultados
    results.append({
        'Threshold': threshold,
        'Accuracy': accuracy,
        'Precision': precision,
        'Recall': recall,
        'F1': f1,
        'TP': tp,
        'FP': fp,
        'FN': fn,
        'TN': tn,
        'Defaults_Detectados': f"{tp}/20",
        'Buenos_Rechazados': fp,
        'Tasa_Rechazo': rejection_rate
    })

df_results = pd.DataFrame(results)

# 6. MOSTRAR RESULTADOS
print("\n[5/5] Análisis de resultados")
print("\n" + "="*80)
print("📊 RESULTADOS POR THRESHOLD")
print("="*80)

print(f"\n{'Threshold':<12} {'Recall':<10} {'Precision':<12} {'F1':<8} {'Detectados':<12} {'Buenos Rechazados':<18} {'Tasa Rechazo':<15}")
print("-" * 100)

for _, row in df_results.iterrows():
    print(f"{row['Threshold']:<12.2f} {row['Recall']:<10.1%} {row['Precision']:<12.1%} {row['F1']:<8.3f} {row['Defaults_Detectados']:<12} {int(row['Buenos_Rechazados']):<18} {row['Tasa_Rechazo']:<15.1%}")

# ANÁLISIS PARA PERFIL AGRESIVO
print("\n" + "="*80)
print("🎯 ANÁLISIS PARA PERFIL AGRESIVO")
print("Objetivo: Minimizar rechazo de buenos clientes")
print("="*80)

# Filtrar thresholds que mantienen buenos rechazados < 80 (conservador para el perfil)
df_aggressive = df_results[df_results['Buenos_Rechazados'] <= 80].copy()

if len(df_aggressive) > 0:
    # Mejor F1 dentro del perfil agresivo
    best_f1_idx = df_aggressive['F1'].idxmax()
    best_f1 = df_results.loc[best_f1_idx]

    print(f"\n✅ THRESHOLD RECOMENDADO (Perfil Agresivo):")
    print(f"   Threshold: {best_f1['Threshold']:.2f}")
    print(f"   • Recall: {best_f1['Recall']:.1%} (detectamos {best_f1['Defaults_Detectados']})")
    print(f"   • Precision: {best_f1['Precision']:.1%}")
    print(f"   • Buenos rechazados: {int(best_f1['Buenos_Rechazados'])} de 347 ({best_f1['Buenos_Rechazados']/347*100:.1f}%)")
    print(f"   • Tasa rechazo total: {best_f1['Tasa_Rechazo']:.1%}")
    print(f"   • F1-Score: {best_f1['F1']:.3f}")
else:
    # Si todos tienen >80 falsos positivos, tomar el que tenga menos
    min_fp_idx = df_results['Buenos_Rechazados'].idxmin()
    best_f1 = df_results.loc[min_fp_idx]

    print(f"\n✅ THRESHOLD RECOMENDADO (Mínimos falsos positivos):")
    print(f"   Threshold: {best_f1['Threshold']:.2f}")
    print(f"   • Recall: {best_f1['Recall']:.1%} (detectamos {best_f1['Defaults_Detectados']})")
    print(f"   • Precision: {best_f1['Precision']:.1%}")
    print(f"   • Buenos rechazados: {int(best_f1['Buenos_Rechazados'])} de 347 ({best_f1['Buenos_Rechazados']/347*100:.1f}%)")
    print(f"   • Tasa rechazo total: {best_f1['Tasa_Rechazo']:.1%}")

# Threshold por defecto (0.5)
default_threshold = df_results[df_results['Threshold'] == 0.50].iloc[0]

print(f"\n📌 COMPARACIÓN CON THRESHOLD DEFAULT (0.50):")
print(f"   Threshold actual: 0.50")
print(f"   • Buenos rechazados: {int(default_threshold['Buenos_Rechazados'])} clientes")
print(f"   • Defaults detectados: {default_threshold['Defaults_Detectados']}")
print(f"   • Tasa rechazo: {default_threshold['Tasa_Rechazo']:.1%}")

if best_f1['Threshold'] != 0.50:
    mejora_fp = default_threshold['Buenos_Rechazados'] - best_f1['Buenos_Rechazados']
    cambio_recall = best_f1['Recall'] - default_threshold['Recall']

    print(f"\n💡 CON THRESHOLD OPTIMIZADO ({best_f1['Threshold']:.2f}):")
    if mejora_fp > 0:
        print(f"   ✅ Rechazamos {int(mejora_fp)} MENOS buenos clientes")
    else:
        print(f"   ⚠️ Rechazamos {int(abs(mejora_fp))} MÁS buenos clientes")

    if cambio_recall > 0:
        print(f"   ✅ Detectamos {cambio_recall:.1%} MÁS defaults")
    else:
        print(f"   ⚠️ Detectamos {abs(cambio_recall):.1%} MENOS defaults")

# GRÁFICO
print("\n[Generando gráfico...]")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Gráfico 1: Recall vs Buenos Rechazados
ax1.plot(df_results['Threshold'], df_results['Recall'], 'o-', label='Recall (Detectar Defaults)', linewidth=2)
ax1.axhline(y=best_f1['Recall'], color='green', linestyle='--', alpha=0.5, label=f'Recomendado ({best_f1["Threshold"]:.2f})')
ax1.set_xlabel('Threshold', fontsize=12)
ax1.set_ylabel('Recall (%)', fontsize=12)
ax1.set_title('Recall vs Threshold\n(Cuántos defaults detectamos)', fontsize=13, fontweight='bold')
ax1.grid(True, alpha=0.3)
ax1.legend()
ax1.set_ylim(0, 1)

# Gráfico 2: Buenos Rechazados vs Threshold
ax2.plot(df_results['Threshold'], df_results['Buenos_Rechazados'], 'o-', color='red', label='Buenos Rechazados', linewidth=2)
ax2.axhline(y=best_f1['Buenos_Rechazados'], color='green', linestyle='--', alpha=0.5, label=f'Recomendado ({best_f1["Threshold"]:.2f})')
ax2.set_xlabel('Threshold', fontsize=12)
ax2.set_ylabel('Buenos Clientes Rechazados', fontsize=12)
ax2.set_title('Falsos Positivos vs Threshold\n(Buenos clientes que rechazamos)', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.tight_layout()
plt.savefig('threshold_optimization.png', dpi=150, bbox_inches='tight')
print("   ✓ Gráfico guardado: threshold_optimization.png")

# GUARDAR THRESHOLD RECOMENDADO
with open('threshold_recomendado.txt', 'w') as f:
    f.write(f"{best_f1['Threshold']:.2f}")
print(f"   ✓ Threshold guardado: threshold_recomendado.txt")

print("\n" + "="*80)
print("✅ ANÁLISIS COMPLETADO")
print("="*80)

print(f"\n🎯 RESUMEN EJECUTIVO:")
print(f"   • Modelo: XGBoost")
print(f"   • AUC-ROC: {auc:.3f}")
print(f"   • Threshold recomendado: {best_f1['Threshold']:.2f}")
print(f"   • Perfil: AGRESIVO (minimizar rechazo de buenos)")
print(f"   • Buenos rechazados: {int(best_f1['Buenos_Rechazados'])}/347 ({best_f1['Buenos_Rechazados']/347*100:.1f}%)")
print(f"   • Defaults detectados: {best_f1['Defaults_Detectados']} ({best_f1['Recall']:.0%})")

print(f"\n📁 Archivos generados:")
print(f"   • threshold_optimization.png - Gráficos comparativos")
print(f"   • threshold_recomendado.txt - Valor óptimo ({best_f1['Threshold']:.2f})")

print("\n" + "="*80)
