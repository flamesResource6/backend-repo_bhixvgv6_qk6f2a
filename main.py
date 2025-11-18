import os
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from database import db, create_document, get_documents
from schemas import Activity, Metric, Claim

app = FastAPI(title="Solana Claim API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Solana Claim API running"}

# Health + DB check
@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# API models
class ActivityResponse(BaseModel):
    wallet: str
    tx_signature: str
    amount_sol: float
    timestamp: datetime
    solscan_url: str

class MetricsResponse(BaseModel):
    total_sol_recovered: float
    total_accounts_claimed: int
    updated_at: datetime

class CreateClaimRequest(BaseModel):
    wallet: str
    accounts: List[str]
    total_amount_sol: float
    fee_percent: float

class CreateClaimResponse(BaseModel):
    claim_id: str
    ok: bool

# Seed starter data if empty
@app.on_event("startup")
async def seed_data():
    try:
        if db is None:
            return
        # Seed metrics doc if none
        if db["metric"].count_documents({}) == 0:
            create_document("metric", Metric(total_sol_recovered=0.0, total_accounts_claimed=0))
        # Seed a few fake activities for UI preview
        if db["activity"].count_documents({}) == 0:
            sample = [
                Activity(wallet="4h...XkQ", tx_signature="5abc...123", amount_sol=1.25),
                Activity(wallet="B9...PqL", tx_signature="8def...456", amount_sol=0.78),
                Activity(wallet="Fs...9Lm", tx_signature="3xyz...789", amount_sol=2.03),
            ]
            for a in sample:
                create_document("activity", a)
    except Exception:
        pass

# Public endpoints
@app.get("/api/metrics", response_model=MetricsResponse)
def get_metrics():
    docs = db["metric"].find().sort("updated_at", -1).limit(1)
    item = next(docs, None)
    if not item:
        raise HTTPException(status_code=404, detail="Metrics not found")
    return MetricsResponse(
        total_sol_recovered=float(item.get("total_sol_recovered", 0.0)),
        total_accounts_claimed=int(item.get("total_accounts_claimed", 0)),
        updated_at=item.get("updated_at", datetime.now(timezone.utc)),
    )

@app.get("/api/activity", response_model=List[ActivityResponse])
def get_activity(limit: int = 12):
    items = get_documents("activity", {}, limit)
    result: List[ActivityResponse] = []
    for it in items:
        sig = it.get("tx_signature", "")
        result.append(ActivityResponse(
            wallet=it.get("wallet", ""),
            tx_signature=sig,
            amount_sol=float(it.get("amount_sol", 0)),
            timestamp=it.get("timestamp") or it.get("created_at") or datetime.now(timezone.utc),
            solscan_url=f"https://solscan.io/tx/{sig}",
        ))
    return result

@app.post("/api/claims", response_model=CreateClaimResponse)
def create_claim(payload: CreateClaimRequest):
    # Store a claim intent; in real app this would kick off onchain flow
    cid = create_document("claim", Claim(
        wallet=payload.wallet,
        accounts=payload.accounts,
        total_amount_sol=payload.total_amount_sol,
        fee_percent=payload.fee_percent,
    ))
    # Update metrics quickly
    try:
        db["metric"].update_one({}, {"$inc": {"total_sol_recovered": payload.total_amount_sol, "total_accounts_claimed": len(payload.accounts)}, "$set": {"updated_at": datetime.now(timezone.utc)}}, upsert=True)
        create_document("activity", Activity(wallet=payload.wallet[:2]+"..."+payload.wallet[-3:], tx_signature="pending", amount_sol=payload.total_amount_sol))
    except Exception:
        pass
    return CreateClaimResponse(ok=True, claim_id=cid)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
