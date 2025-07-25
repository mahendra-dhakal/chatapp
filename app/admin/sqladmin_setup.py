from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..auth.dependencies import get_current_active_user
from ..auth.models import User
from ..chat.models import Room, Message
from ..database import get_db
from ..config import settings

# Simple admin interface without external dependencies
admin_router = APIRouter(prefix="/admin", tags=["admin-interface"])
templates = Jinja2Templates(directory="templates")

def require_admin_access(current_user: User = Depends(get_current_active_user)):
    """Require admin role for admin interface"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

@admin_router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Admin dashboard with basic statistics"""
    
    # Get basic stats
    total_users = db.query(User).count()
    total_rooms = db.query(Room).count()
    total_messages = db.query(Message).filter(Message.is_deleted == False).count()
    
    # Recent users
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    
    # Most active rooms
    active_rooms = db.query(
        Room.name,
        func.count(Message.id).label('message_count')
    ).join(Message, Room.id == Message.room_id)\
     .filter(Message.is_deleted == False)\
     .group_by(Room.id, Room.name)\
     .order_by(func.count(Message.id).desc())\
     .limit(5).all()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chat App Admin Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
            .header {{ text-align: center; margin-bottom: 30px; color: #333; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .stat-card {{ background: #667eea; color: white; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-number {{ font-size: 2em; font-weight: bold; }}
            .stat-label {{ margin-top: 5px; opacity: 0.9; }}
            .section {{ margin-bottom: 30px; }}
            .section h3 {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
            .list-item {{ padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }}
            .btn {{ background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 5px; }}
            .btn:hover {{ background: #5a67d8; }}
            .nav {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🛠️ Chat App Admin Dashboard</h1>
                <p>Welcome, {current_user.username}!</p>
            </div>
            
            <div class="nav">
                <a href="/analytics/overview" class="btn">📊 Analytics</a>
                <a href="/docs" class="btn">📚 API Docs</a>
                <a href="/admin/users" class="btn">👥 Manage Users</a>
                <a href="/admin/rooms" class="btn">💬 Manage Rooms</a>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{total_users}</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_rooms}</div>
                    <div class="stat-label">Chat Rooms</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_messages}</div>
                    <div class="stat-label">Messages</div>
                </div>
            </div>
            
            <div class="section">
                <h3>Recent Users</h3>
                {chr(10).join([f'<div class="list-item"><span>{user.username} ({user.role})</span><span>{user.created_at.strftime("%Y-%m-%d")}</span></div>' for user in recent_users])}
            </div>
            
            <div class="section">
                <h3>Most Active Rooms</h3>
                {chr(10).join([f'<div class="list-item"><span>{room.name}</span><span>{room.message_count} messages</span></div>' for room in active_rooms])}
            </div>
        </div>
    </body>
    </html>
    """

@admin_router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    current_user: User = Depends(require_admin_access),
    db: Session = Depends(get_db)
):
    """Simple user management interface"""
    users = db.query(User).all()
    
    user_rows = ""
    for user in users:
        status = "✅ Active" if user.is_active else "❌ Inactive"
        user_rows += f"""
        <tr>
            <td>{user.id}</td>
            <td>{user.username}</td>
            <td>{user.email}</td>
            <td>{user.role}</td>
            <td>{status}</td>
            <td>{user.created_at.strftime("%Y-%m-%d")}</td>
        </tr>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Management</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #667eea; color: white; }}
            .btn {{ background: #667eea; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👥 User Management</h1>
            <a href="/admin/dashboard" class="btn">← Back to Dashboard</a>
            
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
                    {user_rows}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

# This replaces the complex SQLAdmin setup
admin = admin_router