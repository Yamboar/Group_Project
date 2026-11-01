# XAI Operations Research System

**The Development of an Explainable Artificial Intelligence Operations Research System for Solving Transportation and Assignment Problems**

A final-year project that solves **Transportation** and **Assignment** optimization problems with complete algorithmic transparency using a **React + FastAPI** architecture. Every intermediate calculation, decision, and optimality check is recorded and explained — no black-box optimization libraries.

---

## Features

### Transportation Problems
- **North-West Corner Method** — initial basic feasible solution
- **Least Cost Method** — cost-based initial solution
- **Vogel's Approximation Method** — penalty-based initial solution
- **Stepping Stone Method** — optimization to guaranteed optimality
- Automatic balancing (dummy source/destination) with clear explanations
- Full supply/demand verification and non-negativity checks

### Assignment Problems
- **Hungarian Method** — implemented manually, step-by-step
- Minimization and maximization (with correct max→min transformation)
- Rectangular matrix balancing with dummy rows/columns
- Complete tracking of row reduction, column reduction, zero covering, and matrix adjustment

### Explainability (XAI)
- Structured **solution events** recorded by the algorithm engine
- Natural-language explanations generated from **verified** events only
- Three explanation levels: concise, detailed, technical
- Every claim traceable to an actual calculation (no LLM as source of truth)

### Architecture
```
Presentation Layer (React + Vite)
    ↓  (HTTP/JSON via Vite proxy → FastAPI)
API Layer (FastAPI)
    ↓
Problem Management Layer
    ↓
OR Engine (Transportation / Assignment)  ← pure Python, no OR solver libs
    ↓
XAI Engine (events → explanations)
    ↓
Data Access Layer (SQLAlchemy) → MySQL
```

The OR engine is **completely independent** of the UI, the API, and the database, so it can be reused by any frontend or CLI without rewriting the algorithms.

---

## Getting Started

### Prerequisites
- Python 3.9+ (developed on 3.10)
- Node.js 20.19+ (for the React frontend)
- MySQL server (local or remote)

### 1. Backend setup

**Create a virtual environment (Windows):**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**Install Python dependencies:**
```bash
pip install -r requirements.txt
```

**Configure MySQL:**
1. Create a MySQL database:
   ```sql
   CREATE DATABASE xai_or_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. Create a dedicated user (recommended):
   ```sql
   CREATE USER 'xai_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON xai_or_system.* TO 'xai_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

3. Create your environment file:
   ```bash
   copy .env.example .env        # Windows
   cp .env.example .env           # macOS / Linux
   ```

4. Edit `.env` with your credentials (never commit real credentials):
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=xai_or_system
   DB_USER=xai_user
   DB_PASSWORD=your_password
   ```

**Initialize the database:**
```bash
python -m scripts.init_db
```

**Start the FastAPI backend:**
```bash
uvicorn backend.main:app --reload --port 8000
```

The API is served at `http://localhost:8000`. Interactive Swagger docs are at `http://localhost:8000/docs`.

### 2. Frontend setup

**Install frontend dependencies:**
```bash
cd frontend
npm install
```

**Start the React development server:**
```bash
npm run dev
```

Open `http://localhost:5173` in your browser. The Vite dev server proxies `/api` requests to the FastAPI backend on port `8000`, so no CORS configuration is needed in development.

**Production build:**
```bash
npm run build
```

### 3. Run the tests

```bash
pytest
```

