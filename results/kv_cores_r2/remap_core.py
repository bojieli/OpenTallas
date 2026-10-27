#!/usr/bin/env python3
"""KV-CORES-R2: make a runnable core.json from a surviving one (epyc1 sources deleted 10-27).
Each source file -> (1) same repo-relative path in THIS worktree (if it exists), else (2) the kit-local rtl/<basename>
copy of the given prior kit (byte copy of what that kit built). Writes the new core.json + remap.json (sha per file)."""
import hashlib, json, os, re, sys
from pathlib import Path
src, kitrtl, wt, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
c = json.load(open(src)); rec = []
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]
new = []
for f in c["files"]:
    m = re.search(r"/(?:wt|OpenTallas)/(?:[^/]+/)?((?:rtl|physical|tools)/.*)$", f) if "/wt/" in f else None
    cand = []
    if m: cand.append(("repo", wt / m.group(1)))
    if kitrtl != "-": cand.append(("kit", Path(kitrtl) / Path(f).name))
    if os.path.exists(f) and not cand: cand.append(("orig", Path(f)))
    hit = next(((k, p) for k, p in cand if p.is_file()), None)
    if hit is None and os.path.exists(f): hit = ("orig", Path(f))
    if hit is None: raise SystemExit(f"no source for {f}")
    kind, p = hit
    kp = Path(kitrtl) / Path(f).name if kitrtl != "-" else None
    rec.append(dict(orig=f, used=str(p), how=kind, sha=sha(p), kit_sha=sha(kp) if kp and kp.is_file() else None))
    new.append(str(p))
c["files"] = new
c["kv_cores_r2_remap"] = "remap_core.py: epyc1 sources gone; repo path else prior-kit rtl copy"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(c, indent=1) + "\n")
(out.parent / "remap.json").write_text(json.dumps(rec, indent=1) + "\n")
for r in rec: print(r["how"], Path(r["used"]).name, r["sha"], "kit=" + str(r["kit_sha"]), "SAME" if r["sha"] == r["kit_sha"] else "DIFF")
