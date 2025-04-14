from fastapi import APIRouter, Depends
from app.core.security import admin_required

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/dashboard")
async def get_admin_dashboard(current_admin=Depends(admin_required)):
    return {"message": "Welcome to the admin dashboard!", "admin": current_admin.email}
