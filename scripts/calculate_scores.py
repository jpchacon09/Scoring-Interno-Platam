#!/usr/bin/env python3
"""
Script para calcular scoring de clientes usando datos reales

Carga CSVs de data/raw/ y calcula scores usando el nuevo sistema de 3 componentes.

Sistema actualizado:
- Payment Performance: 600 pts (60%)
- Payment Plan History: 150 pts (15%)
- Deterioration Velocity: 250 pts (25%)

Usage:
    python scripts/calculate_scores.py
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# Importar funciones del código de scoring actualizado
sys.path.append(str(Path(__file__).parent.parent))
from internal_credit_score import (
    calculate_payment_performance,
    calculate_payment_plan_score,
    calculate_deterioration_velocity,
    get_credit_rating,
    calculate_limit_actions,
    check_dpd_alerts,
    generate_dpd_alert_report
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
RAW_DIR = Path('data/raw')
PROCESSED_DIR = Path('data/processed')
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

class ScoringCalculator:
    def __init__(self, reference_date=None):
        self.reference_date = reference_date or datetime.now()
        self.clients_df = None
        self.payments_df = None
        self.payment_plans_df = None

    def load_data(self):
        """Carga todos los CSVs"""
        logger.info("="*60)
        logger.info("PLATAM - Cálculo de Credit Scoring V2.0")
        logger.info("Sistema de 3 componentes")
        logger.info("="*60)
        logger.info(f"\nFecha de cálculo: {self.reference_date.date()}")
        logger.info("\n[1/4] Cargando datos...")

        # Clients (obligatorio)
        clients_path = RAW_DIR / 'clients'
        self.clients_df = self._load_table(clients_path, 'clients', required=True)

        # Payments (obligatorio)
        payments_path = RAW_DIR / 'payments'
        self.payments_df = self._load_table(payments_path, 'payments', required=True)
        if self.payments_df is not None:
            self.payments_df['payment_date'] = pd.to_datetime(self.payments_df['payment_date'])
            self.payments_df['due_date'] = pd.to_datetime(self.payments_df['due_date'], errors='coerce')

        # Payment plans (opcional)
        plans_path = RAW_DIR / 'payment_plans'
        self.payment_plans_df = self._load_table(plans_path, 'payment_plans', required=False)
        if self.payment_plans_df is not None and len(self.payment_plans_df) > 0:
            self.payment_plans_df['plan_start_date'] = pd.to_datetime(
                self.payment_plans_df['plan_start_date']
            )
            if 'plan_end_date' in self.payment_plans_df.columns:
                self.payment_plans_df['plan_end_date'] = pd.to_datetime(
                    self.payment_plans_df['plan_end_date'], errors='coerce'
                )
        else:
            # Crear DataFrame vacío si no hay planes
            self.payment_plans_df = pd.DataFrame(columns=[
                'client_id', 'plan_start_date', 'plan_end_date', 'plan_status'
            ])

        logger.info("\n✓ Datos cargados exitosamente")

    def _load_table(self, folder_path, table_name, required=True):
        """Carga una tabla desde CSVs"""
        if not folder_path.exists():
            if required:
                logger.error(f"  ❌ Carpeta no encontrada: {folder_path}")
                sys.exit(1)
            else:
                logger.info(f"  ℹ {table_name}: No encontrado (opcional)")
                return None

        csv_files = list(folder_path.glob('*.csv'))

        if not csv_files:
            if required:
                logger.error(f"  ❌ No hay CSVs en {folder_path}")
                sys.exit(1)
            else:
                logger.info(f"  ℹ {table_name}: Sin archivos CSV")
                return None

        # Leer y concatenar todos los CSVs
        dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                dfs.append(df)
            except Exception as e:
                logger.error(f"  ❌ Error leyendo {csv_file}: {e}")
                if required:
                    sys.exit(1)

        if not dfs:
            return None

        df = pd.concat(dfs, ignore_index=True)
        logger.info(f"  ✓ {table_name}: {len(df):,} registros de {len(csv_files)} archivo(s)")

        return df

    def calculate_scores(self):
        """Calcula scores para todos los clientes"""
        logger.info("\n[2/4] Calculando scores con sistema de 3 componentes...")

        results = []
        total_clients = len(self.clients_df)

        for idx, client_row in self.clients_df.iterrows():
            client_id = client_row['client_id']

            logger.info(f"\n  [{idx+1}/{total_clients}] Calculando score para: {client_id}")

            try:
                # Preparar datos del cliente
                client_data = {
                    'client_id': client_id,
                    'client_name': client_row.get('client_name', ''),
                    'months_as_client': int(client_row['months_as_client']),
                    'current_credit_limit': float(client_row['current_credit_limit']),
                    'current_outstanding': float(client_row.get('current_outstanding', 0))
                }

                # Calcular los 3 componentes del score
                payment_perf = calculate_payment_performance(
                    self.payments_df,
                    client_id,
                    client_data['months_as_client'],
                    self.reference_date
                )

                payment_plan = calculate_payment_plan_score(
                    self.payment_plans_df,
                    client_id,
                    self.reference_date
                )

                deterioration = calculate_deterioration_velocity(
                    self.payments_df,
                    client_id,
                    self.reference_date
                )

                # Total score (suma de 3 componentes = 1000 puntos)
                total_score = (
                    payment_perf['total'] +
                    payment_plan['total'] +
                    deterioration['total']
                )

                # Rating
                rating = get_credit_rating(total_score)

                # Limit actions (pasa previous_score como None para primera ejecución)
                has_active_plan = payment_plan['active_plans'] > 0
                limit_actions = calculate_limit_actions(
                    total_score,
                    None,  # previous_score - ajustar si tienes histórico
                    deterioration['total'],
                    client_data['current_credit_limit'],
                    has_active_plan
                )

                # Guardar resultado
                result = {
                    'client_id': client_id,
                    'client_name': client_data['client_name'],
                    'calculation_date': self.reference_date.date(),
                    'months_as_client': client_data['months_as_client'],

                    # Component scores (3 componentes)
                    'payment_performance': payment_perf['total'],
                    'payment_plan_history': payment_plan['total'],
                    'deterioration_velocity': deterioration['total'],

                    # Total
                    'total_score': round(total_score, 1),
                    'credit_rating': rating,

                    # Limit actions
                    'current_credit_limit': client_data['current_credit_limit'],
                    'action_type': limit_actions['action_type'],
                    'recommended_credit_limit': limit_actions['new_credit_limit'],
                    'limit_change_pct': limit_actions.get('final_reduction_pct', 0) or limit_actions.get('suggested_increase_pct', 0),
                    'is_frozen': limit_actions['is_frozen'],

                    # Key metrics - Payment Performance
                    'payment_count': payment_perf['payment_count'],
                    'timeliness_score': payment_perf['timeliness_score'],
                    'pattern_score': payment_perf['pattern_score'],
                    'timeliness_weight': payment_perf['timeliness_weight'],
                    'pattern_weight': payment_perf['pattern_weight'],

                    # Key metrics - Deterioration Velocity
                    'dpd_1mo': deterioration['dpd_1mo'],
                    'dpd_6mo': deterioration['dpd_6mo'],
                    'trend_delta': deterioration['trend_delta'],
                    'payments_1mo': deterioration['payments_1mo'],
                    'payments_6mo': deterioration['payments_6mo'],

                    # Key metrics - Payment Plans
                    'active_plans': payment_plan['active_plans'],
                    'completed_plans_12mo': payment_plan['completed_plans_12mo'],
                    'defaulted_plans': payment_plan['defaulted_plans'],
                    'months_since_last_plan': payment_plan['months_since_last_plan'],
                }

                results.append(result)

                logger.info(f"    Score: {total_score:.1f} ({rating}) | Action: {limit_actions['action_type']}")

            except Exception as e:
                logger.error(f"    ❌ Error calculando score: {e}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        return pd.DataFrame(results)

    def save_results(self, results_df):
        """Guarda resultados"""
        logger.info("\n[3/4] Guardando resultados...")

        # Guardar CSV detallado con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = PROCESSED_DIR / f'scores_{timestamp}.csv'

        results_df.to_csv(output_file, index=False)
        logger.info(f"  ✓ Guardado: {output_file}")

        # Guardar también versión "latest"
        latest_file = PROCESSED_DIR / 'scores_latest.csv'
        results_df.to_csv(latest_file, index=False)
        logger.info(f"  ✓ Guardado: {latest_file}")

        return output_file

    def print_summary(self, results_df):
        """Imprime resumen de resultados"""
        logger.info("\n" + "="*60)
        logger.info("RESUMEN DE SCORING V2.0")
        logger.info("="*60)

        logger.info(f"\nTotal clientes procesados: {len(results_df)}")

        # Distribución de ratings
        logger.info("\n📊 Distribución de Ratings:")
        rating_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D/F']
        rating_counts = results_df['credit_rating'].value_counts()
        for rating in rating_order:
            if rating in rating_counts.index:
                count = rating_counts[rating]
                pct = (count / len(results_df)) * 100
                logger.info(f"  {rating}: {count:4} ({pct:5.1f}%)")

        # Estadísticas de scores
        logger.info("\n📈 Estadísticas de Score Total:")
        logger.info(f"  Promedio: {results_df['total_score'].mean():6.1f}")
        logger.info(f"  Mediana:  {results_df['total_score'].median():6.1f}")
        logger.info(f"  Mínimo:   {results_df['total_score'].min():6.1f}")
        logger.info(f"  Máximo:   {results_df['total_score'].max():6.1f}")

        # Promedios por componente (3 componentes)
        logger.info("\n🎯 Promedio por Componente:")
        logger.info(f"  Payment Performance:    {results_df['payment_performance'].mean():6.1f} / 600 ({results_df['payment_performance'].mean()/600*100:5.1f}%)")
        logger.info(f"  Payment Plan History:   {results_df['payment_plan_history'].mean():6.1f} / 150 ({results_df['payment_plan_history'].mean()/150*100:5.1f}%)")
        logger.info(f"  Deterioration Velocity: {results_df['deterioration_velocity'].mean():6.1f} / 250 ({results_df['deterioration_velocity'].mean()/250*100:5.1f}%)")

        # Acciones recomendadas
        logger.info("\n⚙️ Acciones Recomendadas:")
        frozen_count = results_df['is_frozen'].sum()
        reduction_count = (results_df['action_type'] == 'REDUCTION').sum()
        increase_count = (results_df['action_type'] == 'INCREASE_SUGGESTED').sum()
        no_change_count = (results_df['action_type'] == 'NO_CHANGE').sum()

        logger.info(f"  Congelar cuenta:         {frozen_count:4} ({frozen_count/len(results_df)*100:5.1f}%)")
        logger.info(f"  Reducir límite:          {reduction_count:4} ({reduction_count/len(results_df)*100:5.1f}%)")
        logger.info(f"  Aumento sugerido:        {increase_count:4} ({increase_count/len(results_df)*100:5.1f}%)")
        logger.info(f"  Sin cambios:             {no_change_count:4} ({no_change_count/len(results_df)*100:5.1f}%)")

        # Top 5 peores scores
        logger.info("\n🔻 Top 5 Clientes de Mayor Riesgo:")
        worst_5 = results_df.nsmallest(5, 'total_score')[
            ['client_id', 'client_name', 'total_score', 'credit_rating']
        ]
        for idx, row in worst_5.iterrows():
            logger.info(
                f"  {row['client_id']}: {row['total_score']:6.1f} ({row['credit_rating']}) - {row['client_name']}"
            )

        # Top 5 mejores scores
        logger.info("\n🔺 Top 5 Clientes de Menor Riesgo:")
        best_5 = results_df.nlargest(5, 'total_score')[
            ['client_id', 'client_name', 'total_score', 'credit_rating']
        ]
        for idx, row in best_5.iterrows():
            logger.info(
                f"  {row['client_id']}: {row['total_score']:6.1f} ({row['credit_rating']}) - {row['client_name']}"
            )

def main():
    """Función principal"""
    calculator = ScoringCalculator()

    # 1. Cargar datos
    calculator.load_data()

    # 2. Calcular scores
    results_df = calculator.calculate_scores()

    if len(results_df) == 0:
        logger.error("\n❌ No se calcularon scores para ningún cliente")
        sys.exit(1)

    # 3. Guardar resultados
    output_file = calculator.save_results(results_df)

    # 4. Imprimir resumen
    calculator.print_summary(results_df)

    # 5. Mensaje final
    logger.info("\n" + "="*60)
    logger.info("✅ PROCESO COMPLETADO EXITOSAMENTE")
    logger.info("="*60)
    logger.info(f"\nResultados guardados en:")
    logger.info(f"  {output_file}")
    logger.info("\n💡 Próximos pasos:")
    logger.info("  1. Revisar resultados en el CSV generado")
    logger.info("  2. Analizar clientes de alto riesgo")
    logger.info("  3. Validar recomendaciones de límites de crédito")
    logger.info("\n📝 Nota: Sistema actualizado a 3 componentes")
    logger.info("  - Eliminados: Purchase Consistency y Utilization")
    logger.info("  - Payment Performance: 400 → 600 pts (+50%)")
    logger.info("  - Deterioration Velocity: 100 → 250 pts (+150%)")

if __name__ == '__main__':
    main()
