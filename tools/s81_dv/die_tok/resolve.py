#!/usr/bin/env python3
"""TOK-DS-2: close the -v library set: index module definitions under the worktree, then add (transitively) a defining
file for every instantiated-but-undefined module of the sim filelist. Prefers files already listed; ambiguous -> report."""
import re, sys, os, collections
wt, simf, out = sys.argv[1:4]
roots = ["rtl", "physical/die_plan/s81/bind/models", "physical/asap7_memory_macros", "physical/asap7_memory_macros_v2", "physical/asap7_memory_macros_pa", "physical/die_plan/s81/bind/source_modules", "physical/rom_host_ingest"]
MOD = re.compile(r"^\s*module\s+(?:automatic\s+)?(\w+)", re.M)
INST = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\(.*?\)\s*)?([A-Za-z_]\w*)\s*\(", re.M | re.S)
KW = set("module if else for always assign wire reg input output logic begin end case generate function task initial localparam parameter return while foreach assert property typedef genvar integer bit int string".split())
def strip(t): return re.sub(r"\(\*\s*\w[^()]*?\*\)", " ", re.sub(r"//[^\n]*|/\*.*?\*/", "", t, flags=re.S))
defs = collections.defaultdict(list)
for r in roots:
    for dp, dn, fn in os.walk(os.path.join(wt, r)):
        for f in fn:
            if f.endswith((".sv", ".v")) and not f.endswith("_bb.v"):
                p = os.path.join(dp, f)
                try: t = strip(open(p, errors="ignore").read())
                except Exception: continue
                for m in MOD.findall(t): defs[m].append(p)
lines = [l.rstrip("\n") for l in open(simf)]
files = [l[3:] if l.startswith("-v ") else l for l in lines if not l.startswith("+")]
user = {}
have = set(files); defined = set(); used = set(); queue = list(files); seen = set()
def scan(p):
    t = strip(open(p, errors="ignore").read())
    for m in MOD.findall(t): defined.add(m)
    for a, b in INST.findall(t):
        if a not in KW and b not in KW:
            used.add(a); user.setdefault(a, p)
added = []
while queue:
    p = queue.pop()
    if p in seen: continue
    seen.add(p); scan(p)
    if not queue:
        for m in sorted(used - defined):
            c = defs.get(m)
            if not c: continue
            ok = [x for x in c if "/test/" not in x and "/tb_" not in x and "/tb/" not in x] or c
            def rk(x):
                if "asap7_memory_macros_v2/" in x: return 0
                if "asap7_memory_macros/" in x: return 1
                if "/bind/models/" in x: return 0
                if "/rtl/dsrom_sys/" in x or "/rtl/hdc/" in x or "/rtl/lib/" in x or "/rtl/common/" in x: return 2
                return 3
            u = user.get(m, "")
            pick = sorted(ok, key=lambda x: (rk(x), -len(os.path.commonpath([x, u])) if u else 0, len(x)))[0]
            if len(c) > 1: print("AMBIG", m, c, "->", pick, file=sys.stderr)
            if pick not in have: have.add(pick); added.append(pick); queue.append(pick)
miss = sorted(m for m in used - defined if m not in defs)
with open(out, "w") as fh:
    def hasdef(f):
        try: return "`define" in open(f.replace("-v ", ""), errors="ignore").read()
        except Exception: return False
    allf = [l for l in lines if not l.startswith("+")] + ["-v " + p for p in added]
    for l in lines:
        if l.startswith("+"): fh.write(l + "\n")
    for l in [x.replace("-v ", "") for x in allf if hasdef(x)] + [x for x in allf if not hasdef(x)]: fh.write(l + "\n")
    for d in sorted({os.path.dirname(p) for p in added}): fh.write("+incdir+" + d + "\n")
print("added", len(added), "still-undefined (may be false positives)", len(miss))
print(" ".join(miss[:80]))
