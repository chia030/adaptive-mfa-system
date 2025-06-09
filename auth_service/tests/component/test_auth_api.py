# [COMPONENT TEST] for AUTH API ======================================================================================================================

import pytest, pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app as _app
from app.api import auth as auth_module
from app.db.models import User
from app.utils.schemas import RegisterIn, MFAVerifyIn, ChangePasswordIn

from shared_lib.schemas.events import LoginAttempted
from shared_lib.utils.security import pwd_context
from shared_lib.infrastructure.db import get_auth_db
from shared_lib.infrastructure.clients import get_risk_client, get_mfa_client

@pytest_asyncio.fixture(scope="module")
async def engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.db.models import Base
    # make test database
    TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True, connect_args={"uri": True} if "sqlite" in TEST_DATABASE_URL else {})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="module")
async def async_session(engine):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    # fresh async session per test
    TestingSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False
    )
    # directly create a session instance without 'async with'
    session: AsyncSession = TestingSessionLocal()
    try:
        return session
        
    finally:
        await session.rollback()
        await session.close()

class TestResponse:
    def __init__(self, status_code: int, content: dict):
        import json
        self.status_code = status_code
        self.json_data = content
        self.content = json.dumps(content).encode("utf-8")

    def json(self):
        return self.json_data

class TestRiskClient:
    def __init__(self, risk_score: int = 50):
        self.risk_score = risk_score
    async def post(self, path: str, json: dict):
        event_id = json.get("event_id")
        response_content = {
            "message": "Risk Score calculated.",
            "data": {
                "event_id": event_id,
                "risk_score": self.risk_score,
                "persisted": True
            }
        }
        return TestResponse(status_code=200, content=response_content)
    
class TestMFAClient:
    def __init__(self, require_mfa: bool):
        self.require_mfa = require_mfa
    async def post(self, path: str, json: dict):
        if path.endswith("/mfa/check"):
            event_id = json.get("event_id")
            if self.require_mfa:
                content = {
                    "message": "MFA check completed.",
                    "data": {"event_id": event_id, "mfa_required": True}
                }
                return TestResponse(status_code=202, content=content)
            else:
                content = {
                    "message": "MFA check completed.",
                    "data": {"event_id": event_id, "mfa_required": False}
                }
                return TestResponse(status_code=200, content=content)
        elif path.endswith("/mfa/verify"):
            content = {"message": "MFA verified successfully.", "device_saved": True}
            return TestResponse(status_code=200, content=content)
    async def delete(self, path: str):
        response_content = {
            "message": "Deleted...",
            "deleted_rows": 2
        }
        return TestResponse(status_code=200, content=response_content)


class FakeRedis:
    def __init__(self):
        self.store = {}
    
    def setex(self, key, time_sec, value):
        self.store[key] = value # no actual expiration
    
    def get(self, key):
        return self.store.get(key)

@pytest.fixture(scope="module")
def test_auth_redis():
    fake_redis = FakeRedis()
    auth_module.redis = fake_redis
    return fake_redis

@pytest.fixture(scope="module")
def dummy_user():
    test_password = "TestPassword123!"
    hashed_password = pwd_context.hash(test_password)

    user = User(
        email="user@example.com",
        hashed_password=hashed_password,
        srp_salt=b"dummy_salt",
        srp_verifier=b"dummy_verifier",
        role="user"
    )    

    yield {"user": user, "password": test_password}

@pytest_asyncio.fixture(scope="module")
async def test_auth_client(async_session):
    # from app.main import app
    async def override_get_auth_db():
        yield async_session
    _app.dependency_overrides[get_auth_db] = override_get_auth_db  # only works when done before creating the test client
    async with AsyncClient(
        transport=ASGITransport(app=_app), base_url="http://auth-service"
    ) as ac:
        yield ac
    _app.dependency_overrides.pop(get_auth_db, None)

@pytest.mark.asyncio(loop_scope="module")
async def test_register(dummy_user, test_auth_client):
        user = dummy_user["user"]
        test_password = dummy_user["password"]
        auth_client =  test_auth_client

        request_data = RegisterIn(email=user.email, password=test_password)

        resp_register = await auth_client.post(
            "/auth/register",
            json=request_data.model_dump(mode="json")
        )
        assert resp_register.status_code == 201

