   # Training Platform

   FastAPI + PostgreSQL backend, React (Vite) frontend.

   ## Run
   1. Start PostgreSQL and make sure a database named `training` exists.
   2. Backend: `cd backend`, `.venv\Scripts\activate`, `python -m uvicorn main:app --reload`
      (database address is the DATABASE_URL setting; the default is in main.py)
   3. Frontend: `cd frontend`, `npm run dev`, then open http://localhost:5173
   4. API docs: http://localhost:8000/docs
   5. The first registered account becomes the admin.

   ## Tests
   - Backend: `cd backend`, `python -m pytest -q`
   - Frontend: `cd frontend`, `npx vitest run`

   ## Design notes
   - Rules (grading, module locking, certificate numbers) are plain functions in main.py.
   - Certificate number is a hash of user and course, so it is deterministic.
   - Admin and user roles are enforced on the server.