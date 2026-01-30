import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# 1. 取得資料庫連線
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found in .env")

# Supabase (PostgreSQL) 需要安裝 psycopg2
engine = create_engine(DATABASE_URL)

def import_csv_to_customers(csv_path: str):
    print(f"Reading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)

    # 確保欄位名稱對應 Customer model
    # CSV: customer_code, membership_type, total_spent, visit_count, last_visit_date
    # DB:  customer_code, membership_type, total_spent, visit_count, last_visit_date, created_at...

    with engine.begin() as conn:
        # 先清除舊資料（可選，看需求）
        # conn.execute(text("DELETE FROM customers")) 

        rows_inserted = 0
        for _, row in df.iterrows():
            # 使用 INSERT ON CONFLICT DO UPDATE (Upsert) 或是單純 INSERT
            # 這裡示範簡單的 Insert，若 customer_code 重複則忽略
            
            stmt = text("""
                INSERT INTO customers (customer_code, membership_type, total_spent, visit_count, last_visit_date, created_at)
                VALUES (:code, :type, :spent, :count, :date, now())
                ON CONFLICT (customer_code) DO UPDATE 
                SET total_spent = EXCLUDED.total_spent,
                    visit_count = EXCLUDED.visit_count,
                    last_visit_date = EXCLUDED.last_visit_date
            """)
            
            conn.execute(stmt, {
                "code": row["customer_id"],
                "type": row["membership_type"],
                "spent": row["total_spent"],
                "count": row["visit_count"],
                "date": row["last_visit_date"]
            })
            rows_inserted += 1

    print(f"✅ Successfully imported {rows_inserted} customers to Supabase!")

if __name__ == "__main__":
    # 使用我們剛剛產生的 demo csv
    csv_path = "data/demo_customers.csv"
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
    else:
        import_csv_to_customers(csv_path)
