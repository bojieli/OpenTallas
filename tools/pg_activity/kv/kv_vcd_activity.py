#!/usr/bin/env python3
"""PG-ACTIVITY-KVHBM 10-27 KV (generalised tools/s81_head/head_activity.py, INFRA-FIRST-HEAD-4 method): per-bit toggle rates
(transitions 0->1 + 1->0 per clock cycle, X/Z ignored; cycles = rising edges of CLK_PATH) of the scopes ROOT, written as
"<PREFIX><rel.name[bit]>" lines (rel = dotted path below ROOT) so they match hard-core netlist register / port names after
normalisation in kv_core_power_meas.tcl (kit '/' -> '.', '$_...' suffix stripped).
  kv_vcd_activity.py VCD CLK_PATH OUT.txt OUT_summary.json PREFIX=ROOT [PREFIX=ROOT ...]
  env WIN=t0:t1 (VCD time units): count toggles and clock edges only for t0 <= t < t1 (active-window rate)."""
import os
import json, re, sys
from collections import defaultdict
vcd, ckpath, out, summ = sys.argv[1:5]
ROOTS = [a.split("=", 1) for a in sys.argv[5:]]
ids = defaultdict(list); scope = []; ck = None
f = open(vcd, "rb")
for raw in f:
    ln = raw.decode("latin-1").strip()
    if ln.startswith("$scope"): scope.append(ln.split()[2])
    elif ln.startswith("$upscope"): scope.pop()
    elif ln.startswith("$var"):
        p = ln.split(); w, i, nm = int(p[2]), p[3], p[4]
        rng = p[5] if len(p) > 6 and p[5].startswith("[") else None
        path = ".".join(scope)
        if path + "." + nm == ckpath and ck is None: ck = i
        for pre, r in ROOTS:
            if path == r or path.startswith(r + "."):
                rel = path[len(r) + 1:]
                base = pre + (rel + "." if rel else "") + nm
                if rng:
                    m = re.match(r"\[(-?\d+)(?::(-?\d+))?\]", rng); msb = int(m.group(1)); lsb = int(m.group(2)) if m.group(2) else msb
                else: msb = lsb = None
                ids[i].append((pre, base, w, lsb, msb))
    elif ln.startswith("$enddefinitions"): break
assert ck, "clock %s not traced" % ckpath
want = set(ids) | {ck}; prev, tog = {}, defaultdict(int); nck = 0
W0, W1 = (map(int, os.environ["WIN"].split(":")) if os.environ.get("WIN") else (-1, 1 << 62)); t = 0
for raw in f:
    if raw[:1] == b"#": t = int(raw[1:]); continue
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
        if i == ck: nck += n if W0 <= t < W1 else 0; continue
    else: continue
    o = prev.get(i); prev[i] = n
    if o is None or not (W0 <= t < W1): continue
    d = o ^ n
    while d:
        b = d & -d; tog[(i, b.bit_length() - 1)] += 1; d ^= b
rates = {}
for i, lst in ids.items():
    for pre, base, w, lsb, msb in lst:
        for k in range(w):
            if lsb is None and w == 1: name = base
            else:
                lo = lsb if lsb is not None else 0
                bit = (lo + k) if (msb is None or msb >= lo) else (lo - k)
                name = f"{base}[{bit}]"
            rates[name] = tog.get((i, k), 0) / nck
with open(out, "w") as g:
    for k, v in rates.items():
        if " " not in k: g.write(f"{k} {v:.6f}\n")
v = sorted(rates.values())
S = dict(win=os.environ.get("WIN"), vcd=vcd, clock=ckpath, cycles=nck, roots=ROOTS, bits=len(v), mean=sum(v) / len(v), median=v[len(v) // 2],
         p90=v[int(len(v) * .9)], max=v[-1], zero_frac=sum(1 for x in v if x == 0) / len(v))
json.dump(S, open(summ, "w"), indent=1); print(json.dumps(S))
