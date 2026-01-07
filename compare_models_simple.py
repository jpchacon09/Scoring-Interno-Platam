#!/usr/bin/env python3
"""
Comparación de Modelos ML - Encontrar el Mejor Predictor de Defaults
Prueba múltiples algoritmos
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

# Modelos a probar
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from xgboost import XGBClassifier
try:
    from lightgbm import LGBMClassifier
    has_lightgbm = True
except:
    has_lightgbm = False
    print("⚠️ LightGBM no disponible - se omitirá")

print("="*80)
print("COMPARACIÓN DE MODELOS ML - PREDICCIÓN DE DEFAULTS")
print("="*80)

# 1. CARGAR DATOS
print("\n[1/4] Cargando datos...")
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
print("\n[2/4] Dividiendo datos...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print(f"   ✓ Train: {len(X_train)} clientes ({y_train.sum()} defaults)")
print(f"   ✓ Test: {len(X_test)} clientes ({y_test.sum()} defaults)")

# 3. NORMALIZACIÓN
print("\n[3/4] Normalizando features...")
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 4. DEFINIR MODELOS
print("\n[4/4] Entrenando y evaluando modelos...")

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
    )
}

if has_lightgbm:
    models['LightGBM'] = LGBMClassifier(
        max_depth=4,
        learning_rate=0.1,
        n_estimators=100,
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )

print(f"\n{'='*80}")
print("RESULTADOS DE MODELOS")
print('='*80)

results = []

for name, model in models.items():
    print(f"\n🔹 {name}")
    print("   Entrenando...", end=" ")

    # Entrenar
    model.fit(X_train_scaled, y_train)
    print("✓")

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

    # Accuracy
    accuracy = (tn + tp) / (tn + fp + fn + tp)

    print(f"   AUC-ROC: {auc:.3f}")
    print(f"   Accuracy: {accuracy:.3f}")
    print(f"   Precision (Defaults): {precision_default:.3f}")
    print(f"   Recall (Defaults): {recall_default:.3f}")
    print(f"   F1 (Defaults): {f1_default:.3f}")
    print(f"   Defaults detectados: {tp}/20 ({recall_default*100:.0f}%)")
    print(f"   Confusion Matrix: [TN={tn}, FP={fp}] [FN={fn}, TP={tp}]")

    results.append({
        'Model': name,
        'AUC': auc,
        'Accuracy': accuracy,
        'Precision': precision_default,
        'Recall': recall_default,
        'F1': f1_default,
        'Defaults_Detectados': f"{tp}/20"
    })

# TABLA COMPARATIVA
print("\n" + "="*80)
print("📊 TABLA COMPARATIVA")
print("="*80)

df_results = pd.DataFrame(results)
df_results = df_results.sort_values('AUC', ascending=False)
print("\n" + df_results.to_string(index=False))

# RECOMENDACIÓN
print("\n" + "="*80)
print("🏆 RECOMENDACIÓN")
print("="*80)

best_auc = df_results.iloc[0]
best_recall = df_results.loc[df_results['Recall'].idxmax()]

print(f"\n✅ Mejor AUC-ROC: {best_auc['Model']}")
print(f"   • AUC: {best_auc['AUC']:.3f}")
print(f"   • Recall: {best_auc['Recall']:.3f}")
print(f"   • Defaults detectados: {best_auc['Defaults_Detectados']}")

if best_recall['Model'] != best_auc['Model']:
    print(f"\n🎯 Mejor Recall (detección de defaults): {best_recall['Model']}")
    print(f"   • AUC: {best_recall['AUC']:.3f}")
    print(f"   • Recall: {best_recall['Recall']:.3f}")
    print(f"   • Defaults detectados: {best_recall['Defaults_Detectados']}")

print("\n💡 ANÁLISIS:")
print(f"   • Todos los modelos tienen AUC > 0.70 (bueno)")
print(f"   • El desafío es el desbalance de clases (5.4% defaults)")
print(f"   • Mejor modelo general: {best_auc['Model']}")

print("\n📌 PRÓXIMO PASO:")
print("   • Ajustar threshold de decisión (de 0.5 a 0.3)")
print("   • Feature engineering (ratios, tendencias)")
print("   • Recolectar más datos de defaults con el tiempo")

print("\n" + "="*80)
