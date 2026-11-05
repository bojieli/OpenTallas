#!/usr/bin/env python3
"""DIE-HBM-66 d44v part 13: outline event for GRT-0116 rows (COORD 19:1x (3), 19:3x stdcell reading). mk_p13.py PLAN_DIR (plain die_plan.json, clock_entries.json)
q3_edge (M3 126.8%, total congestion 2.16M, macros 70% of area): +60.48 um on W, 216 -> 276.48. E face, clock pin and tap keep die position; W pins follow the new W face, macros centre (+30.24).
dma_back (M2 114%, M3 116%, macros 59%): +60.48 um on local E, 239.976 -> 300.456. Second macro column +30.24. __q0 copies keep origin and every pin. __q1 copies (MY, local E faces u_smw_Q__q1 at 4.32 um)
keep their die W edge, so all their pins and the tap move +60.48 um in die x. hcol_h0_rb is out: real room +7.56 x +1.08 um, 0.62 std, no GRT overflow."""
import json, sys, gzip
from pathlib import Path
pd = Path(sys.argv[1])
def rd(f):
    p = pd / f
    return json.loads(p.read_text()) if p.exists() else json.loads(gzip.decompress((pd / (f + ".gz")).read_bytes()))
D = json.loads((pd / "die_plan.json").read_text()); T = D["partition_types"]
ev = dict(schema="opentallas.hbm_plan_event.part13", rows={})
Q = "ot_hfd_coll_q3_edge_core"; QF = "cores/ot_hfd_coll_q3_edge_core__216x1054.08__r15_relot__codex_g21__centry"; QG = 60.48; QW = 276.48
B = "ot_hgi_dma_back_static_vp4_banks_cp"; BF = "cores/ot_hgi_dma_back_static_vp4_banks_cp__239.976x275.4__c25b__centry"; BG = 60.48; BW = 300.456
QN = "cores/ot_hfd_coll_q3_edge_core__276.48x1054.08__r15_relot__codex_g21__centry__p13"; BN = "cores/ot_hgi_dma_back_static_vp4_banks_cp__300.456x275.4__c25b__centry__p13"
P = rd(QF + ".json"); w = 0
for p in P:
    if p["x"] < 2.0: w += 1
    else: p["x"] = round(p["x"] + QG, 3)
(pd / (QN + ".json")).write_text(json.dumps(P)); assert w == 3681
P2 = rd(BF + ".json"); assert not [p for p in P2 if p["x"] > 238 and p["y"] > 1]
(pd / (BN + ".json")).write_text(json.dumps(P2))
def box(c): x, y = c["origin_um"]; w, h = c["outline_um"]; return x, y, x + w, y + h
def hits(tn, inst, b):
    v = T[tn]; o = []; a0, b0, a1, b1 = b
    for key in ("hard_cores", "contents"):
        for g in v.get(key, []):
            if g.get("inst") == inst or "origin_um" not in g or "outline_um" not in g or str(g.get("note", "")).startswith("as-built"): continue
            x, y = g["origin_um"]; w, h = g["outline_um"]
            if x < a1 and x + w > a0 and y < b1 and y + h > b0: o.append([key, g.get("inst")])
    for s in v.get("ft_slots", []):
        for x, y in s.get("regs_um") or []:
            if a0 <= x <= a1 and b0 <= y <= b1: o.append(["reg", s["name"]])
        cw, ch = s.get("bit_site_cell_um") or [0, 0]
        for st in s.get("bit_sites_um") or []:
            k = sum(1 for x, y in st if x < a1 and x + cw > a0 and y < b1 and y + ch > b0)
            if k: o.append(["bit", s["name"], k])
    for c in v.get("channels", []):
        r = c["rect_um"]
        if r[0] < a1 and r[2] > a0 and r[1] < b1 and r[3] > b0: o.append(["channel", r])
    return o
