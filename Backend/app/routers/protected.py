from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from app.db.users import UserRole
from app.dependencies import get_current_user

router = APIRouter(
    prefix="/api/protected",
    tags=["protected"],
    responses={403: {"description": "Forbidden"}},
)

def require_role(required_role: UserRole):
    def decorator(func):
        async def wrapper(current_user: dict = Depends(get_current_user)):
            if current_user["role"] != required_role.value:  # Compare string values
                raise HTTPException(status_code=403, detail=f"{required_role.value} access required")
            return await func(current_user=current_user)
        return wrapper
    return decorator

@router.get("/admin-only")
@require_role(required_role=UserRole.ADMIN)
async def admin_only(current_user: dict):
    return {"message": "Admin only route"}