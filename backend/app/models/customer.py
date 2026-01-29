from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    last_visit_date: Mapped[datetime.date] = mapped_column(Date)
    total_spent: Mapped[int] = mapped_column(Integer)
    visit_count: Mapped[int] = mapped_column(Integer)
    membership_type: Mapped[str] = mapped_column(String(50), index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
