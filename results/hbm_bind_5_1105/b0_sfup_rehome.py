#!/usr/bin/env python3
"""HBM-BIND-5 plan event B0 (COORD 11-05 06:55, candidate until READY): re-home the N-role SFU programme store
u_sfup_Q__q1 from each hub into its b113, next to its only data consumer u_sfucore_Q. No RTL change. q0 stays in the hub.
usage: b0_sfup_rehome.py PLAN_DIR OUT_DIR MAP_IN MAP_OUT [X Y]   (X,Y = core origin in the b113 type frame)
Other PLAN_DIR entries are hard-linked. Writes OUT_DIR/die_plan.json, core_conns.json, b0_report.json + MAP_OUT."""
import json, os, sys, copy
src, out, mi, mo = sys.argv[1:5]
X, Y = (float(sys.argv[5]), float(sys.argv[6])) if len(sys.argv) > 6 else (25.92, 216.0)
os.makedirs(out, exist_ok=True)
for n in os.listdir(src):
    if n in ("die_plan.json", "core_conns.json", "clock_entries.json"): continue
    d = os.path.join(out, n)
    if not os.path.lexists(d):
        s = os.path.join(src, n)
        (os.symlink(os.path.realpath(s), d) if os.path.isdir(s) else os.link(os.path.realpath(s), d))
P = json.load(open(src + "/die_plan.json")); T = P["partition_types"]
cc = json.load(open(src + "/core_conns.json")); ce = json.load(open(src + "/clock_entries.json"))
m = json.load(open(mi)); rep = dict(moved=[], dropped_chains=[], X=X, Y=Y)
INST = "u_sfup_Q__q1"
parts = {p["name"]: p for p in P["partitions"]}
for side, hub, b113 in (("NW", "NW_hub", "NW_b113"), ("NE", "NE_hub", "NE_b113")):
    th, tb = T[parts[hub]["type"]], T[parts[b113]["type"]]
    h = next(c for c in th["hard_cores"] if c["inst"] == INST)
    w, ht = h["outline_um"]; ox, oy = h["origin_um"]
    for c in tb["hard_cores"]:
        x, y = c["origin_um"]; cw, ch = c["outline_um"]
        if X < x + cw + 4.32 and x < X + w + 4.32 and Y < y + ch + 4.32 and y < Y + ht + 4.32:
            raise SystemExit(f"{b113}: overlaps {c['inst']}")
    th["hard_cores"].remove(h)
    nh = copy.deepcopy(h); nh["origin_um"] = [X, Y]
    nh["note"] = "HBM-BIND-5 B0: re-homed from the hub next to u_sfucore_Q | " + h.get("note", "")
    tb["hard_cores"].append(nh)
    tap = next(t for t in th["clock"]["taps"] if t["name"] == INST)
    th["clock"]["taps"].remove(tap)
    nt = copy.deepcopy(tap); nt["xy"] = [round(tap["xy"][0] - ox + X, 4), round(tap["xy"][1] - oy + Y, 4)]
    nt["note"] = "HBM-BIND-5 B0: follows the core | " + tap.get("note", "")
    tb["clock"]["taps"].append(nt)
    # the two legacy chains from face bus L5_o to the hub store carry compiler_control/io_word, now local in b113
    keep = []
    for s in th["internal_stations"]:
        if str(s.get("capture", "")).startswith("u_sfup_Q."):
            rep["dropped_chains"].append(dict(type=parts[hub]["type"], capture=s["capture"], bits=s["bits"], regs=len(s["regs_um"]),
                                              flops=s["bits"] * len(s["regs_um"])))
        else:
            keep.append(s)
    th["internal_stations"] = keep
    cells = next(c["cells"] for c in th["contents"] if c["inst"] == "u_sfup_Q")
    tb["contents"].append(dict(inst=INST, module=h["module"], status="reuse", cells=cells, origin_um=[X, Y], outline_um=[w, ht],
                               note="HBM-BIND-5 B0: as-built sfup_%s re-homed" % side))
    th["cells"] -= cells; tb["cells"] += cells
    cc_h = cc[parts[hub]["type"]]; cc_b = cc.setdefault(parts[b113]["type"], {})
    cc_b[INST] = dict(clk=["tap:" + INST], compiler_control=["u_sfucore_Q"], io_word=["u_sfucore_Q"])
    ce.setdefault(parts[b113]["type"], {})[INST] = dict(ce[parts[hub]["type"]]["u_sfup_Q"], tap=INST)
    key = "sfup_" + side
    assert m["parts"][key] == [hub, INST], m["parts"][key]
    m["parts"][key] = [b113, INST]
    rep["moved"].append(dict(side=side, hub=parts[hub]["type"], b113=parts[b113]["type"], cells=cells, tap=nt["xy"]))
json.dump(P, open(out + "/die_plan.json", "w"), indent=1); json.dump(cc, open(out + "/core_conns.json", "w"), indent=1)
json.dump(ce, open(out + "/clock_entries.json", "w"), indent=1); json.dump(m, open(mo, "w"), indent=1); json.dump(rep, open(out + "/b0_report.json", "w"), indent=1)
print(json.dumps(rep))
