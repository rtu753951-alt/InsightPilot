from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import Base, engine
from app.routers.auth import router as auth_router

from app.models.customer import Customer  # noqa: F401
from app.routers.customers import router as customers_router



app = FastAPI(title="InsightPilot API", version="0.2.0")


# 你原本的 CORS 清單保留（很OK）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 開發期：啟動時自動建表（users）
Base.metadata.create_all(bind=engine)

@app.get("/api/health")
def health():
    return {"status": "ok"}

# ✅ 掛上登入相關 API
app.include_router(auth_router)
app.include_router(customers_router)
