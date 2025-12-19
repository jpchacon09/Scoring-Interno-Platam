# @PLATAM Internal Credit Score Calculator
"""
PLATAM Internal Credit Score Calculator
Complete implementation for testing in Google Colab
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# SCORE CALCULATION FUNCTIONS
# ============================================================================

def calculate_payment_performance(
    payments_df: pd.DataFrame,
    client_id: str,
    months_as_client: int,
    reference_date: datetime = None
) -> Dict:
    """
    Calculate Payment Performance Score (400 points max)
    Combines timeliness and pattern scores with maturity weighting
    """
    if reference_date is None:
        reference_date = datetime.now()

    client_payments = payments_df[payments_df['client_id'] == client_id].copy()

    # Default scores if insufficient data
    if len(client_payments) < 3:
        return {
            'timeliness_score': 50,
            'pattern_score': 50,
            'timeliness_weight': 0.85,
            'pattern_weight': 0.15,
            'total': 200,
            'payment_count': len(client_payments)
        }

    # Determine weights based on maturity
    if months_as_client < 6:
        timeliness_weight = 0.85
        pattern_weight = 0.15
    elif months_as_client < 12:
        timeliness_weight = 0.70
        pattern_weight = 0.30
    else:
        timeliness_weight = 0.50
        pattern_weight = 0.50

    # A. TIMELINESS SCORE (0-100)
    client_payments['months_ago'] = (
        (reference_date - pd.to_datetime(client_payments['payment_date'])).dt.days / 30
    ).round(1)
    client_payments['recency_weight'] = 1.5 ** client_payments['months_ago']

    def payment_quality_score(dpd):
        """Score individual payment based on days past due"""
        if dpd <= 0:
            return 100
        elif dpd <= 15:
            return 100 - (dpd * 3)
        elif dpd <= 30:
            return 55 - (dpd * 2)
        elif dpd <= 60:
            return max(0, 30 - dpd)
        else:
            return 0

    client_payments['payment_score'] = client_payments['days_past_due'].apply(payment_quality_score)
    client_payments['weighted_score'] = client_payments['payment_score'] * client_payments['recency_weight']

    timeliness_score = (
        client_payments['weighted_score'].sum() / client_payments['recency_weight'].sum()
    )

    # B. PATTERN SCORE (0-100)
    recent_6mo = client_payments[client_payments['months_ago'] <= 6]

    if len(recent_6mo) < 3:
        pattern_score = 50
    else:
        adtp = recent_6mo['days_past_due'].mean()
        payment_stddev = recent_6mo['days_past_due'].std()

        # Consistency score based on standard deviation
        consistency_score = max(0, 100 - (payment_stddev * 2))

        # Pattern break detection (using most recent payment)
        if len(recent_6mo) > 0:
            recent_dpd = recent_6mo.iloc[0]['days_past_due']
            if payment_stddev > 0:
                z_score = abs((recent_dpd - adtp) / payment_stddev)

                if z_score <= 1.5:
                    pattern_break_penalty = 0
                elif z_score <= 2.5:
                    pattern_break_penalty = 15
                elif z_score <= 3.5:
                    pattern_break_penalty = 35
                else:
                    pattern_break_penalty = 60
            else:
                pattern_break_penalty = 0
        else:
            pattern_break_penalty = 0

        pattern_score = max(0, consistency_score - pattern_break_penalty)

    # COMBINED SCORE
    total = (timeliness_score * timeliness_weight + pattern_score * pattern_weight) * 4

    return {
        'timeliness_score': round(timeliness_score, 1),
        'pattern_score': round(pattern_score, 1),
        'timeliness_weight': timeliness_weight,
        'pattern_weight': pattern_weight,
        'total': round(total, 1),
        'payment_count': len(client_payments)
    }


def calculate_purchase_consistency(
    orders_df: pd.DataFrame,
    client_id: str
) -> Dict:
    """
    Calculate Purchase Consistency Score (200 points max)
    A. Order Frequency (120 points)
    B. Order Value Stability (80 points)
    """
    client_orders = orders_df[orders_df['client_id'] == client_id].copy()

    # Default if insufficient data
    if len(client_orders) < 6:
        return {
            'frequency_score': 60,
            'stability_score': 40,
            'total': 100,
            'orders_per_month': 0,
            'cv': 0
        }

    # A. FREQUENCY SCORE (120 points)
    # Group by month and count orders
    client_orders['month'] = pd.to_datetime(client_orders['order_date']).dt.to_period('M')
    orders_per_month = client_orders.groupby('month').size().mean()

    frequency_score = min(120, orders_per_month * 12)

    # B. STABILITY SCORE (80 points)
    # Calculate coefficient of variation
    mean_order_value = client_orders['order_value'].mean()
    std_order_value = client_orders['order_value'].std()

    if mean_order_value > 0:
        cv = (std_order_value / mean_order_value) * 100
    else:
        cv = 0

    stability_score = max(0, 80 - (cv * 1.5))

    total = frequency_score + stability_score

    return {
        'frequency_score': round(frequency_score, 1),
        'stability_score': round(stability_score, 1),
        'total': round(total, 1),
        'orders_per_month': round(orders_per_month, 1),
        'cv': round(cv, 1)
    }


def calculate_utilization_score(
    utilization_df: pd.DataFrame,
    client_id: str
) -> Dict:
    """
    Calculate Utilization Score (150 points max)
    Penalizes volatility, not high utilization
    """
    client_util = utilization_df[utilization_df['client_id'] == client_id].copy()

    # Default if insufficient data
    if len(client_util) < 6:
        return {
            'total': 75,
            'utilization_stddev': 0,
            'avg_utilization': 0
        }

    # Calculate standard deviation of utilization over last 6 months
    util_stddev = client_util['utilization_pct'].std()
    avg_util = client_util['utilization_pct'].mean()

    score = max(0, 150 - (util_stddev * 300))

    return {
        'total': round(score, 1),
        'utilization_stddev': round(util_stddev, 3),
        'avg_utilization': round(avg_util, 3)
    }


def calculate_payment_plan_score(
    payment_plans_df: pd.DataFrame,
    client_id: str,
    reference_date: datetime = None
) -> Dict:
    """
    Calculate Payment Plan History Score (150 points max)
    Cumulative with 12-month reset
    """
    if reference_date is None:
        reference_date = datetime.now()

    client_plans = payment_plans_df[payment_plans_df['client_id'] == client_id].copy()

    # Default - no plan history
    if len(client_plans) == 0:
        return {
            'total': 150,
            'active_plans': 0,
            'completed_plans_12mo': 0,
            'defaulted_plans': 0,
            'months_since_last_plan': None
        }

    # Calculate months since each plan event
    client_plans['plan_start_date'] = pd.to_datetime(client_plans['plan_start_date'])
    client_plans['months_since_start'] = (
        (reference_date - client_plans['plan_start_date']).dt.days / 30
    ).round(1)

    # Check if any plan activity in last 12 months
    plans_last_12mo = client_plans[client_plans['months_since_start'] <= 12]

    if len(plans_last_12mo) == 0:
        # Clean slate - reset to 150
        months_since_last = client_plans['months_since_start'].min()
        return {
            'total': 150,
            'active_plans': 0,
            'completed_plans_12mo': 0,
            'defaulted_plans': 0,
            'months_since_last_plan': round(months_since_last, 1)
        }

    # Calculate score based on events
    score = 150

    # Count active plans
    active_plans = len(plans_last_12mo[plans_last_12mo['plan_status'] == 'active'])
    score -= (active_plans * 50)

    # Count completed plans
    completed_plans = len(plans_last_12mo[plans_last_12mo['plan_status'] == 'completed'])
    score += (completed_plans * 30)

    # Count defaulted plans
    defaulted_plans = len(plans_last_12mo[plans_last_12mo['plan_status'] == 'defaulted'])
    score -= (defaulted_plans * 100)

    # Bound score
    score = max(0, min(150, score))

    return {
        'total': round(score, 1),
        'active_plans': active_plans,
        'completed_plans_12mo': completed_plans,
        'defaulted_plans': defaulted_plans,
        'months_since_last_plan': round(plans_last_12mo['months_since_start'].min(), 1) if len(plans_last_12mo) > 0 else None
    }


def calculate_deterioration_velocity(
    payments_df: pd.DataFrame,
    client_id: str,
    reference_date: datetime = None
) -> Dict:
    """
    Calculate Deterioration Velocity Score (100 points max)
    Compare 1-month vs 6-month average DPD
    """
    if reference_date is None:
        reference_date = datetime.now()

    client_payments = payments_df[payments_df['client_id'] == client_id].copy()

    # Default if insufficient data
    if len(client_payments) < 3:
        return {
            'total': 50,
            'dpd_1mo': 0,
            'dpd_6mo': 0,
            'trend_delta': 0,
            'payments_1mo': 0,
            'payments_6mo': 0
        }

    # Calculate months ago
    client_payments['payment_date'] = pd.to_datetime(client_payments['payment_date'])
    client_payments['months_ago'] = (
        (reference_date - client_payments['payment_date']).dt.days / 30
    ).round(1)

    # 1-month average
    payments_1mo = client_payments[client_payments['months_ago'] <= 1]

    # 6-month average
    payments_6mo = client_payments[client_payments['months_ago'] <= 6]

    # Need at least 3 payments in 6mo window and 1 payment in 1mo window
    if len(payments_6mo) < 3 or len(payments_1mo) < 1:
        return {
            'total': 50,
            'dpd_1mo': 0,
            'dpd_6mo': 0,
            'trend_delta': 0,
            'payments_1mo': len(payments_1mo),
            'payments_6mo': len(payments_6mo)
        }

    dpd_1mo = payments_1mo['days_past_due'].mean()
    dpd_6mo = payments_6mo['days_past_due'].mean()

    # Calculate trend
    trend_delta = dpd_1mo - dpd_6mo

    # Score
    score = 100 - (trend_delta * 3)
    score = max(0, min(100, score))

    return {
        'total': round(score, 1),
        'dpd_1mo': round(dpd_1mo, 1),
        'dpd_6mo': round(dpd_6mo, 1),
        'trend_delta': round(trend_delta, 1),
        'payments_1mo': len(payments_1mo),
        'payments_6mo': len(payments_6mo)
    }

def get_credit_rating(total_score: float) -> str:
    """Convert total score to letter rating"""
    if total_score >= 900:
        return 'A+'
    elif total_score >= 850:
        return 'A'
    elif total_score >= 800:
        return 'A-'
    elif total_score >= 750:
        return 'B+'
    elif total_score >= 700:
        return 'B'
    elif total_score >= 650:
        return 'B-'
    elif total_score >= 600:
        return 'C+'
    elif total_score >= 550:
        return 'C'
    elif total_score >= 500:
        return 'C-'
    else:
        return 'D/F'


def calculate_velocity_multiplier(velocity_score: float) -> float:
    """Calculate reduction multiplier based on deterioration velocity"""
    if velocity_score >= 95:
        return 0.8
    elif velocity_score >= 85:
        return 1.0
    elif velocity_score >= 70:
        return 1.3
    elif velocity_score >= 50:
        return 1.7
    elif velocity_score >= 30:
        return 2.5
    else:
        return 3.0


def calculate_limit_actions(
    total_score: float,
    velocity_score: float,
    current_limit: float,
    has_active_plan: bool
) -> Dict:
    """
    Calculate credit limit actions based on score
    Returns new limit, reduction percentage, and freeze status
    """
    # Determine base reduction percentage
    if total_score >= 700:
        base_reduction = 0.0
    elif total_score >= 650:
        base_reduction = 0.15
    elif total_score >= 600:
        base_reduction = 0.25
    elif total_score >= 550:
        base_reduction = 0.35
    elif total_score >= 500:
        base_reduction = 0.50
    else:
        base_reduction = 1.0  # Collections

    # Apply velocity multiplier
    velocity_multiplier = calculate_velocity_multiplier(velocity_score)
    final_reduction = min(1.0, base_reduction * velocity_multiplier)

    # Calculate new limit
    new_limit = current_limit * (1 - final_reduction)

    # Determine if frozen
    is_frozen = has_active_plan or total_score < 500

    return {
        'base_reduction_pct': round(base_reduction * 100, 1),
        'velocity_multiplier': velocity_multiplier,
        'final_reduction_pct': round(final_reduction * 100, 1),
        'new_credit_limit': round(new_limit, 2),
        'reduction_amount': round(current_limit - new_limit, 2),
        'is_frozen': is_frozen
    }


def calculate_client_score(
    client_data: Dict,
    payments_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    utilization_df: pd.DataFrame,
    payment_plans_df: pd.DataFrame,
    reference_date: datetime = None
) -> Dict:
    """
    Main function to calculate complete credit score for a client
    """
    client_id = client_data['client_id']

    # Calculate all components
    payment_perf = calculate_payment_performance(
        payments_df, client_id, client_data['months_as_client'], reference_date
    )

    purchase_cons = calculate_purchase_consistency(orders_df, client_id)

    utilization = calculate_utilization_score(utilization_df, client_id)

    payment_plan = calculate_payment_plan_score(payment_plans_df, client_id, reference_date)

    deterioration = calculate_deterioration_velocity(payments_df, client_id, reference_date)

    # Calculate total score
    total_score = (
        payment_perf['total'] +
        purchase_cons['total'] +
        utilization['total'] +
        payment_plan['total'] +
        deterioration['total']
    )

    # Get rating
    rating = get_credit_rating(total_score)

    # Calculate limit actions
    has_active_plan = payment_plan['active_plans'] > 0
    limit_actions = calculate_limit_actions(
        total_score,
        deterioration['total'],
        client_data['current_credit_limit'],
        has_active_plan
    )

    return {
        'client_id': client_id,
        'client_name': client_data.get('client_name', ''),
        'calculation_date': reference_date or datetime.now(),
        'months_as_client': client_data['months_as_client'],

        # Component scores
        'payment_performance': payment_perf['total'],
        'payment_performance_details': payment_perf,

        'purchase_consistency': purchase_cons['total'],
        'purchase_consistency_details': purchase_cons,

        'utilization': utilization['total'],
        'utilization_details': utilization,

        'payment_plan_history': payment_plan['total'],
        'payment_plan_details': payment_plan,

        'deterioration_velocity': deterioration['total'],
        'deterioration_velocity_details': deterioration,

        # Total
        'total_score': round(total_score, 1),
        'credit_rating': rating,

        # Limit actions
        'current_credit_limit': client_data['current_credit_limit'],
        'limit_actions': limit_actions
    }


# ============================================================================
# SAMPLE DATA GENERATION
# ============================================================================

def generate_sample_data():
    """Generate sample data for testing"""

    reference_date = datetime(2024, 12, 16)  # Today

    # CLIENT DATA (same as before)
    clients = pd.DataFrame([
        {
            'client_id': 'FERR001',
            'client_name': 'Ferretería El Constructor',
            'months_as_client': 18,
            'current_credit_limit': 100_000_000,
            'current_outstanding': 75_000_000
        },
        {
            'client_id': 'FARM001',
            'client_name': 'Farmacia San José',
            'months_as_client': 24,
            'current_credit_limit': 125_000_000,
            'current_outstanding': 100_000_000
        },
        {
            'client_id': 'FERR002',
            'client_name': 'Ferretería Problemática',
            'months_as_client': 12,
            'current_credit_limit': 80_000_000,
            'current_outstanding': 75_000_000
        }
    ])

    # PAYMENT HISTORY - FIXED to have recent payments
    payments_data = []

    # FERR001 - Good client, improving (was 5 days late, now 3)
    for i in range(20):
        days_late = 5 if i >= 6 else 3  # Last 6 months better than before
        payment_date = reference_date - timedelta(days=15*i)  # Payment every 15 days
        due_date = payment_date - timedelta(days=days_late)
        payments_data.append({
            'client_id': 'FERR001',
            'payment_date': payment_date,
            'due_date': due_date,
            'days_past_due': days_late,
            'payment_amount': 5_000_000
        })

    # FARM001 - Predictable slow payer (always 12 days)
    for i in range(20):
        payment_date = reference_date - timedelta(days=15*i)
        due_date = payment_date - timedelta(days=12)
        payments_data.append({
            'client_id': 'FARM001',
            'payment_date': payment_date,
            'due_date': due_date,
            'days_past_due': 12,
            'payment_amount': 8_000_000
        })

    # FERR002 - Deteriorating client (was 5 days, now 45 days)
    for i in range(15):
        if i < 3:  # Last 3 payments (most recent ~1.5 months)
            dpd = 45
        elif i < 6:  # Next 3 payments (1.5-3 months ago)
            dpd = 20
        else:  # Older payments (3-7.5 months ago)
            dpd = 5

        payment_date = reference_date - timedelta(days=15*i)
        due_date = payment_date - timedelta(days=dpd)
        payments_data.append({
            'client_id': 'FERR002',
            'payment_date': payment_date,
            'due_date': due_date,
            'days_past_due': dpd,
            'payment_amount': 4_000_000
        })

    payments_df = pd.DataFrame(payments_data)

    # ORDER HISTORY (same as before)
    orders_data = []

    for i in range(60):
        orders_data.append({
            'client_id': 'FERR001',
            'order_date': reference_date - timedelta(days=i*3),
            'order_value': np.random.normal(8_000_000, 500_000)
        })

    for i in range(70):
        orders_data.append({
            'client_id': 'FARM001',
            'order_date': reference_date - timedelta(days=i*2),
            'order_value': np.random.normal(10_000_000, 300_000)
        })

    for i in range(40):
        orders_data.append({
            'client_id': 'FERR002',
            'order_date': reference_date - timedelta(days=i*5),
            'order_value': np.random.normal(5_000_000, 2_000_000)
        })

    orders_df = pd.DataFrame(orders_data)

    # UTILIZATION HISTORY (same as before)
    utilization_data = []

    for i in range(6):
        utilization_data.append({
            'client_id': 'FERR001',
            'month': (reference_date - timedelta(days=30*i)).strftime('%Y-%m'),
            'avg_outstanding': 75_000_000 + np.random.normal(0, 3_000_000),
            'credit_limit': 100_000_000,
            'utilization_pct': 0.75 + np.random.normal(0, 0.03)
        })

    for i in range(6):
        utilization_data.append({
            'client_id': 'FARM001',
            'month': (reference_date - timedelta(days=30*i)).strftime('%Y-%m'),
            'avg_outstanding': 100_000_000,
            'credit_limit': 125_000_000,
            'utilization_pct': 0.80 + np.random.normal(0, 0.02)
        })

    for i in range(6):
        utilization_data.append({
            'client_id': 'FERR002',
            'month': (reference_date - timedelta(days=30*i)).strftime('%Y-%m'),
            'avg_outstanding': 75_000_000 if i < 3 else 40_000_000,
            'credit_limit': 80_000_000,
            'utilization_pct': 0.93 if i < 3 else 0.50
        })

    utilization_df = pd.DataFrame(utilization_data)

    # PAYMENT PLANS (same as before)
    payment_plans_data = [
        {
            'client_id': 'FERR001',
            'plan_start_date': reference_date - timedelta(days=240),
            'plan_end_date': reference_date - timedelta(days=180),
            'plan_status': 'completed'
        },
        {
            'client_id': 'FARM001',
            'plan_start_date': reference_date - timedelta(days=150),
            'plan_end_date': reference_date - timedelta(days=90),
            'plan_status': 'completed'
        },
        {
            'client_id': 'FERR002',
            'plan_start_date': reference_date - timedelta(days=120),
            'plan_end_date': reference_date - timedelta(days=60),
            'plan_status': 'completed'
        },
        {
            'client_id': 'FERR002',
            'plan_start_date': reference_date - timedelta(days=30),
            'plan_end_date': None,
            'plan_status': 'active'
        }
    ]

    payment_plans_df = pd.DataFrame(payment_plans_data)

    return clients, payments_df, orders_df, utilization_df, payment_plans_df, reference_date

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""

    print("="*80)
    print("PLATAM INTERNAL CREDIT SCORE CALCULATOR")
    print("="*80)
    print()

    # Generate sample data
    print("Generating sample data...")
    clients, payments_df, orders_df, utilization_df, payment_plans_df, reference_date = generate_sample_data()
    print(f"✓ Generated data for {len(clients)} clients")
    print(f"✓ Reference date: {reference_date.date()}")
    print()

    # Calculate scores for all clients
    results = []

    for _, client in clients.iterrows():
        print(f"\n{'='*80}")
        print(f"CALCULATING SCORE FOR: {client['client_name']} ({client['client_id']})")
        print(f"{'='*80}")

        result = calculate_client_score(
            client.to_dict(),
            payments_df,
            orders_df,
            utilization_df,
            payment_plans_df,
            reference_date
        )

        results.append(result)

        # Print results
        print(f"\n📊 SCORE BREAKDOWN:")
        print(f"  Payment Performance:    {result['payment_performance']:>6.1f} / 400")
        print(f"  Purchase Consistency:   {result['purchase_consistency']:>6.1f} / 200")
        print(f"  Utilization:            {result['utilization']:>6.1f} / 150")
        print(f"  Payment Plan History:   {result['payment_plan_history']:>6.1f} / 150")
        print(f"  Deterioration Velocity: {result['deterioration_velocity']:>6.1f} / 100")
        print(f"  {'─'*45}")
        print(f"  TOTAL SCORE:           {result['total_score']:>6.1f} / 1000")
        print(f"  CREDIT RATING:          {result['credit_rating']:>6}")

        print(f"\n💰 CREDIT LIMIT ACTIONS:")
        print(f"  Current Limit:          ${result['current_credit_limit']:>15,.0f}")
        print(f"  Base Reduction:         {result['limit_actions']['base_reduction_pct']:>6.1f}%")
        print(f"  Velocity Multiplier:    {result['limit_actions']['velocity_multiplier']:>6.1f}x")
        print(f"  Final Reduction:        {result['limit_actions']['final_reduction_pct']:>6.1f}%")
        print(f"  New Limit:              ${result['limit_actions']['new_credit_limit']:>15,.0f}")
        print(f"  Frozen:                 {'YES ❄️' if result['limit_actions']['is_frozen'] else 'NO'}")

        print(f"\n📈 KEY METRICS:")
        pp_details = result['payment_performance_details']
        print(f"  Timeliness Score:       {pp_details['timeliness_score']:>6.1f} (weight: {pp_details['timeliness_weight']:.0%})")
        print(f"  Pattern Score:          {pp_details['pattern_score']:>6.1f} (weight: {pp_details['pattern_weight']:.0%})")

        dv_details = result['deterioration_velocity_details']
        print(f"  DPD 1-month avg:        {dv_details['dpd_1mo']:>6.1f} days")
        print(f"  DPD 6-month avg:        {dv_details['dpd_6mo']:>6.1f} days")
        print(f"  Trend Delta:            {dv_details['trend_delta']:>6.1f} days ({'↑ Worsening' if dv_details['trend_delta'] > 0 else '↓ Improving'})")

        pp_details_data = result['payment_plan_details']
        print(f"  Active Plans:           {pp_details_data['active_plans']}")
        print(f"  Completed Plans (12mo): {pp_details_data['completed_plans_12mo']}")

    print(f"\n\n{'='*80}")
    print("SUMMARY TABLE")
    print(f"{'='*80}")

    # Create summary dataframe
    summary = pd.DataFrame([{
        'Client': r['client_name'],
        'Score': r['total_score'],
        'Rating': r['credit_rating'],
        'Limit': f"${r['limit_actions']['new_credit_limit']:,.0f}",
        'Reduction': f"{r['limit_actions']['final_reduction_pct']:.1f}%",
        'Frozen': '❄️' if r['limit_actions']['is_frozen'] else ''
    } for r in results])

    print(summary.to_string(index=False))
    print()

    return results, clients, payments_df, orders_df, utilization_df, payment_plans_df


# Run if executed directly
if __name__ == "__main__":
    results, clients, payments_df, orders_df, utilization_df, payment_plans_df = main()
