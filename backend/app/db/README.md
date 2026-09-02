# DB fallback (playbook Section 19 risk mitigation)

If `docker compose up` fails for you on Day 1–2 (common with PostGIS on some Windows/WSL setups), don't block:

1. Work against SQLite + GeoPandas in-memory locally instead of PostGIS.
2. Keep your queries inside `app/services/` behind the same function signatures the PostGIS-backed version will use, so swapping back later is a one-file change.
3. Flag it in standup — merge back to PostGIS once your teammate or the lead unblocks your Docker setup.

Do not let this decision spread into `engines/` — engines should stay storage-agnostic where possible.
