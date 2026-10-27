"""CLOCK-KV hm_r26q3 (COORD 10-27 KV-PLAN-DELTA): hm_r26q2 1d257518 -> hm_r26q3, plan pin views only, no cycle/port change.
(a) D-KV-STRAP-FORM: kv3_head_eighth_e1 / e5 strap_bsel[0..1] y 216.000 (edge form) -> 215.904 (centre form = every other
    N-face pin of the KV pin views).  x / layer unchanged.  New files cores/kv3_head_eighth_{e1,e5}_pins_r26q3.json; the
    hard_cores[] entries of those modules are repointed.  Other strap_* pins (e0/e2/e6 W-face M4 strap_bsel, e2-on-e6/e6
    N strap_hid) are alone on their face (one form) and stay byte-identical.
(b) D-KV-ISLAND-ROWS: snap every island_ft arc rect (and its cells) onto the kit std row/site grid in every view frame.
    Audit result: every rect is already on the grid in R0/MX/MY/R180 -> 0 moves (the snap is the identity; asserted).
(c) D-KV-FT-SLOTS-GRAFT (COORD 11:03 ruling on KV-PLAN-EVAL e2be676e45): partition_types[*].ft_slots of the Codex event
    codex/kv-clock-1027@3cb5395c6 (plan f1daa8ad) + the 130 latency.lanes rows they change (+210 cycles, stations only).
    kv3_hub_Ei: event station counts kept, its event sites (regs_um / bit_sites_um / bit_site_cell_um) DROPPED (ft_corridor
    re-site = separate tracked item).  NOT taken: event hard_cores (pv_join/ectlk_q1/q2/kvs_ctl pin files + pv_join
    outline), clock, reset, PG, SD contents, kv3_pv_v12 internal_stations move.  Asserted: slot name/faces/width equal,
    hard_cores / outlines / lanes / ports byte-identical to q2."""
import json, sys, hashlib
pd = sys.argv[1]
INSET, ROW, SITE = 4.32, 0.27, 0.054
P = json.load(open(f"{pd}/hm_r26q2.json"))
# (a)
rep = {}
for mod in ("kv3_head_eighth_e1", "kv3_head_eighth_e5"):
    src = f"cores/{mod}_pins_r26.json"
    d = json.load(open(f"{pd}/{src}"))
    w = h = 216.0
    n = 0
    for p in d["pins"]:
        if p["name"].startswith("strap_bsel["):
            assert p["layer"] == "M5" and abs(p["y"] - h) < 1e-9, p
            p["y"] = round(h - 0.096, 4); n += 1
    assert n == 2
    d["source"] += (" | CLOCK-KV hm_r26q3 10-27 D-KV-STRAP-FORM: strap_bsel[0..1] y 216.000 (edge form) -> 215.904 "
                    "(centre form, as every other N-face pin); x/layer unchanged")
    dst = f"cores/{mod}_pins_r26q3.json"
    open(f"{pd}/{dst}", "w").write(json.dumps(d, indent=1) + "\n")
    rep[src] = dst
nrep = 0
for t in P["partition_types"].values():
    for hc in t.get("hard_cores", []):
        if hc.get("pins_file") in rep:
            hc["pins_file"] = rep[hc["pins_file"]]; nrep += 1
# (c) ft_slots graft
EV = json.load(open(sys.argv[2]))
assert hashlib.sha256(open(sys.argv[2], "rb").read()).hexdigest().startswith("f1daa8ad")
SITE_KEYS = ("regs_um", "bit_sites_um", "bit_site_cell_um")
before = json.dumps({tn: (t.get("hard_cores"), t.get("outline_um")) for tn, t in P["partition_types"].items()}, sort_keys=True)
ns = nt = dst_ = 0
for tn, t in P["partition_types"].items():
    a, b = t.get("ft_slots"), EV["partition_types"][tn].get("ft_slots")
    if a == b:
        continue
    assert len(a) == len(b), tn
    new = []
    for x, y in zip(a, b):
        for k in ("name", "in_face", "out_face", "width"):
            assert x.get(k) == y.get(k), (tn, k)
        assert set(y) - set(x) <= set(SITE_KEYS) and all(x[k] == y[k] for k in x if k not in SITE_KEYS + ("stations",)), (tn, x["name"])
        z = dict(y)
        if tn == "kv3_hub_Ei":
            for k in SITE_KEYS:
                z.pop(k, None)
        dst_ += z["stations"] - x["stations"]
        ns += z != x
        new.append(z)
    t["ft_slots"] = new; nt += 1
la, lb = P["latency"]["lanes"], EV["latency"]["lanes"]
assert set(la) == set(lb)
nl = cyc = 0
for k in la:
    if la[k] != lb[k]:
        assert {f for f in set(la[k]) | set(lb[k]) if la[k].get(f) != lb[k].get(f)} <= {"stations", "natural", "cycles"}, k
        cyc += lb[k]["cycles"] - la[k]["cycles"]; la[k] = lb[k]; nl += 1
assert P["lanes"] == EV["lanes"] and P["ports"] == EV["ports"]
assert before == json.dumps({tn: (t.get("hard_cores"), t.get("outline_um")) for tn, t in P["partition_types"].items()}, sort_keys=True)
print(f"ft_slots graft: {nt} types, {ns} slots changed, station delta {dst_:+d}; latency lanes {nl}, cycles {cyc:+d}; hub_Ei sites dropped")
# (b) snap audit
def snap(v, g, o):
    return round(o + round((v - o) / g) * g, 4)
mv, arcs = 0.0, 0
files = {hc["pins_file"]: hc for t in P["partition_types"].values() for hc in t.get("hard_cores", []) if hc.get("pins_file")}
for pf, hc in sorted(files.items()):
    d = json.load(open(f"{pd}/{pf}"))
    w, h = hc["outline_um"]
    for a in (d.get("island_ft") or {}).get("arcs", []):
        arcs += 1
        x0, y0, x1, y1 = a["rect_um"]
        for (xa, ya) in ((x0, y0), (w - x1, h - y1)):          # R0 and R180 images cover MX / MY
            mv = max(mv, abs(snap(xa, SITE, INSET) - xa), abs(snap(ya, ROW, INSET) - ya))
assert mv < 1e-6, f"island rect off grid by {mv}: write the snap"
P["note"] = (P.get("note", "") + " | hm_r26q3 (CLOCK-KV 10-27): D-KV-STRAP-FORM e1/e5 strap_bsel centre form; "
             "D-KV-ISLAND-ROWS island_ft rects audited on the kit row/site grid in all 4 images (0 moves); "
             "D-KV-FT-SLOTS-GRAFT event 3cb5395c6 ft_slots + latency (+210 cycles/130 lanes), hub_Ei sites dropped")
open(f"{pd}/hm_r26q3.json", "w").write(json.dumps(P, indent=1) + "\n")
print(f"strap files {rep}; repointed {nrep} hard_core entries; island arcs audited {arcs}, max snap move {mv:.4f} um")
