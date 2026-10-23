#!/usr/bin/env python3
"""Bit-level connectivity of a parent's hard children through its soft logic (landings, pads, glue).
input: yosys write_json of the parent after proc+flatten with the hard children blackboxed.
For every hard instance and each of its ports, follow every bit forward (outputs) / backward (inputs) through soft
cells (<= DEPTH cells, nets with > FANOUT sinks = control broadcast, skipped) to hard pins / top ports.
usage: net_affinity.py <yosys.json> <top> <out.json> [hard_type_regex]"""
import json, sys, re, collections
DEPTH, FANOUT = 24, 48
d = json.load(open(sys.argv[1])); top = sys.argv[2]
mods = d["modules"]; m = mods[top]
hard_re = re.compile(sys.argv[4] if len(sys.argv) > 4 else r"^ot_hgi_coll")
def pdir(c):
    if "port_directions" in c and c["port_directions"]: return c["port_directions"]
    t = mods.get(c["type"], {})
    return {p: v["direction"] for p, v in t.get("ports", {}).items()}
drivers = collections.defaultdict(list); sinks = collections.defaultdict(list)
cells = m["cells"]; hard = {}
for n, c in cells.items():
    pd = pdir(c); h = bool(hard_re.match(c["type"]))
    if h: hard[n] = c["type"]
    for p, bits in c["connections"].items():
        dr = pd.get(p, "input")
        for k, b in enumerate(bits):
            if isinstance(b, str): continue
            (drivers if dr == "output" else sinks)[b].append((n, p, k))
portbit = {}
for p, v in m["ports"].items():
    for b in v["bits"]:
        if not isinstance(b, str): portbit[b] = (p, v["direction"])
def soft_outs(n):
    c = cells[n]; pd = pdir(c)
    return [b for p, bits in c["connections"].items() if pd.get(p) == "output" for b in bits if not isinstance(b, str)]
def soft_ins(n):
    c = cells[n]; pd = pdir(c)
    return [b for p, bits in c["connections"].items() if pd.get(p, "input") != "output" for b in bits if not isinstance(b, str)]
def walk(b0, fwd):
    seen = {b0}; fr = [b0]; ends = collections.Counter()
    for depth in range(DEPTH):
        nx = []
        for b in fr:
            if b in portbit: ends["PORT:" + portbit[b][0]] += 1
            nbrs = sinks[b] if fwd else drivers[b]
            if fwd and len(nbrs) > FANOUT: continue
            for (n, p, k) in nbrs:
                if n in hard: ends[n] += 1; continue
                for ob in (soft_outs(n) if fwd else soft_ins(n)):
                    if ob not in seen and (fwd or len(sinks[ob]) <= FANOUT): seen.add(ob); nx.append(ob)
        fr = nx
        if not fr: break
    return ends
out = {}
for n, t in hard.items():
    c = cells[n]; pd = pdir(c); res = {}
    for p, bits in c["connections"].items():
        if re.match(r"^(clk|ck|rst)", p): continue
        fwd = pd.get(p) == "output"; agg = collections.Counter()
        for b in bits:
            if isinstance(b, str): continue
            for e, k in walk(b, fwd).items(): agg[e] += 1
        res[p] = {"dir": "o" if fwd else "i", "w": len(bits), "to": dict(agg.most_common(12))}
    out[n] = {"type": t, "ports": res}
json.dump(out, open(sys.argv[3], "w"), indent=0)
print(len(hard), "hard instances")
