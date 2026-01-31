import csv
import io
import uuid
import traceback
from datetime import date
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func, or_, and_, not_
from sqlalchemy.dialects.postgresql import insert

from app.core.db import get_db
from app.models.customer import Customer
from app.models.import_record import ImportRecord
from app.schemas.customer import CustomerOut, ImportResult, CustomerList
from app.schemas.import_record import ImportRecordOut
from app.core.llm_service import generate_followup_suggestion

router = APIRouter(prefix="/api/customers", tags=["customers"])

REQUIRED_COLUMNS = {
    "customer_code",
    "last_visit_date",
    "total_spent",
    "visit_count",
    "membership_type",
}

def _to_int(v: str, field: str) -> int:
    try:
        return int(float(v))
    except Exception:
        if not v: return 0
        raise HTTPException(status_code=422, detail=f"Invalid int for {field}: {v}")

def _to_date(v: str, field: str) -> date:
    try:
        if not v: raise ValueError("Empty date")
        return date.fromisoformat(v)
    except Exception:
        raise HTTPException(status_code=422, detail=f"Invalid date for {field} (YYYY-MM-DD): {v}")

@router.post("/import", response_model=ImportResult)
async def import_customers_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    from app.core.config import settings
    # print(f"DEBUG: Starting import_customers_csv... DB_URL_FROM_SETTINGS={settings.DATABASE_URL}", flush=True)
    # print(f"DEBUG: Session bind URL={db.bind.url}", flush=True)

    try:
        # 1. Start Import Record
        import_rec = ImportRecord(
            filename=file.filename,
            status="processing",
            row_count=0
        )
        db.add(import_rec)
        db.commit()
        db.refresh(import_rec)

        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Please upload a .csv file")

        raw = await file.read()
        text_content = raw.decode("utf-8-sig", errors="replace")

        reader = csv.DictReader(io.StringIO(text_content))
        
        if not reader.fieldnames:
             raise HTTPException(status_code=400, detail="CSV has no header")

        rows_to_upsert = []
        row_idx = 0
        for row in reader:
            row_idx += 1
            code = row.get("customer_code") or row.get("customer_id")
            if not code:
                continue 

            r_data = {
                "customer_code": code.strip(),
                "last_visit_date": _to_date((row.get("last_visit_date") or "").strip(), f"Row {row_idx} date"),
                "total_spent": _to_int((row.get("total_spent") or "").strip(), f"Row {row_idx} spent"),
                "visit_count": _to_int((row.get("visit_count") or "").strip(), f"Row {row_idx} visit"),
                "membership_type": (row.get("membership_type") or "BASIC").strip(),
                "created_at": date.today()
            }
            rows_to_upsert.append(r_data)

        if not rows_to_upsert:
             import_rec.status = "done"
             import_rec.row_count = 0
             db.commit()
             return ImportResult(import_id=str(import_rec.id), inserted=0, updated=0, total_rows=0)

        # 2. Logic to count Insert vs Update
        codes = [x["customer_code"] for x in rows_to_upsert]
        existing_codes = db.scalars(
            select(Customer.customer_code).where(Customer.customer_code.in_(codes))
        ).all()
        existing_set = set(existing_codes)

        update_count = 0
        insert_count = 0
        for r in rows_to_upsert:
            if r["customer_code"] in existing_set:
                update_count += 1
            else:
                insert_count += 1

        # 3. Bulk Upsert (Raw SQL)
        # Using raw SQL to avoid SQLAlchemy dialect compilation issues (SQLite vs Postgres confusion)
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO customers (customer_code, last_visit_date, total_spent, visit_count, membership_type, created_at)
            VALUES (:customer_code, :last_visit_date, :total_spent, :visit_count, :membership_type, :created_at)
            ON CONFLICT (customer_code) DO UPDATE 
            SET last_visit_date = EXCLUDED.last_visit_date,
                total_spent = EXCLUDED.total_spent,
                visit_count = EXCLUDED.visit_count,
                membership_type = EXCLUDED.membership_type
        """)
        
        # Execute each (or executemany if driver supports it efficiently)
        # SQLAlchemy execute(text, list_of_dicts) does executemany
        db.execute(stmt, rows_to_upsert)
        print("DEBUG: Raw SQL Upsert executed.", flush=True)
        
        # 4. Finish Import Record
        import_rec.status = "done"
        import_rec.row_count = len(rows_to_upsert)
        db.commit()

        return ImportResult(
            import_id=str(import_rec.id),
            inserted=insert_count,
            updated=update_count,
            total_rows=len(rows_to_upsert)
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        err_msg = traceback.format_exc()
        print(f"Import Error: {err_msg}", flush=True)
        # Try to save failed status (best effort)
        try:
             # Need a new transaction?
             # Since we are inside a request, and rolled back, `import_rec` is gone/detached.
             # We won't try to update `import_rec` to avoid complexity here.
             pass 
        except:
             pass
        raise HTTPException(status_code=500, detail=f"Import failed: {err_msg}")

@router.get("/imports", response_model=List[ImportRecordOut])
def get_imports(limit: int = 20, db: Session = Depends(get_db)):
    return db.scalars(
        select(ImportRecord).order_by(desc(ImportRecord.created_at)).limit(limit)
    ).all()


def _churn_rule(membership_type: str, days_since: int) -> tuple[str, str]:
    m = (membership_type or "").upper()
    if m == "VIP":
        if days_since >= 150:
            return "high", f"VIP 已停滯 {days_since} 天 (>=150)"
        if days_since >= 90:
            return "medium", f"VIP 已停滯 {days_since} 天 (>=90)"
        return "low", f"VIP 近期活躍 ({days_since} 天前)"
    if days_since >= 120:
        return "high", f"已停滯 {days_since} 天 (>=120)"
    if days_since >= 60:
        return "medium", f"已停滯 {days_since} 天 (>=60)"
    return "low", f"近期活躍 ({days_since} 天前)"


@router.get("", response_model=CustomerList)
def list_customers(
    limit: int = 100,
    offset: int = 0,
    membership_type: str | None = None,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))
    
    query = select(Customer)
    
    # 1. Apply Membership Filter
    if membership_type and membership_type != "all":
        # Fuzzy match or exact? Assuming exact from UI but let's be safe
        query = query.where(Customer.membership_type == membership_type)

    # 2. Apply Risk Filter (Logic -> Date)
    if risk_level and risk_level != "all":
        from datetime import timedelta
        today = date.today()
        # Risk thresholds
        # VIP: High(>=150), Med(90-149), Low(<90)
        # Normal: High(>=120), Med(60-119), Low(<60)
        
        # We need OR logic: (VIP AND High_Cond) OR (NOT VIP AND High_Cond)
        from sqlalchemy import or_, and_, not_

        is_vip = (func.upper(Customer.membership_type) == "VIP")
        
        if risk_level == "high":
            # VIP >= 150  OR  Not VIP >= 120
            # date <= today - 150
            d_vip = today - timedelta(days=150)
            d_norm = today - timedelta(days=120)
            
            query = query.where(
                or_(
                    and_(is_vip, Customer.last_visit_date <= d_vip),
                    and_(not_(is_vip), Customer.last_visit_date <= d_norm)
                )
            )
        elif risk_level == "medium":
            # VIP: 90 <= days < 150  -->  today-149 <= date <= today-90
            d_vip_start = today - timedelta(days=90)
            d_vip_end = today - timedelta(days=149) # actually date >= today-149 implies days <= 149
            
            # Normal: 60 <= days < 120
            d_norm_start = today - timedelta(days=60)
            d_norm_end = today - timedelta(days=119)
            
            query = query.where(
                or_(
                    and_(is_vip, Customer.last_visit_date <= d_vip_start, Customer.last_visit_date >= d_vip_end),
                    and_(not_(is_vip), Customer.last_visit_date <= d_norm_start, Customer.last_visit_date >= d_norm_end)
                )
            )
        elif risk_level == "low":
             # VIP < 90 --> date > today-90
             d_vip = today - timedelta(days=90)
             d_norm = today - timedelta(days=60)
             
             query = query.where(
                or_(
                    and_(is_vip, Customer.last_visit_date > d_vip),
                    and_(not_(is_vip), Customer.last_visit_date > d_norm)
                )
             )


    # 3. Get Total (with filters)
    # We must compile the query for count separately or use distinct technique
    # count_query = select(func.count()).select_from(query.subquery()) # generic way
    # Or simpler:
    count_query = select(func.count(Customer.id)).where(query.whereclause) if query.whereclause is not None else select(func.count(Customer.id))
    
    total = db.scalar(count_query) or 0

    # 4. Get Rows (Apply sorting and pagination)
    rows = db.execute(
        query.order_by(Customer.customer_code).limit(limit).offset(offset)
    ).scalars().all()

    today = date.today()
    items: list[CustomerOut] = []

    for c in rows:
        days_since = (today - c.last_visit_date).days
        risk_level_calc, risk_reason = _churn_rule(c.membership_type, days_since)
        items.append(
            CustomerOut(
                id=c.id,
                customer_code=c.customer_code,
                last_visit_date=c.last_visit_date,
                total_spent=c.total_spent,
                visit_count=c.visit_count,
                membership_type=c.membership_type,
                days_since_last_visit=days_since,
                risk_level=risk_level_calc,
                risk_reason=risk_reason,
            )
        )
    return CustomerList(items=items, total=total)

@router.post("/{customer_id}/followup_suggestion")
def followup_suggestion(customer_id: int, db: Session = Depends(get_db)):
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
    from pathlib import Path
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "data" / "demo_customers.csv"
    if not csv_path.exists():
        csv_path = base_dir / "backend" / "data" / "demo_customers.csv"
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Demo CSV not found")
    db.query(Customer).delete()
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
             code = row.get("customer_id") or row.get("customer_code")
             if not code: continue
             c = Customer(
                 customer_code=code,
                 last_visit_date=date.fromisoformat(row["last_visit_date"]),
                 total_spent=int(row["total_spent"]),
                 visit_count=int(row["visit_count"]),
                 membership_type=row["membership_type"],
             )
             db.add(c)
    db.commit()
    return {"ok": True, "rows": 999}
