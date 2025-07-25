from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_private: bool = False
    
    @validator('name')
    def name_must_be_valid(cls, v):
        if len(v) < 1 or len(v) > 100:
            raise ValueError('Room name must be between 1 and 100 characters')
        return v.strip()

class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_private: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    room_id: int

class MessageWebSocket(BaseModel):
    content: str
    
    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 1000:
            raise ValueError('Message is too long (max 1000 characters)')
        return v.strip()

class MessageResponse(BaseModel):
    id: int
    content: str
    timestamp: datetime
    edited_at: Optional[datetime]
    is_deleted: bool
    author: str
    author_id: int
    room_id: int
    
    class Config:
        from_attributes = True

class MessageUpdate(BaseModel):
    content: str
    
    @validator('content')
    def content_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 1000:
            raise ValueError('Message is too long (max 1000 characters)')
        return v.strip()

class ChatHistory(BaseModel):
    messages: List[MessageResponse]
    total: int
    page: int
    size: int
    has_more: bool