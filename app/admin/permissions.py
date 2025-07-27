from functools import wraps
from fastapi import HTTPException, status
from ..auth.models import User



def require_admin(func):
    """decorator requiring admin role"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = None
        for key, value in kwargs.items():
            if isinstance(value, User):
                current_user = value
                break
        
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        return await func(*args, **kwargs)
    return wrapper




def require_moderator_or_admin(func):
    """decorator requiring moderator or admin role"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        current_user = None
        for key, value in kwargs.items():
            if isinstance(value, User):
                current_user = value
                break
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if current_user.role not in ["admin", "moderator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Moderator or admin access required"
            )
        
        return await func(*args, **kwargs)
    return wrapper




def check_permission(user: User, required_roles: list) -> bool:
    """check if user has required role"""
    return user.role in required_roles