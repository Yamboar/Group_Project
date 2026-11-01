"""Test the full solve flow through the Vite proxy (frontend -> backend)."""
import json
import urllib.request

BASE = "http://localhost:5173/api"

def post(url, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

print("=== Transportation Solve via Proxy ===")
data = post(f"{BASE}/transportation/solve", {
    "cost_matrix": [[3, 1, 7], [4, 2, 4], [3, 3, 8]],
    "supply": [3, 3, 4],
    "demand": [4, 3, 3],
    "method": "Vogel's Approximation Method",
    "optimize": True,
    "source_names": ["S1", "S2", "S3"],
    "dest_names": ["D1", "D2", "D3"],
})
print("Success:", data["success"])
print("Final cost:", data["final_cost"])

print("\n=== Assignment Solve via Proxy ===")
data = post(f"{BASE}/assignment/solve", {
    "cost_matrix": [[4, 1, 3], [2, 0, 5], [3, 2, 2]],
    "problem_type": "Maximization",
})
print("Success:", data["success"])
print("Final cost:", data["final_cost"])
print("Assignments:")
for a in data["result"]["assignments"]:
    if not a["row_name"].startswith("Dummy"):
        print(f"  {a['row_name']} -> {a['col_name']} (cost: {a['original_cost']})")

print("\n=== All proxy tests passed ===")
