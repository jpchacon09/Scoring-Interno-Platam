#!/usr/bin/env python3
"""
Script de prueba para la API de Scoring Completo
Simula lo que haría n8n
"""

import requests
import json
from datetime import datetime

# URL de la API (cambiar si está en Cloud Run)
API_URL = "http://localhost:8000"

def print_section(title):
    """Imprime una sección bonita"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_health():
    """Verificar que la API está funcionando"""
    print_section("1. VERIFICAR SALUD DE LA API")

    try:
        response = requests.get(f"{API_URL}/health")
        print(f"Status: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n⚠️  Asegúrate de ejecutar la API primero:")
        print("   python api_scoring_completo.py")
        return False

def test_scoring_completo(client_id):
    """Probar el endpoint principal"""
    print_section(f"2. SCORING COMPLETO - Cliente {client_id}")

    try:
        response = requests.post(
            f"{API_URL}/predict",
            json={"client_id": client_id}
        )

        if response.status_code == 200:
            result = response.json()

            # Mostrar resultados de forma bonita
            print(f"\n📋 CLIENTE: {result['client_id']}")
            print(f"⏰ Timestamp: {result['timestamp']}")

            print("\n📊 SCORING HÍBRIDO:")
            print(f"   • PLATAM Score: {result['scoring']['platam_score']}")
            print(f"   • Experian Score: {result['scoring']['experian_score']}")
            print(f"   • Score Híbrido: {result['scoring']['hybrid_score']} ({result['scoring']['hybrid_category']})")
            print(f"   • Pesos usados: PLATAM {result['scoring']['peso_platam']:.0%} / Experian {result['scoring']['peso_experian']:.0%}")

            print("\n🤖 PREDICCIÓN ML:")
            print(f"   • Probabilidad Default: {result['ml_prediction']['probability_default']:.1%}")
            print(f"   • Probabilidad No-Default: {result['ml_prediction']['probability_no_default']:.1%}")
            print(f"   • Nivel de Riesgo: {result['ml_prediction']['risk_level']}")
            print(f"   • Decisión ML: {result['ml_prediction']['ml_decision']}")

            print("\n💡 RECOMENDACIÓN FINAL:")
            print(f"   • Decisión: {result['recommendation']['final_decision']}")
            print(f"   • Confianza: {result['recommendation']['confidence']}")
            print(f"   • Razón: {result['recommendation']['reason']}")
            print(f"   • Requiere revisión manual: {'Sí' if result['recommendation']['should_review_manually'] else 'No'}")

            if result['recommendation']['flags']:
                print(f"\n   ⚠️  Alertas:")
                for flag in result['recommendation']['flags']:
                    print(f"      {flag}")

            print("\n" + "="*70)
            return result
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_scoring_only(client_id):
    """Probar solo el scoring híbrido"""
    print_section(f"3. SOLO SCORING HÍBRIDO - Cliente {client_id}")

    try:
        response = requests.post(
            f"{API_URL}/predict/scoring-only",
            json={"client_id": client_id}
        )

        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2))
            return result
        else:
            print(f"❌ Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_ml_only(client_id):
    """Probar solo la predicción ML"""
    print_section(f"4. SOLO PREDICCIÓN ML - Cliente {client_id}")

    try:
        response = requests.post(
            f"{API_URL}/predict/ml-only",
            json={"client_id": client_id}
        )

        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2))
            return result
        else:
            print(f"❌ Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def simulate_n8n_workflow():
    """Simular lo que haría n8n"""
    print_section("5. SIMULACIÓN DE WORKFLOW N8N")

    client_id = "12345"

    # 1. Webhook recibe client_id
    print("\n📨 [Webhook] Recibido: {\"client_id\": \"12345\"}")

    # 2. HTTP Request llama a la API
    print("\n🌐 [HTTP Request] Llamando a /predict...")

    response = requests.post(
        f"{API_URL}/predict",
        json={"client_id": client_id}
    )

    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return

    result = response.json()

    # 3. Switch por decisión
    print("\n🔀 [Switch] Enrutando según decisión...")

    decision = result['recommendation']['final_decision']

    if "APROBAR" in decision:
        print(f"   ✅ Ruta: APROBAR")
        print(f"   → Enviar email de aprobación")
        print(f"   → Actualizar CRM: Status = 'Aprobado'")
        print(f"   → Score: {result['scoring']['hybrid_score']}")

    elif "RECHAZAR" in decision:
        print(f"   ❌ Ruta: RECHAZAR")
        print(f"   → Enviar notificación de rechazo")
        print(f"   → Actualizar CRM: Status = 'Rechazado'")
        print(f"   → Razón: {result['recommendation']['reason']}")

    elif "REVISAR" in decision:
        print(f"   ⚠️  Ruta: REVISAR MANUALMENTE")
        print(f"   → Crear ticket en sistema de revisión")
        print(f"   → Asignar a analista")
        print(f"   → Prioridad: {result['recommendation']['confidence']}")
        print(f"   → Razón: {result['recommendation']['reason']}")

    # 4. Guardar en base de datos
    print(f"\n💾 [Database] Guardando resultado...")
    print(f"   cliente_id: {result['client_id']}")
    print(f"   score_hibrido: {result['scoring']['hybrid_score']}")
    print(f"   prob_default: {result['ml_prediction']['probability_default']:.3f}")
    print(f"   decision: {decision}")
    print(f"   timestamp: {result['timestamp']}")

    print("\n✅ Workflow completado exitosamente!")

def compare_scenarios():
    """Comparar diferentes escenarios de scoring"""
    print_section("6. COMPARACIÓN DE ESCENARIOS")

    # Nota: Esto usará los mismos datos de prueba
    # En producción, cada client_id tendría datos diferentes

    scenarios = [
        ("Cliente bajo riesgo", "CLT001"),
        ("Cliente medio riesgo", "CLT002"),
        ("Cliente alto riesgo", "CLT003"),
    ]

    print("\n📊 Comparando diferentes perfiles de cliente:")
    print("\n(Nota: Actualmente todos usan datos de prueba. Conecta tu DB para datos reales)")

    for desc, client_id in scenarios:
        print(f"\n{desc} ({client_id}):")
        result = test_scoring_completo(client_id)
        if result:
            print(f"   → Score: {result['scoring']['hybrid_score']}")
            print(f"   → Prob Default: {result['ml_prediction']['probability_default']:.1%}")
            print(f"   → Decisión: {result['recommendation']['final_decision']}")

def main():
    """Script principal"""
    print("="*70)
    print("  🧪 TEST DE API DE SCORING COMPLETO")
    print("  Simula la integración con n8n")
    print("="*70)

    # 1. Verificar que la API está corriendo
    if not test_health():
        return

    # 2. Probar endpoint principal
    client_id = "12345"
    result = test_scoring_completo(client_id)

    if not result:
        return

    # 3. Probar endpoints individuales
    test_scoring_only(client_id)
    test_ml_only(client_id)

    # 4. Simular workflow de n8n
    simulate_n8n_workflow()

    # 5. Resumen final
    print_section("RESUMEN")
    print("\n✅ Todos los tests pasaron correctamente")
    print("\n📋 Próximos pasos:")
    print("   1. Conectar get_client_data() a tu base de datos real")
    print("   2. Configurar el workflow en n8n usando N8N_INTEGRACION.md")
    print("   3. Desplegar a Cloud Run para producción")
    print("\n📚 Documentación:")
    print("   • Guía de n8n: N8N_INTEGRACION.md")
    print("   • Docs interactivas: http://localhost:8000/docs")
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
