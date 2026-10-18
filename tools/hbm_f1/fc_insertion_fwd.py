#!/usr/bin/env python3
"""insertion.json "forwarded_clock" of an F1 relay view (fc or fork fc_f<N>) from its re-exported libs (H-NETLIST F1):
per corner and per clk_out pin, the clk_in -> clk_out<k> combinational arc (one kept buffer) at a light load, at
1 / 4 clk_in pins, and with the 405 um branch wire (0.15 fF/um), plus R (insertion.json <corner>.boundary.mean).
    fc_insertion_fwd.py VIEW_DIR CELL [--fork]    (fc: the fork4 model of the coordinator's 2026-10-16 views; fork: 1 pin)"""
import json, re, sys
from pathlib import Path

V, CELL = Path(sys.argv[1]), sys.argv[2]
FORK = "--fork" in sys.argv
WIRE_FF = 405.0 * 0.15


def block(t, start):
    j = t.index("{", start); d = 0
    for k in range(j, len(t)):
        d += {"{": 1, "}": -1}.get(t[k], 0)
        if d == 0:
            return t[start:k + 1]


def interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0])
    for a in range(len(xs) - 1):
        if xs[a] <= x <= xs[a + 1]:
            return ys[a] + (ys[a + 1] - ys[a]) * (x - xs[a]) / (xs[a + 1] - xs[a])
    return ys[-2] + (ys[-1] - ys[-2]) * (x - xs[-2]) / (xs[-1] - xs[-2])


ins = json.loads((V / "insertion.json").read_text())
out = dict(arc="clk_in -> clk_out<k> combinational positive_unate (one kept buffer per branch, off the CTS tree)",
           model=("per branch: 1 x clk_in pin cap; + wire 405 um x 0.15 fF/um" if FORK else
                  "fork4: 4 x clk_in pin cap; + wire 4 x 405.0 um x 0.15 fF/um"),
           etm="re-exported without the clk_out*_fwd generated clocks (tools/hbm_f1/fc_etm_reexport.sh); register arcs "
               "byte-identical to the closure-loop export", corners={})
for c in ("tt", "ff", "ss"):
    t = (V / f"{CELL}_{c}.lib").read_text()
    cin = float(re.search(r'pin\("clk_in"\)\s*\{[^}]*?capacitance\s*:\s*([\d.]+)', t, re.S).group(1))
    cc = out["corners"][c] = dict(R_ps=(ins.get(c) or {}).get("boundary", {}).get("mean"), clk_in_pin_ff=cin, pins={})
    for m in re.finditer(r'pin\("(clk_out\d*)"\)', t):
        b = block(t, m.start())
        g = next((block(b, x.start()) for x in re.finditer(r"timing\(\)", b)
                  if 'related_pin : "clk_in"' in block(b, x.start()) and "combinational" in block(b, x.start())), None)
        if g is None:
            sys.exit(f"{c}: {m.group(1)} has no combinational clk_in arc")
        cr = re.search(r"cell_rise\(\w+\)\s*\{\s*index_1\(\"([^\"]+)\"\);\s*values\(\"([^\"]+)\"\)", g)
        xs = [float(x) for x in cr.group(1).split(",")]; ys = [float(x) for x in cr.group(2).split(",")]
        loads = {"light": xs[0], "pins": cin * (1 if FORK else 4)}
        loads["pins_wire"] = loads["pins"] + (WIRE_FF if FORK else 4 * WIRE_FF)
        cc["pins"][m.group(1)] = {k: dict(load_ff=round(v, 2), ps=round(interp(xs, ys, v), 2)) for k, v in loads.items()}
ins["forwarded_clock"] = out
(V / "insertion.json").write_text(json.dumps(ins, indent=1) + "\n")
print(CELL, json.dumps({c: {p: v["pins_wire"]["ps"] for p, v in d["pins"].items()} for c, d in out["corners"].items()}))
