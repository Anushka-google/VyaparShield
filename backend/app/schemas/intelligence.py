import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# --- Receivables Aging ---

class AgingBucketSummary(BaseModel):
    bucket_name: str
    amount: Decimal
    invoice_count: int


class CustomerAgingSummary(BaseModel):
    customer_id: uuid.UUID
    customer_name: str
    total_outstanding: Decimal
    current_amount: Decimal
    days_1_30: Decimal
    days_31_60: Decimal
    days_61_90: Decimal
    days_90_plus: Decimal


class ReceivablesAgingResponse(BaseModel):
    as_of_date: date
    total_receivables: Decimal
    total_overdue: Decimal
    buckets: List[AgingBucketSummary]
    customers: List[CustomerAgingSummary]


# --- Overdue Risk ---

class RiskReason(BaseModel):
    code: str
    description: str
    impact: str  # positive, negative, neutral


class InvoiceRiskScore(BaseModel):
    invoice_id: uuid.UUID
    invoice_number: str
    customer_name: str
    due_date: date
    outstanding_balance: Decimal
    days_until_due_or_overdue: int
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_tier: str  # low, medium, high, critical
    reasons: List[RiskReason]


class OverdueRiskResponse(BaseModel):
    model_version: str
    is_heuristic_baseline: bool
    data_sufficiency_warning: Optional[str] = None
    total_invoices_evaluated: int
    high_risk_invoices_count: int
    invoices: List[InvoiceRiskScore]


class ModelTrainResponse(BaseModel):
    model_version: str
    samples_count: int
    train_samples: int
    test_samples: int
    pr_auc: float
    roc_auc: float
    brier_score_calibration: float
    precision: float
    recall: float
    high_risk_top_decile_precision: float
    data_sufficiency_gate_passed: bool
    message: str


# --- Anomaly Triage ---

class AnomalyAlertResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    alert_type: str
    severity: str
    anomaly_score: float
    status: str
    rule_code: str
    reason: str
    features: Dict[str, Any]
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalyScanResponse(BaseModel):
    scanned_items_count: int
    alerts_generated: int
    alerts: List[AnomalyAlertResponse]


class AnomalyTriageRequest(BaseModel):
    status: str = Field(..., pattern="^(open|expected|suspicious|investigating|dismissed)$")
    reviewer_notes: Optional[str] = None


# --- Cash Flow Forecast ---

class DailyForecastPoint(BaseModel):
    forecast_date: date
    expected_inflows: Decimal
    expected_outflows: Decimal
    net_cash_flow: Decimal
    cumulative_cash_position: Decimal
    lower_bound_80: Decimal
    upper_bound_80: Decimal
    lower_bound_95: Decimal
    upper_bound_95: Decimal


class ScenarioForecast(BaseModel):
    scenario_name: str
    total_inflows: Decimal
    total_outflows: Decimal
    net_flow: Decimal
    daily_points: List[DailyForecastPoint]


class ForecastEvaluationMetrics(BaseModel):
    mae: float
    rmse: float
    forecast_bias: float
    naive_baseline_mae: float
    seasonal_naive_mae: float


class CashFlowForecastResponse(BaseModel):
    horizon_days: int
    as_of_date: date
    starting_cash_estimate: Decimal
    scenarios: Dict[str, ScenarioForecast]
    evaluation_metrics: ForecastEvaluationMetrics
    data_sufficiency_note: Optional[str] = None
    model_version: str
