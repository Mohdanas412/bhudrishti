# backend/app/models/feature.py
from sqlalchemy import JSON, Column, Float, ForeignKey, Integer, String

from app.db.base import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    feature_id = Column(
        String, nullable=False
    )  # original ID from source data, e.g. "P102"
    geometry_geojson = Column(
        String, nullable=False
    )  # SQLite fallback: GeoJSON string, not a real geometry column
    area = Column(Float, nullable=True)
    capture_date = Column(
        String, nullable=True
    )  # kept as plain string for SQLite simplicity, not parsed yet
    authority = Column(String, nullable=True)
    accuracy = Column(Float, nullable=True)
    attributes = Column(
        JSON, default=dict
    )  # canonical per-type fields — SQLAlchemy's JSON type works fine on SQLite
