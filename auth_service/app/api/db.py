from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from shared_lib.infrastructure.db import get_auth_db
from app.db.models import User
from app.utils.clients import get_mfa_client

router = APIRouter()

@router.get("/users")
async def get_all_users(db: AsyncSession = Depends(get_auth_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    
    users_data = []
    for u in users: # create dictionary for each user & pop unwanted attributes
        u_dict = {**u.__dict__}
        u_dict.pop("hashed_password", None)
        u_dict.pop("srp_salt", None)
        u_dict.pop("srp_verifier", None)
        users_data.append(u_dict)
    
    payload = jsonable_encoder({ # cannot encode bytes into utf-8!
        "message": "Fetched all users successfully.",
        "data": users_data
    })
    return JSONResponse(
        status_code=200,
        content=payload
    )

@router.delete("/users")
async def delete_all_users(db: AsyncSession = Depends(get_auth_db), mfa_client = Depends(get_mfa_client)):
    r = await db.execute(select(User.id))
    user_ids: list[UUID] = r.scalars().all()
    print(">Deleting trusted devices for:", *user_ids, sep=', ')
    for u in user_ids:
        mfa_r = await mfa_client.delete(
            f"/trusted/{u}"
        )
        print(mfa_r)
        print(mfa_r.json())
    print(">Deleting users:")
    print(*user_ids, sep=', ')
    result = await db.execute(delete(User))
    await db.commit()
    print(f">Deleted {result.rowcount} users.")
    return {"message": f"Deleted {result.rowcount} users."}
