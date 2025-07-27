from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..chat.models import Room, Message
from ..chat.schemas import RoomCreate, RoomResponse
from ..database import get_db



router = APIRouter(prefix="/admin", tags=["admin"])




@router.post("/rooms", response_model=RoomResponse)
async def create_new_room(
    room_data: RoomCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """create a new chat room (moderators and admins only)"""
    
    if not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only moderators and admins can create rooms"
        )
    
    
    existing_room = db.query(Room).filter(Room.name == room_data.name).first()
    if existing_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A room named '{room_data.name}' already exists"
        )
    
    new_room = Room(
        name=room_data.name,
        description=room_data.description,
        is_private=room_data.is_private,
        created_by=current_user.id
    )
    
    
    
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    
    return RoomResponse.from_orm(new_room)





@router.delete("/rooms/{room_id}")
async def delete_room(
    room_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """delete a chat room admins only"""
    
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete rooms"
        )
    
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    
    
    total_rooms = db.query(Room).count()
    if total_rooms <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last remaining room"
        )
    
    room_name = room.name
    db.delete(room)
    db.commit()
    
    return {"message": f"Room '{room_name}' has been deleted"}





@router.get("/users", response_model=List[dict])
async def list_all_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """get list of all users (admins only)"""
    
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view user list"
        )
    
    users = db.query(User).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "last_seen": user.last_seen.isoformat() if user.last_seen else None
        }
        for user in users
    ]




@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    new_role: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """change a user's role.. admins only"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles"
        )
    
    
    if new_role not in ["user", "moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'user', 'moderator', or 'admin'"
        )
    
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # don't allow changing own role
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role"
        )
    
    old_role = target_user.role
    target_user.role = new_role
    db.commit()
    
    return {
        "message": f"User '{target_user.username}' role changed from '{old_role}' to '{new_role}'"
    }




@router.put("/users/{user_id}/toggle-status")
async def toggle_user_account_status(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """activate or deactivate user account ...admins only"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change account status"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    
    
    # Don't allow deactivating own account
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    target_user.is_active = not target_user.is_active
    db.commit()
    
    action = "activated" if target_user.is_active else "deactivated"
    return {
        "message": f"User '{target_user.username}' has been {action}"
    }





@router.delete("/messages/{message_id}/moderate")
async def moderate_delete_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """delete any message as moderator (moderators and admins)"""
    
    
    if not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only moderators and admins can moderate messages"
        )
    
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    
    author_name = message.author.username
    message.is_deleted = True
    message.content = f"[Message removed by moderator {current_user.username}]"
    db.commit()
    
    
    return {
        "message": f"Message by '{author_name}' has been removed",
        "moderated_by": current_user.username
    }