# InsightPilot – AI Customer Follow-up Recommendation System

InsightPilot is a full-stack AI-powered web application that helps businesses identify customer churn risk and automatically generate personalized follow-up strategies for sales and CRM teams.

It supports CSV import, customer behavior analysis, risk classification, and AI-generated communication scripts (LINE / SMS / Call).

---

## 🚀 Live Demo

Frontend (Vercel):  
👉 https://insight-pilot-omega.vercel.app/

Backend API (Render):  
👉 https://insightpilot-kqns.onrender.com/docs

> You can try the system using the built-in sample CSV download button.

---

## ✨ Features

- CSV customer data import & preview
- Automatic customer metrics calculation (days since last visit, visit count, total spent)
- Rule-based churn & risk classification (LOW / MEDIUM / HIGH)
- AI-generated follow-up strategies and scripts
  - LINE
  - SMS
  - Phone call
- Modal-based AI suggestion UI
- Pagination & filtering
- JWT authentication (login system)
- RESTful API design
- Frontend & backend separated architecture

---

## 🧱 Tech Stack

### Frontend

- React
- TypeScript
- Vite

### Backend

- FastAPI
- Python
- SQLAlchemy
- JWT Authentication

### Database

- SQLite (development)
- Planned: PostgreSQL (Supabase)

### AI

- LLM API integration
- Prompt engineering
- LangChain-ready architecture

### Deployment

- Frontend: Vercel
- Backend: Render
- Monorepo: GitHub

---

## 🏗 Architecture

frontend/ # React UI
backend/ # FastAPI API server
docs/ # Documentation

---

## 💼 Use Cases

- CRM teams identify inactive or high-risk customers
- Sales teams receive AI-generated reactivation strategies
- Reduce manual script writing and improve conversion rates
- Small businesses without complex CRM systems

---

## 👤 Author

GitHub: rtu753951-alt

---

## 🛠 Backend Setup & Commercial Import

### 1. Database Initialization

Ensure your `.env` has the correct `DATABASE_URL` (Supabase/Postgres).
Run the initialization script to create the `imports` tracking table and ensure `UNIQUE` constraints on `customer_code`:

```bash
cd backend
python scripts/init_db.py
```

### 2. Testing Import API (curl)

You can test the commercial CSV import (Upsert) directly:

```bash
curl -X POST "http://localhost:8000/api/customers/import" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/demo_customers.csv"
```

### 3. Check Import History

View the status of recent imports:

```bash
curl -X GET "http://localhost:8000/api/customers/imports?limit=5"
```
