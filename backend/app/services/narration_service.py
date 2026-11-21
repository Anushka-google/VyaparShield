import re
from typing import List, Optional
from app.schemas.reconciliation import NormalizedNarration


class NarrationService:
    """
    Parses and normalizes noisy Indian banking narrations (UPI, NEFT, IMPS, RTGS, CHEQUE).
    Extracts transaction reference / UTR, counterparty hints, and invoice reference numbers.
    """

    # Common Indian Bank transaction prefixes and regex patterns
    UPI_PATTERN = re.compile(r"UPI(?:/|-)(?:CR/)?([A-Za-z0-9]+)(?:/|-)([^/]+)", re.IGNORECASE)
    NEFT_PATTERN = re.compile(r"NEFT(?:/|-)(?:CR/)?([A-Za-z0-9]+)(?:/|-)([^/]+)", re.IGNORECASE)
    RTGS_PATTERN = re.compile(r"RTGS(?:/|-)(?:CR/)?([A-Za-z0-9]+)(?:/|-)([^/]+)", re.IGNORECASE)
    IMPS_PATTERN = re.compile(r"IMPS(?:/|-)(?:P2A/|P2P/)?([A-Za-z0-9]+)(?:/|-)([^/]+)", re.IGNORECASE)
    CHQ_PATTERN = re.compile(r"(?:CHQ|CHEQUE|CTS)\s*(?:NO\.?)?\s*([0-9]+)", re.IGNORECASE)

    # Invoice reference pattern (e.g. INV-2026-001, INV/001, BILL-102, #1001)
    INVOICE_REF_PATTERN = re.compile(r"\b(?:INV[-_/][0-9]{4}[-_/][0-9]+|INV[-_/]?[0-9]{3,}|BILL[-_/]?[0-9]+|#[0-9]{3,})\b", re.IGNORECASE)

    @classmethod
    def normalize(cls, raw: str) -> NormalizedNarration:
        text = raw.strip()
        payment_mode = "OTHER"
        ref_num: Optional[str] = None
        utr: Optional[str] = None
        counterparty: Optional[str] = None

        upper_text = text.upper()

        if "UPI" in upper_text:
            payment_mode = "UPI"
            match = cls.UPI_PATTERN.search(text)
            if match:
                ref_num = match.group(1).strip()
                utr = ref_num
                counterparty = cls._clean_party(match.group(2))
        elif "NEFT" in upper_text:
            payment_mode = "NEFT"
            match = cls.NEFT_PATTERN.search(text)
            if match:
                ref_num = match.group(1).strip()
                utr = ref_num
                counterparty = cls._clean_party(match.group(2))
        elif "RTGS" in upper_text:
            payment_mode = "RTGS"
            match = cls.RTGS_PATTERN.search(text)
            if match:
                ref_num = match.group(1).strip()
                utr = ref_num
                counterparty = cls._clean_party(match.group(2))
        elif "IMPS" in upper_text:
            payment_mode = "IMPS"
            match = cls.IMPS_PATTERN.search(text)
            if match:
                ref_num = match.group(1).strip()
                utr = ref_num
                counterparty = cls._clean_party(match.group(2))
        elif "CHQ" in upper_text or "CHEQUE" in upper_text:
            payment_mode = "CHEQUE"
            match = cls.CHQ_PATTERN.search(text)
            if match:
                ref_num = match.group(1).strip()

        # Extract potential invoice references
        inv_matches = cls.INVOICE_REF_PATTERN.findall(text)
        cleaned_inv_refs = list(set([r.strip("#").strip() for r in inv_matches]))

        # Fallback counterparty extraction if not caught by pattern
        if not counterparty and ("/" in text or "-" in text):
            parts = [p.strip() for p in re.split(r"[/|-]", text) if len(p.strip()) > 3]
            for part in parts:
                if not re.search(r"^[0-9]+$", part) and part.upper() not in ["UPI", "NEFT", "RTGS", "IMPS", "CR", "DR", "P2A"]:
                    counterparty = cls._clean_party(part)
                    break

        return NormalizedNarration(
            raw_narration=raw,
            payment_mode=payment_mode,
            reference_number=ref_num,
            utr_number=utr,
            counterparty_name=counterparty,
            invoice_references=cleaned_inv_refs,
        )

    @staticmethod
    def _clean_party(raw_name: str) -> str:
        cleaned = re.sub(r"(\.IN|\.COM|@.*|PAYMENT FOR.*|INV.*)", "", raw_name, flags=re.IGNORECASE)
        cleaned = re.sub(r"[/_-]", " ", cleaned).strip()
        return cleaned
