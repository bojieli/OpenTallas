#!/usr/bin/env python3
"""DIE-HBM-28 pre-split of one plan lane (and its NE mirror) into K equal-width parallel lanes of the SAME chain, before a
re-plan event re-routes them (die-local, opt-in, no shared tool).  The parts keep one cycle count via a latency_groups
'bus' entry (<id>_word, lanes lsb-first: part 0 = bits [w-1:0]).  New lane ids <id>b, <id>c, ...; NE mirror <id>bm ...;
buses <id>b_o/_i, slots <id>bx<k> (copies of the original declarations, width w/K; windows are re-made by the event).
usage: lane_presplit.py PLAN_JSON LANE_ID K|W0,W1,...   (explicit part widths, lsb part first)"""
import json, sys, copy
plan, lid = sys.argv[1], sys.argv[2]
WS = [int(x) for x in sys.argv[3].split(",")] if "," in sys.argv[3] else None
K = len(WS) if WS else int(sys.argv[3])
raw = json.load(open(plan))
T = raw["partition_types"]; pt = {p["name"]: p["type"] for p in raw["partitions"]}
lanes = {l["id"]: l for l in raw["lanes"]}; ports = {p["id"]: p for p in raw["ports"]}
rep = []
for base, suf in ((lid, ""), (lid + "m", "m")):
    L = lanes[base]
    w = ports[L["ports"][0]]["width"]
    ws = WS or [w // K] * K
    assert sum(ws) == w, (base, w, ws)
    lo = [sum(ws[:i]) for i in range(K)]
    for i in range(1, K):
        nid = lid + "bcdefg"[i - 1] + suf
        tag = lid + "bcdefg"[i - 1]
        wk = ws[i]
        nports = []
        for q in L["ports"]:
            p = copy.deepcopy(ports[q]); p["id"] = q.replace(base + "_", nid + "_", 1); p["width"] = wk
            for side in ("src", "dst"):
                b = p[side]["bus"]
                nb = b.replace(lid, tag, 1) if b.startswith(lid) else b
                part = p[side]["part"]
                if part in pt:
                    t = T[pt[part]]
                    for d in t.get("buses", []):
                        if d["name"] == b and not any(x["name"] == nb for x in t["buses"]):
                            e = copy.deepcopy(d); e["name"] = nb; e["width"] = wk; t["buses"].append(e)
                    stem = b.rsplit("_", 1)[0]
                    for s in list(t.get("ft_slots", [])):
                        if s["name"] == stem and not any(x["name"] == nb.rsplit("_", 1)[0] for x in t["ft_slots"]):
                            e = copy.deepcopy(s); e["name"] = nb.rsplit("_", 1)[0]; e["width"] = wk
                            e.pop("bit_sites_um", None); e.pop("bit_site_cell_um", None); t["ft_slots"].append(e)
                p[side]["bus"] = nb
            nports.append(p)
        raw["ports"].extend(nports)
        raw["lanes"].append(dict(id=nid, ports=[p["id"] for p in nports],
                                 note=f"DIE-HBM-28: {base} split part {i}/{K} bits [{lo[i]+wk-1}:{lo[i]}]; latency group {lid}{suf}_word"))
        raw["latency"]["lanes"][nid] = dict(raw["latency"]["lanes"][base], param="LAT_" + nid.upper())
        rep.append(nid)
    # shrink the original to part 0
    wk = ws[0]
    for q in L["ports"]:
        ports[q]["width"] = wk
        for side in ("src", "dst"):
            part, b = ports[q][side]["part"], ports[q][side]["bus"]
            if part in pt:
                for d in T[pt[part]].get("buses", []):
                    if d["name"] == b: d["width"] = wk
                for s in T[pt[part]].get("ft_slots", []):
                    if s["name"] == b.rsplit("_", 1)[0]: s["width"] = wk; s.pop("bit_sites_um", None); s.pop("bit_site_cell_um", None)
    L["note"] = L.get("note", "") + f" | DIE-HBM-28: split part 0/{K} bits [{wk-1}:0]; latency group {lid}{suf}_word"
    raw.setdefault("latency_groups", []).append(dict(name=f"{lid}{suf}_word", kind="bus",
        lanes=[base] + [lid + "bcdefg"[i - 1] + suf for i in range(1, K)],
        source=f"{ports[L['ports'][0]]['src']['part']}.{ports[L['ports'][0]]['src']['bus']}",
        note=f"DIE-HBM-28: one as-built bus ({w} b) over {K} lanes {ws}, same cycle (hub face full after V-R1)"))
json.dump(raw, open(plan, "w"), indent=1)
print("split", lid, K, "new lanes", rep)
