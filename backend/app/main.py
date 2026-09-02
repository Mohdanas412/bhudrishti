"""
BhuDrishti backend entrypoint.

Rule (playbook Section 12): route files stay thin — they call into
services/, which call into engines/. No GIS/matching logic here.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import datasets, matching, conflicts, reconciliation, reviews, harmonized

app = FastAPI(title="BhuDrishti API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before demo day
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
app.include_router(matching.router, prefix="/matching", tags=["matching"])
app.include_router(conflicts.router, prefix="/conflicts", tags=["conflicts"])
app.include_router(reconciliation.router, prefix="/reconciliation", tags=["reconciliation"])
app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
app.include_router(harmonized.router, prefix="/harmonized", tags=["harmonized"])


@app.get("/health")
def health():
    return {"status": "ok"}
