# GIS Engine — owner M4

Pipeline order (playbook Section 6): ingestion → validation → normalization → spatial_index → candidate_generation.

Files to create here:
- `ingestion.py` — detect CRS, normalize via pyproj
- `validation.py` — fix geometry via shapely (self-intersections, empty geoms). Work on a copy — never mutate the original upload (see hard rule, Section 10).
- `normalization.py` — map schema to canonical fields via rapidfuzz + synonym dictionary
- `spatial_index.py` — GeoPandas sindex / PostGIS GiST
- `candidate_generation.py` — nearby-only candidate pairs, not all-to-all

Known open item from audit: canonical schema's single `land_use` field doesn't map cleanly from Municipal (`zone/address`) or Building (`building_type/status`) datasets. Confirm field-mapping table with M5/M6 before finalizing `normalization.py`.
