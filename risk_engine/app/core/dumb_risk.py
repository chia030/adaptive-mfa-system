from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, bindparam
from uuid import UUID
from shared_lib.schemas.events import LoginAttempted
from shared_lib.infrastructure.clients import mfa_client
from app.db.models import LoginAttempt

tot_verified: list[UUID] = [] # TODO: ideally once they are verified it should be stored in the db, maybe in a separate table
tot_unverified: list[UUID] = []

async def verify_success(event_id: UUID):
    print(">Verifying past attempts' success...")

    client = await mfa_client()
    mfa_r = await client.get(
        f"/otp-logs/{event_id}"
    )
    
    # 1. MFA not required: success = true
    # no results
    if mfa_r.status_code == 204:
        print(f">{event_id} did not require MFA => was successful")
        tot_verified.append(event_id)
        return True
    
    mfa_response = mfa_r.json()
    # 2. OTP sent + verified: success = true
    # 1 res with OTPLog.status = "sent" + 1 result with OTPLog.status = "verified"
    if mfa_response.get("sent_logs_count") == 1 and mfa_response.get("verified_logs_count") == 1:
        print(f">{event_id} did require MFA => was successful")
        tot_verified.append(event_id)
        return True
    else: # 1 res with OTP sent: success = false
        print(f">{event_id} did require MFA => was unsuccessful")
        tot_unverified.append(event_id)
        return False


