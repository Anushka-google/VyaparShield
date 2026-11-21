import uuid
import pytest
from decimal import Decimal
from datetime import date, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.entities import Organization, User, Membership, Customer, Invoice, Payment
from app.services.finance_service import FinanceService
from app.services.risk_service import RiskService
from app.services.anomaly_service import AnomalyService
from app.services.forecast_service import ForecastService
from app.schemas.intelligence import AnomalyTriageRequest
from app.core.security import create_access_token


@pytest.fixture
async def sample_intelligence_data(db_session):
    # Setup Tenant & Admin User
    tenant = Organization(name="Intelligence Test Corp", currency="INR")
    db_session.add(tenant)
    await db_session.flush()

    user = User(email="intel_admin@test.com", hashed_password="hashed_pwd", full_name="Intel Admin", is_active=True)
    db_session.add(user)
    await db_session.flush()

    mem = Membership(tenant_id=tenant.id, user_id=user.id, role="owner")
    db_session.add(mem)

    # Setup Customers
    cust_reliable = Customer(tenant_id=tenant.id, name="Reliable Corp", credit_period_days=30)
    cust_late = Customer(tenant_id=tenant.id, name="Slow Payer Ltd", credit_period_days=15)
    db_session.add_all([cust_reliable, cust_late])
    await db_session.flush()

    as_of = date(2026, 11, 1)

    # Invoices for Aging and Risk
    # 1. Current (due in 10 days)
    inv_curr = Invoice(
        tenant_id=tenant.id,
        customer_id=cust_reliable.id,
        invoice_number="INV-AGING-01",
        invoice_date=as_of - timedelta(days=20),
        due_date=as_of + timedelta(days=10),
        subtotal=Decimal("10000.00"),
        cgst_amount=Decimal("900.00"),
        sgst_amount=Decimal("900.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("11800.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("11800.00"),
        status="approved",
    )
    # 2. 1-30 days overdue
    inv_30 = Invoice(
        tenant_id=tenant.id,
        customer_id=cust_late.id,
        invoice_number="INV-AGING-02",
        invoice_date=as_of - timedelta(days=40),
        due_date=as_of - timedelta(days=10),
        subtotal=Decimal("20000.00"),
        cgst_amount=Decimal("1800.00"),
        sgst_amount=Decimal("1800.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("23600.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("23600.00"),
        status="approved",
    )
    # 3. 31-60 days overdue
    inv_60 = Invoice(
        tenant_id=tenant.id,
        customer_id=cust_late.id,
        invoice_number="INV-AGING-03",
        invoice_date=as_of - timedelta(days=75),
        due_date=as_of - timedelta(days=45),
        subtotal=Decimal("15000.00"),
        cgst_amount=Decimal("1350.00"),
        sgst_amount=Decimal("1350.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("17700.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("17700.00"),
        status="overdue",
    )
    # 4. 61-90 days overdue
    inv_90 = Invoice(
        tenant_id=tenant.id,
        customer_id=cust_late.id,
        invoice_number="INV-AGING-04",
        invoice_date=as_of - timedelta(days=105),
        due_date=as_of - timedelta(days=75),
        subtotal=Decimal("8000.00"),
        cgst_amount=Decimal("720.00"),
        sgst_amount=Decimal("720.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("9440.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("9440.00"),
        status="overdue",
    )
    # 5. 90+ days overdue
    inv_old = Invoice(
        tenant_id=tenant.id,
        customer_id=cust_late.id,
        invoice_number="INV-AGING-05",
        invoice_date=as_of - timedelta(days=150),
        due_date=as_of - timedelta(days=120),
        subtotal=Decimal("5000.00"),
        cgst_amount=Decimal("450.00"),
        sgst_amount=Decimal("450.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("5900.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("5900.00"),
        status="overdue",
    )
    db_session.add_all([inv_curr, inv_30, inv_60, inv_90, inv_old])
    await db_session.commit()

    return {
        "tenant": tenant,
        "user": user,
        "cust_reliable": cust_reliable,
        "cust_late": cust_late,
        "as_of": as_of,
    }


@pytest.mark.asyncio
async def test_receivables_aging_buckets(db_session, sample_intelligence_data):
    """Test deterministic SQL receivables aging across standard Indian MSME aging buckets."""
    t = sample_intelligence_data["tenant"]
    as_of = sample_intelligence_data["as_of"]

    res = await RiskService.get_receivables_aging(db_session, t.id, as_of)

    # Total receivables: 11800 + 23600 + 17700 + 9440 + 5900 = 68440.00
    assert res.total_receivables == Decimal("68440.00")
    # Total overdue (everything except Current): 68440 - 11800 = 56640.00
    assert res.total_overdue == Decimal("56640.00")

    bucket_dict = {b.bucket_name: b.amount for b in res.buckets}
    assert bucket_dict["Current"] == Decimal("11800.00")
    assert bucket_dict["1-30 Days"] == Decimal("23600.00")
    assert bucket_dict["31-60 Days"] == Decimal("17700.00")
    assert bucket_dict["61-90 Days"] == Decimal("9440.00")
    assert bucket_dict["90+ Days"] == Decimal("5900.00")

    # Customer breakdowns
    assert len(res.customers) == 2
    late_summary = next(c for c in res.customers if c.customer_name == "Slow Payer Ltd")
    assert late_summary.total_outstanding == Decimal("56640.00")
    assert late_summary.current_amount == Decimal("0.00")


@pytest.mark.asyncio
async def test_overdue_risk_baseline_and_reason_codes(db_session, sample_intelligence_data):
    """Test overdue risk scoring, heuristic baseline, and explainable reason codes."""
    t = sample_intelligence_data["tenant"]
    as_of = sample_intelligence_data["as_of"]

    eval_res = await RiskService.evaluate_overdue_risk(db_session, t.id, as_of)

    assert eval_res.is_heuristic_baseline is True
    assert eval_res.data_sufficiency_warning is not None
    assert eval_res.total_invoices_evaluated == 5

    # Check that severely overdue invoice has higher risk than current invoice
    inv_curr_res = next(i for i in eval_res.invoices if i.invoice_number == "INV-AGING-01")
    inv_old_res = next(i for i in eval_res.invoices if i.invoice_number == "INV-AGING-05")

    assert inv_old_res.risk_score > inv_curr_res.risk_score
    assert inv_old_res.risk_tier in ["high", "critical"]

    # Verify explainable reason codes
    old_reason_codes = [r.code for r in inv_old_res.reasons]
    assert "ALREADY_OVERDUE" in old_reason_codes


@pytest.mark.asyncio
async def test_overdue_risk_ml_training_and_chronological_split(db_session, sample_intelligence_data):
    """Test scikit-learn classifier training with chronological train/test split when data >= 20."""
    t = sample_intelligence_data["tenant"]
    cust = sample_intelligence_data["cust_reliable"]
    as_of = sample_intelligence_data["as_of"]

    # 1. First verify data sufficiency gate when < 20 samples
    train_res_early = await RiskService.train_risk_model(db_session, t.id)
    assert train_res_early.data_sufficiency_gate_passed is False
    assert "minimum 20 required" in train_res_early.message

    # 2. Add 20 historical paid/overdue invoices to pass the data gate
    for i in range(22):
        inv = Invoice(
            tenant_id=t.id,
            customer_id=cust.id,
            invoice_number=f"HIST-INV-{i:03d}",
            invoice_date=as_of - timedelta(days=200 - (i * 8)),
            due_date=as_of - timedelta(days=170 - (i * 8)),
            subtotal=Decimal("10000.00"),
            cgst_amount=Decimal("900.00"),
            sgst_amount=Decimal("900.00"),
            igst_amount=Decimal("0.00"),
            total_amount=Decimal("11800.00"),
            paid_amount=Decimal("11800.00") if i % 2 == 0 else Decimal("0.00"),
            outstanding_balance=Decimal("0.00") if i % 2 == 0 else Decimal("11800.00"),
            status="paid" if i % 2 == 0 else "overdue",
        )
        db_session.add(inv)
    await db_session.commit()

    # 3. Train model with chronological split
    train_res = await RiskService.train_risk_model(db_session, t.id)
    assert train_res.data_sufficiency_gate_passed is True
    assert train_res.samples_count >= 20
    assert train_res.train_samples > 0
    assert train_res.test_samples > 0
    assert train_res.pr_auc > 0.0
    assert train_res.roc_auc > 0.0
    assert train_res.brier_score_calibration >= 0.0

    # 4. Verify evaluate_overdue_risk now uses ML model instead of heuristic baseline
    eval_post_train = await RiskService.evaluate_overdue_risk(db_session, t.id, as_of)
    assert eval_post_train.is_heuristic_baseline is False
    assert "ml-risk-logreg" in eval_post_train.model_version


@pytest.mark.asyncio
async def test_anomaly_detection_rules_and_triage(db_session, sample_intelligence_data):
    """Test deterministic anomaly rules (duplicate, amount outlier, velocity) and triage workflow."""
    t = sample_intelligence_data["tenant"]
    u = sample_intelligence_data["user"]
    cust = sample_intelligence_data["cust_reliable"]
    as_of = sample_intelligence_data["as_of"]

    # Inject Anomaly 1: Rapid Identical Amount for Same Customer
    dup_inv1 = Invoice(
        tenant_id=t.id,
        customer_id=cust.id,
        invoice_number="ANOM-DUP-999-A",
        invoice_date=as_of,
        due_date=as_of + timedelta(days=30),
        subtotal=Decimal("5000.00"),
        cgst_amount=Decimal("0.00"),
        sgst_amount=Decimal("0.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("5000.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("5000.00"),
        status="approved",
    )
    dup_inv2 = Invoice(
        tenant_id=t.id,
        customer_id=cust.id,
        invoice_number="ANOM-DUP-999-B",  # Identical amount within 48h!
        invoice_date=as_of,
        due_date=as_of + timedelta(days=30),
        subtotal=Decimal("5000.00"),
        cgst_amount=Decimal("0.00"),
        sgst_amount=Decimal("0.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("5000.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("5000.00"),
        status="approved",
    )
    # Inject Anomaly 2: Extreme Amount Outlier
    spike_inv = Invoice(
        tenant_id=t.id,
        customer_id=cust.id,
        invoice_number="SPIKE-INV-001",
        invoice_date=as_of,
        due_date=as_of + timedelta(days=30),
        subtotal=Decimal("1500000.00"),  # ₹15 Lakhs vs normal ₹10k
        cgst_amount=Decimal("0.00"),
        sgst_amount=Decimal("0.00"),
        igst_amount=Decimal("0.00"),
        total_amount=Decimal("1500000.00"),
        paid_amount=Decimal("0.00"),
        outstanding_balance=Decimal("1500000.00"),
        status="approved",
    )
    db_session.add_all([dup_inv1, dup_inv2, spike_inv])
    await db_session.commit()

    # Scan anomalies
    scan_res = await AnomalyService.scan_anomalies(db_session, t.id)
    assert scan_res.alerts_generated >= 1

    rule_codes = [a.rule_code for a in scan_res.alerts]
    assert "ANOM-01" in rule_codes or "ANOM-02" in rule_codes or "ANOM-04" in rule_codes

    # Triage workflow: Human accountant marks alert as suspicious
    target_alert = scan_res.alerts[0]
    triage_req = AnomalyTriageRequest(status="suspicious", reviewer_notes="Confirmed unexpected high-value spike")
    triaged = await AnomalyService.triage_alert(db_session, t.id, target_alert.id, u.id, triage_req)

    assert triaged.status == "suspicious"
    assert triaged.reviewer_notes == "Confirmed unexpected high-value spike"


@pytest.mark.asyncio
async def test_cash_flow_forecast_scenarios_and_bounds(db_session, sample_intelligence_data):
    """Test multi-scenario cash flow forecasting with 80%/95% confidence intervals and baseline comparison."""
    t = sample_intelligence_data["tenant"]
    as_of = sample_intelligence_data["as_of"]

    res = await ForecastService.generate_forecast(db_session, t.id, horizon_days=30, as_of_date=as_of)

    assert res.horizon_days == 30
    assert "base" in res.scenarios
    assert "best" in res.scenarios
    assert "worst" in res.scenarios

    base = res.scenarios["base"]
    best = res.scenarios["best"]
    worst = res.scenarios["worst"]

    assert len(base.daily_points) == 30
    # In best scenario, net cash flow should exceed worst scenario
    assert best.total_inflows >= worst.total_inflows

    # Check uncertainty interval monotonic dispersion on base trajectory
    p = base.daily_points[15]
    assert p.lower_bound_95 <= p.lower_bound_80
    assert p.lower_bound_80 <= p.cumulative_cash_position
    assert p.cumulative_cash_position <= p.upper_bound_80
    assert p.upper_bound_80 <= p.upper_bound_95

    # Check baseline error benchmarks
    assert res.evaluation_metrics.mae > 0
    assert res.evaluation_metrics.naive_baseline_mae > 0


@pytest.mark.asyncio
async def test_intelligence_api_endpoints_via_client(db_session, sample_intelligence_data):
    """Test all Phase 3 endpoints via HTTP client with Bearer authorization."""
    t = sample_intelligence_data["tenant"]
    u = sample_intelligence_data["user"]

    token = create_access_token({
        "sub": str(u.id),
        "tenant_id": str(t.id),
        "role": "owner",
        "email": u.email,
    })
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Aging endpoint
        r1 = await client.get("/api/v1/intelligence/receivables-aging", headers=headers)
        assert r1.status_code == 200
        assert "buckets" in r1.json()

        # 2. Overdue risk endpoint
        r2 = await client.get("/api/v1/intelligence/overdue-risk", headers=headers)
        assert r2.status_code == 200
        assert "invoices" in r2.json()

        # 3. Anomaly scan endpoint
        r3 = await client.post("/api/v1/intelligence/anomalies/scan", headers=headers)
        assert r3.status_code == 200
        assert "alerts" in r3.json()

        # 4. Cash flow forecast endpoint
        r4 = await client.get("/api/v1/intelligence/cash-flow-forecast?horizon_days=30", headers=headers)
        assert r4.status_code == 200
        assert "scenarios" in r4.json()
