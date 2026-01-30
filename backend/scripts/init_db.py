import os
import sys

# Add parent dir to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.import_record import ImportRecord
from app.models.customer import Customer # Ensures customer table is known

def init_db():
    print(f"Connecting to DB: {settings.DATABASE_URL.split('@')[-1]}") # Mask password
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.begin() as conn:
        # 1. Create tables (imports)
        print("Creating table: imports (if not exists)...")
        ImportRecord.metadata.create_all(bind=engine)

        # 2. Add UNIQUE constraint to customers.customer_code
        print("Ensuring UNIQUE constraint on customers(customer_code)...")
        try:
            conn.execute(text("ALTER TABLE customers ADD CONSTRAINT customers_customer_code_key UNIQUE (customer_code);"))
            print("✅ Added UNIQUE constraint.")
        except Exception as e:
            if "already exists" in str(e):
                print("ℹ️ UNIQUE constraint already exists.")
            else:
                print(f"⚠️ Warning: {e}")

if __name__ == "__main__":
    init_db()
