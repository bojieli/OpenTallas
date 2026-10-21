# runs ON ot-epyc6: stdin = JSON list of paths; prints JSON {path: {dir, exists, kb, files}} (du/find with the copy excludes)
import json, os, subprocess, sys
EXC = ["src", "src[0-9]*", "bench_src*", "bsrc_*", "obj_dir", "obj", "obj[0-9]*", ".git", "__pycache__", "*.o", "*.gch", "*.vvp"]
paths = json.load(sys.stdin)
res = {}
for p in paths:
    q = p
    while q.count("/") >= 5 and not os.path.exists(q):
        q = os.path.dirname(q)
    if not os.path.exists(q):
        res[p] = dict(dir=None, exists=False); continue
    if os.path.isfile(q):
        q = os.path.dirname(q)
    # never a whole user root or a whole umbrella project dir (depth >= 5: /srv/<root>/<user>/<proj>/<x>)
    depth = q.rstrip("/").count("/")
    res[p] = dict(dir=q, exists=True, depth=depth)
dirs = sorted({r["dir"] for r in res.values() if r.get("dir") and r["depth"] < 5})   # du only for umbrella-level dirs
sizes = {}
for d in dirs:
    try:
        o = subprocess.run(["du", "-sk"] + ["--exclude=" + e for e in EXC] + [d], capture_output=True, text=True, timeout=600).stdout.split()
        sizes[d] = int(o[0]) if o else -1
    except Exception:
        sizes[d] = -1
for r in res.values():
    if r.get("dir"):
        r["kb"] = sizes.get(r["dir"], 0)
json.dump(res, sys.stdout)
