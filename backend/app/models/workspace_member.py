from sqlalchemy import Column, Integer, ForeignKey, String
from .user import Base

class WorkspaceMember(Base):
    __tablename__ = 'workspace_members'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    workspace_id = Column(Integer, nullable=False)
    role = Column(String, default='member')
