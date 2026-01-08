"""
Script para monitorear salud del modelo ML

FRECUENCIA: Ejecutar trimestralmente (cada 3 meses)

PROPÓSITO:
- Detectar si el modelo necesita reentrenamiento
- Monitorear data drift (cambios en distribución de datos)
- Alertar sobre degradación de precisión

USO:
    python check_model_drift.py

SALIDA:
- Reporte de salud del modelo
- Alertas de cambios significativos
- Recomendación de reentrenamiento (sí/no)

IMPORTANTE:
Para monitoreo completo, debes actualizar la función check_prediction_accuracy()
con datos reales de predicciones pasadas vs resultados reales.
"""

import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# 1. MONITOREO DE PREDICCIONES vs REALIDAD
# ============================================================

def check_prediction_accuracy():
    """
    Compara las predicciones del modelo con lo que realmente pasó

    Necesitas:
    - Predicciones que hizo el modelo hace 3 meses
    - Datos reales de si esos clientes efectivamente hicieron default
    """

    # Ejemplo conceptual:
    print("="*60)
    print("📊 VERIFICACIÓN DE PRECISIÓN DEL MODELO")
    print("="*60)

    # Esto lo deberías llenar con datos reales
    predicciones_pasadas = {
        'cliente_1': {'pred_default': 0.20, 'real_default': False},  # ✅ Correcto
        'cliente_2': {'pred_default': 0.15, 'real_default': True},   # ❌ Error
        'cliente_3': {'pred_default': 0.75, 'real_default': True},   # ✅ Correcto
        'cliente_4': {'pred_default': 0.10, 'real_default': False},  # ✅ Correcto
    }

    correctos = 0
    total = len(predicciones_pasadas)

    for cliente, data in predicciones_pasadas.items():
        pred = data['pred_default']
        real = data['real_default']

        # Umbral: >40% default se considera "alto riesgo"
        pred_categoria = pred > 0.40

        if pred_categoria == real:
            correctos += 1
            status = "✅"
        else:
            status = "❌"

        print(f"{status} {cliente}: Predicción {pred:.1%} | Real: {real}")

    precision = correctos / total * 100
    print(f"\n📈 Precisión: {precision:.1f}%")

    if precision < 70:
        print("\n⚠️ ALERTA: Modelo necesita reentrenamiento")
    elif precision < 80:
        print("\n⚡ ADVERTENCIA: Monitorear de cerca")
    else:
        print("\n✅ Modelo funcionando bien")

    return precision


# ============================================================
# 2. MONITOREO DE DATA DRIFT
# ============================================================

def check_data_drift(csv_path="data/processed/hybrid_scores.csv"):
    """
    Verifica si la distribución de los datos ha cambiado
    """

    print("\n" + "="*60)
    print("📊 VERIFICACIÓN DE DATA DRIFT")
    print("="*60)

    try:
        df = pd.read_csv(csv_path)

        # Estadísticas actuales
        stats_actuales = {
            'score_promedio': df['hybrid_score'].mean(),
            'score_std': df['hybrid_score'].std(),
            'prob_default_estimada': (df['hybrid_score'] < 600).mean(),
            'clientes_nuevos_pct': (df['months_as_client'] < 3).mean(),
            'mora_promedio': df['days_past_due_mean'].mean()
        }

        # Estadísticas cuando entrenaste (deberías guardar estas)
        stats_entrenamiento = {
            'score_promedio': 687.3,  # Del entrenamiento original
            'score_std': 120.0,
            'prob_default_estimada': 0.15,
            'clientes_nuevos_pct': 0.25,
            'mora_promedio': 8.5
        }

        print("\n📊 Comparación de distribuciones:")
        print("-" * 60)

        alertas = []

        for metrica, valor_actual in stats_actuales.items():
            valor_entrenamiento = stats_entrenamiento.get(metrica, 0)

            if valor_entrenamiento == 0:
                continue

            # Calcular cambio porcentual
            cambio_pct = abs((valor_actual - valor_entrenamiento) / valor_entrenamiento * 100)

            if cambio_pct > 20:
                status = "🔴"
                alertas.append(metrica)
            elif cambio_pct > 10:
                status = "🟡"
            else:
                status = "🟢"

            print(f"{status} {metrica}:")
            print(f"   Entrenamiento: {valor_entrenamiento:.2f}")
            print(f"   Actual: {valor_actual:.2f}")
            print(f"   Cambio: {cambio_pct:.1f}%\n")

        if len(alertas) > 0:
            print(f"\n⚠️ ALERTAS: {len(alertas)} métricas con cambios significativos")
            print(f"   Métricas: {', '.join(alertas)}")
            print("\n💡 Recomendación: Reentrenar modelo con datos actualizados")
        else:
            print("\n✅ Distribución de datos estable")

    except Exception as e:
        print(f"❌ Error: {e}")


