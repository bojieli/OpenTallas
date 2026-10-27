#!/usr/bin/env python3
"""PG-ACTIVITY-KVHBM (10-27): per-bit toggle rates (transitions per clock cycle, X/Z ignored) under named VCD scopes.
Generalised from INFRA-FIRST-HEAD-4 tools/s81_head/head_activity.py.  Keys are scope-relative "a.b.sig[bit]".
  vcd_activity.py X.vcd OUTDIR --clk SCOPE.SIGNAME --root TAG=SCOPE [--root ...] [--list-scopes PATTERN]
Writes OUTDIR/act_<TAG>.txt ("name rate" lines) and OUTDIR/activity_summary.json."""
import argparse, json, re, sys
from collections import defaultdict
ap = argparse.ArgumentParser(); ap.add_argument("vcd"); ap.add_argument("out")
ap.add_argument("--clk", required=True); ap.add_argument("--root", action="append", default=[])
ap.add_argument("--list-scopes")
a = ap.parse_args()
ROOTS = dict(r.split("=", 1) for r in a.root)
ckscope, ckname = a.clk.rsplit(".", 1)
ids = defaultdict(list); scope = []; ck = None; scopes = set()
f = open(a.vcd, "rb")
for raw in f:
    ln = raw.decode("latin-1").strip()
    if ln.startswith("$scope"):
        scope.append(ln.split()[2]); scopes.add(".".join(scope))
    elif ln.startswith("$upscope"):
        scope.pop()
    elif ln.startswith("$var"):
        p = ln.split(); w, i, nm = int(p[2]), p[3], p[4]
        rng = p[5] if len(p) > 6 and p[5].startswith("[") else None
        path = ".".join(scope)
        if nm == ckname and path == ckscope: ck = i
        for t, r in ROOTS.items():
            if path == r or path.startswith(r + "."):
                rel = path[len(r) + 1:]; base = (rel + "." if rel else "") + nm
                if rng:
                    m = re.match(r"\[(-?\d+)(?::(-?\d+))?\]", rng); msb = int(m.group(1)); lsb = int(m.group(2)) if m.group(2) else msb
                else:
                    msb = lsb = None
                ids[i].append((t, base, w, lsb, msb))
    elif ln.startswith("$enddefinitions"):
        break
if a.list_scopes:
    for s in sorted(scopes):
        if re.search(a.list_scopes, s): print(s)
    sys.exit(0)
assert ck, "clock not traced"
want = set(ids) | {ck}; prev = {}; tog = defaultdict(int); nck = 0
for raw in f:
    if not raw or raw[0] in b"#$": continue
    c = raw[0:1]
    if c in (b"b", b"B"):
        v, i = raw[1:].split(); i = i.decode()
        if i not in want: continue
        s = v.decode()
        if any(ch in s for ch in "xzXZ"): continue
        n = int(s, 2)
    elif c in (b"0", b"1"):
        i = raw[1:].strip().decode()
        if i not in want: continue
        n = int(c)
        if i == ck: nck += n; continue
    else:
        continue
    o = prev.get(i); prev[i] = n
    if o is None: continue
    d = o ^ n
    while d:
        b = d & -d; tog[(i, b.bit_length() - 1)] += 1; d ^= b
cycles = nck; rates = {t: {} for t in ROOTS}
for i, lst in ids.items():
    for t, base, w, lsb, msb in lst:
        for k in range(w):
            if lsb is None and w == 1: name = base
            else:
                lo = lsb if lsb is not None else 0
                bit = (lo + k) if (msb is None or msb >= lo) else (lo - k)
                name = f"{base}[{bit}]"
            rates[t][name] = tog.get((i, k), 0) / cycles
res = dict(cycles=cycles, roots=ROOTS, types={})
for t, r in rates.items():
    v = sorted(r.values())
    if not v: print(t, "NO SIGNALS"); continue
    res["types"][t] = dict(bits=len(v), mean=sum(v) / len(v), median=v[len(v) // 2], p90=v[int(len(v) * .9)], max=v[-1],
                           zero_frac=sum(1 for x in v if x == 0) / len(v))
    print(t, {k: round(x, 4) if isinstance(x, float) else x for k, x in res["types"][t].items()})
    with open(f"{a.out}/act_{t}.txt", "w") as fo:
        for k, x in r.items():
            if " " not in k: fo.write(f"{k} {x:.6f}\n")
print("cycles", cycles)
json.dump(res, open(f"{a.out}/activity_summary.json", "w"), indent=1)
