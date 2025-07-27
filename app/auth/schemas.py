from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime



class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    
    
    @validator('username')
    def username_must_be_valid(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError('Username must be between 3 and 20 characters')
        if not v.replace('_', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v.lower()
    
    
    @validator('password')
    def password_must_be_strong(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v




class UserLogin(BaseModel):
    username: str
    password: str




class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_seen: Optional[datetime] = None
    
    
    class Config:
        from_attributes = True




class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse



class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None