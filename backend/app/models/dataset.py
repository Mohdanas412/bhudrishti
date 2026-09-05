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

    # PostGIS: geometry(Polygon, 4326). Fallback: GeoJSON text via GeoPandas.
    coverage_boundary_geojson = Column(Text, nullable=True)

    # NEW in schema.sql per this fix — not yet added to the actual file, do that first
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
