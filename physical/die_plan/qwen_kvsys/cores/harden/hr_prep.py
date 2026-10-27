#!/usr/bin/env python3
"""KVHR2: map an hr core.json (kv_core_rtl --hr-elab, 10-24 snapshot paths) onto repo sources; keep reached files only."""
import json, re, sys, hashlib, subprocess
from pathlib import Path
cj_path, repo, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
cj = json.load(open(cj_path))
mod = cj["module"]
PFX = ["/home/ubuntu/scratch/kv-g3/src/", "/home/ubuntu/wt/kv-g3/", "/srv/opentallas-scratch2/claude/wt/cores-kits-kvhr-1026/",
       "/home/ubuntu/scratch/kv-g3/wi/patched/"]


def relof(f):
    for p in PFX[:3]:
        if f.startswith(p):
            return f[len(p):]
    return None


def rd(f):
    if Path(f).exists():
        return Path(f).read_bytes()
    r = relof(f)
    return (repo / r).read_bytes()  # predecessor remapped byte-identical files into its (removed) wt of this repo
files = cj["files"]
wrapper = Path(files[0])
defs = {}
txt = {}
for f in files[1:]:
    t = rd(f).decode(errors="replace")
    t2 = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))
    txt[f] = t2
    for m in re.findall(r"^\s*module\s+(\w+)", t2, flags=re.M):
        defs.setdefault(m, f)
reached, todo, need = set(), [mod], []
wt = re.sub(r"//.*", "", wrapper.read_text())
body = {mod: wt}
while todo:
    m = todo.pop()
    t = body.get(m) if m == mod else txt[defs[m]]
    for n in set(re.findall(r"\b(\w+)\s*(?:#\s*\(|\w+\s*\()", t)):
        if n in defs and n not in reached and n != m:
            reached.add(n); todo.append(n)
fs = sorted({defs[m] for m in reached})
# packages / includes referenced
for f in list(fs):
    for pk in re.findall(r"\b(\w+)::", txt[f]):
        for g in files[1:]:
            if re.search(rf"^\s*package\s+{pk}\b", txt[g], flags=re.M) and g not in fs:
                fs.insert(0, g)
res, bad = [], []
for f in fs:
    rel = relof(f)
    if rel is None or not (repo / rel).exists():
        bad.append(f); continue
    same = rd(f) == (repo / rel).read_bytes()
    res.append(dict(snap=f, repo=rel, same_as_snapshot=same))
out.mkdir(parents=True, exist_ok=True)
(out / f"{mod}.sv").write_bytes(wrapper.read_bytes())
cj2 = dict(cj)
cj2["files"] = [str(out / f"{mod}.sv")] + [str(repo / r["repo"]) for r in res]
cj2["sources_repo_relative"] = [r["repo"] for r in res]
cj2["sources_vs_snapshot"] = {r["repo"]: ("same" if r["same_as_snapshot"] else "DIFFERS (main used)") for r in res}
cj2["reached_modules"] = sorted(reached)
cj2["unmapped"] = bad
(out / f"{mod}_core.json").write_text(json.dumps(cj2, indent=1) + "\n")
print(mod, "reached", len(reached), "files", len(res), "differ", sum(not r["same_as_snapshot"] for r in res), "UNMAPPED", bad)
