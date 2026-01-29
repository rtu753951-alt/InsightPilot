import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.db import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerOut, ImportResult
from app.core.llm_service import generate_followup_suggestion


router = APIRouter(prefix="/api/customers", tags=["customers"])

REQUIRED_COLUMNS = {
    "customer_id",
    "last_visit_date",
    "total_spent",
    "visit_count",
    "membership_type",
}

def _to_int(v: str, field: str) -> int:
    try:
        return int(v)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid int for {field}: {v}")

def _to_date(v: str, field: str) -> date:
    try:
        # 期待格式 YYYY-MM-DD
        return date.fromisoformat(v)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid date for {field} (YYYY-MM-DD): {v}")

@router.post("/import", response_model=ImportResult)
async def import_customers_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw = await file.read()
    text = raw.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row")

    missing = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing columns: {sorted(list(missing))}")

    inserted = 0
    updated = 0
    total_rows = 0

    for row in reader:
        total_rows += 1

        customer_id = (row.get("customer_id") or "").strip()
        if not customer_id:
            raise HTTPException(status_code=422, detail=f"Row {total_rows}: customer_id is empty")

        last_visit_date = _to_date((row.get("last_visit_date") or "").strip(), "last_visit_date")
        total_spent = _to_int((row.get("total_spent") or "").strip(), "total_spent")
        visit_count = _to_int((row.get("visit_count") or "").strip(), "visit_count")
        membership_type = (row.get("membership_type") or "").strip()

        existing = db.scalar(select(Customer).where(Customer.customer_code == customer_id))

        if existing:
            existing.last_visit_date = last_visit_date
            existing.total_spent = total_spent
            existing.visit_count = visit_count
            existing.membership_type = membership_type
            updated += 1
        else:
            c = Customer(
                customer_code=customer_id,
                last_visit_date=last_visit_date,
                total_spent=total_spent,
                visit_count=visit_count,
                membership_type=membership_type,
            )
            db.add(c)
            inserted += 1

    db.commit()

    return ImportResult(inserted=inserted, updated=updated, total_rows=total_rows)


def _churn_rule(membership_type: str, days_since: int) -> tuple[str, str]:
    m = (membership_type or "").upper()

    # VIP 放寬一點
    if m == "VIP":
        if days_since >= 150:
            return "high", f"VIP but inactive for {days_since} days (>=150)"
        if days_since >= 90:
            return "medium", f"VIP inactive for {days_since} days (>=90)"
        return "low", f"VIP active within {days_since} days"

    # 其他會員
    if days_since >= 120:
        return "high", f"Inactive for {days_since} days (>=120)"
    if days_since >= 60:
        return "medium", f"Inactive for {days_since} days (>=60)"
    return "low", f"Active within {days_since} days"


@router.get("", response_model=list[CustomerOut])
def list_customers(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))  # 防呆：最多一次 500
    rows = db.execute(
        select(Customer).order_by(Customer.customer_code).limit(limit).offset(offset)
    ).scalars().all()

    today = date.today()
    result: list[CustomerOut] = []

    for c in rows:
        days_since = (today - c.last_visit_date).days
        
        # ✅ 新增：算風險 (Moved logic to helper function)
        risk_level, risk_reason = _churn_rule(c.membership_type, days_since)

        result.append(
            CustomerOut(
                id=c.id,
                customer_code=c.customer_code,
                last_visit_date=c.last_visit_date,
                total_spent=c.total_spent,
                visit_count=c.visit_count,
                membership_type=c.membership_type,
                days_since_last_visit=days_since,
                # ✅ 新增：回傳風險欄位
                risk_level=risk_level,
                risk_reason=risk_reason,
            )
        )

    return result
    
@router.post("/{customer_id}/followup_suggestion")
def followup_suggestion(customer_id: int, db: Session = Depends(get_db)):
    # 取客戶
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    today = date.today()
    days_since = (today - c.last_visit_date).days

    # 你已經有 churn_rule 的話就用你那個；沒有就先用簡單版
    # 這裡假設你已經在 list 裡有 churn_rule，可把它搬成共用函式
    risk_level, risk_reason = _churn_rule(c.membership_type, days_since)  # 若你這行報錯，往下看我給你的替代方案

    payload = {
        "customer_id": c.id,
        "customer_code": c.customer_code,
        "membership_type": c.membership_type,
        "days_since_last_visit": days_since,
        "total_spent": c.total_spent,
        "visit_count": c.visit_count,
        "risk_level": risk_level,
        "risk_reason": risk_reason,
    }

    return generate_followup_suggestion(payload)

