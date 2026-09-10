"""
Application configuration for BhuDrishti.
Loads environment variables and .env file with robust defaults.
"""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Lightweight .env loader that doesn't depend on python-dotenv."""
    for candidate in [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
        Path(__file__).resolve().parent.parent.parent.parent / ".env",
    ]:
        if candidate.is_file():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k and k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


_load_dotenv()


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./bhudrishti_fallback.db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "bhudrishti")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "bhudrishti")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))

    # Server
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", 8000))
    ENV: str = os.getenv("ENV", "development")

    # Matching Thresholds
    MATCH_HIGH_CONFIDENCE: int = int(os.getenv("MATCH_HIGH_CONFIDENCE", 90))
    MATCH_REVIEW_THRESHOLD: int = int(os.getenv("MATCH_REVIEW_THRESHOLD", 70))
    MATCH_MAX_DISTANCE: float = float(os.getenv("MATCH_MAX_DISTANCE", 0.01))
    MATCH_MAX_HAUSDORFF: float = float(os.getenv("MATCH_MAX_HAUSDORFF", 0.005))

    # GIS Canonical Specifications
    TARGET_CRS: str = os.getenv("TARGET_CRS", "EPSG:4326")
    AREA_CALC_CRS: str = os.getenv("AREA_CALC_CRS", "EPSG:32643")  # UTM Zone 43N
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    STANDARDIZED_DIR: str = os.path.join(UPLOAD_DIR, "standardized")

    # ArcGIS Integration
    ARCGIS_USERNAME: str = os.getenv("ARCGIS_USERNAME", "samit_kumar")
    ARCGIS_PASSWORD: str = os.getenv("ARCGIS_PASSWORD", "")


settings = Settings()
