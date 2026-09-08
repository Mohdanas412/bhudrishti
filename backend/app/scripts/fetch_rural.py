import json
import os
import random
import urllib.parse
import urllib.request

# Punjab rural area bbox
bbox = "30.85,75.75,30.90,75.85"
url = "https://overpass-api.de/api/interpreter"
query = f"""
[out:json];
way["landuse"="farmland"]({bbox});
(._;>;);
out body;
"""

print("Fetching rural farmland from OSM...")
req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': query}).encode('utf-8'))
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode('utf-8'))

ways = [e for e in data["elements"] if e["type"] == "way" and "nodes" in e]
nodes = {e["id"]: (e["lon"], e["lat"]) for e in data["elements"] if e["type"] == "node"}

features = []
for way in ways:
    try:
        coords = [nodes[n] for n in way["nodes"]]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        if len(coords) < 4:
            continue
        
        features.append({
            "type": "Feature",
            "properties": {
                "parcel_id": f"PB-FAR-{way['id']}",
                "land_use": "Agricultural",
                "owner": random.choice(["Singh", "Kaur", "Gill", "Sandhu", "Mann"]) + " Family",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        })
    except KeyError:
        continue

if not features:
    print("No farmland features found in this bbox. Trying another rural bbox (Maharashtra)...")
    bbox = "18.5,74.0,18.6,74.1" # Rural Pune area
    query = f"[out:json];way[\"landuse\"=\"farmland\"]({bbox});(._;>;);out body;"
    req = urllib.request.Request(url, data=urllib.parse.urlencode({'data': query}).encode('utf-8'))
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
    ways = [e for e in data["elements"] if e["type"] == "way" and "nodes" in e]
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in data["elements"] if e["type"] == "node"}
    for way in ways:
        try:
            coords = [nodes[n] for n in way["nodes"]]
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])
            if len(coords) < 4:
                continue
            features.append({
                "type": "Feature",
                "properties": {
                    "parcel_id": f"MH-FAR-{way['id']}",
                    "land_use": "Agricultural"
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]}
            })
        except KeyError:
            continue

out = {
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
    "features": features
}

os.makedirs("/app/uploads/rural", exist_ok=True)
with open("/app/uploads/rural/rural_cadastral_base.geojson", "w") as f:
    json.dump(out, f)

print(f"Generated {len(features)} rural farm features.")