# "dumb" - although a little smarter now - scoring logic
async def calculate_risk_score(
        db: AsyncSession,
        evt: LoginAttempted
) -> int:
    print(f">Calculating risk score for evt: '{evt.event_id}'.")

    score = 0

    """
    'was_successful', based on this logic, should really only be set to true once the whole login process is 
          completed, in case the password is hacked.

    There can be 2 success cases:
        - login successful and OTP was never sent (safe login)
        - login successful and OTP was sent + verified
    """

    # last score + verification risk
    print(">Calculating last attempt risk...")
    last_attempt: LoginAttempt = (await db.execute(select(LoginAttempt).where(LoginAttempt.email == evt.email).order_by(LoginAttempt.timestamp.desc()).limit(1))).scalar_one_or_none()
    if last_attempt and last_attempt.risk_score == 100:
        if last_attempt.event_id not in tot_verified and last_attempt.event_id in tot_unverified or not await verify_success(last_attempt.event_id):
            score = 100
            print(f">3+ sequential unsuccessful attempts for {evt.email}! Defaulting to highest score. Final score:{score}")
        return score

    # user/email risk
    print(">Calculating user/email risk...")
    # if user_id and email never seen before = first login for new user
    if evt.user_id and not (await db.execute(select(LoginAttempt).where(LoginAttempt.email == evt.email))).scalars().first():
        score += 50
        print(f">First login for new user. Defaulting to high risk attempt. Final score:{score}") # default to OTP request
        return score
    # sadly this is not supported by sqlite (used in pytests) => commenting it out for now
    # elif not evt.user_id: # email not found in Auth DB
    #     # check if email is a partial match to existing attempts in db
    #     stmt = (
    #         select(LoginAttempt.email)
    #         .where( # only keep rows at or below threshold
    #             func.levenshtein(
    #                 LoginAttempt.email,
    #                 bindparam("target_email")
    #             ) <= 2 # 2 characters difference threshold
    #         )
    #     )
    #     result = (await db.execute(stmt, {"target_email": evt.email})).scalars().first()
    #     if result:
    #         score -= 5 # probably just a typo
    #         print(f">Fuzzy match to existing emails detected. Decreasing score by 5. Current score: {score}")
    #     else:
    #         print(f">Attempt email is entirely new and does not match to a user.")

    # IP risk
    print(">Calculating IP risk...")
    ip_results: list [LoginAttempt] = (await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.ip_address == evt.ip_address, LoginAttempt.was_successful == True)
    )).scalars().all() # scalars converts first column value (id) into ScalarResult and first() returns the first row only, all() returns all rows

    if not ip_results: 
        score += 30 # new IP
        print(f">New IP detected! Increasing score by 30. Current score:{score}")
    else:
        ip_verified: list[UUID] = []
        for a in ip_results:
            if a.event_id in tot_verified:
                ip_verified.append(a.event_id)
                continue # skip rest of code for this loop
            elif a.event_id not in tot_unverified and await verify_success(a.event_id):
                print(f">Verified past success consistency with MFA Handler's OTP Logs for {evt.email}, event: {a.event_id}.")
                ip_verified.append(a.event_id)
        if not ip_verified: # list empty
            score += 30 # unverified IP
            print(f">Unverified IP detected! Increasing score by 30. Current score:{score}")

    # time risk
    print(">Calculating hour-of-day risk...")
    if evt.timestamp.hour < 5 or evt.timestamp.hour > 23:
        score += 20 # odd hours
        print(f">Odd hours detected! Increasing score by 20. Current score:{score}")

    # device risk
    print(">Calculating device risk...")
    device_results: list[LoginAttempt] = (await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.user_agent == evt.user_agent, LoginAttempt.was_successful == True)
    )).scalars().all()
    if not device_results: # as before, check if any results
        score += 20 # new device
        print(f">New device detected! Increasing score by 20. Current score:{score}")
    else:
        device_verified: list[UUID] = []
        for a in device_results:
            if a.event_id in tot_verified:
                device_verified.append(a.event_id)
                continue # skip rest of code for this loop
            elif a.event_id not in tot_unverified and await verify_success(a.event_id):
                print(f">Verified past success consistency with MFA Handler's OTP Logs for {evt.email}, event: {a.event_id}.")
                device_verified.append(a.event_id)
        if not device_verified:
            score += 20 # unverified device
            print(f">Unverified device detected! Increasing score by 20. Current score:{score}")
    
    # geolocation risk
    print(">Calculating country risk...")
    match evt.country:
        case "Local": # local docker ip
            print(">Local IP location, skipping...")
            pass
        case "Unknown" | None: # default or error
            score += 15 # could not fetch country => default to increased risk
            print(f">'Unknown' country detected! Increasing score by 15. Current score:{score}")
        case _:
            country_results: list[LoginAttempt] = (await db.execute(
                select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.country == evt.country, LoginAttempt.was_successful == True)
            )).scalars().all()
            if not country_results:
                score += 15 # new country
                print(f">New country detected! Increasing score by 15. Current score:{score}")
            else:
                country_verified: list[UUID] = []
                for a in country_results:
                    if a.event_id in tot_verified:
                        country_verified.append(a.event_id)
                        continue # skip rest of code for this loop
                    elif a.event_id not in tot_unverified and await verify_success(a.event_id):
                        print(f">Verified past success consistency with MFA Handler's OTP Logs for {evt.email}, event: {a.event_id}.")
                        country_verified.append(a.event_id)
                if not country_verified:
                    score += 15 # unverified country
                    print(f">Unverified country detected! Increasing score by 15. Current score:{score}")
                # else: tot_verified += list(set(country_verified) - set(tot_verified))

    print(">Calculating region risk...")
    match evt.region:
        case "Local": # local docker ip
            print(">Local IP location. Skipping...")
            pass
        case "Unknown" | None: # default or error
            score += 10 # could not fetch country => default to increased risk
            print(f">'Unknown' country detected! Increasing score by 15. Current score:{score}")
        case _:
            region_results: list[LoginAttempt] = (await db.execute(
                select(LoginAttempt).where(LoginAttempt.email == evt.email, LoginAttempt.region == evt.region, LoginAttempt.was_successful == True)
            )).scalars().all()
            if not region_results:
                score += 10 # new region
                print(f">New region detected! Increasing score by 10. Current score:{score}")
            else:
                region_verified: list[UUID] = []
                for a in region_results:
                    if a.event_id in tot_verified:
                        region_verified.append(a.event_id)
                        continue # skip rest of code for this loop
                    elif a.event_id not in tot_unverified and await verify_success(a.event_id):
                        print(f">Verified past success consistency with MFA Handler's OTP Logs for {evt.email}, event: {a.event_id}.")
                        region_verified.append(a.event_id)
                if not region_verified:
                    score += 10 # unverified region
                    print(f">Unverified region detected! Increasing score by 10. Current score:{score}")

    # success risk
    print(">Calculating success risk...")
    if not evt.was_successful:
        score += 15
        print(f"Unsuccessful login attempt detected! Increasing score by 15. Current score:{score}")
        # if last 3 attempts == failure || unverified => SCORE=100 to be repeated until the users verifies account with MFA successfully.
    success_results: list[LoginAttempt] = (await db.execute(
        select(LoginAttempt).where(LoginAttempt.email == evt.email).order_by(LoginAttempt.timestamp.desc()).limit(3) # order by timestamp.descending()
    )).scalars().all()
    bad = []
    if len(success_results) == 3:
        for a in success_results:
            if not a.was_successful:
                bad.append(a.event_id)
                continue
            elif a.event_id in tot_unverified:
                bad.append(a.event_id)
                continue
            elif a.event_id not in tot_verified and not await verify_success(a.event_id):
                bad.append(a.event_id)
        if len(bad) == 3:
            score += 100
            print(f">Past 3 login attempts were unsuccessful or unverified with MFA. Increasing score by 100. Current score:{score}")
    
    print(f">Final score before cap: {score}")
    return min(score, 100) # cap at 100
