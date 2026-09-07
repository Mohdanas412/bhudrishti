from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_api_datasets_and_pipeline_smoke():
    # 1. Health check
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    # 2. Seed sample datasets
    r = client.post("/datasets/sample-seed")
    assert r.status_code == 200
    seed_body = r.json()
    assert seed_body["status"] == "seeded"
    assert len(seed_body["dataset_ids"]) == 3

    # 3. List datasets
    r = client.get("/datasets")
    assert r.status_code == 200
    datasets = r.json()
    assert len(datasets) >= 3

    ds_id = seed_body["dataset_ids"][0]

    # 4. Get single dataset & geojson
    r = client.get(f"/datasets/{ds_id}")
    assert r.status_code == 200
    assert r.json()["id"] == ds_id

    r = client.get(f"/datasets/{ds_id}/geojson")
    assert r.status_code == 200
    geojson = r.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0

    # 5. Matching endpoint
    r = client.get("/matching")
    assert r.status_code == 200
    matches = r.json()
    assert len(matches) > 0
    assert "score" in matches[0]
    assert "feature_a" in matches[0]

    # 6. Conflicts endpoint
    r = client.get("/conflicts")
    assert r.status_code == 200
    conflicts = r.json()
    assert len(conflicts) > 0
    assert "type" in conflicts[0]
    assert "severity" in conflicts[0]

    # 7. Recommendations endpoint
    r = client.get("/reconciliation")
    assert r.status_code == 200
    recs = r.json()
    assert len(recs) > 0
    assert "action" in recs[0]

    # 8. Submit review
    c_id = conflicts[0]["id"]
    r = client.post(f"/reviews/{c_id}", json={
        "reviewer": "Officer Sharma",
        "decision": "accept",
        "comment": "Verified against survey benchmark."
    })
    assert r.status_code == 200
    assert r.json()["status"] == "recorded"

    # 9. List reviews
    r = client.get("/reviews")
    assert r.status_code == 200
    reviews = r.json()
    assert len(reviews) > 0

    # 10. Harmonized GeoJSON
    r = client.get("/harmonized")
    assert r.status_code == 200
    harm = r.json()
    assert harm["type"] == "FeatureCollection"
    assert len(harm["features"]) > 0
