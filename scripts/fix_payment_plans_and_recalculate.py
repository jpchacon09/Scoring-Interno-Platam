"""
Script para recalcular scores con la lógica correcta de planes de pago
Basado en export-planes_de_pago-30-12-2025.csv

Lógica correcta:
- Status "Activo" → tiene_plan_activo = TRUE → -50 pts
- Status "Pendiente" → NO afecta score → 0 pts
- Status "Default/Cancelado" → tiene_plan_default = TRUE → -100 pts
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent.parent
PLANS_FILE = BASE_DIR / "export-planes_de_pago-30-12-2025.csv"
CLIENTS_FILE = BASE_DIR / "data" / "processed" / "clientes_clean.csv"
SCORES_FILE = BASE_DIR / "data" / "processed" / "platam_scores.csv"
HYBRID_FILE = BASE_DIR / "data" / "processed" / "hybrid_scores.csv"
OUTPUT_FILE = BASE_DIR / "SCORES_V2_ANALISIS_COMPLETO.csv"
STATS_FILE = BASE_DIR / "ESTADISTICAS_SCORES_V2.csv"

print("=" * 80)
print("RECALCULANDO SCORES CON LÓGICA CORRECTA DE PLANES DE PAGO")
print("=" * 80)

# 1. Cargar mapeo de clientes (client_id → cedula)
print("\n[1/10] Cargando mapeo de clientes...")
clientes_df = pd.read_csv(CLIENTS_FILE)
clientes_df['client_id'] = pd.to_numeric(clientes_df['client_id'], errors='coerce')
clientes_df['cedula'] = pd.to_numeric(clientes_df['cedula'], errors='coerce')
# Drop rows with NaN before converting to int
clientes_df = clientes_df.dropna(subset=['client_id', 'cedula'])
clientes_df['client_id'] = clientes_df['client_id'].astype(int)
clientes_df['cedula'] = clientes_df['cedula'].astype(int)
client_to_cedula = dict(zip(clientes_df['client_id'], clientes_df['cedula']))
print(f"   ✓ {len(client_to_cedula)} clientes mapeados (client_id → cedula)")

# 2. Cargar planes de pago
print("\n[2/10] Cargando planes de pago...")
planes_df = pd.read_csv(PLANS_FILE)
print(f"   ✓ {len(planes_df)} planes cargados")

# 3. Convertir client_id a cedula
print("\n[3/10] Convirtiendo client_id a cedula...")
planes_df['client_id'] = pd.to_numeric(planes_df['client_id'], errors='coerce').astype(int)
planes_df['cedula'] = planes_df['client_id'].map(client_to_cedula)

# Remover planes sin mapeo
antes = len(planes_df)
planes_df = planes_df.dropna(subset=['cedula'])
despues = len(planes_df)
planes_df['cedula'] = planes_df['cedula'].astype(int)
print(f"   ✓ client_id convertido a cedula")
print(f"   - Planes con mapeo: {despues}/{antes}")

# Ver distribución de status
print(f"\n   Distribución de status:")
status_counts = planes_df['status'].value_counts()
for status, count in status_counts.items():
    print(f"      {status}: {count}")

# 4. Procesar planes por cliente (ahora agrupados por cedula)
print("\n[4/10] Procesando planes por cliente...")
planes_por_cliente = planes_df.groupby('cedula').agg({
    'status': lambda x: list(x),
    '_ID': 'count'
}).reset_index()
planes_por_cliente.columns = ['cedula', 'lista_status', 'num_planes']

# Determinar flags basados en status
planes_por_cliente['tiene_plan_activo'] = planes_por_cliente['lista_status'].apply(
    lambda statuses: 'Activo' in statuses
)
planes_por_cliente['tiene_plan_default'] = planes_por_cliente['lista_status'].apply(
    lambda statuses: any(s in ['Default', 'Cancelado'] for s in statuses)
)
planes_por_cliente['tiene_plan_pendiente'] = planes_por_cliente['lista_status'].apply(
    lambda statuses: 'Pendiente' in statuses
)

print(f"   ✓ Clientes únicos con planes: {len(planes_por_cliente)}")
print(f"   - Planes activos: {planes_por_cliente['tiene_plan_activo'].sum()}")
print(f"   - Planes default: {planes_por_cliente['tiene_plan_default'].sum()}")
print(f"   - Planes pendientes: {planes_por_cliente['tiene_plan_pendiente'].sum()}")

# 5. Cargar scores actuales
print("\n[5/10] Cargando scores actuales...")
scores_df = pd.read_csv(SCORES_FILE)
print(f"   ✓ {len(scores_df)} clientes cargados")

# Convertir cedula a entero
scores_df['cedula'] = pd.to_numeric(scores_df['cedula'], errors='coerce')
scores_df = scores_df.dropna(subset=['cedula'])
scores_df['cedula'] = scores_df['cedula'].astype(int)
print(f"   ✓ cedula convertido a int: {scores_df['cedula'].dtype}")

# 6. Merge con planes
print("\n[6/10] Haciendo merge con datos de planes...")

# Drop existing plan columns if they exist (for re-runs)
cols_to_drop = ['tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes']
for col in cols_to_drop:
    if col in scores_df.columns:
        scores_df = scores_df.drop(col, axis=1)

scores_df = scores_df.merge(
    planes_por_cliente[['cedula', 'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes']],
    on='cedula',
    how='left'
)

# Rellenar NaN (clientes sin planes)
scores_df['tiene_plan_activo'] = scores_df['tiene_plan_activo'].fillna(False).astype(bool)
scores_df['tiene_plan_default'] = scores_df['tiene_plan_default'].fillna(False).astype(bool)
scores_df['tiene_plan_pendiente'] = scores_df['tiene_plan_pendiente'].fillna(False).astype(bool)
scores_df['num_planes'] = scores_df['num_planes'].fillna(0).astype(int)
print(f"   ✓ Merge completado")
print(f"   - Clientes con al menos un plan: {scores_df['num_planes'].gt(0).sum()}")

# 7. Recalcular componente de Payment Plan
print("\n[7/10] Recalculando componente Payment Plan...")

def calcular_payment_plan_correcto(row):
    """
    Lógica correcta:
    - Base: 150 pts (sin planes o solo planes pendientes)
    - Plan Activo: -50 pts
    - Plan Default/Cancelado: -100 pts
    - Plan Pendiente: NO afecta (0 pts)
    """
    score = 150

    if row['tiene_plan_activo']:
        score -= 50

    if row['tiene_plan_default']:
        score -= 100

    # Pendiente NO afecta el score

    return max(0, min(150, score))

# Guardar componente antiguo para comparación
scores_df['score_payment_plan_old'] = scores_df['score_payment_plan'].copy()

# Calcular nuevo componente
scores_df['score_payment_plan'] = scores_df.apply(calcular_payment_plan_correcto, axis=1)

# Estadísticas del cambio
cambio = scores_df['score_payment_plan'] - scores_df['score_payment_plan_old']
print(f"   ✓ Componente recalculado")
print(f"   - Promedio anterior: {scores_df['score_payment_plan_old'].mean():.2f}")
print(f"   - Promedio nuevo: {scores_df['score_payment_plan'].mean():.2f}")
print(f"   - Cambio promedio: {cambio.mean():+.2f} pts")
print(f"   - Clientes afectados: {(cambio != 0).sum()}")

# 8. Recalcular PLATAM V2.0 total
print("\n[8/10] Recalculando PLATAM V2.0 total...")

# Guardar score antiguo
scores_df['platam_score_old'] = scores_df['platam_score'].copy()

# Recalcular
scores_df['platam_score'] = (
    scores_df['score_payment_performance'] +
    scores_df['score_payment_plan'] +
    scores_df['score_deterioration']
)

# Asegurar rango 0-1000
scores_df['platam_score'] = scores_df['platam_score'].clip(0, 1000)

# Recalcular rating
def get_rating_v2(score):
    if score >= 900: return 'A+'
    elif score >= 800: return 'A'
    elif score >= 700: return 'B+'
    elif score >= 600: return 'B'
    elif score >= 500: return 'C+'
    elif score >= 400: return 'C'
    else: return 'D'

scores_df['platam_rating'] = scores_df['platam_score'].apply(get_rating_v2)

cambio_total = scores_df['platam_score'] - scores_df['platam_score_old']
print(f"   ✓ Score PLATAM V2.0 recalculado")
print(f"   - Promedio anterior: {scores_df['platam_score_old'].mean():.1f}")
print(f"   - Promedio nuevo: {scores_df['platam_score'].mean():.1f}")
print(f"   - Cambio promedio: {cambio_total.mean():+.1f} pts")
print(f"   - Mediana: {scores_df['platam_score'].median():.1f}")
print(f"   - Std: {scores_df['platam_score'].std():.1f}")

# Distribución de ratings
rating_dist = scores_df['platam_rating'].value_counts().sort_index()
print("\n   Distribución de ratings:")
for rating, count in rating_dist.items():
    pct = (count / len(scores_df)) * 100
    print(f"      {rating}: {count:4d} ({pct:5.1f}%)")

# 9. Guardar scores actualizados
print("\n[9/10] Guardando scores actualizados...")

# Remover columnas temporales
scores_df = scores_df.drop(['score_payment_plan_old', 'platam_score_old'], axis=1)

# Actualizar platam_scores.csv
scores_df.to_csv(SCORES_FILE, index=False)
print(f"   ✓ Guardado: {SCORES_FILE.name}")

# 10. Recalcular hybrid scores
print("\n[10/10] Recalculando hybrid scores...")

if HYBRID_FILE.exists():
    hybrid_df = pd.read_csv(HYBRID_FILE, encoding='utf-8-sig')  # Skip BOM if present

    # Actualizar cedula
    hybrid_df['cedula'] = pd.to_numeric(hybrid_df['cedula'], errors='coerce')
    hybrid_df = hybrid_df.dropna(subset=['cedula'])
    hybrid_df['cedula'] = hybrid_df['cedula'].astype(int)

    # Actualizar componentes y scores desde scores_df recalculados
    # Eliminar columnas que vamos a reemplazar, incluyendo duplicados con sufijos _x y _y
    cols_to_drop = [
        'platam_score', 'platam_rating',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes',
        'tiene_plan_activo_x', 'tiene_plan_default_x', 'tiene_plan_pendiente_x', 'num_planes_x',
        'tiene_plan_activo_y', 'tiene_plan_default_y', 'tiene_plan_pendiente_y', 'num_planes_y'
    ]
    hybrid_df = hybrid_df.drop([col for col in cols_to_drop if col in hybrid_df.columns], axis=1)

    hybrid_df = hybrid_df.merge(
        scores_df[[
            'cedula', 'platam_score', 'platam_rating',
            'score_payment_performance', 'score_payment_plan', 'score_deterioration',
            'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
        ]],
        on='cedula',
        how='left'
    )

    # Recalcular hybrid score
    hybrid_df['hybrid_score'] = (
        hybrid_df['peso_platam_usado'] * hybrid_df['platam_score'] +
        hybrid_df['peso_hcpn_usado'] * hybrid_df['experian_score_normalized'].fillna(0)
    )
    hybrid_df['hybrid_score'] = hybrid_df['hybrid_score'].clip(0, 1000)
    hybrid_df['hybrid_rating'] = hybrid_df['hybrid_score'].apply(get_rating_v2)

    # Guardar
    hybrid_df.to_csv(HYBRID_FILE, index=False, encoding='utf-8-sig')
    print(f"   ✓ Guardado: {HYBRID_FILE.name}")

    # Crear CSV completo para analytics
    print(f"\n   Creando CSV de análisis completo...")
    output_df = hybrid_df[[
        'cedula', 'client_name',
        'platam_score', 'experian_score_normalized', 'hybrid_score',
        'platam_rating', 'hybrid_rating',
        'score_payment_performance', 'score_payment_plan', 'score_deterioration',
        'peso_platam_usado', 'peso_hcpn_usado', 'categoria_madurez', 'estrategia_hibrido',
        'payment_count', 'months_as_client', 'days_past_due_mean', 'days_past_due_max',
        'pct_early', 'pct_late',
        'tiene_plan_activo', 'tiene_plan_default', 'tiene_plan_pendiente', 'num_planes'
    ]].copy()

    output_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"   ✓ Guardado: {OUTPUT_FILE.name}")
    print(f"      - Tamaño: {len(output_df)} clientes, {len(output_df.columns)} columnas")

    # Crear estadísticas
    print(f"\n   Creando CSV de estadísticas...")
    from scipy import stats as sp_stats

    stats_data = []
    for col_name, col_data in [
        ('PLATAM V2.0', hybrid_df['platam_score']),
        ('HCPN Normalizado', hybrid_df['experian_score_normalized']),
        ('Score Híbrido', hybrid_df['hybrid_score']),
        ('Payment Performance', hybrid_df['score_payment_performance']),
        ('Payment Plan', hybrid_df['score_payment_plan']),
        ('Deterioration', hybrid_df['score_deterioration'])
    ]:
        valid_data = col_data.dropna()
        stats_data.append({
            'variable': col_name,
            'n': len(valid_data),
            'n_missing': col_data.isna().sum(),
            'mean': valid_data.mean(),
            'median': valid_data.median(),
            'std': valid_data.std(),
            'min': valid_data.min(),
            'q25': valid_data.quantile(0.25),
            'q75': valid_data.quantile(0.75),
            'max': valid_data.max(),
            'skewness': sp_stats.skew(valid_data),
            'kurtosis': sp_stats.kurtosis(valid_data)
        })

    stats_df = pd.DataFrame(stats_data)
    stats_df.to_csv(STATS_FILE, index=False)
    print(f"   ✓ Guardado: {STATS_FILE.name}")

print("\n" + "=" * 80)
print("RECALCULACIÓN COMPLETADA")
print("=" * 80)
print(f"\nRESUMEN FINAL:")
print(f"  • Clientes procesados: {len(scores_df)}")
print(f"  • Clientes con planes: {scores_df['num_planes'].gt(0).sum()}")
print(f"  • Planes activos: {scores_df['tiene_plan_activo'].sum()}")
print(f"  • Planes pendientes: {scores_df['tiene_plan_pendiente'].sum()}")
print(f"  • Planes default: {scores_df['tiene_plan_default'].sum()}")
print(f"\n  • Score PLATAM V2.0 promedio: {scores_df['platam_score'].mean():.1f}")
print(f"  • Score Híbrido promedio: {hybrid_df['hybrid_score'].mean():.1f}")
print(f"\n  • Componente Payment Plan promedio: {scores_df['score_payment_plan'].mean():.2f}/150")
print(f"\n✓ Archivos actualizados:")
print(f"   - {SCORES_FILE.name}")
print(f"   - {HYBRID_FILE.name}")
print(f"   - {OUTPUT_FILE.name}")
print(f"   - {STATS_FILE.name}")
