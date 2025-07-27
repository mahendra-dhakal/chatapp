from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import Optional, List
from datetime import datetime, date, timedelta
import csv
import io

from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..chat.models import Message, Room
from ..database import get_db





router = APIRouter(prefix="/analytics", tags=["analytics"])



def require_admin_or_moderator(current_user: User = Depends(get_current_active_user)):
    """Only admins and moderators can access analytics"""
    if not current_user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analytics access requires moderator or admin privileges"
        )
    return current_user




@router.get("/overview")
async def get_analytics_overview(
    current_user: User = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db)
):
    """Get high-level chat analytics overview"""
    
    total_users = db.query(User).count()
    total_rooms = db.query(Room).count()
    total_messages = db.query(Message).filter(Message.is_deleted == False).count()
    
    week_ago = datetime.now() - timedelta(days=7)
    active_users_count = db.query(func.count(func.distinct(Message.user_id)))\
                         .filter(Message.timestamp >= week_ago, Message.is_deleted == False)\
                         .scalar()
    
    # Today's activity
    today = datetime.now().date()
    messages_today = db.query(Message)\
                      .filter(func.date(Message.timestamp) == today, Message.is_deleted == False)\
                      .count()
    
    # Most active room
    most_active_room = db.query(
        Room.name,
        func.count(Message.id).label('message_count')
    ).join(Message, Room.id == Message.room_id)\
     .filter(Message.is_deleted == False)\
     .group_by(Room.id, Room.name)\
     .order_by(desc(func.count(Message.id)))\
     .first()
    
    
    
    # Most active user (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    most_active_user = db.query(
        User.username,
        func.count(Message.id).label('message_count')
    ).join(Message, User.id == Message.user_id)\
     .filter(Message.timestamp >= thirty_days_ago, Message.is_deleted == False)\
     .group_by(User.id, User.username)\
     .order_by(desc(func.count(Message.id)))\
     .first()
    
    return {
        "summary": {
            "total_users": total_users,
            "total_rooms": total_rooms,
            "total_messages": total_messages,
            "active_users_last_7_days": active_users_count or 0,
            "messages_today": messages_today
        },
        "highlights": {
            "most_active_room": {
                "name": most_active_room[0] if most_active_room else "No data",
                "message_count": most_active_room[1] if most_active_room else 0
            },
            "most_active_user_30_days": {
                "username": most_active_user[0] if most_active_user else "No data",
                "message_count": most_active_user[1] if most_active_user else 0
            }
        },
        "generated_at": datetime.now().isoformat()
    }






@router.get("/messages-per-room")
async def get_messages_per_room(
    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: User = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db)
):
    """Gget message count breakdown by room with optional date filtering"""
    
    query = db.query(
        Room.id,
        Room.name,
        Room.description,
        func.count(Message.id).label('message_count'),
        func.count(func.distinct(Message.user_id)).label('unique_users')
    ).outerjoin(Message, and_(
        Room.id == Message.room_id,
        Message.is_deleted == False
    ))
    
    if start_date:
        query = query.filter(Message.timestamp >= start_date)
        
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Message.timestamp <= end_datetime)
    
    results = query.group_by(Room.id, Room.name, Room.description)\
                   .order_by(desc(func.count(Message.id))).all()
    
    
    room_stats = []
    for room_id, room_name, room_desc, msg_count, unique_users in results:
        # get first and last message dates for this room
        first_msg = db.query(Message.timestamp).filter(
            Message.room_id == room_id,
            Message.is_deleted == False
        ).order_by(Message.timestamp.asc()).first()
        
        last_msg = db.query(Message.timestamp).filter(
            Message.room_id == room_id,
            Message.is_deleted == False
        ).order_by(Message.timestamp.desc()).first()
        
        room_stats.append({
            "room_id": room_id,
            "room_name": room_name,
            "room_description": room_desc,
            "message_count": msg_count or 0,
            "unique_users": unique_users or 0,
            "first_message": first_msg[0].isoformat() if first_msg else None,
            "last_message": last_msg[0].isoformat() if last_msg else None
        })
    
    
    return {
        "data": room_stats,
        "filters_applied": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        },
        "summary": {
            "total_rooms": len(room_stats),
            "total_messages_in_period": sum(room["message_count"] for room in room_stats),
            "rooms_with_activity": len([r for r in room_stats if r["message_count"] > 0])
        }
    }





