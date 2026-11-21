import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import Document
from app.schemas.document import DocumentResponse, DocumentReviewRequest
from app.schemas.finance import InvoiceResponse
from app.services.document_service import DocumentService
from app.core.security import get_current_context, AuthenticatedContext, require_roles

router = APIRouter(prefix="/documents", tags=["Document Intelligence & OCR"])


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("invoice"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """
    Securely uploads a financial document (PDF/image), computes SHA-256 for deduplication,
    executes OCR layout and field extraction, and validates arithmetic & GST rules.
    """
    return await DocumentService.upload_document(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        file=file,
        document_type=document_type,
    )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """List documents uploaded by the authenticated tenant."""
    query = select(Document).where(Document.tenant_id == ctx.tenant_id)
    if status_filter:
        query = query.where(Document.status == status_filter)
    res = await db.execute(query.order_by(Document.created_at.desc()))
    return res.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(get_current_context),
):
    """Retrieve document metadata, extracted fields, bounding boxes, and validation checks."""
    res = await db.execute(
        select(Document).where(Document.tenant_id == ctx.tenant_id, Document.id == document_id)
    )
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return doc


@router.post("/{document_id}/review", response_model=InvoiceResponse)
async def review_and_approve_document(
    document_id: uuid.UUID,
    review: DocumentReviewRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthenticatedContext = Depends(require_roles(["owner", "accountant", "admin"])),
):
    """
    Human Review Queue: Reviewer corrects or confirms extracted values and promotes
    the document into an authoritative Invoice record with full audit tracking.
    """
    return await DocumentService.review_and_approve(
        db=db,
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        document_id=document_id,
        review=review,
    )
