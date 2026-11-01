Option B: React + FastAPI App (full stack)
This needs three things running: the database (optional), the backend, and the frontend.

1. Start the FastAPI backend

cmd

cd c:\Users\ernes\Desktop\xai-kiro3-OC
uvicorn backend.main:app --reload --port 8000
2. Start the React frontend (in a separate terminal)

cmd

cd c:\Users\ernes\Desktop\xai-kiro3-OC\frontend
npm run dev
Frontend opens at http://localhost:5173, backend API at http://localhost:8000.
