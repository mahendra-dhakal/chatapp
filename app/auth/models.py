from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base



class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # user, moderator, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime)
    
    
    messages = relationship("Message", back_populates="author", cascade="all, delete-orphan")
    
    
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
 
    
    @property
    def is_admin(self):
        return self.role == "admin"
    
    
    @property 
    def is_moderator(self):
        return self.role in ["admin", "moderator"]