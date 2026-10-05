"""Push chronicle repo to GitHub via Git Data API - fixed .github handling."""
import os, json, base64, urllib.request, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

REPO = "18971181532/chronicle"
LOCAL = r"C:\Users\了\Documents\git\chronicle"
TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "Content-Type": "application/json",
    "User-Agent": "chronicle-push",
}

def api_call(method, path, data=None):
    url = f"{API}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Collect files - fixed: check .git as path component, not substring
files = []
for root, dirs, filenames in os.walk(LOCAL):
    parts = root.split(os.sep)
    if ".git" in parts or "__pycache__" in parts:
        continue
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
    for fn in filenames:
        if fn.endswith(".pyc"):
            continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, LOCAL).replace("\\", "/")
        files.append((rel, full))

print(f"Files to push: {len(files)}")
for rel, _ in files:
    print(f"  {rel}")

# Create blobs concurrently
def create_blob(item):
    rel, full = item
    with open(full, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")
    result = api_call("POST", f"/repos/{REPO}/git/blobs", {
        "content": content, "encoding": "base64",
    })
    return rel, result["sha"]

blobs = {}
print("\nCreating blobs...")
with ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(create_blob, f): f[0] for f in files}
    for fut in as_completed(futures):
        rel, sha = fut.result()
        blobs[rel] = sha

# Create tree
tree_entries = [{"path": rel, "mode": "100644", "type": "blob", "sha": sha}
                for rel, sha in blobs.items()]
print("Creating tree...")
tree = api_call("POST", f"/repos/{REPO}/git/trees", {"tree": tree_entries})
tree_sha = tree["sha"]

# Create commit
print("Creating commit...")
commit = api_call("POST", f"/repos/{REPO}/git/commits", {
    "message": "feat: Chronicle - git history analysis and visualization tool",
    "tree": tree_sha,
    "author": {"name": "遥か", "email": "280000356+18971181532@users.noreply.github.com"},
})
commit_sha = commit["sha"]

# Update ref
print("Updating main ref...")
ref = api_call("PATCH", f"/repos/{REPO}/git/refs/heads/main", {
    "sha": commit_sha, "force": True,
})
print(f"\nDONE! commit={commit_sha}")
print(f"https://github.com/18971181532/chronicle")