@router.get("/user-activity")
async def get_user_activity_stats(
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=200, description="Max users to return"),
    min_messages: int = Query(0, ge=0, description="Minimum messages to include user"),
    current_user: User = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db)
):
    """track user participation and activity patterns"""
    
    
    
    message_query = db.query(
        User.id,
        User.username,
        User.email,
        User.role,
        User.created_at,
        User.last_seen,
        func.count(Message.id).label('messages_sent'),
        func.count(func.distinct(Message.room_id)).label('rooms_participated'),
        func.min(Message.timestamp).label('first_message_date'),
        func.max(Message.timestamp).label('last_message_date')
    ).outerjoin(Message, and_(
        User.id == Message.user_id,
        Message.is_deleted == False
    ))
    
    
    
    # Apply date filters to messages
    if start_date:
        message_query = message_query.filter(Message.timestamp >= start_date)
        
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        message_query = message_query.filter(Message.timestamp <= end_datetime)
    
    results = message_query.group_by(
        User.id, User.username, User.email, User.role, User.created_at, User.last_seen
    ).having(func.count(Message.id) >= min_messages)\
     .order_by(desc(func.count(Message.id)))\
     .limit(limit).all()
    
    
    user_activity = []
    for result in results:
        user_id, username, email, role, created_at, last_seen, messages_sent, \
        rooms_participated, first_msg_date, last_msg_date = result
        
        # Calculate activity score (messages per day since joining)
        if created_at and messages_sent:
            days_since_join = max((datetime.now() - created_at).days, 1)
            activity_score = round(messages_sent / days_since_join, 2)
            
        else:
            activity_score = 0
        
        user_activity.append({
            "user_id": user_id,
            "username": username,
            "email": email,
            "role": role,
            "account_created": created_at.isoformat() if created_at else None,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "messages_sent": messages_sent or 0,
            "rooms_participated": rooms_participated or 0,
            "first_message_date": first_msg_date.isoformat() if first_msg_date else None,
            "last_message_date": last_msg_date.isoformat() if last_msg_date else None,
            "activity_score": activity_score
        })
    
    return {
        "data": user_activity,
        "filters_applied": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "limit": limit,
            "min_messages": min_messages
        },
        "summary": {
            "users_returned": len(user_activity),
            "total_messages": sum(u["messages_sent"] for u in user_activity),
            "average_messages_per_user": round(
                sum(u["messages_sent"] for u in user_activity) / len(user_activity), 1
            ) if user_activity else 0,
            "most_active_user": user_activity[0]["username"] if user_activity else None
        }
    }





@router.get("/export/messages-csv")
async def export_messages_to_csv(
    room_id: Optional[int] = Query(None, description="Filter by specific room"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db)
):
    """Export message data as CSV file"""
    
    query = db.query(
        Message.id,
        Message.content,
        Message.timestamp,
        Message.is_deleted,
        Message.edited_at,
        User.username.label('author'),
        User.role.label('author_role'),
        Room.name.label('room_name')
    ).join(User, Message.user_id == User.id)\
     .join(Room, Message.room_id == Room.id)
    
    
    # Apply filters
    if room_id:
        query = query.filter(Message.room_id == room_id)
        
    if start_date:
        query = query.filter(func.date(Message.timestamp) >= start_date)
        
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Message.timestamp <= end_datetime)
    
    messages = query.order_by(Message.timestamp.desc()).all()
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    
    # Write header
    writer.writerow([
        'Message ID', 'Content Preview', 'Author', 'Author Role', 
        'Room', 'Timestamp', 'Is Deleted', 'Edited At'
    ])
    
    # Write data
    for msg in messages:
        content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        content_preview = content_preview.replace('\n', ' ').replace('\r', ' ')
        
        writer.writerow([
            msg.id,
            content_preview,
            msg.author,
            msg.author_role,
            msg.room_name,
            msg.timestamp.isoformat(),
            msg.is_deleted,
            msg.edited_at.isoformat() if msg.edited_at else ""
        ])
    
    output.seek(0)
    
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"chat_messages_export_{timestamp}.csv"
    
    
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )








@router.get("/export/user-activity-csv")
async def export_user_activity_to_csv(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db)
):
    """Export user activity statistics as CSV"""
    
    
    
    message_query = db.query(
        User.id,
        User.username,
        User.email,
        User.role,
        User.created_at,
        User.last_seen,
        User.is_active,
        func.count(Message.id).label('total_messages'),
        func.count(func.distinct(Message.room_id)).label('rooms_used'),
        func.min(Message.timestamp).label('first_message'),
        func.max(Message.timestamp).label('last_message')
    ).outerjoin(Message, and_(
        User.id == Message.user_id,
        Message.is_deleted == False
    ))
    
    
    
    # Apply date filters
    if start_date:
        message_query = message_query.filter(Message.timestamp >= start_date)
        
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        message_query = message_query.filter(Message.timestamp <= end_datetime)
    
    results = message_query.group_by(
        User.id, User.username, User.email, User.role, 
        User.created_at, User.last_seen, User.is_active
    ).order_by(desc(func.count(Message.id))).all()
    
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    
    # Header
    writer.writerow([
        'User ID', 'Username', 'Email', 'Role', 'Account Status',
        'Account Created', 'Last Seen', 'Total Messages', 'Rooms Used',
        'First Message', 'Last Message'
    ])
    
    
    # Data
    for row in results:
        writer.writerow([
            row.id,
            row.username,
            row.email,
            row.role,
            "Active" if row.is_active else "Inactive",
            row.created_at.isoformat() if row.created_at else "",
            row.last_seen.isoformat() if row.last_seen else "",
            row.total_messages or 0,
            row.rooms_used or 0,
            row.first_message.isoformat() if row.first_message else "",
            row.last_message.isoformat() if row.last_message else ""
        ])
    
    output.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"user_activity_export_{timestamp}.csv"
    
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )