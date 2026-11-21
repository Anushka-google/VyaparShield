import uuid
from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Optional, Any, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Invoice, Payment, Customer, AnomalyAlert, User
from app.schemas.intelligence import (
    AnomalyAlertResponse,
    AnomalyScanResponse,
    AnomalyTriageRequest,
)
from app.database.session import round_currency


class AnomalyService:
    @classmethod
    async def scan_anomalies(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        max_alerts_limit: int = 25,
    ) -> AnomalyScanResponse:
        """Executes multi-rule deterministic checks and unsupervised ML anomaly scoring across tenant invoices and payments."""
        alerts: List[AnomalyAlert] = []

        # 1. Fetch recent invoices & customer context
        inv_stmt = (
            select(Invoice)
            .options(selectinload(Invoice.customer))
            .where(Invoice.tenant_id == tenant_id)
            .order_by(Invoice.created_at.desc())
        )
        inv_res = await db.execute(inv_stmt)
        invoices = inv_res.scalars().all()

        # 2. Fetch existing alerts to avoid re-alerting duplicate open issues
        existing_alerts_res = await db.execute(
            select(AnomalyAlert.rule_code, AnomalyAlert.entity_id)
            .where(AnomalyAlert.tenant_id == tenant_id, AnomalyAlert.status.in_(["open", "investigating"]))
        )
        existing_signatures = set(existing_alerts_res.all())

        # Precompute customer transaction amounts for statistical baseline
        customer_amounts: Dict[uuid.UUID, List[float]] = {}
        for inv in invoices:
            cid = inv.customer_id
            if cid not in customer_amounts:
                customer_amounts[cid] = []
            customer_amounts[cid].append(float(inv.total_amount))

        # --- Rule ANOM-01: Duplicate Invoice Number / Rapid Identical Amount ---
        seen_numbers: Dict[str, Invoice] = {}
        seen_amounts_per_customer: Dict[Tuple[uuid.UUID, float], List[Invoice]] = {}

        for inv in invoices:
            # Duplicate invoice number within tenant
            num_clean = inv.invoice_number.strip().upper()
            if num_clean in seen_numbers:
                prev_inv = seen_numbers[num_clean]
                sig = ("ANOM-01", inv.id)
                if sig not in existing_signatures:
                    alerts.append(AnomalyAlert(
                        tenant_id=tenant_id,
                        entity_type="invoice",
                        entity_id=inv.id,
                        alert_type="duplicate_invoice",
                        severity="high",
                        anomaly_score=Decimal("0.9000"),
                        rule_code="ANOM-01",
                        reason=f"Duplicate invoice number '{inv.invoice_number}' matches existing invoice ID {prev_inv.id}.",
                        features={
                            "invoice_number": inv.invoice_number,
                            "duplicate_of_id": str(prev_inv.id),
                            "amount": float(inv.total_amount),
                            "date": str(inv.invoice_date),
                        },
                    ))
            else:
                seen_numbers[num_clean] = inv

            # Identical amount within 48h for same customer
            amt_key = (inv.customer_id, float(inv.total_amount))
            if amt_key in seen_amounts_per_customer:
                for prior_inv in seen_amounts_per_customer[amt_key]:
                    diff_days = abs((inv.invoice_date - prior_inv.invoice_date).days)
                    if diff_days <= 2 and inv.id != prior_inv.id:
                        sig = ("ANOM-01-AMT", inv.id)
                        if sig not in existing_signatures:
                            alerts.append(AnomalyAlert(
                                tenant_id=tenant_id,
                                entity_type="invoice",
                                entity_id=inv.id,
                                alert_type="duplicate_invoice",
                                severity="medium",
                                anomaly_score=Decimal("0.7500"),
                                rule_code="ANOM-01-AMT",
                                reason=f"Identical billing amount ₹{inv.total_amount:,.2f} issued to same customer within {diff_days} day(s).",
                                features={
                                    "customer_name": inv.customer.name if inv.customer else "Unknown",
                                    "amount": float(inv.total_amount),
                                    "days_between": diff_days,
                                    "prior_invoice_number": prior_inv.invoice_number,
                                },
                            ))
                            break
                seen_amounts_per_customer[amt_key].append(inv)
            else:
                seen_amounts_per_customer[amt_key] = [inv]

        # --- Rule ANOM-02: Amount Outlier (> 3 Standard Deviations / Extreme IQR) ---
        for inv in invoices:
            hist = customer_amounts.get(inv.customer_id, [])
            if len(hist) >= 4:
                mean_val = float(np.mean(hist))
                std_val = float(np.std(hist))
                inv_amt = float(inv.total_amount)
                if std_val > 0:
                    z_score = (inv_amt - mean_val) / std_val
                    if z_score >= 3.0:
                        sig = ("ANOM-02", inv.id)
                        if sig not in existing_signatures:
                            alerts.append(AnomalyAlert(
                                tenant_id=tenant_id,
                                entity_type="invoice",
                                entity_id=inv.id,
                                alert_type="unusual_amount",
                                severity="high" if z_score >= 4.0 else "medium",
                                anomaly_score=Decimal(str(min(0.98, round(0.60 + z_score * 0.08, 4)))),
                                rule_code="ANOM-02",
                                reason=f"Invoice amount ₹{inv_amt:,.2f} is {z_score:.1f} standard deviations above customer historical mean of ₹{mean_val:,.2f}.",
                                features={
                                    "amount": inv_amt,
                                    "customer_mean": round(mean_val, 2),
                                    "z_score": round(z_score, 2),
                                    "historical_transactions_count": len(hist),
                                },
                            ))

        # --- Rule ANOM-03: Velocity Spikes (> 3 Invoices within 24h) ---
        customer_date_counts: Dict[Tuple[uuid.UUID, date], List[Invoice]] = {}
        for inv in invoices:
            key = (inv.customer_id, inv.invoice_date)
            customer_date_counts.setdefault(key, []).append(inv)

        for (cid, dt), day_invoices in customer_date_counts.items():
            if len(day_invoices) >= 4:
                for inv in day_invoices:
                    sig = ("ANOM-03", inv.id)
                    if sig not in existing_signatures:
                        alerts.append(AnomalyAlert(
                            tenant_id=tenant_id,
                            entity_type="invoice",
                            entity_id=inv.id,
                            alert_type="velocity_spike",
                            severity="medium",
                            anomaly_score=Decimal("0.7000"),
                            rule_code="ANOM-03",
                            reason=f"Abnormal billing velocity: {len(day_invoices)} invoices generated for single customer on {dt}.",
                            features={
                                "count_on_date": len(day_invoices),
                                "invoice_date": str(dt),
                                "customer_id": str(cid),
                            },
                        ))

        # --- Rule ANOM-04: Suspicious Round Amount on High Values ---
        for inv in invoices:
            amt = float(inv.total_amount)
            if amt >= 50000.0 and (amt % 10000.0 == 0.0):
                sig = ("ANOM-04", inv.id)
                if sig not in existing_signatures:
                    alerts.append(AnomalyAlert(
                        tenant_id=tenant_id,
                        entity_type="invoice",
                        entity_id=inv.id,
                        alert_type="round_number_surge",
                        severity="low",
                        anomaly_score=Decimal("0.5500"),
                        rule_code="ANOM-04",
                        reason=f"Exact round amount of ₹{amt:,.2f} with zero paise on high-value transaction.",
                        features={
                            "amount": amt,
                            "round_multiple": 10000,
                        },
                    ))

        # --- Unsupervised ML Scoring: IsolationForest for Multidimensional Outliers ---
        if len(invoices) >= 10:
            feat_matrix = []
            inv_ref_list = []
            for inv in invoices:
                amt = float(inv.total_amount)
                day_w = inv.invoice_date.weekday()
                lines_count = len(inv.lines) if inv.lines else 1
                feat_matrix.append([amt, float(day_w), float(lines_count)])
                inv_ref_list.append(inv)

            X_mat = np.array(feat_matrix)
            iso_forest = IsolationForest(contamination=0.10, random_state=42)
            preds = iso_forest.fit_predict(X_mat)
            scores = -iso_forest.decision_function(X_mat)  # higher = more anomalous

            for idx, pred in enumerate(preds):
                if pred == -1:  # Anomaly detected by IsolationForest
                    inv = inv_ref_list[idx]
                    sig = ("ANOM-ML", inv.id)
                    if sig not in existing_signatures:
                        raw_s = float(scores[idx])
                        normalized_score = min(0.95, max(0.50, (raw_s + 0.2) * 1.5))
                        alerts.append(AnomalyAlert(
                            tenant_id=tenant_id,
                            entity_type="invoice",
                            entity_id=inv.id,
                            alert_type="ml_outlier",
                            severity="medium" if normalized_score < 0.8 else "high",
                            anomaly_score=Decimal(str(round(normalized_score, 4))),
                            rule_code="ANOM-ML",
                            reason="Unsupervised multi-feature outlier identified by IsolationForest pattern detector.",
                            features={
                                "amount": float(inv.total_amount),
                                "day_of_week": inv.invoice_date.strftime("%A"),
                                "anomaly_raw_score": round(raw_s, 4),
                            },
                        ))

        # Volume control: sort by severity/score descending and cap at max_alerts_limit
        alerts.sort(key=lambda a: float(a.anomaly_score), reverse=True)
        throttled_alerts = alerts[:max_alerts_limit]

        # Save new alerts to database
        for a in throttled_alerts:
            db.add(a)
        if throttled_alerts:
            await db.commit()

        # Query all active alerts to return full queue
        active_stmt = (
            select(AnomalyAlert)
            .where(AnomalyAlert.tenant_id == tenant_id, AnomalyAlert.status != "dismissed")
            .order_by(AnomalyAlert.anomaly_score.desc())
        )
        active_res = await db.execute(active_stmt)
        all_active = active_res.scalars().all()

        return AnomalyScanResponse(
            scanned_items_count=len(invoices),
            alerts_generated=len(throttled_alerts),
            alerts=[AnomalyAlertResponse.model_validate(a) for a in all_active],
        )

    @classmethod
    async def get_active_alerts(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        status_filter: Optional[str] = None,
    ) -> List[AnomalyAlertResponse]:
        """Lists active anomaly alerts for human reviewer triage."""
        stmt = (
            select(AnomalyAlert)
            .where(AnomalyAlert.tenant_id == tenant_id)
            .order_by(AnomalyAlert.anomaly_score.desc())
        )
        if status_filter:
            stmt = stmt.where(AnomalyAlert.status == status_filter)

        res = await db.execute(stmt)
        alerts = res.scalars().all()
        return [AnomalyAlertResponse.model_validate(a) for a in alerts]

    @classmethod
    async def triage_alert(
        cls,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        alert_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        request: AnomalyTriageRequest,
    ) -> AnomalyAlertResponse:
        """Enables human reviewer to label alert as expected, suspicious, or investigating."""
        stmt = select(AnomalyAlert).where(
            AnomalyAlert.id == alert_id,
            AnomalyAlert.tenant_id == tenant_id,
        )
        res = await db.execute(stmt)
        alert = res.scalar_one_or_none()
        if not alert:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Anomaly alert not found.")

        alert.status = request.status
        alert.reviewer_id = reviewer_id
        alert.reviewer_notes = request.reviewer_notes
        alert.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)
        return AnomalyAlertResponse.model_validate(alert)
