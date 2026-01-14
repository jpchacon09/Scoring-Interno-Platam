"""
Custom Predictor para Vertex AI - Python 3.11
Compatible con modelo XGBoost 2.0.3
"""

import os
import json
import joblib
import numpy as np
from flask import Flask, request, jsonify

app = Flask(__name__)

# Variables globales para modelo
model = None
scaler = None
feature_names = None

def load_model():
    """Carga modelo desde archivos locales en el container"""
    global model, scaler, feature_names

    print("Loading model from local files...")

    try:
        # Cargar desde archivos copiados en el container
        model = joblib.load("/app/model.pkl")
        scaler = joblib.load("/app/scaler.pkl")

        with open("/app/feature_names.json", 'r') as f:
            feature_names = json.load(f)

        print(f"✓ Model loaded successfully")
        print(f"  Features: {len(feature_names)}")
        print(f"  Model type: {type(model).__name__}")

    except Exception as e:
        print(f"ERROR loading model: {e}")
        raise

@app.route(os.environ.get('AIP_HEALTH_ROUTE', '/health'), methods=['GET'])
def health():
    """Health check endpoint"""
    if model is None:
        return jsonify({'status': 'unhealthy', 'reason': 'Model not loaded'}), 503
    return jsonify({'status': 'healthy'}), 200

@app.route(os.environ.get('AIP_PREDICT_ROUTE', '/predict'), methods=['POST'])
def predict():
    """Prediction endpoint"""
    try:
        # Obtener request
        request_json = request.get_json()

        if not request_json or 'instances' not in request_json:
            return jsonify({'error': 'Missing instances in request'}), 400

        instances = request_json['instances']

        # Convertir a numpy array
        X = np.array(instances, dtype=np.float32)

        # Validar número de features
        if X.shape[1] != len(feature_names):
            return jsonify({
                'error': f'Expected {len(feature_names)} features, got {X.shape[1]}'
            }), 400

        # Normalizar
        X_scaled = scaler.transform(X)

        # Predecir
        predictions = model.predict_proba(X_scaled)

        # Retornar en formato Vertex AI
        return jsonify({
            'predictions': predictions.tolist()
        }), 200

    except Exception as e:
        print(f"ERROR in prediction: {e}")
        return jsonify({'error': str(e)}), 500

# Cargar modelo al iniciar
print("=" * 80)
print("PLATAM Scoring Custom Predictor - Python 3.11")
print("=" * 80)
load_model()
print("✓ Ready to serve predictions")
print("=" * 80)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('AIP_HTTP_PORT', 8080)))
