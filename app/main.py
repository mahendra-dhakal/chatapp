from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import create_tables, SessionLocal
from .auth.router import router as auth_router
from .chat.router import router as chat_router
from .chat.websocket import websocket_endpoint
from .admin.router import router as admin_router
from .analytics.router import router as analytics_router
from .admin.sqladmin_setup import admin

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    description="Real-time chat with admin dashboard and analytics"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(analytics_router)

# Include simple admin interface
app.include_router(admin)

# WebSocket endpoint for real-time chat
@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int, token: str):
    await websocket_endpoint(websocket, room_id, token)

@app.get("/")
async def welcome():
    return {
        "message": f"Welcome to {settings.APP_NAME}! 🚀",
        "status": "running",
        "features": {
            "authentication": "JWT with role-based access",
            "real_time_chat": "WebSocket powered",
            "admin_dashboard": "Custom admin interface at /admin/dashboard",
            "analytics": "Comprehensive chat analytics",
        },
        "quick_links": {
            "api_docs": "/docs",
            "admin_panel": "/admin/dashboard",
            "analytics": "/analytics/overview"
        },
        "note": "Admin interface requires admin role. Create admin user via API first."
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    create_tables()
    
    # Create default room if it doesn't exist
    from .chat.models import Room
    db = SessionLocal()
    try:
        existing_room = db.query(Room).filter(Room.name == "General Chat").first()
        if not existing_room:
            default_room = Room(
                name="General Chat",
                description="Welcome to the main chat room! Feel free to introduce yourself.",
                is_private=False
            )
            db.add(default_room)
            db.commit()
            print("✅ Created default 'General Chat' room")
    except Exception as e:
        print(f"Warning: Could not create default room - {e}")
    finally:
        db.close()
    
    print(f"\n🚀 {settings.APP_NAME} is ready!")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🔌 WebSocket: ws://localhost:8000/ws/{{room_id}}?token={{jwt_token}}")
    print(f"🛠️  Admin Panel: http://localhost:8000/admin/dashboard")
    print(f"📊 Analytics: http://localhost:8000/analytics/overview")
    print(f"📝 Create admin user, then access admin panel\n")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )