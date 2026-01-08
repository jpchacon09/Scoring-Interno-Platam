"""
API de Scoring con Actualización Automática desde Cloud Storage

Características:
- Carga CSV desde Cloud Storage al iniciar
- Fallback a base de datos si cliente no existe en CSV
- Endpoint para forzar recarga del CSV
- Monitoreo de freshness de datos

Deploy:
docker build -t gcr.io/platam-analytics/scoring-api:auto-update .
gcloud run deploy scoring-api --image gcr.io/platam-analytics/scoring-api:auto-update
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pandas as pd
import os

from google.cloud import storage
from google.cloud import aiplatform
from google.cloud import bigquery

# ==============================================================
# CONFIGURACIÓN
# ==============================================================

app = FastAPI(
    title="PLATAM Scoring API - Auto Update",
    description="API con actualización automática de datos",
    version="2.0"
)

# Cloud Storage
PROJECT_ID = os.getenv("PROJECT_ID", "platam-analytics")
BUCKET_NAME = os.getenv("BUCKET_NAME", "platam-scoring-data")
CSV_FILENAME = os.getenv("CSV_FILENAME", "hybrid_scores.csv")

# Vertex AI
REGION = "us-central1"
ENDPOINT_ID = "3426032820691755008"

# Estado global
df_clientes = None
last_update = None
endpoint = None

# ==============================================================
# CARGA INICIAL
# ==============================================================

print("="*80)
print("🚀 PLATAM Scoring API v2.0 - Auto Update")
print("="*80)

def load_csv_from_cloud_storage():
    """Carga CSV desde Cloud Storage"""
    global df_clientes, last_update

    try:
        print(f"\n📂 Cargando desde: gs://{BUCKET_NAME}/{CSV_FILENAME}")

        # Inicializar cliente de Storage
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(CSV_FILENAME)

        # Descargar como string
        csv_content = blob.download_as_text()

        # Cargar en DataFrame
        from io import StringIO
        df_clientes = pd.read_csv(StringIO(csv_content))

        # Limpiar
        df_clientes.columns = df_clientes.columns.str.strip()
        df_clientes['cedula'] = df_clientes['cedula'].astype(str)

        # Metadata del blob
        blob.reload()
        last_update = blob.updated

        print(f"✅ Cargados {len(df_clientes)} clientes")
        print(f"📅 Última actualización: {last_update}")
        print(f"📊 Columnas disponibles: {len(df_clientes.columns)}")

        # Mostrar estadísticas
        if 'calculation_date' in df_clientes.columns:
            calc_date = df_clientes['calculation_date'].iloc[0]
            print(f"📆 Fecha de cálculo: {calc_date}")

        return True

    except Exception as e:
        print(f"❌ Error al cargar CSV: {e}")
        print("⚠️  API funcionará solo con fallback a base de datos")
        return False


def connect_vertex_ai():
    """Conecta con Vertex AI"""
    global endpoint

    try:
        print(f"\n🌐 Conectando con Vertex AI...")
        aiplatform.init(project=PROJECT_ID, location=REGION)
        endpoint = aiplatform.Endpoint(
            endpoint_name=f"projects/741488896424/locations/{REGION}/endpoints/{ENDPOINT_ID}"
        )
        print(f"✅ Conectado al endpoint: {ENDPOINT_ID}")
        return True
    except Exception as e:
        print(f"❌ Error al conectar con Vertex AI: {e}")
        return False


# Inicialización
csv_loaded = load_csv_from_cloud_storage()
vertex_connected = connect_vertex_ai()

print("\n" + "="*80)
print("✅ API lista para recibir requests")
print("="*80 + "\n")

# ==============================================================
# MODELOS DE DATOS
# ==============================================================

class ClientRequest(BaseModel):
    cedula: Optional[str] = None
    client_id: Optional[str] = None

class ScoringData(BaseModel):
    platam_score: float
    experian_score: float
    hybrid_score: float
    hybrid_category: str
    peso_platam: float
    peso_experian: float

class MLPrediction(BaseModel):
    probability_default: float
    probability_no_default: float
    risk_level: str
    attention_level: str

class Recommendation(BaseModel):
    action_plan: str
    priority: str
    reason: str
    requires_follow_up: bool
    flags: list

class ClientInfo(BaseModel):
    cedula: str
    client_name: Optional[str]
    months_as_client: int
    payment_count: int
    has_payment_history: bool
    data_source: str  # 'cache' o 'database'

class CompleteResponse(BaseModel):
    client_info: ClientInfo
    timestamp: str
    data_freshness: str  # Hace cuánto se actualizaron los datos
    scoring: ScoringData
    ml_prediction: MLPrediction
    recommendation: Recommendation

# ==============================================================
# FUNCIONES AUXILIARES
# ==============================================================

def get_client_from_cache(cedula: str) -> dict:
    """Busca cliente en caché (CSV)"""
    global df_clientes

    if df_clientes is None:
        return None

    client = df_clientes[df_clientes['cedula'] == cedula]

    if len(client) == 0:
        return None

    return client.iloc[0].to_dict()


def get_client_from_database(cedula: str) -> dict:
    """
    Fallback: Busca cliente en base de datos si no está en caché

    IMPORTANTE: Implementa la lógica de conexión a tu BD aquí
    """

    print(f"⚠️  Cliente {cedula} no encontrado en caché, consultando BD...")

    # TODO: Implementar query a tu base de datos
    # Ejemplo con BigQuery:
    """
    client = bigquery.Client(project=PROJECT_ID)

    query = f'''
    SELECT
        cedula,
        client_name,
        platam_score,
        experian_score_normalized,
        months_as_client,
        payment_count,
        ... (todas las columnas necesarias)
    FROM clientes_scoring
    WHERE cedula = '{cedula}'
    LIMIT 1
    '''

    df = client.query(query).to_dataframe()

    if len(df) == 0:
        return None

    return df.iloc[0].to_dict()
    """

    # Por ahora, retornar None (cliente no encontrado)
    return None


def get_client_by_cedula(cedula: str) -> tuple:
    """
    Busca cliente primero en caché, luego en BD si es necesario

    Returns:
        (client_data: dict, source: str)
    """

    # 1. Intentar desde caché
    client_data = get_client_from_cache(cedula)
    if client_data:
        return client_data, 'cache'

    # 2. Fallback a base de datos
    client_data = get_client_from_database(cedula)
    if client_data:
        return client_data, 'database'

    # 3. Cliente no encontrado
    raise HTTPException(
        status_code=404,
        detail=f"Cliente con cédula {cedula} no encontrado ni en caché ni en base de datos"
    )


def get_ml_prediction(client_data: dict) -> tuple:
    """Obtiene predicción del modelo ML en Vertex AI"""

    feature_order = [
        'platam_score', 'experian_score_normalized',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'payment_count', 'months_as_client',
        'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late',
        'peso_platam_usado', 'peso_hcpn_usado',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]

    instance = []
    for feature in feature_order:
        value = client_data.get(feature, 0)
        if pd.isna(value):
            value = 0
        if isinstance(value, bool):
            value = int(value)
        instance.append(float(value))

    prediction = endpoint.predict(instances=[instance])

    prob_no_default = prediction.predictions[0][0]
    prob_default = prediction.predictions[0][1]

    return prob_default, prob_no_default


def calculate_risk_level(prob_default: float) -> str:
    """Categoriza el nivel de riesgo"""
    if prob_default < 0.10:
        return "Muy Bajo"
    elif prob_default < 0.20:
        return "Bajo"
    elif prob_default < 0.40:
        return "Medio"
    elif prob_default < 0.60:
        return "Alto"
    else:
        return "Muy Alto"


def get_attention_level(prob_default: float) -> str:
    """Determina el nivel de atención según probabilidad de default"""
    if prob_default >= 0.60:
        return "Alerta crítica"
    elif prob_default >= 0.40:
        return "Seguimiento cercano"
    elif prob_default >= 0.20:
        return "Atención moderada"
    else:
        return "Monitoreo normal"


def categorize_hybrid_score(score: float) -> str:
    """Categoriza el score híbrido"""
    if score >= 750:
        return "Excelente"
    elif score >= 650:
        return "Bueno"
    elif score >= 550:
        return "Medio"
    elif score >= 450:
        return "Regular"
    else:
        return "Bajo"


def generate_recommendation(client_data: dict, ml_data: dict) -> dict:
    """Genera recomendación de seguimiento y cobranza"""
    # (Misma lógica que en api_scoring_cedula.py)
    # ... código omitido por brevedad ...
    pass  # Copiar función completa de api_scoring_cedula.py


def calculate_data_freshness() -> str:
    """Calcula hace cuánto se actualizaron los datos"""
    global last_update

    if last_update is None:
        return "Desconocido"

    now = datetime.now(last_update.tzinfo)
    delta = now - last_update

    if delta.days > 0:
        return f"Hace {delta.days} día(s)"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"Hace {hours} hora(s)"
    else:
        minutes = delta.seconds // 60
        return f"Hace {minutes} minuto(s)"


# ==============================================================
# ENDPOINTS
# ==============================================================

@app.get("/")
def root():
    return {
        "message": "PLATAM Scoring API v2.0 - Auto Update",
        "status": "online",
        "version": "2.0",
        "features": [
            "Actualización automática desde Cloud Storage",
            "Fallback a base de datos",
            "Recarga manual de datos"
        ]
    }


@app.post("/predict", response_model=CompleteResponse)
async def predict_by_cedula(request: ClientRequest):
    """
    Predice riesgo de default de un cliente

    Busca primero en caché (CSV actualizado semanalmente),
    si no existe hace fallback a base de datos
    """

    if not request.cedula and not request.client_id:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar cedula o client_id"
        )

    cedula = request.cedula or request.client_id

    try:
        # 1. Buscar cliente (caché o BD)
        client_data, source = get_client_by_cedula(cedula)

        print(f"📋 Cliente encontrado en: {source}")

        # 2. Extraer datos de scoring
        scoring_data = {
            'platam_score': float(client_data.get('platam_score', 0)),
            'experian_score': float(client_data.get('experian_score_normalized', 0)),
            'hybrid_score': float(client_data.get('hybrid_score', 0)),
            'hybrid_category': categorize_hybrid_score(client_data.get('hybrid_score', 0)),
            'peso_platam': float(client_data.get('peso_platam_usado', 0)),
            'peso_experian': float(client_data.get('peso_hcpn_usado', 0))
        }

        # 3. Obtener predicción ML
        prob_default, prob_no_default = get_ml_prediction(client_data)

        ml_data = {
            'probability_default': prob_default,
            'probability_no_default': prob_no_default,
            'risk_level': calculate_risk_level(prob_default),
            'attention_level': get_attention_level(prob_default)
        }

        # 4. Generar recomendación
        recommendation = generate_recommendation(client_data, ml_data)

        # 5. Información del cliente
        client_name = client_data.get('client_name', 'N/A')
        if pd.isna(client_name):
            client_name = 'N/A'

        months = client_data.get('months_as_client', 0)
        if pd.isna(months):
            months = 0

        payment_count = client_data.get('payment_count', 0)
        if pd.isna(payment_count):
            payment_count = 0

        client_info = ClientInfo(
            cedula=cedula,
            client_name=client_name,
            months_as_client=int(months),
            payment_count=int(payment_count),
            has_payment_history=client_data.get('has_payment_history', False),
            data_source=source
        )

        # 6. Response completa
        return CompleteResponse(
            client_info=client_info,
            timestamp=datetime.now().isoformat(),
            data_freshness=calculate_data_freshness(),
            scoring=ScoringData(**scoring_data),
            ml_prediction=MLPrediction(**ml_data),
            recommendation=Recommendation(**recommendation)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.post("/reload")
async def reload_data():
    """
    Fuerza recarga de datos desde Cloud Storage

    Útil si quieres actualizar sin esperar al cold start
    """

    success = load_csv_from_cloud_storage()

    if success:
        return {
            "status": "success",
            "message": f"Datos recargados: {len(df_clientes)} clientes",
            "last_update": last_update.isoformat() if last_update else None,
            "freshness": calculate_data_freshness()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error al recargar datos desde Cloud Storage"
        )


@app.get("/health")
def health_check():
    """Verifica estado de la API"""

    return {
        "status": "healthy",
        "data_loaded": df_clientes is not None,
        "vertex_ai": "connected" if endpoint else "disconnected",
        "model": "platam-custom-final",
        "clientes_cache": len(df_clientes) if df_clientes is not None else 0,
        "last_update": last_update.isoformat() if last_update else None,
        "data_freshness": calculate_data_freshness()
    }


@app.get("/stats")
def get_stats():
    """Estadísticas de los datos cargados"""

    if df_clientes is None:
        raise HTTPException(
            status_code=503,
            detail="Datos no cargados"
        )

    return {
        "total_clientes": len(df_clientes),
        "score_promedio": float(df_clientes['hybrid_score'].mean()),
        "score_min": float(df_clientes['hybrid_score'].min()),
        "score_max": float(df_clientes['hybrid_score'].max()),
        "clientes_con_historial": int(df_clientes['has_payment_history'].sum()),
        "last_update": last_update.isoformat() if last_update else None,
        "data_freshness": calculate_data_freshness(),
        "distribucion": {
            "excelente": int((df_clientes['hybrid_score'] >= 750).sum()),
            "bueno": int((df_clientes['hybrid_score'] >= 650).sum() - (df_clientes['hybrid_score'] >= 750).sum()),
            "medio": int((df_clientes['hybrid_score'] >= 550).sum() - (df_clientes['hybrid_score'] >= 650).sum()),
            "regular": int((df_clientes['hybrid_score'] >= 450).sum() - (df_clientes['hybrid_score'] >= 550).sum()),
            "bajo": int((df_clientes['hybrid_score'] < 450).sum()),
        }
    }


# ==============================================================
# RUN
# ==============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