# ============================================================
# 3. RECOMENDACIÓN DE REENTRENAMIENTO
# ============================================================

def recommend_retraining():
    """
    Recomienda si debes reentrenar basado en tiempo y uso
    """

    print("\n" + "="*60)
    print("🤖 RECOMENDACIÓN DE REENTRENAMIENTO")
    print("="*60)

    # Fecha de último entrenamiento (actualiza esto)
    fecha_entrenamiento = datetime(2025, 12, 19)
    fecha_hoy = datetime.now()

    dias_desde_entrenamiento = (fecha_hoy - fecha_entrenamiento).days
    meses = dias_desde_entrenamiento / 30

    print(f"\n📅 Último entrenamiento: {fecha_entrenamiento.strftime('%Y-%m-%d')}")
    print(f"📅 Hoy: {fecha_hoy.strftime('%Y-%m-%d')}")
    print(f"⏰ Han pasado: {dias_desde_entrenamiento} días ({meses:.1f} meses)")

    print("\n📋 Checklist de reentrenamiento:")

    checklist = [
        ("Han pasado más de 3 meses", meses > 3),
        ("Tienes más de 200 clientes nuevos", False),  # Actualiza esto
        ("Cambió política de crédito", False),  # Actualiza esto
        ("Precisión del modelo bajó", False),  # Del check anterior
        ("Data drift detectado", False),  # Del check anterior
    ]

    reentrenar = False
    for item, cumple in checklist:
        status = "✅" if cumple else "⬜"
        print(f"{status} {item}")
        if cumple:
            reentrenar = True

    print("\n" + "="*60)
    if reentrenar:
        print("🚨 RECOMENDACIÓN: REENTRENAR EL MODELO")
        print("\nPasos:")
        print("1. Exportar datos actualizados con columna 'default' (0/1)")
        print("2. Ejecutar: python retrain_model.py")
        print("3. Validar nuevo modelo en test set")
        print("4. Desplegar a Vertex AI si mejora el anterior")
    else:
        print("✅ RECOMENDACIÓN: Modelo aún vigente")
        print(f"\n💡 Próxima revisión recomendada en: {90 - dias_desde_entrenamiento} días")


# ============================================================
# EJECUTAR TODAS LAS VERIFICACIONES
# ============================================================

def save_report(precision, drift_alerts, should_retrain):
    """Guarda reporte histórico para comparar trimestralmente"""

    report = {
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'precision': precision,
        'drift_alerts': drift_alerts,
        'debe_reentrenar': should_retrain,
        'modelo_version': 'platam-custom-final'
    }

    # Guardar en CSV histórico
    import os
    report_file = 'model_health_history.csv'

    df_report = pd.DataFrame([report])

    if os.path.exists(report_file):
        df_history = pd.read_csv(report_file)
        df_history = pd.concat([df_history, df_report], ignore_index=True)
    else:
        df_history = df_report

    df_history.to_csv(report_file, index=False)
    print(f"\n💾 Reporte guardado en: {report_file}")

    # Mostrar histórico
    if len(df_history) > 1:
        print("\n📊 Histórico de monitoreos:")
        print(df_history.to_string(index=False))


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔍 MONITOREO TRIMESTRAL DE SALUD DEL MODELO ML")
    print("="*60)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modelo: platam-custom-final")
    print(f"Frecuencia recomendada: Cada 3 meses")

    # Variables para el reporte
    precision = None
    drift_alerts = []
    should_retrain = False

    # 1. Verificar precisión (necesitas llenar con datos reales)
    precision = check_prediction_accuracy()

    # 2. Verificar data drift
    check_data_drift()

    # 3. Recomendación final
    recommend_retraining()

    # 4. Guardar reporte histórico
    # save_report(precision, drift_alerts, should_retrain)  # Descomentar cuando tengas datos reales

    print("\n" + "="*60)
    print("📝 PRÓXIMOS PASOS:")
    print("="*60)
    print("1. Ejecutar este script cada 3 meses")
    print("2. Comparar con reportes anteriores")
    print("3. Si aparecen alertas: considerar reentrenamiento")
    print("4. Actualizar fecha_entrenamiento después de reentrenar")
    print("\n⏰ Próxima ejecución recomendada: Abril 2026")
    print("="*60)
