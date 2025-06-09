# [INTEGRATION TEST] for FULL AUTH FLOW with service dependencies ======================================================================================================================

import pytest, pytest_asyncio
from httpx import ASGITransport, AsyncClient
import json

from app.main import app as _app
from app.api import auth as auth_module
from app.db.models import User
from app.utils.schemas import RegisterIn, MFAVerifyIn

from shared_lib.schemas.events import LoginAttempted
from shared_lib.utils.security import pwd_context
from shared_lib.infrastructure.cache import get_mfa_redis
from shared_lib.infrastructure.clients import risk_client

@pytest.fixture(scope="module")
def event_loop():
    import asyncio
    # override pytest-asyncio's event loop to module scope
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
def dummy_user():
    test_password = "TestPassword123!"
    hashed_password = pwd_context.hash(test_password)

    user = User(
        email="test@test.ts",
        hashed_password=hashed_password,
        srp_salt=b"dummy_salt",
        srp_verifier=b"dummy_verifier",
        role="user"
    )    

    yield {"user": user, "password": test_password}

@pytest_asyncio.fixture(scope="module")
async def auth_cli(dummy_user):
    user = dummy_user["user"]
    risk_cli = await risk_client()
    # delete test LoginAttempt(s) (uncaught previously)
    print(f">Deleting login attempts for test user: {user.email}...")
    resp_risk_delete = await risk_cli.delete(
            f"/login-attempts/{user.email}"
        )
    assert resp_risk_delete.status_code == 200
    body_risk = resp_risk_delete.json()
    print(f">Deleted {body_risk.get("deleted_rows")} rows.")
    # try: 
    async with AsyncClient(
        transport=ASGITransport(app=_app), base_url="http://auth-service", timeout=10.0
    ) as ac:
        # delete test user (uncaught previously)
        resp_auth_delete = await ac.delete(
            f"/auth/users/{user.email}"
        )
        assert resp_auth_delete.status_code == 200 or 404
        yield ac
        # CLEAN UP
        # delete test user
        resp_auth_delete = await ac.delete(
            f"/auth/users/{user.email}"
        )
        assert resp_auth_delete.status_code == 200
        body_auth = resp_auth_delete.json()
        assert int(body_auth.get("deleted_trusted_devices")) >= 1
        assert int(body_auth.get("deleted_otp_logs")) >= 1
        assert int(body_auth.get("deleted_users")) >= 1
        # delete test LoginAttempt(s)
        print(f">Deleting login attempts for test user: {user.email}...")
        resp_risk_delete = await risk_cli.delete(
            f"/login-attempts/{user.email}"
        )
        assert resp_risk_delete.status_code == 200
        body_risk = resp_risk_delete.json()
        assert int(body_risk.get("deleted_rows")) >= 1
        print(f">Deleted {body_risk.get("deleted_rows")} rows.")


@pytest.mark.asyncio(loop_scope="module")
async def test_register(dummy_user, auth_cli):
        user = dummy_user["user"]
        test_password = dummy_user["password"]
        auth_client = auth_cli

        request_data = RegisterIn(email=user.email, password=test_password)
        resp_register = await auth_client.post(
            "/auth/register",
            json=request_data.model_dump(mode="json")
        )
        assert resp_register.status_code == 201

@pytest.mark.asyncio(loop_scope="module")
async def test_login_success_with_MFA(dummy_user, auth_cli, monkeypatch):
    user = dummy_user["user"]
    test_password = dummy_user["password"]

    def test_publish(data: LoginAttempted):
        return

    monkeypatch.setattr(auth_module, "publish_login_event", test_publish)

    auth_client = auth_cli
    resp_login = await auth_client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": test_password,
            "device_id": "dev1"
        }
    )
    assert resp_login.status_code == 202, "Expected MFA required for user's first login."
    body_login = resp_login.json()
    assert body_login.get("mfa_required") is True, "Expected MFA required for user's first login."

    mfa_redis = get_mfa_redis()
    otp_key = f"otp:{user.email}"
    cached = mfa_redis.get(otp_key)
    assert cached is not None, "Expected otp in cache."

    stored = json.loads(cached)
    otp = stored["otp"]

    request = MFAVerifyIn(email=user.email, device_id="dev1", otp=otp)
    resp_verify = await auth_client.post(
        "/auth/verify-otp",
        json=request.model_dump(mode="json")
    )
    assert resp_verify.status_code == 200, (f"Expected HTTP 200 after correct OTP verification, got {resp_verify.status_code}")
    body_verify = resp_verify.json()
    assert "access_token" in body_verify, "Expected JWT access_token in response"

@pytest.mark.asyncio(loop_scope="module")
async def test_login_success_without_MFA(dummy_user, auth_cli, monkeypatch):
    user = dummy_user["user"]
    test_password = dummy_user["password"]

    def test_publish(data: LoginAttempted):
        return

    monkeypatch.setattr(auth_module, "publish_login_event", test_publish)

    auth_client = auth_cli
    resp_login = await auth_client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": test_password,
            "device_id": "dev1"
        }
    )
    assert resp_login.status_code == 200, (f"Expected HTTP 200 when no MFA is required, got {resp_login.status_code}")
    body_login = resp_login.json()
    assert body_login.get("mfa_required") is False, "Expected mfa_required=False"
    assert "access_token" in body_login, "Expected JWT access_token in response"

@pytest.mark.asyncio(loop_scope="module")
async def test_login_fail(dummy_user, auth_cli, monkeypatch):
    user = dummy_user["user"]
    bad_password = "bababa123"

    def test_publish(data: LoginAttempted):
        return

    # monkeypatch.setattr(auth_module, "publish_login_event", test_publish)
    
    auth_client = auth_cli
    resp_login = await auth_client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": bad_password,
            "device_id": "dev1"
        }
    )
    assert resp_login.status_code == 401, (f"Expected HTTP 401 for invalid credentials, got {resp_login.status_code}")
    body = resp_login.json()
    assert body.get("detail") == "Invalid credentials.", "Error detail did not match expected 'Invalid credentials.'"
