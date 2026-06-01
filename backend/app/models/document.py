from sqlalchemy import Column, Integer, String, ForeignKey, Text
from .user import Base

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    workspace_id = Column(Integer)
