from sqlalchemy import Column, Integer, String, Text
from .user import Base

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    event = Column(String)
    details = Column(Text)
