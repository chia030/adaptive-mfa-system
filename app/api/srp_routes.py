import srp
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User
# get_db() is a func in database now, should it be imported like this?
from app.db.database import get_db
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
import hashlib

srp.rfc5054_enable()

router = APIRouter(prefix="/auth/srp", tags=["SRP"])
_srp_sessions: dict[str, srp.Verifier] = {} # username -> verifier instance


class SRPStartIN(BaseModel):
    email: EmailStr
    A: str

@router.post("/start")
async def srp_start(data: SRPStartIN, db: AsyncSession = Depends(get_db)):
    # SERVER 1. find user by identity (email)
    result = await db.execute(select(User).where(User.email==data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    
    # SERVER 2. create verifier with stored verifier, salt & A = public ephemeral (from client)
    salt = user.srp_salt
    verifier = user.srp_verifier
    A_bytes = bytes.fromhex(data.A)
    svr = srp.Verifier(data.email, salt, verifier, A_bytes, hash_alg=srp.SHA256, ng_type=srp.NG_2048)

    # SERVER 3. generate server's public ephemeral (B)
    s, B = svr.get_challenge()
    if s is None or B is None:
        raise HTTPException(401, "Authentication failed")
    
    # clean up session
    _srp_sessions.pop(data.email, None)
    
    # start SRP session
    _srp_sessions[data.email] = svr

    server_salt = s.hex()
    server_B = B.hex()

    print("Server B:", server_B)
    print("Server salt:", server_salt)


    # calculate the shared session key u = H(A,B)
    digest = hashlib.sha256(A_bytes + B).digest()
    u = int.from_bytes(digest, 'big')
    print("u =", u)

    # SERVER 4. return s + B to client
    return {"salt": server_salt, "B": server_B}

class SRPProofIN(BaseModel):
    email: EmailStr
    M1: str # client's proof

@router.post("/verify")
async def srp_verify(proof: SRPProofIN):
    # verify SRP session
    svr = _srp_sessions.get(proof.email)
    if not svr:
        raise HTTPException(400, "SRP session not found")
    
    print("Client M1:", proof.M1)
    M1 = bytes.fromhex(proof.M1)
  
    # SERVER 5. verify client's proof + compute server's proof (M2)
    HAMK = svr.verify_session(M1)
    if HAMK is None:
        print("Bad proof M1")
        raise HTTPException(401, "SRP verification failed")
    
    HAMK_hex = HAMK.hex()
    print("Server M2:", HAMK_hex)
    # print("Server M2 bytes:", HAMK)
    print("Server K =", svr.get_session_key().hex())
    
    # cleanup session
    _srp_sessions.pop(proof.email, None)

    # authentication complete
    assert svr.authenticated()

    # SERVER 6. return server proof => client can verify mutual authentication
    return {"M2": HAMK_hex, "message":"SRP authentication successful"}
