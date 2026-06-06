from fastapi import HTTPException, Request
from typing import Optional
from config.security import get_security_settings

settings = get_security_settings()

async def get_token_from_cookie(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        return token[7:]  # Remove "Bearer " prefix
    return None

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    async def __call__(self, request: Request):
        # AuthStateMiddleware already decoded the token and loaded the user
        # onto request.state for every request -- reuse it instead of
        # decoding the JWT and querying the database a second time.
        user = getattr(request.state, "user", None)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You don't have sufficient permissions to perform this action",
            )

        return True

# Create role checker instances
admin_required = RoleChecker(["admin"])
staff_required = RoleChecker(["admin", "staff"])
user_required = RoleChecker(["admin", "staff", "user"]) 