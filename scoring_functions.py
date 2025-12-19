"""
PLATAM Internal Credit Score Calculator - Core Functions

Funciones extraídas del código original para usar con datos reales.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


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
