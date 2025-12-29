"""
PLATAM CREDIT SCORING SYSTEM - Complete Implementation
Version: 2.0
Date: December 2024

Components:
- Payment Performance: 600 points (60%)
- Payment Plan History: 150 points (15%)
- Deterioration Velocity: 250 points (25%)
- Total: 1000 points

Features:
- Automatic limit reductions (≤B-)
- Suggested limit increases (B- improvements)
- FPD Prevention DPD Alert System
- Pattern-based risk assessment

Usage in Google Colab:
1. Run all cells
2. Scores and alerts calculated automatically
3. Results displayed in formatted output
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CREDIT SCORE CALCULATION FUNCTIONS
# ============================================================================

def calculate_payment_performance(
    payments_df: pd.DataFrame,
    client_id: str,
    months_as_client: int,
    reference_date: datetime = None
) -> Dict:
    """
    Calculate Payment Performance Score (600 points max)
    Combines timeliness and pattern scores with maturity weighting

    Returns score on 600-point scale (60% of total credit score)
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
            'total': 300,  # 50% of 600
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

        # Pattern break detection
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

    # COMBINED SCORE - Scaled to 600 points
    total = (timeliness_score * timeliness_weight + pattern_score * pattern_weight) * 6

    return {
        'timeliness_score': round(timeliness_score, 1),
        'pattern_score': round(pattern_score, 1),
        'timeliness_weight': timeliness_weight,
        'pattern_weight': pattern_weight,
        'total': round(total, 1),
        'payment_count': len(client_payments)
    }


