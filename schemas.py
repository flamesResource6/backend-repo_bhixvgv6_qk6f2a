"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- Activity -> "activity"
- Metric -> "metric"
- Claim -> "claim"
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Activity(BaseModel):
    """Recent on-chain-like activity for public audit feed"""
    wallet: str = Field(..., description="Wallet address (base58)")
    tx_signature: str = Field(..., description="Transaction signature")
    amount_sol: float = Field(..., ge=0, description="Amount in SOL")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC time of activity")

class Metric(BaseModel):
    """Aggregated platform metrics"""
    total_sol_recovered: float = Field(0, ge=0)
    total_accounts_claimed: int = Field(0, ge=0)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Claim(BaseModel):
    """User claim record"""
    wallet: str = Field(..., description="Requester wallet")
    accounts: List[str] = Field(default_factory=list, description="Claimed account addresses")
    total_amount_sol: float = Field(0, ge=0)
    fee_percent: float = Field(1.0, ge=0, le=100, description="Protocol fee percent shown to user")
    tx_signature: Optional[str] = Field(None, description="Chain transaction signature if executed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
