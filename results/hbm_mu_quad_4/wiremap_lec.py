#!/usr/bin/env python3
"""Pure-wiring equivalence (HBM-MU-QUAD-4): member wrapper vs canonical strap wrapper + member straps (shim).
Both sides elaborated by yosys (canonical top blackboxed, flatten, opt_clean -purge, write_json).  PASS iff (1) no
cells other than the one blackbox instance on each side, and (2) the connection map {blackbox pin bit -> top port bit |
constant} and {top output bit -> blackbox pin bit | constant} is identical.  Any logic difference shows as a map diff.
Usage: wiremap_lec.py GOLD.json GATE.json"""
import json, sys


def cmap(path):
    J = json.load(open(path))
    mods = [m for m, v in J["modules"].items() if not v.get("attributes", {}).get("blackbox") and v.get("cells") is not None and "top" in v.get("attributes", {})]
    if len(mods) != 1:
        mods = [m for m, v in J["modules"].items() if v.get("attributes", {}).get("top")]
    M = J["modules"][mods[0]]
    name = {}
    for pn, p in M["ports"].items():
        for i, b in enumerate(p["bits"]):
            name.setdefault(b, f"{pn}[{i}]")
    cells = M["cells"]
    bb = [c for c in cells.values()]
    if len(bb) != 1:
        return None, f"{len(bb)} cells: " + ",".join(sorted({c['type'] for c in bb}))
    c = bb[0]
    m = {}
    for pn, bits in c["connections"].items():
        for i, b in enumerate(bits):
            m[f"bb.{pn}[{i}]"] = name.get(b, b if isinstance(b, str) else f"net{b}" if c["port_directions"].get(pn) == "input" else f"bbout:{pn}[{i}]")
    out_src = {}
    for pn, bits in c["connections"].items():
        if c["port_directions"].get(pn) == "output":
            for i, b in enumerate(bits):
                out_src[b] = f"bb.{pn}[{i}]"
    for pn, p in M["ports"].items():
        if p["direction"] == "output":
            for i, b in enumerate(p["bits"]):
                m[f"out.{pn}[{i}]"] = b if isinstance(b, str) else out_src.get(b, name.get(b) if name.get(b, '').split('[')[0] != pn else f"undriven")
    return (c["type"], m), None


g, eg = cmap(sys.argv[1]); t, et = cmap(sys.argv[2])
if eg or et:
    print("FAIL", eg, et); sys.exit(1)
if g[0] != t[0]:
    print("FAIL blackbox type", g[0], t[0]); sys.exit(1)
d = [k for k in set(g[1]) | set(t[1]) if g[1].get(k) != t[1].get(k)]
print(("PASS" if not d else "FAIL"), len(g[1]), "pin bits mapped;", len(d), "differ", sorted(d)[:5])
sys.exit(1 if d else 0)