n = dict(q=0, b0=0, b1=0); H = {}
for tn in ("q_hub_nw", "q_hub_ne"):
    v = T[tn]
    for c in v["hard_cores"]:
        if c.get("module") == Q:
            c["origin_um"] = [round(c["origin_um"][0] - QG, 3), c["origin_um"][1]]; c["outline_um"] = [QW, 1054.08]; c["pins_file"] = QN + ".json"; n["q"] += 1
            H[tn + "/" + c["inst"]] = hits(tn, c["inst"], box(c))
        elif c.get("module") == B:
            assert c["pins_file"] == BF + ".json"
            c["outline_um"] = [BW, 275.4]; c["pins_file"] = BN + ".json"
            if c.get("orient") == "MY":
                n["b1"] += 1
                tap = [t for t in v["clock"]["taps"] if t["name"] == c["inst"]]; assert len(tap) == 1
                tap[0]["xy"] = [round(tap[0]["xy"][0] + BG, 3), tap[0]["xy"][1]]
                tap[0]["note"] = (tap[0].get("note") or "") + " | d44v part 13: moves with the MY copy, +60.48 um"
            else: n["b0"] += 1
            H[tn + "/" + c["inst"]] = hits(tn, c["inst"], box(c))
assert n == dict(q=1, b0=2, b1=2), n
cm = rd("core_macros.json"); r = cm["cores"][Q]; r["outline_um"] = [QW, 1054.08]
for m in r["macros"]: a = m["rect_um"]; m["rect_um"] = [round(a[0] + 30.24, 3), a[1], round(a[2] + 30.24, 3), a[3]]
r["basis"] = "DIE-HBM-66 part 13: +60.48 um on W, macros centred, same 12 macros; " + r.get("basis", "")
r = cm["cores"][B]; r["outline_um"] = [BW, 275.4]
for m in r["macros"]:
    a = m["rect_um"]
    if a[0] > 120: m["rect_um"] = [round(a[0] + 30.24, 3), a[1], round(a[2] + 30.24, 3), a[3]]
r["basis"] = "DIE-HBM-66 part 13: +60.48 um on local E, second column +30.24, same 10 macros; " + r.get("basis", "")
(pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
ce = json.loads((pd / "clock_entries.json").read_text()); e = ce["q_hub_nw"]["u_hb_coll_Q_edge"]
e["xy_um"] = [round(e["xy_um"][0] + QG, 3), e["xy_um"][1]]; a = e["island_um"]; e["island_um"] = [round(a[0] + QG, 3), a[1], round(a[2] + QG, 3), a[3]]
e["source"] += " | d44v part 13: +60.48 um local, die position kept"
(pd / "clock_entries.json").write_text(json.dumps(ce, indent=1) + "\n")
cr = rd("core_clock_regions.json"); m = cr["modules"][Q]; m["outline_um"] = [QW, 1054.08]
for g in m.get("regional_entries", []):
    g["xy_um"] = [round(g["xy_um"][0] + QG, 3), g["xy_um"][1]]; a = g["region_um"]; g["region_um"] = [a[0], a[1], round(a[2] + QG, 3), a[3]]
m = cr["modules"].get(B, {})
if m: m["outline_um"] = [BW, 275.4]
for g in m.get("regional_entries", []):
    a = g["region_um"]
    if a[2] >= 239.9: g["region_um"] = [a[0], a[1], round(a[2] + BG, 3), a[3]]
(pd / "core_clock_regions.json").write_text(json.dumps(cr, indent=1) + "\n")
(pd / "die_plan.json").write_text(json.dumps(D, indent=1) + "\n")
ev["rows"] = {Q: dict(outline_um=[[216.0, 1054.08], [QW, 1054.08]], grow="W", pins_file=QN + ".json", std_util=[0.30, 0.23], cycles=0), B: dict(outline_um=[[239.976, 275.4], [BW, 275.4]], grow="local E", pins_file=BN + ".json", q1_die_shift_um=BG, std_util=[0.32, 0.23], cycles=0)}
ev["slot_hits"] = H; (pd / "part13_event.json").write_text(json.dumps(ev, indent=1) + "\n"); print(json.dumps(H)[:1500])
