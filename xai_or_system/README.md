# XAI Operations Research System

**The Development of an Explainable Artificial Intelligence Operations Research System for Solving Transportation and Assignment Problems**

A final-year project that solves **Transportation** and **Assignment** optimization problems with complete algorithmic transparency. Every intermediate calculation, decision, and optimality check is recorded and explained — no black-box optimization libraries.

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
Presentation Layer (Streamlit)
    ↓
Problem Management Layer
    ↓
OR Engine (Transportation / Assignment)  ← pure Python, no OR solver libs
    ↓
XAI Engine (events → explanations)
    ↓
Data Access Layer (SQLAlchemy) → MySQL
```

The OR engine is **completely independent** of Streamlit and the database, so a future `React → FastAPI → Engine → XAI → SQLAlchemy → MySQL` architecture is possible without rewriting the algorithms.

---

## Getting Started

### Prerequisites
- Python 3.9+ (developed on 3.10)
- MySQL server (local or remote)
- Git (optional, for version control)

### 1. Create a virtual environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MySQL

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

### 4. Initialize the database

```bash
python -m scripts.init_db
```

This creates all required tables using SQLAlchemy models.

### 5. Run the Streamlit application

```bash
streamlit run app.py
```

Open the URL shown in the terminal (usually `http://localhost:8501`).

### 6. Run the tests

```bash
pytest
```

The test suite runs independently of the user interface and verifies every algorithm against known benchmarks, constraint satisfaction, and reproducibility.

---

## Project Structure

```
xai_or_system/
├── app.py                        # Streamlit entry point
├── engine/                       # OR Engine (pure Python, no Streamlit/DB deps)
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
├── presentation/
│   ├── pages/                    # Streamlit pages (Home, Transportation, Assignment, Saved, Help)
│   └── components/               # Reusable UI components
├── scripts/
│   ├── init_db.py                # Database initialization
│   └── demo.py                   # CLI verification demo
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

## Roadmap / Future Architecture

The OR engine is UI- and DB-independent. A future API layer could be added as:

```
React → FastAPI → Python OR Engine → XAI Engine → SQLAlchemy → MySQL
```

without modifying any algorithm module.

---

## License
For academic / final-year project use.
