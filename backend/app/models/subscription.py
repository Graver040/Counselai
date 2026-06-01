from sqlalchemy import Column, Integer, String
from .user import Base

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    plan = Column(String)
    user_id = Column(Integer)
