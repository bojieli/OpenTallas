#!/usr/bin/env python3
# collect.py TREE KIT... : bench-read paths of kits in a merge tree (git -C OpenTallas)
import json, re, subprocess, sys, os
G = ["git", "--git-dir", "/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git"]
tree, kits = sys.argv[1], sys.argv[2:]
def exists(p): return subprocess.run(G + ["cat-file", "-e", f"{tree}:{p}"], capture_output=True).returncode == 0
def typ(p): return subprocess.run(G + ["cat-file", "-t", f"{tree}:{p}"], capture_output=True, text=True).stdout.strip()
P = {"Makefile", "rtl", "tools", "physical/common_flow"}
for k in kits:
    P.add(f"physical/ref_tile/{k}")
    j = json.loads(subprocess.run(G + ["show", f"{tree}:physical/ref_tile/{k}/job.json"], capture_output=True, text=True).stdout)
    toks = []
    for st in j["stages"]["bench"]: toks += re.findall(r"[A-Za-z0-9_./-]+", st["cmd"].replace("{RUN}", "/RUN"))
    src = j.get("source")
    if isinstance(src, list): toks += [s if isinstance(s, str) else s.get("path", "") for s in src]
    elif isinstance(src, dict):
        for v in src.values():
            if isinstance(v, str): toks.append(v)
            elif isinstance(v, list): toks += [x for x in v if isinstance(x, str)]
    for x in j.get("extra_paths", []) or []: toks.append(x)
    for t in toks:
        t = t.strip("./") if t.startswith("./") else t
        if not re.match(r"^(results|physical|rtl|tools|docs|build)/", t): continue
        while t and not exists(t): t = os.path.dirname(t)
        if not t or t in ("results", "physical", "build"): continue
        if typ(t) == "blob" and t.startswith(("results/", "physical/")): t = os.path.dirname(t)
        P.add(t)
print(" ".join(sorted(P)))
