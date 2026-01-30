import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found")

engine = create_engine(DATABASE_URL)

def check_data():
    with engine.connect() as conn:
        # 1. 檢查總筆數
        count = conn.execute(text("SELECT count(*) FROM customers")).scalar()
        print(f"📊 目前資料庫共有 {count} 筆客戶資料。")

        # 2. 列出最新 5 筆
        print("\n📝 最新 5 筆資料：")
        rows = conn.execute(text("SELECT customer_code, last_visit_date, total_spent FROM customers ORDER BY created_at DESC LIMIT 5")).fetchall()
        
        for r in rows:
            print(f" - ID: {r.customer_code} | Date: {r.last_visit_date} | Spent: {r.total_spent}")

if __name__ == "__main__":
    try:
        check_data()
    except Exception as e:
        print("❌ 連線失敗或查詢錯誤：")
        print(e)
