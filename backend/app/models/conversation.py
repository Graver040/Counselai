from sqlalchemy import Column, Integer, String
from .user import Base

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True)
    title = Column(String)
