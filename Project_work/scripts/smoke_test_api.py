"""Quick smoke test for the FastAPI backend."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)

print("=== Health ===")
r = c.get("/api/health")
print("Status:", r.status_code)
print(r.json())

print("\n=== Transportation Solve ===")
payload = {
    "cost_matrix": [[3, 1, 7], [4, 2, 4], [3, 3, 8]],
    "supply": [3, 3, 4],
    "demand": [4, 3, 3],
    "method": "Vogel's Approximation Method",
    "optimize": True,
}
r = c.post("/api/transportation/solve", json=payload)
print("Status:", r.status_code)
data = r.json()
print("Success:", data.get("success"))
print("Final cost:", data.get("final_cost"))
print("Errors:", data.get("errors"))
print("Verification passed:", data.get("verification", {}).get("passed"))
print("Has initial_solution:", bool(data.get("initial_solution")))
print("Has optimized_solution:", bool(data.get("optimized_solution")))
print("Num events:", len(data.get("events", [])))

print("\n=== Transportation Explain ===")
r = c.post("/api/transportation/explain", json=payload)
print("Status:", r.status_code)
data = r.json()
print("Algorithm:", data.get("algorithm"))
print("Summary:", data.get("summary")[:100] + "...")
print("Key decisions:", len(data.get("key_decisions", [])))
print("Explanations:", len(data.get("explanations", [])))

print("\n=== Assignment Solve ===")
payload2 = {
    "cost_matrix": [[4, 1, 3], [2, 0, 5], [3, 2, 2]],
    "problem_type": "Minimization",
}
r = c.post("/api/assignment/solve", json=payload2)
print("Status:", r.status_code)
data = r.json()
print("Success:", data.get("success"))
print("Final cost:", data.get("final_cost"))
print("Verification passed:", data.get("verification", {}).get("passed"))
print("Num events:", len(data.get("events", [])))
result = data.get("result", {})
print("Has result:", bool(result))
if result:
    print("Assignments:", len(result.get("assignments", [])))

print("\n=== Assignment Explain ===")
r = c.post("/api/assignment/explain", json=payload2)
print("Status:", r.status_code)
data = r.json()
print("Algorithm:", data.get("algorithm"))
print("Summary:", data.get("summary"))
print("Key decisions:", len(data.get("key_decisions", [])))

print("\n=== Validation Error Test (mismatched dims) ===")
bad_payload = {
    "cost_matrix": [[3, 1, 7], [4, 2]],
    "supply": [3, 3],
    "demand": [4, 3, 3],
    "method": "North-West Corner Method",
}
r = c.post("/api/transportation/solve", json=bad_payload)
print("Status:", r.status_code)
print("Detail:", r.json())

print("\n=== Validation Error Test (bad method) ===")
bad_payload2 = {
    "cost_matrix": [[3, 1], [4, 2]],
    "supply": [3, 3],
    "demand": [4, 3],
    "method": "Not A Real Method",
}
r = c.post("/api/transportation/solve", json=bad_payload2)
print("Status:", r.status_code)
print("Detail:", r.json())

print("\n=== History (may need DB) ===")
r = c.get("/api/history/transportation")
print("Status:", r.status_code)
if r.status_code == 200:
    print("Items:", len(r.json()))
else:
    print("Detail:", r.json())

print("\nAll smoke tests complete.")
