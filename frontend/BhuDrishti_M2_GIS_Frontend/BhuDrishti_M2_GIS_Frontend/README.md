# BhuDrishti - M2 GIS Frontend Starter

This package contains the M2 GIS frontend files.

## Structure

frontend/src/
- map/
  - MapView.jsx
  - LayerControl.jsx
  - MapLegend.jsx
  - FeaturePanel.jsx
  - GISPage.jsx
  - GISApp.jsx
  - map.css
- mock/
  - map.json

## Install

From the existing BhuDrishti `frontend` folder:

```bash
npm install leaflet react-leaflet
```

Then import the GIS page from your application where required.

Example:

```jsx
import GISPage from "./map/GISPage";
import "./map/map.css";

function App() {
  return <GISPage />;
}

export default App;
```

## M2 ownership

M2 focuses on:
- frontend/src/map
- map layers
- GIS interactions
- feature selection
- map legend
- feature details

The data in `mock/map.json` is only starter/mock data. Replace it with the team's frozen contract/backend data when integration is ready.
