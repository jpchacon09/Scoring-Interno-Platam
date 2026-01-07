#!/usr/bin/env python3
"""
Comparación de Modelos ML - Encontrar el Mejor Predictor de Defaults
Prueba múltiples algoritmos con y sin SMOTE
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix, precision_recall_curve
from imblearn.over_sampling import SMOTE
import warnings
warnings.filterwarnings('ignore')

# Modelos a probar
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

print("="*80)
print("COMPARACIÓN DE MODELOS ML - PREDICCIÓN DE DEFAULTS")
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

print(f"   ✓ {len(df)} clientes")
print(f"   ✓ {y.sum()} defaults ({y.sum()/len(y)*100:.1f}%)")
print(f"   ✓ {len(feature_cols)} features")

# 2. TRAIN/TEST SPLIT
print("\n[2/5] Dividiendo datos...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print(f"   ✓ Train: {len(X_train)} clientes ({y_train.sum()} defaults)")
print(f"   ✓ Test: {len(X_test)} clientes ({y_test.sum()} defaults)")

# 3. NORMALIZACIÓN
print("\n[3/5] Normalizando features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. DEFINIR MODELOS
print("\n[4/5] Preparando modelos...")

scale_pos_weight = len(y_train[y_train==0]) / len(y_train[y_train==1])

models = {
    'Logistic Regression': LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        random_state=42
    ),
    'Random Forest': RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        random_state=42
    ),
    'XGBoost': XGBClassifier(
        max_depth=4,
        learning_rate=0.1,
        n_estimators=100,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric='auc'
    ),
    'LightGBM': LGBMClassifier(
        max_depth=4,
        learning_rate=0.1,
        n_estimators=100,
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )
}

print(f"   ✓ {len(models)} modelos configurados")

# 5. ENTRENAR Y EVALUAR
print("\n[5/5] Entrenando y evaluando modelos...")
print("\n" + "="*80)
print("RESULTADOS SIN SMOTE")
print("="*80)

results_no_smote = []

for name, model in models.items():
    print(f"\n🔹 {name}")

    # Entrenar
    model.fit(X_train_scaled, y_train)

    # Predecir
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)

    # Métricas
    auc = roc_auc_score(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred)

    # Calcular precision y recall manualmente para defaults
    tn, fp, fn, tp = cm.ravel()
    precision_default = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall_default = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_default = 2 * (precision_default * recall_default) / (precision_default + recall_default) if (precision_default + recall_default) > 0 else 0

    print(f"   AUC-ROC: {auc:.3f}")
    print(f"   Precision (Defaults): {precision_default:.3f}")
    print(f"   Recall (Defaults): {recall_default:.3f}")
    print(f"   F1 (Defaults): {f1_default:.3f}")
    print(f"   Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    results_no_smote.append({
        'Model': name,
        'AUC': auc,
        'Precision': precision_default,
        'Recall': recall_default,
        'F1': f1_default,
        'TP': tp,
        'FN': fn
    })

# 6. ENTRENAR CON SMOTE
print("\n" + "="*80)
print("RESULTADOS CON SMOTE (Balanceo de Clases)")
print("="*80)

# Aplicar SMOTE
print("\n⚡ Aplicando SMOTE...")
smote = SMOTE(random_state=42)
X_train_smote, y_train_smote = smote.fit_resample(X_train_scaled, y_train)

print(f"   ✓ Train original: {len(y_train)} clientes ({y_train.sum()} defaults)")
print(f"   ✓ Train con SMOTE: {len(y_train_smote)} clientes ({y_train_smote.sum()} defaults)")

results_smote = []

for name, model in models.items():
    print(f"\n🔹 {name} + SMOTE")

    # Recrear modelo (para tener fresh start)
    if name == 'Logistic Regression':
        model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    elif name == 'Random Forest':
        model = RandomForestClassifier(n_estimators=100, max_depth=6, class_weight='balanced', random_state=42, n_jobs=-1)
    elif name == 'Gradient Boosting':
        model = GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
    elif name == 'XGBoost':
        model = XGBClassifier(max_depth=4, learning_rate=0.1, n_estimators=100, random_state=42, eval_metric='auc')
    elif name == 'LightGBM':
        model = LGBMClassifier(max_depth=4, learning_rate=0.1, n_estimators=100, random_state=42, verbose=-1)

    # Entrenar con datos balanceados
    model.fit(X_train_smote, y_train_smote)

    # Predecir en test set ORIGINAL (sin SMOTE)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)

    # Métricas
    auc = roc_auc_score(y_test, y_pred_proba)
    cm = confusion_matrix(y_test, y_pred)

    tn, fp, fn, tp = cm.ravel()
    precision_default = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall_default = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1_default = 2 * (precision_default * recall_default) / (precision_default + recall_default) if (precision_default + recall_default) > 0 else 0

    print(f"   AUC-ROC: {auc:.3f}")
    print(f"   Precision (Defaults): {precision_default:.3f}")
    print(f"   Recall (Defaults): {recall_default:.3f}")
    print(f"   F1 (Defaults): {f1_default:.3f}")
    print(f"   Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    results_smote.append({
        'Model': name,
        'AUC': auc,
        'Precision': precision_default,
        'Recall': recall_default,
        'F1': f1_default,
        'TP': tp,
        'FN': fn
    })

# 7. TABLA COMPARATIVA
print("\n" + "="*80)
print("TABLA COMPARATIVA FINAL")
print("="*80)

print("\n📊 SIN SMOTE:")
df_no_smote = pd.DataFrame(results_no_smote)
df_no_smote = df_no_smote.sort_values('AUC', ascending=False)
print(df_no_smote.to_string(index=False))

print("\n📊 CON SMOTE:")
df_smote = pd.DataFrame(results_smote)
df_smote = df_smote.sort_values('AUC', ascending=False)
print(df_smote.to_string(index=False))

# 8. RECOMENDACIÓN
print("\n" + "="*80)
print("🏆 RECOMENDACIÓN")
print("="*80)

# Mejor modelo sin SMOTE (por AUC)
best_no_smote = df_no_smote.iloc[0]
print(f"\n✅ Mejor modelo SIN SMOTE: {best_no_smote['Model']}")
print(f"   • AUC: {best_no_smote['AUC']:.3f}")
print(f"   • Recall: {best_no_smote['Recall']:.3f} ({int(best_no_smote['TP'])}/20 defaults detectados)")

# Mejor modelo con SMOTE (por AUC)
best_smote = df_smote.iloc[0]
print(f"\n✅ Mejor modelo CON SMOTE: {best_smote['Model']}")
print(f"   • AUC: {best_smote['AUC']:.3f}")
print(f"   • Recall: {best_smote['Recall']:.3f} ({int(best_smote['TP'])}/20 defaults detectados)")

# Comparación
print("\n💡 ANÁLISIS:")
if best_smote['AUC'] > best_no_smote['AUC']:
    print(f"   • SMOTE mejora el AUC en {(best_smote['AUC'] - best_no_smote['AUC']):.3f}")
    print(f"   • RECOMENDACIÓN: Usar {best_smote['Model']} + SMOTE")
else:
    print(f"   • Sin SMOTE tiene mejor AUC")
    print(f"   • RECOMENDACIÓN: Usar {best_no_smote['Model']} sin SMOTE")

# Mejor recall
best_recall = max(results_no_smote + results_smote, key=lambda x: x['Recall'])
print(f"\n🎯 Modelo con mejor detección de defaults: {best_recall['Model']}")
print(f"   • Recall: {best_recall['Recall']:.3f} ({int(best_recall['TP'])}/20 defaults detectados)")
print(f"   • AUC: {best_recall['AUC']:.3f}")

print("\n" + "="*80)
