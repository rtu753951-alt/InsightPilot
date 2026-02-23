from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    connect_args["connect_timeout"] = 10  # 增加連線超時時間（秒），應對跨區域延遲

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args, 
    pool_pre_ping=True,  # 在每次使用連線前先「戳」一下，確保連線還活著
    pool_recycle=300,    # 每 5 分鐘強制重置連線，防止被 Render 或 Supabase 單方面切斷
    future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