def calculate_payment_plan_score(
    payment_plans_df: pd.DataFrame,
    client_id: str,
    reference_date: datetime = None
) -> Dict:
    """
    Calculate Payment Plan History Score (150 points max)
    Cumulative with 12-month reset

    Returns score on 150-point scale (15% of total credit score)
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
    Calculate Deterioration Velocity Score (250 points max)
    Compare 1-month vs 6-month average DPD

    Returns score on 250-point scale (25% of total credit score)
    """
    if reference_date is None:
        reference_date = datetime.now()

    client_payments = payments_df[payments_df['client_id'] == client_id].copy()

    # Default if insufficient data
    if len(client_payments) < 3:
        return {
            'total': 125,  # 50% of 250
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
            'total': 125,
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

    # Score (base 0-100, then scaled to 250)
    base_score = 100 - (trend_delta * 3)
    base_score = max(0, min(100, base_score))

    # Scale to 250 points
    score = base_score * 2.5

    return {
        'total': round(score, 1),
        'dpd_1mo': round(dpd_1mo, 1),
        'dpd_6mo': round(dpd_6mo, 1),
        'trend_delta': round(trend_delta, 1),
        'payments_1mo': len(payments_1mo),
        'payments_6mo': len(payments_6mo)
    }


# ============================================================================
# CREDIT RATING AND LIMIT LOGIC
# ============================================================================

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


def get_score_bucket(score: float) -> int:
    """Return bucket number (lower = better)"""
    if score >= 900:
        return 1   # A+
    elif score >= 850:
        return 2   # A
    elif score >= 800:
        return 3   # A-
    elif score >= 750:
        return 4   # B+
    elif score >= 700:
        return 5   # B
    elif score >= 650:
        return 6   # B-
    elif score >= 600:
        return 7   # C+
    elif score >= 550:
        return 8   # C
    elif score >= 500:
        return 9   # C-
    else:
        return 10  # D/F


def calculate_velocity_multiplier(velocity_score: float) -> float:
    """Calculate reduction multiplier based on deterioration velocity"""
    if velocity_score >= 237.5:  # 95+ on 0-100 scale
        return 0.8
    elif velocity_score >= 212.5:  # 85+ on 0-100 scale
        return 1.0
    elif velocity_score >= 175:  # 70+ on 0-100 scale
        return 1.3
    elif velocity_score >= 125:  # 50+ on 0-100 scale
        return 1.7
    elif velocity_score >= 75:  # 30+ on 0-100 scale
        return 2.5
    else:
        return 3.0


def calculate_limit_actions(
    total_score: float,
    previous_score: Optional[float],
    velocity_score: float,
    current_limit: float,
    has_active_plan: bool
) -> Dict:
    """
    Calculate credit limit actions based on score CHANGE

    REDUCTIONS: Automatic if score ≤ B- and bucket worsened
    INCREASES: Suggested if score improved from B- or above
    """

    current_bucket = get_score_bucket(total_score)
    current_rating = get_credit_rating(total_score)

    if previous_score is not None:
        previous_bucket = get_score_bucket(previous_score)
        previous_rating = get_credit_rating(previous_score)
        bucket_changed = current_bucket != previous_bucket
    else:
        previous_bucket = current_bucket
        previous_rating = current_rating
        bucket_changed = False

    # REDUCTIONS - Automatic if ≤ B- and bucket worsened
    if bucket_changed and current_bucket > previous_bucket and total_score <= 650:
        # Determine base reduction
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
        new_limit = current_limit * (1 - final_reduction)

        return {
            'action_type': 'REDUCTION',
            'previous_score': previous_score,
            'current_score': total_score,
            'previous_rating': previous_rating,
            'current_rating': current_rating,
            'bucket_changed': True,
            'base_reduction_pct': round(base_reduction * 100, 1),
            'velocity_multiplier': velocity_multiplier,
            'final_reduction_pct': round(final_reduction * 100, 1),
            'suggested_increase_pct': 0,
            'new_credit_limit': round(new_limit, 2),
            'limit_change_amount': round(new_limit - current_limit, 2),
            'is_frozen': has_active_plan or total_score < 500
        }

    # INCREASES - Suggested if improved from B- or above
    if bucket_changed and current_bucket < previous_bucket and previous_score >= 650:
        # Determine suggested increase based on new bucket
        if total_score >= 900:  # A → A+
            suggested_increase = 0.25
        elif total_score >= 850:  # A- → A
            suggested_increase = 0.20
        elif total_score >= 800:  # B+ → A-
            suggested_increase = 0.15
        elif total_score >= 750:  # B → B+
            suggested_increase = 0.10
        elif total_score >= 700:  # B- → B
            suggested_increase = 0.10
        else:
            suggested_increase = 0

        return {
            'action_type': 'INCREASE_SUGGESTED',
            'previous_score': previous_score,
            'current_score': total_score,
            'previous_rating': previous_rating,
            'current_rating': current_rating,
            'bucket_changed': True,
            'base_reduction_pct': 0,
            'velocity_multiplier': 1.0,
            'final_reduction_pct': 0,
            'suggested_increase_pct': round(suggested_increase * 100, 1),
            'new_credit_limit': current_limit,  # Not changed yet
            'limit_change_amount': 0,
            'is_frozen': has_active_plan,
            'note': 'Requires validation with Engagement Score'
        }

    # NO CHANGE
    return {
        'action_type': 'NO_CHANGE',
        'previous_score': previous_score,
        'current_score': total_score,
        'previous_rating': previous_rating if previous_score else None,
        'current_rating': current_rating,
        'bucket_changed': False,
        'base_reduction_pct': 0,
        'velocity_multiplier': 1.0,
        'final_reduction_pct': 0,
        'suggested_increase_pct': 0,
        'new_credit_limit': current_limit,
        'limit_change_amount': 0,
        'is_frozen': has_active_plan or total_score < 500
    }


def calculate_credit_score(
    client_data: Dict,
    payments_df: pd.DataFrame,
    payment_plans_df: pd.DataFrame,
    previous_score: Optional[float] = None,
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

    payment_plan = calculate_payment_plan_score(payment_plans_df, client_id, reference_date)

    deterioration = calculate_deterioration_velocity(payments_df, client_id, reference_date)

    # Calculate total score
    total_score = (
        payment_perf['total'] +
        payment_plan['total'] +
        deterioration['total']
    )

    # Get rating
    rating = get_credit_rating(total_score)

    # Calculate limit actions
    has_active_plan = payment_plan['active_plans'] > 0
    limit_actions = calculate_limit_actions(
        total_score,
        previous_score,
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
# DPD ALERT SYSTEM
# ============================================================================

def check_dpd_alerts(
    client_id: str,
    client_name: str,
    current_dpd: float,
    payment_history_df: pd.DataFrame,
    reference_date: datetime = None
) -> Dict:
    """
    Two-tier alert system for current DPD vs. payment pattern

    NEW CLIENT (< 3 payments): Tiered absolute thresholds (FPD prevention)
    ESTABLISHED CLIENT (3+ payments): Z-score pattern analysis
    """
    if reference_date is None:
        reference_date = datetime.now()

    # Get 3-month payment history
    client_payments = payment_history_df[payment_history_df['client_id'] == client_id].copy()
    client_payments['payment_date'] = pd.to_datetime(client_payments['payment_date'])
    client_payments['months_ago'] = (
        (reference_date - client_payments['payment_date']).dt.days / 30
    ).round(1)

    recent_3mo = client_payments[client_payments['months_ago'] <= 3]

    # NEW CLIENT - FPD Prevention with tiered thresholds
    if len(recent_3mo) < 3:
        if current_dpd >= 30:
            return {
                'alert': True,
                'client_id': client_id,
                'client_name': client_name,
                'severity': 'CRITICAL',
                'tier': 'ACTION',
                'reason': 'New client 30+ days late - FPD in progress',
                'current_dpd': round(current_dpd, 0),
                'z_score': None,
                'action': '🚨 FREEZE account + Collections immediately',
                'block_new_orders': True,
                'freeze_account': True
            }
        elif current_dpd >= 15:
            return {
                'alert': True,
                'client_id': client_id,
                'client_name': client_name,
                'severity': 'HIGH',
                'tier': 'ACTION',
                'reason': 'New client 15-29 days late - FPD prevention',
                'current_dpd': round(current_dpd, 0),
                'z_score': None,
                'action': '📞 Immediate call + BLOCK NEW ORDERS',
                'block_new_orders': True,
                'freeze_account': False
            }
        elif current_dpd >= 7:
            return {
                'alert': True,
                'client_id': client_id,
                'client_name': client_name,
                'severity': 'WATCH',
                'tier': 'MONITOR',
                'reason': 'New client 7-14 days late - early intervention',
                'current_dpd': round(current_dpd, 0),
                'z_score': None,
                'action': '📞 Call today + educate on payment terms',
                'block_new_orders': False,
                'freeze_account': False
            }
        return {'alert': False}

    # ESTABLISHED CLIENT - Z-score pattern analysis
    avg_dpd_3mo = recent_3mo['days_past_due'].mean()
    std_dpd_3mo = recent_3mo['days_past_due'].std()

    # Apply minimum std_dev of 3 days
    # Prevents false alerts for ultra-consistent payers
    safe_std = max(std_dpd_3mo, 3.0)

    z_score = (current_dpd - avg_dpd_3mo) / safe_std

    if z_score > 2.0:
        severity = 'CRITICAL' if z_score > 3.0 else 'HIGH'
        action = '🚨 Contact IMMEDIATELY' if z_score > 3.0 else '📞 Contact today'
        tier = 'ACTION'
    elif z_score > 1.5:
        severity = 'WATCH'
        tier = 'MONITOR'
        action = '👁️ Watch list + automated reminder'
    else:
        return {'alert': False}

    return {
        'alert': True,
        'client_id': client_id,
        'client_name': client_name,
        'severity': severity,
        'tier': tier,
        'reason': f'Current DPD {current_dpd:.0f} days vs 3mo avg {avg_dpd_3mo:.0f} days',
        'current_dpd': round(current_dpd, 0),
        'z_score': round(z_score, 2),
        'avg_3mo': round(avg_dpd_3mo, 1),
        'deviation_days': round(current_dpd - avg_dpd_3mo, 1),
        'action': action,
        'block_new_orders': False,
        'freeze_account': False
    }


def generate_dpd_alert_report(
    active_loans_df: pd.DataFrame,
    payment_history_df: pd.DataFrame,
    reference_date: datetime = None
) -> pd.DataFrame:
    """Generate daily DPD alert report for all active overdue loans"""
    alerts = []

    for _, loan in active_loans_df.iterrows():
        if loan['current_dpd'] > 0:
            alert = check_dpd_alerts(
                loan['client_id'],
                loan['client_name'],
                loan['current_dpd'],
                payment_history_df,
                reference_date
            )

            if alert['alert']:
                alerts.append(alert)

    if not alerts:
        return pd.DataFrame()

    alerts_df = pd.DataFrame(alerts)
    severity_order = {'CRITICAL': 1, 'HIGH': 2, 'WATCH': 3}
    alerts_df['severity_rank'] = alerts_df['severity'].map(severity_order)
    alerts_df = alerts_df.sort_values(['severity_rank', 'current_dpd'], ascending=[True, False])
    alerts_df = alerts_df.drop('severity_rank', axis=1)

    return alerts_df


# ============================================================================
# SAMPLE DATA GENERATION
# ============================================================================

def generate_sample_data():
    """Generate sample data for testing credit scoring system"""

    reference_date = datetime(2024, 12, 23)

    # CLIENT DATA
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
        },
        {
            'client_id': 'NEW001',
            'client_name': 'Nueva Ferretería',
            'months_as_client': 2,
            'current_credit_limit': 50_000_000,
            'current_outstanding': 15_000_000
        }
    ])

    # PAYMENT HISTORY
    payments_data = []

    # FERR001 - Excellent, improving
    for i in range(20):
        days_late = 5 if i >= 6 else 3
        payment_date = reference_date - timedelta(days=15*i)
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

    # FERR002 - Deteriorating (was 5, now 45)
    for i in range(15):
        dpd = 45 if i < 3 else (20 if i < 6 else 5)
        payment_date = reference_date - timedelta(days=15*i)
        due_date = payment_date - timedelta(days=dpd)
        payments_data.append({
            'client_id': 'FERR002',
            'payment_date': payment_date,
            'due_date': due_date,
            'days_past_due': dpd,
            'payment_amount': 4_000_000
        })

    # NEW001 - New client (only 2 payments)
    for i in range(2):
        payment_date = reference_date - timedelta(days=30*i)
        due_date = payment_date - timedelta(days=5)
        payments_data.append({
            'client_id': 'NEW001',
            'payment_date': payment_date,
            'due_date': due_date,
            'days_past_due': 5,
            'payment_amount': 3_000_000
        })

    payments_df = pd.DataFrame(payments_data)

    # PAYMENT PLANS
    payment_plans_data = [
        {
            'client_id': 'FERR001',
            'plan_start_date': reference_date - timedelta(days=450),
            'plan_end_date': reference_date - timedelta(days=390),
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
            'plan_start_date': reference_date - timedelta(days=30),
            'plan_end_date': None,
            'plan_status': 'active'
        }
    ]

    payment_plans_df = pd.DataFrame(payment_plans_data)

    # ACTIVE LOANS (for DPD alerts)
    active_loans_data = [
        {
            'client_id': 'FERR001',
            'client_name': 'Ferretería El Constructor',
            'loan_id': 'L001',
            'current_dpd': 12,
            'due_date': reference_date - timedelta(days=12)
        },
        {
            'client_id': 'FARM001',
            'client_name': 'Farmacia San José',
            'loan_id': 'L002',
            'current_dpd': 13,
            'due_date': reference_date - timedelta(days=13)
        },
        {
            'client_id': 'FERR002',
            'client_name': 'Ferretería Problemática',
            'loan_id': 'L003',
            'current_dpd': 50,
            'due_date': reference_date - timedelta(days=50)
        },
        {
            'client_id': 'NEW001',
            'client_name': 'Nueva Ferretería',
            'loan_id': 'L004',
            'current_dpd': 8,
            'due_date': reference_date - timedelta(days=8)
        }
    ]

    active_loans_df = pd.DataFrame(active_loans_data)

    return clients, payments_df, payment_plans_df, active_loans_df, reference_date


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""

    print("="*80)
    print("PLATAM CREDIT SCORING SYSTEM V2.0")
    print("="*80)
    print()

    # Generate sample data
    print("Generando datos de prueba...")
    clients, payments_df, payment_plans_df, active_loans_df, reference_date = generate_sample_data()
    print(f"✓ {len(clients)} clientes generados")
    print(f"✓ Fecha de referencia: {reference_date.date()}")
    print()

    # Calculate credit scores
    print("\n" + "="*80)
    print("CÁLCULO DE CREDIT SCORES")
    print("="*80)

    results = []

    for _, client in clients.iterrows():
        print(f"\n{'='*80}")
        print(f"CLIENTE: {client['client_name']} ({client['client_id']})")
        print(f"{'='*80}")

        result = calculate_credit_score(
            client.to_dict(),
            payments_df,
            payment_plans_df,
            previous_score=None,
            reference_date=reference_date
        )

        results.append(result)

        print(f"\n📊 DESGLOSE DE SCORE:")
        print(f"  Payment Performance:    {result['payment_performance']:>6.1f} / 600")
        print(f"  Payment Plan History:   {result['payment_plan_history']:>6.1f} / 150")
        print(f"  Deterioration Velocity: {result['deterioration_velocity']:>6.1f} / 250")
        print(f"  {'─'*45}")
        print(f"  CREDIT SCORE TOTAL:    {result['total_score']:>6.1f} / 1000")
        print(f"  RATING:                 {result['credit_rating']:>6}")

        print(f"\n💰 ACCIONES DE LÍMITE:")
        la = result['limit_actions']
        print(f"  Tipo de Acción:         {la['action_type']}")
        print(f"  Límite Actual:          ${la['new_credit_limit']:>15,.0f}")

        if la['action_type'] == 'REDUCTION':
            print(f"  Reducción Base:         {la['base_reduction_pct']:>6.1f}%")
            print(f"  Multiplicador Velocity: {la['velocity_multiplier']:>6.1f}x")
            print(f"  Reducción Final:        {la['final_reduction_pct']:>6.1f}%")
        elif la['action_type'] == 'INCREASE_SUGGESTED':
            print(f"  Aumento Sugerido:       +{la['suggested_increase_pct']:>6.1f}%")
            print(f"  Nota:                   {la['note']}")

        print(f"  Congelado:              {'SÍ ❄️' if la['is_frozen'] else 'NO'}")

    # Summary table
    print(f"\n\n{'='*80}")
    print("RESUMEN DE CREDIT SCORES")
    print(f"{'='*80}")

    summary = pd.DataFrame([{
        'Cliente': r['client_name'],
        'Score': f"{r['total_score']:.0f}",
        'Rating': r['credit_rating'],
        'Acción': r['limit_actions']['action_type'],
        'Límite': f"${r['limit_actions']['new_credit_limit']:,.0f}"
    } for r in results])

    print(summary.to_string(index=False))

    # DPD Alerts
    print(f"\n\n{'='*80}")
    print("SISTEMA DE ALERTAS DPD (Prevención de FPD)")
    print(f"{'='*80}")

    alerts_df = generate_dpd_alert_report(active_loans_df, payments_df, reference_date)

    if len(alerts_df) > 0:
        action_alerts = alerts_df[alerts_df['tier'] == 'ACTION']
        monitor_alerts = alerts_df[alerts_df['tier'] == 'MONITOR']

        if len(action_alerts) > 0:
            print(f"\n🚨 ACCIÓN REQUERIDA ({len(action_alerts)} clientes)")
            print("─" * 80)
            for _, alert in action_alerts.iterrows():
                print(f"\n{alert['severity']}: {alert['client_name']}")
                print(f"  DPD Actual: {alert['current_dpd']} días")
                if alert['z_score']:
                    print(f"  Z-score: {alert['z_score']}")
                print(f"  Razón: {alert['reason']}")
                print(f"  Acción: {alert['action']}")
                if alert.get('block_new_orders'):
                    print(f"  🚫 BLOQUEAR PEDIDOS")
                if alert.get('freeze_account'):
                    
                    print(f"  ❄️ CONGELAR CUENTA")

        if len(monitor_alerts) > 0:
            print(f"\n\n👁️  LISTA DE VIGILANCIA ({len(monitor_alerts)} clientes)")
            print("─" * 80)
            for _, alert in monitor_alerts.iterrows():
                print(f"\n{alert['client_name']}: {alert['current_dpd']} DPD")
                print(f"  {alert['action']}")
    else:
        print("\n✅ No hay alertas - todos los clientes dentro del patrón normal")

    print("\n" + "="*80)
    print("✅ Sistema ejecutado exitosamente")
    print("="*80)

    return results, clients, payments_df, payment_plans_df, active_loans_df


# ============================================================================
# RUN THE SYSTEM
# ============================================================================

if __name__ == "__main__":
    results, clients, payments_df, payment_plans_df, active_loans_df = main()