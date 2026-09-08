import json
import os
import random

# Base coordinate in rural Punjab (approx 30.5, 75.5)
basex, basey = 75.500, 30.500
# Farm parcel size: ~100m wide (0.001 deg)
w, h = 0.001, 0.001

random.seed(123)

features_a = []
features_b = []

# Generate a 10x10 grid of rural farms
idx = 1
for i in range(10):
    for j in range(10):
        # Add some slight irregularity so they aren't perfect squares
        x1 = basex + (i * w) + random.uniform(-0.0002, 0.0002)
        y1 = basey + (j * h) + random.uniform(-0.0002, 0.0002)
        x2 = x1 + w + random.uniform(-0.0002, 0.0002)
        y2 = y1
        x3 = x2
        y3 = y2 + h + random.uniform(-0.0002, 0.0002)
        x4 = x1
        y4 = y3

        coords = [[x1, y1], [x2, y2], [x3, y3], [x4, y4], [x1, y1]]

        # Base Cadastral Feature
        features_a.append({
            "type": "Feature",
            "properties": {
                "parcel_id": f"PB-R-{idx}",
                "land_use": "Agricultural",
                "crop": random.choice(["Wheat", "Paddy", "Sugarcane"]),
                "owner": f"Farmer {idx}"
            },
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })

        # Panchayat / Secondary Survey Feature (jittered slightly, 15% mislabeled)
        jitter_x = random.uniform(-0.0001, 0.0001)
        jitter_y = random.uniform(-0.0001, 0.0001)
        coords_b = [[cx + jitter_x, cy + jitter_y] for cx, cy in coords]
        
        crop_b = features_a[-1]["properties"]["crop"]
        if random.random() < 0.15:
            crop_b = random.choice(["Fallow", "Mustard"])

        features_b.append({
            "type": "Feature",
            "properties": {
                "parcel_id": f"PCH-{idx}",
                "zone": "Rural Panchayat",
                "crop_registry": crop_b
            },
            "geometry": {"type": "Polygon", "coordinates": [coords_b]}
        })
        idx += 1

out_a = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": features_a}
out_b = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:4326"}}, "features": features_b}

os.makedirs("/app/uploads/rural", exist_ok=True)
with open("/app/uploads/rural/punjab_cadastral.geojson", "w") as f:\
    json.dump(out_a, f)
with open("/app/uploads/rural/punjab_panchayat.geojson", "w") as f:\
    json.dump(out_b, f)

print(f"Generated {len(features_a)} rural features (Dataset A & B).")

