from sqlalchemy import Column, Integer, String
from .user import Base

class UsageLog(Base):
    __tablename__ = 'usage_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    action = Column(String)
