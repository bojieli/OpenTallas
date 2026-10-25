import json, sys
js, fm, entry, top = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3]), sys.argv[4]
a = json.load(open(js))
m = a["modules"][top] if top in a["modules"] else [v for k, v in a["modules"].items() if k.endswith(top) or top in k][0]
readers = {}
for cn, c in m["cells"].items():
    pd = c.get("port_directions", {})
    for p, bits in c["connections"].items():
        if pd.get(p, "input") != "output":
            for b in bits:
                if isinstance(b, int): readers.setdefault(b, []).append(f"{cn}.{p}")
def port_bits(n): return m["ports"][n]["bits"]
# bit-level LIVENESS (a wide $dff whose Q bits for these inputs are unread is not a reader): seed = top output bits +
# every input of a non-$ (black box) cell; a $ flop maps D[i] -> Q[i] (its control pins live with any live Q); any other
# $ cell makes all its inputs live when any output bit is live.
drv = {}
for cn, c in m["cells"].items():
    pd = c.get("port_directions", {})
    for p, bits in c["connections"].items():
        if pd.get(p) == "output":
            for i, b in enumerate(bits):
                if isinstance(b, int): drv[b] = (cn, p, i)
live = set(); work = []
def mark(b):
    if isinstance(b, int) and b not in live: live.add(b); work.append(b)
for pn, p in m["ports"].items():
    if p["direction"] == "output":
        for b in p["bits"]: mark(b)
for cn, c in m["cells"].items():
    if not c["type"].startswith("$"):
        pd = c.get("port_directions", {})
        for p, bits in c["connections"].items():
            if pd.get(p, "input") != "output":
                for b in bits: mark(b)
done_cells = set()
while work:
    b = work.pop()
    if b not in drv: continue
    cn, p, i = drv[b]; c = m["cells"][cn]; pd = c.get("port_directions", {})
    bw = {"$mux": ("A", "B"), "$and": ("A", "B"), "$or": ("A", "B"), "$xor": ("A", "B"), "$xnor": ("A", "B"), "$not": ("A",)}
    t = c["type"]
    if t in bw and all(len(c["connections"][x]) == len(c["connections"]["Y"]) for x in bw[t]) and p == "Y":
        for x in bw[t]: mark(c["connections"][x][i])          # bitwise: Y[i] reads A[i] / B[i] only
        if t == "$mux" and cn not in done_cells:
            done_cells.add(cn); mark(c["connections"]["S"][0])
    elif "dff" in t and p == "Q":
        mark(c["connections"]["D"][i])
        if cn not in done_cells:
            done_cells.add(cn)
            for q, bits in c["connections"].items():
                if q not in ("D", "Q") and pd.get(q) != "output":
                    for x in bits: mark(x)
    elif cn not in done_cells:
        done_cells.add(cn)
        for q, bits in c["connections"].items():
            if pd.get(q, "input") != "output":
                for x in bits: mark(x)
res = []
if top == "dsdv_svc_rs_c":
    W = {"dn_i": 805, "up_i": 16, "ri": 514, "gi_v": 1, "gi_d": 2132, "si_v": 1, "si_d": 1076}
    G = {"dn_i": 0, "up_i": 8, "ri": 16, "gi_v": 24, "gi_d": 24, "si_v": 32, "si_d": 32}
    chk = []
    for p, w in W.items():
        for f in range(4):
            if not (fm >> (G[p] + f) & 1):
                chk.append((f"{p}[face{f}]", port_bits(p)[w * f:w * f + w]))
    ctl = []
    for p, w in W.items():
        for f in range(4):
            if fm >> (G[p] + f) & 1:
                ctl.append((f"{p}[face{f}]", port_bits(p)[w * f:w * f + w]))
    if entry:
        ctl.append(("q[512:0]", port_bits("q")[:513]))
    for name, bits in ctl:   # negative control: every KEPT face must have readers
        r = {x for b in bits if isinstance(b, int) for x in readers.get(b, [])}
        lv = sum(1 for b in bits if b in live)
        print("CONTROL", name, "readers", len(r), "live", lv, "OK" if lv else "NOT_LIVE(!)")
    if entry:
        chk.append(("q[514:513]", port_bits("q")[513:515]))
    else:
        chk += [("j", port_bits("j")), ("q", port_bits("q")), ("hw", port_bits("hw"))]
else:   # dsdv_pv_so_program TF 0: q[514:513] may only reach q_pass[514:513]
    chk = [("q[514:513]", port_bits("q")[513:515])]
    qp = port_bits("q_pass")
    print("q_pass[514:513] bits", qp[513:515], "q[514:513] bits", port_bits("q")[513:515])
bad = 0; tot = 0
for name, bits in chk:
    r = sorted({x for b in bits if isinstance(b, int) for x in readers.get(b, [])})
    lv = [b for b in bits if b in live]
    tot += len(bits)
    if lv: bad += 1; print("LIVE", name, len(bits), "b,", len(lv), "live, readers", r[:6], "...", len(r))
    elif r: print("DEAD_READER_ONLY", name, len(bits), "b: cells", r[:4], "read it but no output depends on it")
    else: print("NO_READER", name, len(bits), "b")
print("VERDICT", "PASS" if bad == 0 else "FAIL", "checked_bits", tot, "ports_with_readers", bad, "cells", len(m["cells"]))