The test suite runs independently of the user interface and verifies every algorithm against known benchmarks, constraint satisfaction, and reproducibility.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/transportation/solve` | Solve a transportation problem (JSON body with cost matrix, supply, demand, method) |
| `POST` | `/api/transportation/explain` | Solve + return full XAI explanations |
| `POST` | `/api/assignment/solve` | Solve an assignment problem (JSON body with cost matrix) |
| `POST` | `/api/assignment/explain` | Solve + return full XAI explanations |
| `GET` | `/api/history/transportation` | List saved transportation problems |
| `GET` | `/api/history/assignment` | List saved assignment problems |
| `DELETE` | `/api/history/transportation/{id}` | Delete a saved transportation problem |
| `DELETE` | `/api/history/assignment/{id}` | Delete a saved assignment problem |
| `GET` | `/api/health` | Health check |

**Example transportation request:**
```json
{
  "cost_matrix": [[3, 1, 7], [4, 2, 4], [3, 3, 8]],
  "supply": [3, 3, 4],
  "demand": [4, 3, 3],
  "method": "Vogel's Approximation Method",
  "optimize": true,
  "source_names": ["Source 1", "Source 2", "Source 3"],
  "dest_names": ["Dest 1", "Dest 2", "Dest 3"]
}
```

**Example assignment request:**
```json
{
  "cost_matrix": [[4, 1, 3], [2, 0, 5], [3, 2, 2]],
  "problem_type": "Minimization",
  "row_names": ["Worker 1", "Worker 2", "Worker 3"],
  "col_names": ["Job 1", "Job 2", "Job 3"]
}
```

---

## Project Structure

```
xai_or_system/
├── backend/                      # FastAPI layer
│   ├── main.py                   # FastAPI app, CORS, router registration
│   ├── schemas.py                # Pydantic request/response models
│   ├── serializers.py            # Dataclass → JSON serialization
│   └── routers/
│       ├── transportation.py     # /api/transportation endpoints
│       ├── assignment.py         # /api/assignment endpoints
│       └── history.py            # /api/history endpoints
├── frontend/                     # React + Vite UI
│   ├── src/
│   │   ├── api/client.js         # Axios API client
│   │   ├── components/           # Layout, DataTable, EditableMatrix
│   │   └── pages/                # Home, Transportation, Assignment, Saved, Help
│   ├── index.html
│   ├── package.json
│   └── vite.config.js            # Dev proxy → http://localhost:8000
├── engine/                       # OR Engine (pure Python, no UI/API/DB deps)
│   ├── transportation/
│   │   ├── models.py             # Dataclasses for problem/solution structures
│   │   ├── validation.py         # Input validation
│   │   ├── balancing.py          # Dummy source/destination balancing
│   │   ├── northwest_corner.py   # NWC algorithm
│   │   ├── least_cost.py         # Least Cost algorithm
│   │   ├── vogel.py              # Vogel's Approximation algorithm
│   │   ├── stepping_stone.py     # Stepping Stone optimization
│   │   └── solver.py             # Orchestrates the full pipeline
│   └── assignment/
│       ├── models.py             # Assignment dataclasses
│       ├── validation.py         # Input validation
│       ├── hungarian.py          # Hungarian Method implementation
│       └── solver.py             # Orchestrates the pipeline
├── xai/                          # XAI Engine
│   ├── events.py                 # Structured solution event dataclasses
│   ├── templates.py              # Explanation templates
│   └── explanation_engine.py     # Generates explanations from events
├── database/
│   ├── connection.py             # SQLAlchemy engine/session setup
│   ├── models.py                 # ORM table definitions
│   └── repository.py             # Data access repository functions
├── utils/
│   ├── validation.py             # Shared matrix/vector validation
│   └── formatting.py             # Table/currency formatting helpers
├── presentation/                 # (legacy Streamlit UI, kept for reference)
│   └── pages/
├── scripts/
│   ├── init_db.py                # Database initialization
│   ├── demo.py                   # CLI verification demo
│   ├── smoke_test_api.py         # Backend API smoke tests
│   └── test_proxy.py             # End-to-end proxy integration test
├── tests/                        # Pytest test suite (independent of UI)
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
└── README.md
```

---

## Algorithms — Mathematical Notes

### Transportation: Total Cost
```
Z = Σᵢ Σⱼ cᵢⱼ · xᵢⱼ
```
where `cᵢⱼ` is the cost from source `i` to destination `j` and `xᵢⱼ` is the quantity shipped. The system clearly distinguishes the **initial feasible solution cost** from the **optimized cost**, quantifying the reduction.

### Stepping Stone Method
- For each non-basic cell, a **closed loop** through basic cells is constructed.
- Alternating `+`/`−` signs begin at the candidate cell.
- **Improvement index** = `Σ (± cᵢⱼ)` around the loop. Negative → cost reduction possible.
- The most negative index selects the entering cell; adjustment quantity = minimum at `−` positions.
- **Degeneracy** (fewer than `m + n − 1` basic cells) is handled by retaining epsilon allocations to preserve a valid basis.
- Loop-finding is deterministic, prevents duplicate cells, and terminates on no-negative-index optimality.

### Hungarian Method
1. Balance rectangular matrices (dummy rows/columns with zero cost).
2. Maximization → `max − value` transformation.
3. **Row reduction**, then **column reduction**.
4. **Cover zeros** with minimum lines (via maximum bipartite matching on zeros).
5. If lines < n, adjust matrix by the smallest uncovered value.
6. Repeat until a complete independent-zero assignment exists, then extract it.
7. Final cost is computed from the **original** cost matrix (never the reduced one).

---

## Testing

Run the full suite:
```bash
pytest
```

The suite covers:
- Balanced and unbalanced transportation problems
- All three initial-solution methods + Stepping Stone optimization
- Degeneracy, ties, multiple iterations, and already-optimal cases
- Hungarian minimization, maximization, rectangular matrices
- Constraint satisfaction and one-to-one assignment verification
- Determinism and reproducibility checks
- XAI event/explanation generation
- Invalid-input handling

---

## Verification Layer

Every solved problem is verified before being presented:
- Row allocations sum to supply; column allocations sum to demand (incl. dummies).
- All allocations are non-negative.
- Stepping Stone final solution has no negative improvement indices.
- Assignment cost is recomputed from the original matrix.
- If verification fails, the system reports it explicitly and does **not** claim optimality.

---

## License
For academic / final-year project use.