@pytest.mark.asyncio(loop_scope="module")
async def test_login_success_with_MFA(dummy_user, test_auth_redis, test_auth_client, monkeypatch):
    user = dummy_user["user"]
    test_password = dummy_user["password"]

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_risk_client,
        lambda: TestRiskClient(risk_score=50) # user's first login
    )

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_mfa_client,
        lambda: TestMFAClient(require_mfa=True)
    )

    def test_publish(data: LoginAttempted):
        return

    monkeypatch.setattr(auth_module, "publish_login_event", test_publish)
    
    auth_client = test_auth_client
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

    otp_key = f"mfa:{user.email}"
    event_id = test_auth_redis.get(otp_key)
    assert event_id is not None, "Expected event_id in cache."

    request = MFAVerifyIn(email=user.email, device_id="dev1", otp=123456)
    resp_verify = await auth_client.post(
        "/auth/verify-otp",
        json=request.model_dump(mode="json")
    )
    assert resp_verify.status_code == 200, (f"Expected HTTP 200 after correct OTP verification, got {resp_verify.status_code}")
    body_verify = resp_verify.json()
    assert "access_token" in body_verify, "Expected JWT access_token in response"

    _app.dependency_overrides.pop(get_risk_client, None)
    _app.dependency_overrides.pop(get_mfa_client, None)

@pytest.mark.asyncio(loop_scope="module")
async def test_login_success_without_MFA(dummy_user, test_auth_client, monkeypatch):
    user = dummy_user["user"]
    test_password = dummy_user["password"]

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_risk_client,
        lambda: TestRiskClient(risk_score=10)
    )

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_mfa_client,
        lambda: TestMFAClient(require_mfa=False)
    )

    def test_publish(data: LoginAttempted):
        return

    monkeypatch.setattr(auth_module, "publish_login_event", test_publish)
    
    auth_client = test_auth_client
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

    _app.dependency_overrides.pop(get_risk_client, None)
    _app.dependency_overrides.pop(get_mfa_client, None)

@pytest.mark.asyncio(loop_scope="module")
async def test_login_fail(dummy_user, test_auth_client, monkeypatch):
    user = dummy_user["user"]
    bad_password = "bababa123"

    def test_publish(data: LoginAttempted):
        return

    monkeypatch.setattr(auth_module, "publish_login_event", test_publish)

    auth_client = test_auth_client
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

    _app.dependency_overrides.pop(get_risk_client, None)
    _app.dependency_overrides.pop(get_mfa_client, None)

# change password
@pytest.mark.asyncio(loop_scope="module")
async def test_change_password(dummy_user, test_auth_client):
    user = dummy_user["user"]
    new_password = "newPassword1!"
    auth_client = test_auth_client

    request = ChangePasswordIn(email=user.email, new_password=new_password, confirm_password=new_password)

    resp_change_password = await auth_client.post(
        "/auth/change-password",
        json=request.model_dump(mode="json")
    )
    assert resp_change_password.status_code == 200

@pytest.mark.asyncio(loop_scope="module")
async def test_login_success_new_password(dummy_user, test_auth_client, monkeypatch):
    user = dummy_user["user"]
    new_password = "newPassword1!"

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_risk_client,
        lambda: TestRiskClient(risk_score=10)
    )

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_mfa_client,
        lambda: TestMFAClient(require_mfa=False)
    )

    def test_publish(data: LoginAttempted):
        return

    monkeypatch.setattr(auth_module, "publish_login_event", test_publish)
    
    auth_client = test_auth_client
    resp_login = await auth_client.post(
        "/auth/login",
        data={
            "username": user.email,
            "password": new_password,
            "device_id": "dev1"
        }
    )
    assert resp_login.status_code == 200, (f"Expected HTTP 200 when no MFA is required, got {resp_login.status_code}")
    body_login = resp_login.json()
    assert body_login.get("mfa_required") is False, "Expected mfa_required=False"
    assert "access_token" in body_login, "Expected JWT access_token in response"

    _app.dependency_overrides.pop(get_risk_client, None)
    _app.dependency_overrides.pop(get_mfa_client, None)

# delete user
@pytest.mark.asyncio(loop_scope="module")
async def test_delete_user(dummy_user, test_auth_client, monkeypatch):
    user = dummy_user["user"]

    monkeypatch.setitem(
        _app.dependency_overrides,
        get_mfa_client,
        lambda: TestMFAClient(require_mfa=False)
    )

    auth_client = test_auth_client

    resp_delete = await auth_client.delete(
        f"/auth/users/{user.email}",
    )
    assert resp_delete.status_code == 200
    delete_body = resp_delete.json()
    assert int(delete_body.get("deleted_users")) >= 1
    
    _app.dependency_overrides.pop(get_mfa_client, None)