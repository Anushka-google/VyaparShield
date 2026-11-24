import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.entities import Organization, User, Membership, Customer, Invoice
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_deactivated_user_token_is_rejected():
    """
    Security Invariant: A user whose account is marked is_active=False must be
    immediately blocked from using existing valid JWT tokens (403 Forbidden).
    """
    async with TestingSessionLocal() as db:
        org = Organization(name="Security Org Alpha")
        db.add(org)
        await db.flush()

        user = User(
            email="revoked.user@example.com",
            hashed_password=get_password_hash("testpass"),
            full_name="Revoked User",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        membership = Membership(tenant_id=org.id, user_id=user.id, role="accountant")
        db.add(membership)
        await db.commit()

        token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(org.id),
            "role": "accountant",
            "email": user.email,
        })
        user_id = user.id

    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initial access succeeds while user is active
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/invoices", headers=headers)
        assert resp.status_code == 200

    # 2. Deactivate the user in the database
    async with TestingSessionLocal() as db:
        db_user = await db.get(User, user_id)
        assert db_user is not None
        db_user.is_active = False
        await db.commit()

    # 3. Subsequent request with the same valid JWT must now be rejected
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_revoked = await client.get("/api/v1/invoices", headers=headers)
        assert resp_revoked.status_code == 403
        data = resp_revoked.json()
        assert "deactivated" in data["detail"] or "revoked" in data["detail"]


@pytest.mark.asyncio
async def test_removed_membership_token_is_rejected():
    """
    Security Invariant: A user whose membership in an organization was revoked
    must be immediately rejected when presenting a token for that tenant (403 Forbidden).
    """
    async with TestingSessionLocal() as db:
        org = Organization(name="Security Org Beta")
        db.add(org)
        await db.flush()

        user = User(
            email="ex.member@example.com",
            hashed_password=get_password_hash("testpass"),
            full_name="Ex Member",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        membership = Membership(tenant_id=org.id, user_id=user.id, role="accountant")
        db.add(membership)
        await db.commit()

        token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(org.id),
            "role": "accountant",
            "email": user.email,
        })
        membership_id = membership.id

    transport = ASGITransport(app=app)
    headers = {"Authorization": f"Bearer {token}"}

    # Remove membership from database
    async with TestingSessionLocal() as db:
        mem = await db.get(Membership, membership_id)
        assert mem is not None
        await db.delete(mem)
        await db.commit()

    # Request with tenant token must now be rejected
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/invoices", headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert "active membership" in data["detail"]
