from sqlalchemy import Column, Integer, Text
from .user import Base

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer)
    content = Column(Text)
