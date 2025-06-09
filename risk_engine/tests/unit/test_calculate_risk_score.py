# [UNIT TEST] for CALCULATE RISK SCORE ======================================================================================================================

import pytest
import pytest_asyncio
from datetime import datetime

@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    # override pytest-asyncio's event loop to session scope
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
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

@pytest_asyncio.fixture(scope="session")
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
        yield session
        await session.rollback()
    finally:
        await session.close()

@pytest.fixture
def tot_verified_list():
    from app.core.dumb_risk import tot_verified
    tot_verified.clear()
    yield tot_verified
    tot_verified.clear()

@pytest.fixture
def tot_unverified_list():
    from app.core.dumb_risk import tot_unverified
    tot_unverified.clear()
    yield tot_unverified
    tot_unverified.clear()

@pytest.mark.asyncio(loop_scope="session") # required for async tests so they are not skipped
async def test_calculate_score(tot_verified_list, tot_unverified_list, async_session):

    import random
    import uuid
    from faker import Faker
    from faker.providers import internet, user_agent, geo
    from app.core.dumb_risk import calculate_risk_score
    from app.db.models import LoginAttempt
    from shared_lib.schemas.events import LoginAttempted

    fake = Faker()
    fake.add_provider(internet)
    fake.add_provider(user_agent)
    fake.add_provider(geo)

    # dummy data for db
    db1 = LoginAttempt(
        event_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        email=fake.email(),
        ip_address=fake.ipv4_public(),
        device_id=None,
        user_agent=fake.user_agent(),
        country=fake.country(),
        region=fake.state(),
        city=fake.city(),
        timestamp=fake.date_time_between(start_date="-1d", end_date="now"),
        was_successful=True,
        risk_score=random.randrange(0, 99)
    )
    db2 = LoginAttempt(
        event_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        email=fake.email(),
        ip_address=fake.ipv4_public(),
        device_id=None,
        user_agent=fake.user_agent(),
        country=fake.country(),
        region=fake.state(),
        city=fake.city(),
        timestamp=fake.date_time_between(start_date="-1d", end_date="now"),
        was_successful=True,
        risk_score=random.randrange(0, 99)
    )
    db3 = LoginAttempt(
        event_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        email=fake.email(),
        ip_address=fake.ipv4_public(),
        device_id=None,
        user_agent=fake.user_agent(),
        country=fake.country(),
        region=fake.state(),
        city=fake.city(),
        timestamp=fake.date_time_between(start_date="-1d", end_date="now"),
        was_successful=False,
        risk_score=random.randrange(0, 99)
    )
    db4 = LoginAttempt(
        event_id=uuid.uuid4(),
        user_id=db3.user_id,
        email=db3.email,
        ip_address=fake.ipv4_public(),
        device_id=None,
        user_agent=fake.user_agent(),
        country=fake.country(),
        region=fake.state(),
        city=fake.city(),
        timestamp=fake.date_time_between(start_date="-1d", end_date="now"),
        was_successful=True,
        risk_score=random.randrange(0, 99)
    )
    db5 = LoginAttempt(
        event_id=uuid.uuid4(),
        user_id=db3.user_id,
        email=db3.email,
        ip_address=fake.ipv4_public(),
        device_id=None,
        user_agent=fake.user_agent(),
        country=fake.country(),
        region=fake.state(),
        city=fake.city(),
        timestamp=fake.date_time_between(start_date="-1d", end_date="now"),
        was_successful=True,
        risk_score=random.randrange(0, 99)
    )

    # insert login attempts into db
    async_session.add(db1)
    async_session.add(db2)
    async_session.add(db3)
    async_session.add(db4)
    async_session.add(db5)
    
    await async_session.commit()
    
    # insert dummy data in tot_ver and tot_unver so calculate_risk_score() won't call MFA Handler for verification
    tot_verified_list.extend([db1.event_id, db2.event_id])
    tot_unverified_list.extend([db3.event_id, db4.event_id, db5.event_id])

    # dummy login attempted events:
    # - completely new user (with ID and correct password but never logged in before) | score=50
    evt1 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        email=fake.email(), # new email +50
        ip_address=fake.ipv4_public(),
        user_agent=fake.user_agent(),
        country=fake.country(),
        region=fake.state(),
        city=fake.city(),
        timestamp=datetime.now(), 
        was_successful=True
    )
    # - inexistent user | score=90
    evt2 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=None,
        email=fake.email(),
        ip_address=fake.ipv4_public(), # +30
        user_agent=fake.user_agent(), # +20
        country=fake.country(), # +15
        region=fake.state(), # +10
        city=fake.city(),
        timestamp=datetime.now().replace(hour=random.randint(5,22)),
        was_successful=False # +15
    )
    # - existing user low risk login attempt | score=20
    evt3 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=db1.user_id,
        email=db1.email,
        ip_address=db1.ip_address,
        user_agent=fake.user_agent(), # new device  +20
        country=db1.country,
        region=db1.region,
        city=db1.city,
        timestamp=datetime.now().replace(hour=random.randint(5,22)), # safe hour no matter when the tests are run
        was_successful=True
    )
    if evt3.user_agent == db1.user_agent:
        evt3.user_agent = fake.user_agent()

    # - existing user high risk login attempt | score=55
    evt4 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=db2.user_id,
        email=db2.email,
        ip_address=fake.ipv4_public(), # new ip +30
        user_agent=db2.user_agent, # if the device is trusted this would go through anyway!
        country=fake.country(), # new country +15
        region=fake.state(), # new region +10
        city=fake.city(),
        timestamp=datetime.now().replace(hour=random.randint(5,22)),
        was_successful=True
    )
    if evt4.ip_address == db2.ip_address or evt4.country == db2.country or evt4.region == db2.region:
        evt4.ip_address=fake.ipv4_public()
        evt4.country=fake.country()
        evt4.region=fake.state()
    
    # - typical fraudolent login (correct username and password) | score=95
    evt5 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=db1.user_id,
        email=db1.email,
        ip_address=fake.ipv4_public(), # new ip +30
        user_agent=fake.user_agent(), # new device +20
        country=fake.country(), # new country +15
        region=fake.state(), # new region +10
        city=fake.city(),
        timestamp=fake.date_time_between(start_date="-1d", end_date="now").replace(hour=random.randint(0,4)), # odd hour +20
        was_successful=True
    )
    if evt5.ip_address == db1.ip_address or evt5.user_agent == db1.user_agent or evt5.country == db1.country or evt5.region == db1.region:
        evt5.ip_address=fake.ipv4_public()
        evt5.user_agent=fake.user_agent()
        evt5.country=fake.country()
        evt5.region=fake.state()

    # 4th failed login attempt | score=100
    evt6 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=db3.user_id,
        email=db3.email,
        ip_address=fake.ipv4_public(), # new ip +30
        user_agent=fake.user_agent(), # new device +20
        country=fake.country(), # new country +15
        region=fake.state(), # new region +10
        city=fake.city(),
        timestamp=datetime.now(),
        was_successful=True
    )
    # 5th failed login attempt | score=100
    evt7 = LoginAttempted(
        event_id=uuid.uuid4(),
        user_id=db3.user_id,
        email=db3.email,
        ip_address=fake.ipv4_public(), # new ip +30
        user_agent=fake.user_agent(), # new device +20
        country=fake.country(), # new country +15
        region=fake.state(), # new region +10
        city=fake.city(),
        timestamp=datetime.now(),
        was_successful=True
    )

    score1 = await calculate_risk_score(async_session, evt1)

    score2 = await calculate_risk_score(async_session, evt2)

    score3 = await calculate_risk_score(async_session, evt3)

    score4 = await calculate_risk_score(async_session, evt4)

    score5 = await calculate_risk_score(async_session, evt5)

    score6 = await calculate_risk_score(async_session, evt6)
    # saving in db and tot_unverified for evt7
    async_session.add(LoginAttempt(
        **evt6.model_dump(),
        risk_score=score6
    ))
    await async_session.commit()
    tot_unverified_list.extend([evt6.event_id])

    score7 = await calculate_risk_score(async_session, evt7)
    
    assert score1 >= 50, f">Score #1 (user's first login): {score1} | Expected Score: 50" # high
    assert score2 >= 50, f">Score #2 (inexistent user): {score2} | Expected Score: 90" # high
    assert score3 <= 50, f">Score #3 (low risk attempt): {score3} | Expected Score: 20" # low
    assert score4 >= 50, f">Score #4 (high risk attempt): {score4} | Expected Score: 75" # high
    assert score5 >= 50, f">Score #5 (typical fraud): {score5} | Expected Score: 95" # high
    assert score6 >= 50, f">Score #6 (4th failed attempt): {score6} | Expected Score: 100" # high
    assert score7 >= 50, f">Score #7 (5th failed attempt): {score7} | Expected Score: 100" # high
