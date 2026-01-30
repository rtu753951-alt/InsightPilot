import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings

def cleanup_tables():
    print(f"Connecting to DB: {settings.DATABASE_URL.split('@')[-1]}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.begin() as conn:
        print("Dropping legacy tables (if exist)...")
        # Drop imports first (or with CASCADE)
        conn.execute(text("DROP TABLE IF EXISTS raw_records CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS imports CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS data_sources CASCADE"))
        print("✅ Legacy tables dropped.")

if __name__ == "__main__":
    cleanup_tables()
