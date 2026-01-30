from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class ImportRecordOut(BaseModel):
    id: UUID
    filename: Optional[str]
    status: str
    row_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
