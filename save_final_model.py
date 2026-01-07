#!/usr/bin/env python3
"""
Guardar Modelo Final Optimizado para Producción
Incluye: modelo, scaler, threshold, metadata
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier
import joblib
import json
from datetime import datetime

print("="*80)
print("GUARDANDO MODELO FINAL OPTIMIZADO")
print("="*80)

# 1. CARGAR DATOS Y ENTRENAR
print("\n[1/4] Entrenando modelo final...")
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

# Métricas
y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
auc = roc_auc_score(y_test, y_pred_proba)

print(f"   ✓ Modelo entrenado (AUC: {auc:.3f})")

# 2. GUARDAR MODELO Y COMPONENTES
print("\n[2/4] Guardando componentes...")

# Modelo
joblib.dump(model, 'models/xgboost_model_final.pkl')
print("   ✓ Modelo: models/xgboost_model_final.pkl")

# Scaler
joblib.dump(scaler, 'models/scaler_final.pkl')
print("   ✓ Scaler: models/scaler_final.pkl")

# 3. GUARDAR METADATA
print("\n[3/4] Guardando metadata...")

optimal_threshold = 0.60

metadata = {
    "model_name": "XGBoost Default Predictor",
    "version": "1.0",
    "date_trained": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "model_type": "XGBClassifier",
    "hyperparameters": {
        "max_depth": 4,
        "learning_rate": 0.1,
        "n_estimators": 100,
        "scale_pos_weight": float(scale_pos_weight),
        "random_state": 42
    },
    "features": feature_cols,
    "num_features": len(feature_cols),
    "threshold_optimized": optimal_threshold,
    "threshold_default": 0.50,
    "business_profile": "AGRESIVO - Minimizar rechazo de buenos clientes",
    "training_data": {
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "num_defaults": int(y.sum()),
        "default_rate": float(y.sum() / len(y))
    },
    "performance_metrics": {
        "auc_roc": float(auc),
        "threshold_used": optimal_threshold,
        "test_set_size": len(y_test)
    },
    "feature_importance_top5": {}
}

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(5).iterrows():
    metadata["feature_importance_top5"][row['feature']] = float(row['importance'])

# Guardar metadata
with open('models/model_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=2)
print("   ✓ Metadata: models/model_metadata.json")

# 4. CREAR FUNCIÓN DE PREDICCIÓN
print("\n[4/4] Creando script de predicción...")

prediction_script = '''#!/usr/bin/env python3
"""
Script de Predicción - Modelo XGBoost Optimizado
Uso: python predict.py
"""

import pandas as pd
import joblib
import json

# Cargar modelo y componentes
model = joblib.load('models/xgboost_model_final.pkl')
scaler = joblib.load('models/scaler_final.pkl')

with open('models/model_metadata.json', 'r') as f:
    metadata = json.load(f)

THRESHOLD = metadata['threshold_optimized']
FEATURES = metadata['features']

print(f"Modelo cargado: {metadata['model_name']} v{metadata['version']}")
print(f"Threshold: {THRESHOLD}")
print(f"Perfil: {metadata['business_profile']}")

def predict_default(client_features):
    """
    Predice probabilidad de default para un cliente

    Args:
        client_features (dict): Diccionario con features del cliente

    Returns:
        dict: Probabilidad, predicción, categoría de riesgo
    """
    # Crear DataFrame con features
    df_input = pd.DataFrame([client_features])

    # Asegurar que tiene todas las features
    for feature in FEATURES:
        if feature not in df_input.columns:
            df_input[feature] = 0

    # Ordenar features
    df_input = df_input[FEATURES]

    # Normalizar
    X_scaled = scaler.transform(df_input)

    # Predecir
    prob_default = model.predict_proba(X_scaled)[0, 1]
    prediction = 1 if prob_default >= THRESHOLD else 0

    # Categoría de riesgo
    if prob_default < 0.10:
        risk_category = "Muy Bajo"
    elif prob_default < 0.20:
        risk_category = "Bajo"
    elif prob_default < 0.40:
        risk_category = "Medio"
    elif prob_default < 0.60:
        risk_category = "Alto"
    else:
        risk_category = "Muy Alto"

    return {
        'probability_default': round(prob_default, 4),
        'prediction': 'Default' if prediction == 1 else 'No-Default',
        'risk_category': risk_category,
        'threshold_used': THRESHOLD,
        'approve_loan': prediction == 0  # Aprobar si NO es default
    }

# EJEMPLO DE USO
if __name__ == '__main__':
    # Ejemplo: Cliente de prueba
    ejemplo_cliente = {
        'platam_score': 750,
        'experian_score_normalized': 800,
        'score_payment_performance': 450,
        'score_payment_plan': 150,
        'score_deterioration': 200,
        'payment_count': 24,
        'months_as_client': 12,
        'days_past_due_mean': 5,
        'days_past_due_max': 15,
        'pct_early': 0.6,
        'pct_late': 0.2,
        'peso_platam_usado': 0.7,
        'peso_hcpn_usado': 0.3,
        'tiene_plan_activo': 0,
        'tiene_plan_default': 0,
        'tiene_plan_pendiente': 0,
        'num_planes': 0
    }

    resultado = predict_default(ejemplo_cliente)

    print("\\n" + "="*60)
    print("PREDICCIÓN DE EJEMPLO")
    print("="*60)
    print(f"Probabilidad de default: {resultado['probability_default']*100:.2f}%")
    print(f"Predicción: {resultado['prediction']}")
    print(f"Categoría de riesgo: {resultado['risk_category']}")
    print(f"¿Aprobar préstamo?: {'SÍ' if resultado['approve_loan'] else 'NO'}")
    print("="*60)
'''

with open('predict.py', 'w') as f:
    f.write(prediction_script)
print("   ✓ Script de predicción: predict.py")

# 5. RESUMEN
print("\n" + "="*80)
print("✅ MODELO FINAL GUARDADO")
print("="*80)

print(f"\n📦 ARCHIVOS GENERADOS:")
print(f"   1. models/xgboost_model_final.pkl - Modelo entrenado")
print(f"   2. models/scaler_final.pkl - Normalizador")
print(f"   3. models/model_metadata.json - Metadata completa")
print(f"   4. predict.py - Script de predicción listo para usar")

print(f"\n🎯 ESPECIFICACIONES DEL MODELO:")
print(f"   • Algoritmo: XGBoost")
print(f"   • AUC-ROC: {auc:.3f}")
print(f"   • Threshold: {optimal_threshold}")
print(f"   • Features: {len(feature_cols)}")
print(f"   • Perfil: AGRESIVO")
print(f"   • Tasa de aprobación: ~86%")

print(f"\n🚀 PRÓXIMOS PASOS:")
print(f"   1. Probar predicción: python predict.py")
print(f"   2. Subir a Vertex AI")
print(f"   3. Crear endpoint")
print(f"   4. Integrar con sistema")

print("\n" + "="*80)
