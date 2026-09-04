-- BhuDrishti schema — owner: M6
-- Matches playbook Section 13, updated per Addendum v1 (Critical Fixes 1, 2, 4).
-- GiST index on every geometry column (Section 13 note).

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
    status TEXT,
    -- Addendum Critical Fix 4: coverage boundary, computed once by M4 at ingestion.
    -- Used by the coverage-aware missing-feature rule (no candidate + inside this
    -- boundary = real gap; outside it = expected absence, not a conflict).
    coverage_boundary geometry(Polygon, 4326)
);
CREATE INDEX idx_datasets_coverage ON datasets USING GIST (coverage_boundary);

-- Addendum Critical Fix 1: canonical schema is no longer lossy.
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id),
    feature_id TEXT NOT NULL,              -- original ID from source data, e.g. "P102"
    geometry geometry(Geometry, 4326) NOT NULL,
    area NUMERIC,
    capture_date DATE,
    authority TEXT,
    accuracy NUMERIC,
    attributes JSONB DEFAULT '{}'::jsonb   -- Cadastral: land_use/owner. Municipal: zone/address.
                                            -- Building: building_type/status.
);
CREATE INDEX idx_features_geometry ON features USING GIST (geometry);
CREATE INDEX idx_features_attributes ON features USING GIN (attributes);

-- Pairwise matches — unchanged, this is still the raw matching-engine output (M5).
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    feature_a_id INTEGER REFERENCES features(id),
    feature_b_id INTEGER REFERENCES features(id),
    score NUMERIC,
    status TEXT
);

-- Addendum Critical Fix 2: NEW. Connected-component groups built from matches
-- with score >= 70. A group needs >=2 pairwise agreements to auto-cluster;
-- a lone pairwise match still proceeds but status = 'partial_group'.
CREATE TABLE match_groups (
    id SERIAL PRIMARY KEY,
    member_feature_ids INTEGER[] NOT NULL,
    status TEXT  -- e.g. 'clustered', 'partial_group'
);

-- Addendum Critical Fix 2: conflicts now run PER CLUSTER, not per pair —
-- so this references match_groups, not matches.
CREATE TABLE conflicts (
    id SERIAL PRIMARY KEY,
    match_group_id INTEGER REFERENCES match_groups(id),
    type TEXT,      -- geometry | area | attribute | missing_feature | duplicate | temporal
    severity TEXT   -- informational | low | medium | high
);

-- Addendum Critical Fix 3: recommendation action enum frozen. This table stores
-- whatever action string the app layer validates against that enum.
CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    conflict_id INTEGER REFERENCES conflicts(id),
    action TEXT,
    preferred_source_id INTEGER REFERENCES sources(id),  -- set only when action = 'prefer_source'
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

CREATE TABLE harmonized_features (
    id SERIAL PRIMARY KEY,
    match_group_id INTEGER REFERENCES match_groups(id),
    geometry geometry(Geometry, 4326) NOT NULL,
    source_feature_ids INTEGER[],
    lineage JSONB
);
CREATE INDEX idx_harmonized_geometry ON harmonized_features USING GIST (geometry);