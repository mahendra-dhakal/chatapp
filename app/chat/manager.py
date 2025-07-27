import json
import asyncio
from typing import Dict, List, Set
from fastapi import WebSocket




class ConnectionManager:
    """manages WebSocket connections for real-time chat"""
    
    
    
    def __init__(self):
        self.active_connections: Dict[int, List[Dict]] = {}
        self.user_rooms: Dict[int, Set[int]] = {}
     
     
     
        
    async def connect(self, websocket: WebSocket, room_id: int, user):
        """cccept WebSocket connection and add to room"""
        await websocket.accept()
        
        connection_info = {
            'websocket': websocket,
            'user': user,
            'room_id': room_id,
            'connected_at': asyncio.get_event_loop().time()
        }
        
        
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(connection_info)
        
        if user.id not in self.user_rooms:
            self.user_rooms[user.id] = set()
        self.user_rooms[user.id].add(room_id)
        
        
        
        print(f"👤 {user.username} joined room {room_id}")
        
        await self.broadcast_to_room(room_id, {
            'type': 'user_joined',
            'user': user.username,
            'message': f'{user.username} joined the chat',
            'user_count': len(self.get_room_users(room_id))
        }, exclude_websocket=websocket)
       
       
        
    def disconnect(self, websocket: WebSocket, room_id: int, user):
        """remove connection from room"""
        if room_id in self.active_connections:
            self.active_connections[room_id] = [
                conn for conn in self.active_connections[room_id]
                if conn['websocket'] != websocket
            ]
            
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
        
        if user.id in self.user_rooms:
            self.user_rooms[user.id].discard(room_id)
            if not self.user_rooms[user.id]:
                del self.user_rooms[user.id]
        
        print(f"👋 {user.username} left room {room_id}")
        
        asyncio.create_task(
            self.broadcast_to_room(room_id, {
                'type': 'user_left',
                'user': user.username,
                'message': f'{user.username} left the chat',
                'user_count': len(self.get_room_users(room_id))
            })
        )
    
    
    
    
    async def broadcast_to_room(self, room_id: int, message: dict, exclude_websocket: WebSocket = None):
        """send message to everyone in the room"""
        if room_id not in self.active_connections:
            return
            
        message_str = json.dumps(message)
        dead_connections = []
        
        for connection in self.active_connections[room_id]:
            websocket = connection['websocket']
            
            if websocket == exclude_websocket:
                continue
                
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                print(f"Failed to send to {connection['user'].username}: {e}")
                dead_connections.append(connection)
        
        for dead_conn in dead_connections:
            self.active_connections[room_id].remove(dead_conn)
    
    
    
    
    def get_room_users(self, room_id: int) -> List[str]:
        if room_id not in self.active_connections:
            return []
            
        users = []
        seen_users = set()
        
        for connection in self.active_connections[room_id]:
            username = connection['user'].username
            if username not in seen_users:
                users.append(username)
                seen_users.add(username)
                
        return users
    
    
    
    def get_connection_count(self, room_id: int) -> int:
        """get number of active connections in room"""
        return len(self.active_connections.get(room_id, []))






manager = ConnectionManager()