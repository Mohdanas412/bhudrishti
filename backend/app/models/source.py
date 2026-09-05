from sqlalchemy import Column, Float, Integer, String

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    authority = Column(String, nullable=True)
    reliability_score = Column(Float, nullable=True)
