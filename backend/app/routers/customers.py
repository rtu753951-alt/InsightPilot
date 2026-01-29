import csv
import io
import os
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, delete

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
            db.rollback() 
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
        
        # ✅ 新增：算風險
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

    risk_level, risk_reason = _churn_rule(c.membership_type, days_since)

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

@router.post("/load_demo_data")
def load_demo_data(db: Session = Depends(get_db)):
    """
    1. 清空 customers 表
    2. 讀取 backend/data/demo_customers.csv
    3. 批次匯入
    """
    
    # 1. 確保 CSV 存在 (使用絕對路徑)
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "data" / "demo_customers.csv"
    
    if not csv_path.exists():
        # Fallback for some structures
        csv_path = base_dir / "backend" / "data" / "demo_customers.csv"

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Demo CSV not found at {csv_path}")

    # 2. 清空資料表
    db.query(Customer).delete()
    
    # 3. 讀取並匯入
    inserted = 0
    # encoding="utf-8-sig" 處理 Excel 存檔可能帶有的 BOM
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
             # handle empty rows or bad data if necessary
            if not row.get("customer_id"):
                continue
                
            c = Customer(
                customer_code=row["customer_id"],
                last_visit_date=date.fromisoformat(row["last_visit_date"]),
                total_spent=int(row["total_spent"]),
                visit_count=int(row["visit_count"]),
                membership_type=row["membership_type"],
            )
            db.add(c)
            inserted += 1
            
    db.commit()
    return {"ok": True, "rows": inserted}
