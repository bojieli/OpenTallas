#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-4: measured per-bit toggle rates of the head elements from the VCD of head_activity_sim.sh
(tb_s81hd_mini scenario A: released head.weight + golden x of the 1M token, one full head pass, TB_PASS).
activity = transitions (0->1 + 1->0, X/Z ignored) per clock cycle over the whole window (cycles = tb ck rises).
Keys are element-relative flattened names "scope.sub.sig[bit]" = the hard-core netlist register names without the
"u_m." wrapper prefix and the "$_DFF..." suffix.
  head_activity.py elem.vcd OUT.json"""
import json, re, sys
from collections import defaultdict
vcd, out = sys.argv[1], sys.argv[2]
ROOTS = {"A": "tb_s81hd_mini.u_t0.u_b.g_a[0].g_rtl.u_e", "B": "tb_s81hd_mini.u_t0.u_b.g_rtlb.u_b"}
ids = defaultdict(list)          # id -> [(type, relname, width, lsb, msb)]
scope = []
ck = None
f = open(vcd, "rb")
for raw in f:
    ln = raw.decode("latin-1").strip()
    if ln.startswith("$scope"):
        scope.append(ln.split()[2])
    elif ln.startswith("$upscope"):
        scope.pop()
    elif ln.startswith("$var"):
        p = ln.split()
        w, i, nm = int(p[2]), p[3], p[4]
        rng = p[5] if len(p) > 6 and p[5].startswith("[") else None
        path = ".".join(scope)
        if nm == "ck" and path == "tb_s81hd_mini":
            ck = i
        for t, r in ROOTS.items():
            if path == r or path.startswith(r + "."):
                rel = path[len(r) + 1:]
                base = (rel + "." if rel else "") + nm
                if rng:
                    m = re.match(r"\[(-?\d+)(?::(-?\d+))?\]", rng)
                    msb = int(m.group(1)); lsb = int(m.group(2)) if m.group(2) else msb
                else:
                    msb = lsb = None
                ids[i].append((t, base, w, lsb, msb))
    elif ln.startswith("$enddefinitions"):
        break
assert ck, "tb ck not traced"
want = set(ids) | {ck}
prev, tog = {}, defaultdict(int)
nck = 0
for raw in f:
    if not raw or raw[0] in b"#$":
        continue
    c = raw[0:1]
    if c in (b"b", b"B"):
        v, i = raw[1:].split()
        i = i.decode()
        if i not in want:
            continue
        s = v.decode()
        if "x" in s or "z" in s or "X" in s or "Z" in s:
            continue
        n = int(s, 2)
    elif c in (b"0", b"1"):
        i = raw[1:].strip().decode()
        if i not in want:
            continue
        n = int(c)
        if i == ck:
            nck += n
            continue
    else:
        continue
    o = prev.get(i)
    prev[i] = n
    if o is None:
        continue
    d = o ^ n
    while d:
        b = d & -d
        tog[(i, b.bit_length() - 1)] += 1
        d ^= b
cycles = nck
rates = {t: {} for t in ROOTS}
for i, lst in ids.items():
    for t, base, w, lsb, msb in lst:
        for k in range(w):
            if lsb is None and w == 1:
                name = base
            else:
                lo = lsb if lsb is not None else 0
                bit = (lo + k) if (msb is None or msb >= lo) else (lo - k)
                name = f"{base}[{bit}]"
            rates[t][name] = tog.get((i, k), 0) / cycles
res = dict(cycles=cycles, roots=ROOTS, types={})
for t, r in rates.items():
    v = sorted(r.values())
    res["types"][t] = dict(bits=len(v), mean=sum(v) / len(v), median=v[len(v) // 2], p90=v[int(len(v) * .9)], max=v[-1],
                           zero_frac=sum(1 for x in v if x == 0) / len(v), rates=r)
    print(t, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in res["types"][t].items() if k != "rates"})
print("cycles", cycles)
json.dump(res, open(out, "w"))
