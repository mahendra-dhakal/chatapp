import json
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from .models import Message, Room
from .schemas import MessageWebSocket
from .manager import manager
from ..auth.utils import verify_token
from ..auth.models import User
from ..database import get_db



async def websocket_endpoint(websocket: WebSocket, room_id: int, token: str):
    """handle WebSocket connections for real-time chat"""
    
    db = next(get_db())
    user = None
    
    
    try:
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid or expired token")
            return
        
        username = payload.get("sub")
        user = db.query(User).filter(User.username == username).first()
        
        if not user or not user.is_active:
            await websocket.close(code=4002, reason="User not found or account deactivated")
            return
        
        room = db.query(Room).filter(Room.id == room_id).first()
        if not room:
            await websocket.close(code=4003, reason="Chat room not found")
            return
        
        await manager.connect(websocket, room_id, user)
        
        
        
        await websocket.send_text(json.dumps({
            'type': 'room_info',
            'room': {
                'id': room.id,
                'name': room.name,
                'description': room.description or f"Welcome to {room.name}!"
            },
            'users_online': manager.get_room_users(room_id),
            'connection_count': manager.get_connection_count(room_id),
            'message': f'Connected to {room.name}! 🎉'
        }))
        
        
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                try:
                    msg = MessageWebSocket(**message_data)
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': f'Invalid message format: {str(e)}'
                    }))
                    continue
                
                # save to database
                try:
                    db_message = Message(
                        content=msg.content,
                        user_id=user.id,
                        room_id=room_id
                    )
                    db.add(db_message)
                    db.commit()
                    db.refresh(db_message)
                    
                    
                    # broadcast to room
                    broadcast_data = {
                        'type': 'message',
                        'id': db_message.id,
                        'content': db_message.content,
                        'timestamp': db_message.timestamp.isoformat(),
                        'author': user.username,
                        'author_id': user.id,
                        'room_id': room_id
                    }
                    
                    await manager.broadcast_to_room(room_id, broadcast_data)
                    
                    
                except SQLAlchemyError as e:
                    db.rollback()
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': 'Failed to save message. Please try again.'
                    }))
                    print(f"Database error: {e}")
                
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'Please send valid JSON data'
                }))
            except Exception as e:
                print(f"Unexpected error in WebSocket: {e}")
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'Something went wrong. Please refresh and try again.'
                }))
                
                
                
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        if websocket.client_state.name != "DISCONNECTED":
            await websocket.close(code=4000, reason="Internal server error")
    finally:
        if user:
            manager.disconnect(websocket, room_id, user)
        db.close()