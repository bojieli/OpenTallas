"""HBM-HUB-RTL-1 11-12: drop $adlatch/$dlatch cells whose Q drives nothing (no cell input, no module output port) from an
as-built Yosys JSON, in place of a re-run with another yosys build.  The current ORFS yosys infers these for the loop
variable / temporaries of always @* blocks (ot_hbm_idx_score_quarter_static_h.sv:73-79, `for (integer j...)`); the
Nov-8 bind_e0 elaboration has none (224 vs 227 cells, same source).  Fails closed: any latch whose Q is read is kept and
reported.  usage: prune_dead_latches.py IN.json OUT.json"""
import json, sys
y = json.load(open(sys.argv[1])); dropped, kept = [], []
for mn, m in y["modules"].items():
    cells = m.get("cells", {})
    lat = [n for n, c in cells.items() if c["type"] in ("$adlatch", "$dlatch", "$adlatche", "$dlatchsr")]
    if not lat:
        continue
    read = set()
    for n, c in cells.items():
        for p, bits in c["connections"].items():
            if c.get("port_directions", {}).get(p, "input") != "output" or c["type"] in ("$adlatch", "$dlatch"):
                if c["type"] in ("$adlatch", "$dlatch") and p == "Q":
                    continue
                read.update(b for b in bits if isinstance(b, int))
    for p, d in m.get("ports", {}).items():
        if d["direction"] in ("output", "inout"):
            read.update(b for b in d["bits"] if isinstance(b, int))
    for n in lat:
        q = [b for b in cells[n]["connections"]["Q"] if isinstance(b, int)]
        (kept if any(b in read for b in q) else dropped).append((mn.split("\\")[-1], n))
        if not any(b in read for b in q):
            del cells[n]
json.dump(y, open(sys.argv[2], "w"))
print(json.dumps({"dropped": len(dropped), "kept_live": len(kept), "dropped_list": dropped[:6], "kept_list": kept[:6]}))
sys.exit(1 if kept else 0)
