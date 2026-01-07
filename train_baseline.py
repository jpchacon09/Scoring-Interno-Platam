#!/usr/bin/env python3
"""
Entrenamiento Baseline - Modelo de Predicción de Defaults
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# 1. CARGAR DATOS
print("Cargando datos...")
df = pd.read_csv('ml_training_data.csv')

# 2. SELECCIONAR FEATURES
# Excluir: cedula (ID), client_type (categórica), ratings (derivados de scores)
feature_cols = [
    'platam_score', 'experian_score_normalized',
    'score_payment_performance', 'score_payment_plan', 'score_deterioration',
    'payment_count', 'months_as_client',
    'days_past_due_mean', 'days_past_due_max',
    'pct_early', 'pct_late',
    'peso_platam_usado', 'peso_hcpn_usado',
    'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
]

# Filtrar features disponibles
feature_cols = [col for col in feature_cols if col in df.columns]

X = df[feature_cols].fillna(0)  # Imputar NaN con 0
y = df['default_flag']

print(f"Features: {len(feature_cols)}")
print(f"Clientes: {len(df)}")
print(f"Defaults: {y.sum()} ({y.sum()/len(y)*100:.1f}%)")

# 3. TRAIN/TEST SPLIT
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print(f"\nTrain: {len(X_train)} clientes ({y_train.sum()} defaults)")
print(f"Test: {len(X_test)} clientes ({y_test.sum()} defaults)")

# 4. NORMALIZACIÓN
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. ENTRENAR XGBOOST
print("\nEntrenando XGBoost...")

# Calcular scale_pos_weight para balancear clases
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

# 6. EVALUAR
print("\n" + "="*60)
print("EVALUACIÓN EN TEST SET")
print("="*60)

# Predicciones
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
y_pred = model.predict(X_test_scaled)

# AUC-ROC
auc = roc_auc_score(y_test, y_pred_proba)
print(f"\nAUC-ROC: {auc:.3f}")

# Classification Report
print("\n" + classification_report(y_test, y_pred))

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred)
print(f"\nConfusion Matrix:")
print(f"TN: {cm[0,0]}  FP: {cm[0,1]}")
print(f"FN: {cm[1,0]}  TP: {cm[1,1]}")

# 7. FEATURE IMPORTANCE
print("\n" + "="*60)
print("FEATURE IMPORTANCE")
print("="*60)

feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(feature_importance.head(10))

# Guardar gráfico
plt.figure(figsize=(10, 6))
plt.barh(feature_importance['feature'][:10], feature_importance['importance'][:10])
plt.xlabel('Importance')
plt.title('Top 10 Features')
plt.tight_layout()
plt.savefig('feature_importance.png', dpi=150)
print("\nGráfico guardado: feature_importance.png")

# 8. GUARDAR MODELO
import joblib
joblib.dump(model, 'xgboost_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("\nModelo guardado: xgboost_model.pkl")
print("Scaler guardado: scaler.pkl")
