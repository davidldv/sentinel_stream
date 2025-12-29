from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Transaction(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    timestamp: datetime
    merchant_id: str
    location: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
