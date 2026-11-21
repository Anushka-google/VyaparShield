from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.users import router as users_router
from app.api.v1.parties import router as parties_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.payments import router as payments_router
from app.api.v1.audit import router as audit_router

from app.api.v1.documents import router as documents_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.intelligence import router as intelligence_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(tenants_router)
api_router.include_router(users_router)
api_router.include_router(parties_router)
api_router.include_router(invoices_router)
api_router.include_router(payments_router)
api_router.include_router(documents_router)
api_router.include_router(reconciliation_router)
api_router.include_router(intelligence_router)
api_router.include_router(audit_router)
