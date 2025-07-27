from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List
from .models import Message, Room
from .schemas import MessageResponse, RoomResponse, ChatHistory, MessageUpdate
from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..database import get_db
from datetime import datetime



router = APIRouter(prefix="/chat", tags=["chat"])




@router.get("/rooms", response_model=List[RoomResponse])
async def get_available_rooms(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """get list of chat rooms user can access"""
    rooms = db.query(Room).filter(Room.is_private == False).all()
    return [RoomResponse.from_orm(room) for room in rooms]




@router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room_details(
    room_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    return RoomResponse.from_orm(room)






@router.get("/rooms/{room_id}/messages", response_model=ChatHistory)
async def get_room_messages(
    room_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Messages per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """get paginated message history for a room"""
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    
    offset = (page - 1) * size
    
    
    
    total = db.query(Message).filter(
        Message.room_id == room_id,
        Message.is_deleted == False
    ).count()
    
    
    messages = db.query(Message).filter(
        Message.room_id == room_id,
        Message.is_deleted == False
    ).order_by(desc(Message.timestamp)).offset(offset).limit(size).all()
    
    
    message_responses = []
    for msg in reversed(messages):
        message_responses.append(MessageResponse(
            id=msg.id,
            content=msg.content,
            timestamp=msg.timestamp,
            edited_at=msg.edited_at,
            is_deleted=msg.is_deleted,
            author=msg.author.username,
            author_id=msg.author.id,
            room_id=msg.room_id
        ))
    
    return ChatHistory(
        messages=message_responses,
        total=total,
        page=page,
        size=size,
        has_more=offset + size < total
    )




@router.put("/messages/{message_id}")
async def edit_message(
    message_id: int,
    update_data: MessageUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """edit your own message"""
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own messages"
        )
    
    if message.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a deleted message"
        )
    
    # update message
    message.content = update_data.content
    message.edited_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Message updated successfully", "edited_at": message.edited_at}






@router.delete("/messages/{message_id}")
async def delete_my_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """delete your own message"""
    
    message = db.query(Message).filter(Message.id == message_id).first()
    
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    
    if message.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own messages"
        )
    
    message.is_deleted = True
    message.content = "[This message was deleted]"
    db.commit()
    
    return {"message": "Message deleted successfully"}