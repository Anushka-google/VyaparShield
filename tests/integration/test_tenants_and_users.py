import pytest
import sys
import os
import uuid
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend")))

from app.main import app
from app.models.entities import Organization, User, Membership
from app.core.security import get_password_hash, create_access_token
from tests.conftest import TestingSessionLocal


@pytest.mark.asyncio
async def test_tenant_profile_and_update():
    """Verify tenant profile retrieval and update with audit logging."""
    async with TestingSessionLocal() as db:
        org = Organization(name="Initial Name Org", gstin="27AAAAA1111A1Z1", pan="AAAAA1111A")
        db.add(org)
        await db.flush()

        user = User(email="owner@org.com", hashed_password=get_password_hash("pass"), full_name="Owner User")
        db.add(user)
        await db.flush()

        db.add(Membership(tenant_id=org.id, user_id=user.id, role="owner"))
        await db.commit()

        token = create_access_token({
            "sub": str(user.id),
            "tenant_id": str(org.id),
            "role": "owner",
            "email": user.email,
        })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Get current tenant
        resp = await client.get("/api/v1/tenants/current", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Initial Name Org"
        assert data["gstin"] == "27AAAAA1111A1Z1"

        # 2. Update tenant
        update_payload = {"name": "Updated Fabrics MSME", "gstin": "27BBBBB2222B1Z2"}
        patch_resp = await client.patch("/api/v1/tenants/current", json=update_payload, headers=headers)
        assert patch_resp.status_code == 200
        updated_data = patch_resp.json()
        assert updated_data["name"] == "Updated Fabrics MSME"
        assert updated_data["gstin"] == "27BBBBB2222B1Z2"


@pytest.mark.asyncio
async def test_users_management_and_invite():
    """Verify tenant users listing and new member invitation."""
    async with TestingSessionLocal() as db:
        org = Organization(name="Team Org", gstin="27AAAAA1111A1Z1")
        db.add(org)
        await db.flush()

        owner = User(email="owner@team.com", hashed_password=get_password_hash("pass"), full_name="Team Owner")
        db.add(owner)
        await db.flush()
        db.add(Membership(tenant_id=org.id, user_id=owner.id, role="owner"))
        await db.commit()

        owner_token = create_access_token({
            "sub": str(owner.id),
            "tenant_id": str(org.id),
            "role": "owner",
            "email": owner.email,
        })

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": f"Bearer {owner_token}"}

        # 1. List users
        res = await client.get("/api/v1/users", headers=headers)
        assert res.status_code == 200
        members = res.json()
        assert len(members) == 1
        assert members[0]["email"] == "owner@team.com"
        assert members[0]["role"] == "owner"

        # 2. Invite accountant
        invite_payload = {
            "email": "accountant@team.com",
            "full_name": "Accountant Alex",
            "password": "SecurePassword123!",
            "role": "accountant",
        }
        inv_res = await client.post("/api/v1/users/invite", json=invite_payload, headers=headers)
        assert inv_res.status_code == 201
        invited = inv_res.json()
        assert invited["email"] == "accountant@team.com"
        assert invited["role"] == "accountant"

        # 3. List users again
        res2 = await client.get("/api/v1/users", headers=headers)
        assert res2.status_code == 200
        assert len(res2.json()) == 2
