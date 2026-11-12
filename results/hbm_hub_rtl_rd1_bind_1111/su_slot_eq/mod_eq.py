"""Extract one module (by name suffix) from two as-built JSONs (cached bind_e0 = gold, fresh elab with the fixed source =
gate) into one small JSON for yosys equiv: submodule types become port-only blackboxes (same names on both sides)."""
import json, sys
gold_f, gate_f, out, MOD = sys.argv[1:5]
def pick(f):
    y = json.load(open(f)); M = y["modules"]
    name = next(n for n in M if n.endswith("\\" + MOD) or n == MOD)
    return M, name
Mg, ng = pick(gold_f); Mt, nt = pick(gate_f)
assert ng == nt, (ng, nt)
mods = {"gold": Mg[ng], "gate": Mt[nt]}
lat = {k: sum(1 for c in v["cells"].values() if "latch" in c["type"]) for k, v in mods.items()}
for M, m in ((Mg, Mg[ng]), (Mt, Mt[nt])):
    for c in m["cells"].values():
        t = c["type"]
        if not t.startswith("$") or t.startswith("$paramod"):
            if t not in mods:
                src = M[t]
                mods[t] = {"attributes": {"blackbox": "00000000000000000000000000000001"}, "ports": src["ports"],
                           "parameter_default_values": src.get("parameter_default_values", {}), "cells": {}, "netnames": {}}
json.dump({"modules": mods}, open(out, "w"))
print(json.dumps({"module": ng, "cells_gold": len(Mg[ng]["cells"]), "cells_gate": len(Mt[nt]["cells"]), "latches": lat,
                  "blackboxes": len(mods) - 2}))
