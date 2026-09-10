# Topology Fix Visual Changes Debug Outline

## Problem Statement
After clicking "Run Topology Fix", users report not seeing visual map changes even though the backend reports successful topology correction.

## Diagnostic Steps

### 1. Verify Backend Response
Check if the backend is actually returning corrected geometries that differ from originals:
- Network tab → Check response from `/harmonized/topology/correct`
- Look for `corrected_geometries` object in response
- Compare a sample geometry before/after to see if coordinates actually changed

### 2. Frontend Data Flow Verification
Trace how corrected geometries flow from response to map rendering:
- `handleRunTopologyFix` receives response
- Extracts `correctedGeometries` and `affectedPairs`
- Updates `matches` state with corrected geometries
- `useEffect` with `[matches, selectedMatch, layersVisibility, mapReady]` triggers
- Calls `renderVectorLayers(map, matches, selectedMatch)`
- `renderVectorLayers` builds GeoJSON from `matches[i].feature_a_details?.geometry`
- Map source updated with `setData()`
- `map.triggerRepaint()` called to force redraw

### 3. Potential Failure Points

#### A. Geometry Not Actually Changing
- Tolerance too small (0.00005° ≈ 5m) - may not snap if already aligned
- Topology engine determines no fixes needed
- Sample data already topologically correct

#### B. State Update Not Triggering Render
- `matches` state update not detecting change (shallow comparison issue)
- `useEffect` dependencies incomplete
- Map not ready when update occurs

#### C. Map Source Update Issues
- Source ID mismatch
- GeoJSON format incorrect
- `setData()` not actually updating data
- `triggerRepaint()` called at wrong time

#### D. Geometry Access Issues
- `feature_a_details?.geometry` null/undefined
- Geometry structure not matching MapLibre expectations
- Coordinate system mismatch

### 4. Verification Commands

#### Backend Check:
```bash
curl -s -X POST http://localhost:8000/harmonized/topology/correct?tolerance=0.00005 | jq '.corrected_geometries | to_entries | .[0]'
```

#### Frontend Debug (add temporary logging):
```javascript
// In handleRunTopologyFix after setting matches:
console.log('Matches after topology fix:', JSON.stringify(matches, null, 2));
console.log('Sample geometry before:', matches[0]?.feature_a_details?.geometry);
console.log('Sample geometry after:', correctedGeometries[matches[0]?.feature_a]);

// In renderVectorLayers:
console.log('Rendering cadastralFC:', JSON.stringify(cadastralFC, null, 2));
```

### 5. Solutions Based on Diagnosis

#### If geometries aren't changing:
- Increase tolerance for testing (0.0005° ≈ 50m)
- Use known mismatched sample data
- Force topology correction regardless of need

#### If state isn't updating:
- Use functional state update: `setMatches(prev => [...])`
- Ensure deep equality check works (consider using lodash.isEqual)

#### If map source not updating:
- Verify source IDs exactly match: "cadastral-source", "municipal-source"
- Check that GeoJSON is valid FeatureCollection
- Add error handling around map operations

#### If triggerRepaint() not working:
- Call after small delay: `setTimeout(() => map.triggerRepaint(), 100)`
- Ensure map is styled loaded: `if (map.isLoaded()) map.triggerRepaint()`

### 6. Implementation Notes

Our current implementation:
```javascript
// After updating match state with corrected geometries:
setMatches((prev) =>
  prev.map((m) => {
    // ... update logic
    return { ...m, score, status, breakdown, feature_a_details, feature_b_details };
  })
);

// Then in useEffect:
useEffect(() => {
  const map = mapInstanceRef.current;
  if (!map || !map.isStyleLoaded()) return;
  renderVectorLayers(map, matches, selectedMatch);
  // ... focus logic
}, [matches, selectedMatch, layersVisibility, mapReady]);

// In renderVectorLayers:
if (map.getSource("cadastral-source")) {
  map.getSource("cadastral-source").setData(cadastralFC);
} else {
  map.addSource("cadastral-source", { type: "geojson", data: cadastralFC );
}
// Trigger repaint to ensure visual updates
if (map.isStyleLoaded()) {
  map.triggerRepaint();
}
```

### 7. Quick Test Procedure
1. Open browser dev tools
2. Network tab: clear and preserve log
3. Console: temporarily log geometry updates
4. Click "Run Topology Fix"
5. Check:
   - Network response for corrected_geometries
   - Console logs for geometry differences
   - Whether renderVectorLayers is called
   - Whether map source setData is called
   - Whether triggerRepaint is called

## Conclusion
Visual changes require:
1. Backend to return actually different geometries
2. Frontend to correctly update match state with those geometries
3. Rendering pipeline to pick up the new geometries
4. Map to redraw with the new data

If any step fails, no visual change will be seen despite successful processing.