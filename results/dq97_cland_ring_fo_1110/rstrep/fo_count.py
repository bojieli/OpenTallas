"""Leaf sink-pin count (through the kept hierarchy) of the cas reset port bits rst_n / rst_xn[j]: every non-module cell
input pin reached from the bit, inner module ports followed.  argv: synthesized yosys json files"""
import json, sys
from functools import lru_cache
for f in sys.argv[1:]:
    J = json.load(open(f)); M = J["modules"]
    def sinks(mn):
        m = M[mn]; loads = {}
        for c in m["cells"].values():
            for pn, bits in c["connections"].items():
                if c.get("port_directions", {}).get(pn, "input") == "output": continue
                for i, b in enumerate(bits):
                    if isinstance(b, int): loads.setdefault(b, []).append((c["type"], pn, i))
        return loads
    S = {mn: sinks(mn) for mn in M}
    @lru_cache(None)
    def leaf(mn, port, i):
        b = M[mn]["ports"][port]["bits"][i]
        n = 0
        for t, pn, j in S[mn].get(b, []):
            n += leaf(t, pn, j) if t in M else 1
        return n
    for mn, m in M.items():
        if "ot_dp_clk_landing_cas" not in mn: continue
        out = [f"{p}[{i}]={leaf(mn, p, i)}" for p in ("rst_n", "rst_xn") if p in m["ports"] for i in range(len(m["ports"][p]["bits"]))]
        print(f.split("/")[-1], " ".join(out))
