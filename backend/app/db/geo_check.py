import geopandas as gpd

for filename in ["good_parcel.geojson", "bad_parcel.geojson"]:
    path = f"uploads/{filename}"
    print(f"\n--- {filename} ---")

    gdf = gpd.read_file(path)

    print("CRS:", gdf.crs)
    print("Feature count:", len(gdf))

    for idx, geom in enumerate(gdf.geometry):
        print(f"  feature {idx}: is_valid={geom.is_valid}, is_empty={geom.is_empty}")
