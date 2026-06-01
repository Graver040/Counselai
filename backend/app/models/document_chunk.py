from sqlalchemy import Column, Integer, ForeignKey, Text
from .user import Base

class DocumentChunk(Base):
    __tablename__ = 'document_chunks'
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer)
    text = Column(Text)
