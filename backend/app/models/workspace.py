from sqlalchemy import Column, Integer, String, ForeignKey
from .user import Base

class Workspace(Base):
    __tablename__ = 'workspaces'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
