from typing import List
from datetime import date
from pydantic import BaseModel

class CustomerIn(BaseModel):
    customer_id: str
    last_visit_date: date
    total_spent: int
    visit_count: int
    membership_type: str

class CustomerOut(BaseModel):
    id: int
    customer_code: str
    last_visit_date: date
    total_spent: int
    visit_count: int
    membership_type: str
    days_since_last_visit: int
    risk_level: str
    risk_reason: str

class CustomerList(BaseModel):
    items: List[CustomerOut]
    total: int

class ImportResult(BaseModel):
    import_id: str
    inserted: int
    updated: int
    total_rows: int
