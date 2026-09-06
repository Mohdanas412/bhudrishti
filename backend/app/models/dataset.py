from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    crs = Column(String, nullable=True)
    feature_count = Column(Integer, default=0)
    status = Column(String, default="uploaded")
    dataset_type = Column(
        String, nullable=False, default="cadastral"
    )  # 'cadastral' | 'municipal' | 'building' — required at upload, per Stage 4 decision
    coverage_boundary_geojson = Column(Text, nullable=True)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
