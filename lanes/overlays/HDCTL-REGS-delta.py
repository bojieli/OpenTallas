"""HEAD hd_ctl register stations (TYPE-HDCTL-REGS, FABLE-PLAN-EVENTS item 4: "add one register on the face-to-face classes").
Measured cause (hd_ctl attempt_6 geom.tsv, placed): the output-lane flops u_ht.u_tx.oq_p sit at x 55-405 / y 12-222 (centroid 161,163)
and the face register u_bout_h_tx_o at the S face x 396-471 -> 606 um; u_hr.u_rx asm_q/iq_p (centroid 149,147 / 305,45) are fed from
u_bin_h_rx_i (S face); u_logic.ro[] (centroid 58,271, x to 277 / y 70-510) feed u_bout_lepk_o0 on the W face; n_rx_i (E face y 440-466)
is captured by the mrd_q/g_ms mesh flops at (480-530, 37-99).  Structural change: ONE plan station per bus (internal_stations,
bit_route per_bit, realized in the wrapper by kit_istations), hops <= 340 um (<= 550 asked); the lane latency table gets +1 cycle
(fixed_cycles) on host_tx, host_rx, kd (lepk_o0) and m7N_rx (n_rx_i).  usage: hdctl_regs_delta.py PLAN_IN PLAN_OUT"""
import json, sys
src, dst = sys.argv[1:3]
d = json.load(open(src)); t = d["partition_types"]["hd_ctl"]
assert not t.get("internal_stations")
def mid(a, b): return [round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)]
BUS = {b["name"]: b for b in t["buses"]}
ENT = [  # bus, leaf point (source/capture cluster), face pin centre, lane
 ("h_tx_o", (150.0, 165.0), "host_tx", "u_ht.u_tx.oq_p -> u_bout_h_tx_o, 606 um worst"),
 ("h_rx_i", (149.0, 147.0), "host_rx", "u_bin_h_rx_i -> u_hr.u_rx asm_q/iq_p, 48 bits > 405 um"),
 ("lepk_o0", (150.0, 300.0), "kd", "u_logic.ro[] -> u_bout_lepk_o0, 47 bits > 405 um"),
 ("n_rx_i", (500.0, 90.0), "m7N_rx", "u_bin_n_rx_i -> mesh mrd_q capture, 35 bits > 405 um"),
]
ist = []
lane_add = {}
for bus, leaf, lane, why in ENT:
    b = BUS[bus]; lo, hi = b["window_um"]; c = (lo + hi) / 2
    pin = {"S": [c, 0.0], "N": [c, 518.4], "W": [0.0, c], "E": [587.52, c]}[b["face"]]
    e = dict(conn="bus:" + bus, bits=b["width"], leaf_um=list(leaf), bit_route="per_bit",
             note=f"HDCTL-REGS 11-14 (FABLE-PLAN-EVENTS 4): one station, {why}")
    if b["dir"] == "out":
        e.update(from_um=list(leaf), to_um=pin)
    else:
        e.update(from_um=pin, to_um=list(leaf))
    e["regs_um"] = [mid(e["from_um"], e["to_um"])]
    ist.append(e); lane_add[lane] = 1
t["internal_stations"] = ist
t["realize_internal_stations"] = True
t["note"] += " | HEAD-99/TYPE-HDCTL-REGS rp21z18e (FABLE-PLAN-EVENTS 4): one internal station on h_tx_o, h_rx_i, lepk_o0, n_rx_i (+1 cycle each lane)."
for l in d["lanes"]:
    if l["id"] in lane_add:
        l["fixed_cycles"] = int(l.get("fixed_cycles", 0)) + lane_add.pop(l["id"])
assert not lane_add, lane_add
LT = d["latency"]["lanes"]   # same table gen.py latency --inplace writes (cycles/natural/fixed +1; verified vs the tool)
for k in ("host_tx", "host_rx", "kd", "m7N_rx"):
    LT[k]["cycles"] += 1; LT[k]["natural"] += 1; LT[k]["fixed"] += 1
json.dump(d, open(dst, "w"), indent=1, ensure_ascii=False)
for e in ist: print(e["conn"], e["bits"], e["from_um"], e["regs_um"], e["to_um"])
