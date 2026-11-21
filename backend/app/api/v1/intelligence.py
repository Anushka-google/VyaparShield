import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.security import require_roles, AuthenticatedContext
from app.schemas.intelligence import (
    ReceivablesAgingResponse,
    OverdueRiskResponse,
    ModelTrainResponse,
    AnomalyScanResponse,
    AnomalyAlertResponse,
    AnomalyTriageRequest,
    CashFlowForecastResponse,
)
from app.services.risk_service import RiskService
from app.services.anomaly_service import AnomalyService
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/intelligence", tags=["Financial Intelligence & ML"])


@router.get("/receivables-aging", response_model=ReceivablesAgingResponse)
async def get_receivables_aging(
    as_of_date: Optional[date] = None,
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant", "reviewer"])),
    db: AsyncSession = Depends(get_db),
):
    """Computes deterministic receivables aging across standard buckets (Current, 1-30, 31-60, 61-90, 90+ days)."""
    return await RiskService.get_receivables_aging(db, ctx.tenant_id, as_of_date)


@router.get("/overdue-risk", response_model=OverdueRiskResponse)
async def get_overdue_risk(
    as_of_date: Optional[date] = None,
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant", "reviewer"])),
    db: AsyncSession = Depends(get_db),
):
    """Evaluates overdue and default probability for open invoices with reason codes and data-sufficiency indicators."""
    return await RiskService.evaluate_overdue_risk(db, ctx.tenant_id, as_of_date)


@router.post("/overdue-risk/train", response_model=ModelTrainResponse)
async def train_overdue_risk_model(
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant"])),
    db: AsyncSession = Depends(get_db),
):
    """Trains scikit-learn overdue risk classifier using chronological split with calibration & PR-AUC evaluation."""
    return await RiskService.train_risk_model(db, ctx.tenant_id)


@router.get("/anomalies", response_model=List[AnomalyAlertResponse])
async def get_anomalies(
    status: Optional[str] = None,
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant", "reviewer"])),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves active anomaly triage queue with explainable features and scores."""
    return await AnomalyService.get_active_alerts(db, ctx.tenant_id, status)


@router.post("/anomalies/scan", response_model=AnomalyScanResponse)
async def scan_for_anomalies(
    max_alerts: int = Query(25, ge=1, le=100),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant"])),
    db: AsyncSession = Depends(get_db),
):
    """Executes deterministic rules and IsolationForest ML scoring to identify financial and operational outliers."""
    return await AnomalyService.scan_anomalies(db, ctx.tenant_id, max_alerts_limit=max_alerts)


@router.post("/anomalies/{alert_id}/triage", response_model=AnomalyAlertResponse)
async def triage_anomaly_alert(
    alert_id: uuid.UUID,
    request: AnomalyTriageRequest,
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant", "reviewer"])),
    db: AsyncSession = Depends(get_db),
):
    """Allows accountants or reviewers to triage an anomaly alert (expected, suspicious, investigating, dismissed)."""
    return await AnomalyService.triage_alert(db, ctx.tenant_id, alert_id, ctx.user_id, request)


@router.get("/cash-flow-forecast", response_model=CashFlowForecastResponse)
async def get_cash_flow_forecast(
    horizon_days: int = Query(30, ge=7, le=90),
    as_of_date: Optional[date] = None,
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "admin", "accountant", "reviewer"])),
    db: AsyncSession = Depends(get_db),
):
    """Generates multi-scenario (base, best, worst) daily cash flow projections with 80%/95% confidence intervals and baseline error benchmarks."""
    return await ForecastService.generate_forecast(db, ctx.tenant_id, horizon_days, as_of_date)
