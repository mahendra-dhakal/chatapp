from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base





class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    
    
    def __repr__(self):
        return f"<Room '{self.name}' ({self.id})>"




class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    edited_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    author = relationship("User", back_populates="messages")
    room = relationship("Room", back_populates="messages")
    
    
    
    def __repr__(self):
        return f"<Message {self.id} by {self.author.username if self.author else 'Unknown'}>"
    
    
    
    
    @property
    def content_preview(self):
        """get first 50 characters of content for previews"""
        if len(self.content) <= 50:
            return self.content
        return self.content[:47] + "..."