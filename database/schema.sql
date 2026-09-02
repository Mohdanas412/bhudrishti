-- BhuDrishti schema — owner: M6
-- Matches playbook Section 13. GiST index on every geometry column (Section 13 note).

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    authority TEXT,
    reliability_score NUMERIC
);

CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    crs TEXT,
    feature_count INTEGER,
    status TEXT
);

CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id),
    geometry geometry(Geometry, 4326) NOT NULL,
    area NUMERIC,
    land_use TEXT,
    capture_date DATE
);
CREATE INDEX idx_features_geometry ON features USING GIST (geometry);

CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    feature_a_id INTEGER REFERENCES features(id),
    feature_b_id INTEGER REFERENCES features(id),
    score NUMERIC,
    status TEXT
);

CREATE TABLE conflicts (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    type TEXT,
    severity TEXT
);

CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    conflict_id INTEGER REFERENCES conflicts(id),
    action TEXT,
    confidence NUMERIC,
    reason TEXT
);

CREATE TABLE review_decisions (
    id SERIAL PRIMARY KEY,
    recommendation_id INTEGER REFERENCES recommendations(id),
    reviewer TEXT,
    decision TEXT,
    comment TEXT,
    timestamp TIMESTAMPTZ DEFAULT now()
);

-- NOTE (see audit): source_feature_ids groups >2 features (Cadastral+Municipal+Building).
-- matches/conflicts above are strictly pairwise. Resolve the pairwise -> group clustering
-- rule with M5 before implementing this table's population logic.
CREATE TABLE harmonized_features (
    id SERIAL PRIMARY KEY,
    geometry geometry(Geometry, 4326) NOT NULL,
    source_feature_ids INTEGER[],
    lineage JSONB
);
CREATE INDEX idx_harmonized_geometry ON harmonized_features USING GIST (geometry);
