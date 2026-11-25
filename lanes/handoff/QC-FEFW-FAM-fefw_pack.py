#!/usr/bin/env python3
"""QC-FEFW-FAM: generic interval packer for FE/FW station channels (VISQC-FEFW-1 form, VIS-QC 11-23).

Per type: every eligible internal_station (bus:, bit_route per_bit, leaf_um, face E/W, leg_order not yet channel) gets a
vertical channel band [lo,hi] (width max(4, 0.1*bits), the width rule of the cl69f5e854 de-stack) in x. Buses whose vertical
spans (pin y .. leaf y) overlap get disjoint x bands; buses with disjoint y spans share a band. Bands stay inside the
pin-x..leaf-x hull (so the Manhattan path length, hence every hop, is unchanged) and prefer to avoid the spine column.
regs_um = istation_channel.sites() at the band centre with the existing station count. Existing channels are fixed obstacles.
usage: fefw_pack.py PLAN.json OUT_ROW.json REPORT.json [--types t1,t2] [--validate TYPE]
"""
import json, sys, math, argparse
KIT_LIMIT = 403.0
SPINE = 311.04; SPINE_HALF = 20.0
GAP = 4.0; YM = 0.0; EDGE = 2.0

def width(bits): return round(max(4.0, 0.1 * bits), 3)

def sites(px, py, lx, ly, direction, col, n):
    pts = [(px, py), (col, py), (col, ly), (lx, ly)]
    if direction != "in": pts = pts[::-1]
    segs = [abs(a[0]-b[0]) + abs(a[1]-b[1]) for a, b in zip(pts, pts[1:])]
    L = sum(segs); out = []
    for k in range(n):
        t = L * (k + 1) / (n + 1)
        for (a, b), d in zip(zip(pts, pts[1:]), segs):
            if t <= d or (a, b) == (pts[-2], pts[-1]):
                f = 0.0 if d == 0 else min(1.0, t / d)
                out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))); break
            t -= d
    return out, L

def items_of(T, ignore_existing=False):
    B = {b["name"]: b for b in T["buses"]}
    fixed, todo, skipped = [], [], []
    for i, e in enumerate(T["internal_stations"]):
        c = e["conn"]
        if not c.startswith("bus:"): skipped.append((c, "not bus")); continue
        b = B.get(c[4:])
        if b is None: skipped.append((c, "no bus")); continue
        if e.get("bit_route") != "per_bit" or "leaf_um" not in e: skipped.append((c, "not per_bit/leaf")); continue
        if b["face"] not in ("E", "W"): skipped.append((c, "face " + b["face"])); continue
        pin = e["from_um"] if b["dir"] == "in" else e["to_um"]
        lx, ly = e["leaf_um"]
        it = dict(idx=i, conn=c, bits=e["bits"], dir=b["dir"], px=pin[0], py=pin[1], lx=lx, ly=ly, n=len(e["regs_um"]),
                  ylo=min(pin[1], ly), yhi=max(pin[1], ly), w=width(e["bits"]))
        if e.get("leg_order") == "channel" and e.get("channel_um") and not ignore_existing:
            it["lo"], it["hi"] = e["channel_um"]; fixed.append(it)
        else: todo.append(it)
    return fixed, todo, skipped

def overlap_y(a, b): return a["yhi"] + YM > b["ylo"] and b["yhi"] + YM > a["ylo"]

def feas(lo, hi, it, placed, gap):
    for p in placed:
        if overlap_y(it, p) and lo < p["hi"] + gap and p["lo"] < hi + gap: return False
    return True

def place(it, placed, W, relax):
    hl = max(EDGE, min(it["px"], it["lx"])); hh = min(W - EDGE, max(it["px"], it["lx"]))
    mid = (it["px"] + it["lx"]) / 2
    best = None
    for gap, spine in ((GAP, True), (GAP, False), (1.0, False), (0.0, False)):
        for x0 in range(int(math.ceil(hl)), int(math.floor(hh - it["w"])) + 1):
            lo, hi = float(x0), round(x0 + it["w"], 3)
            if hi > hh + 1e-9: continue
            if spine and hi > SPINE - SPINE_HALF and lo < SPINE + SPINE_HALF: continue
            if not feas(lo, hi, it, placed, gap): continue
            sc = abs((lo + hi) / 2 - mid)
            if best is None or sc < best[0]: best = (sc, lo, hi, gap, spine)
        if best: return best[1], best[2], dict(gap=best[3], spine_clear=best[4])
    return None

def pack(T, ignore_existing=False):
    W = T["outline_um"][0]
    fixed, todo, skipped = items_of(T, ignore_existing)
    placed = list(fixed); res = {}; unfit = []
    for it in sorted(todo, key=lambda x: (-x["w"], -(x["yhi"] - x["ylo"]), x["conn"])):
        r = place(it, placed, W, False)
        if r is None: unfit.append((it["conn"], "no x band in hull")); continue
        it["lo"], it["hi"] = r[0], r[1]; it["how"] = r[2]; placed.append(it); res[it["conn"]] = it
    return res, fixed, unfit, skipped

def entry_regs(it):
    col = (it["lo"] + it["hi"]) / 2
    pts, L = sites(it["px"], it["py"], it["lx"], it["ly"], it["dir"], col, it["n"])
    return [[round(x, 3), round(y, 3)] for x, y in pts], L

def check(placed_all):
    bad = []
    for i, a in enumerate(placed_all):
        for b in placed_all[i+1:]:
            if overlap_y(a, b) and a["lo"] < b["hi"] and b["lo"] < a["hi"]: bad.append((a["conn"], b["conn"]))
    return bad

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--types"); ap.add_argument("--validate")
    a = ap.parse_args()
    P = json.load(open(a.plan)); pt = P["partition_types"]
    if a.validate:
        T = pt[a.validate]; rep = {}
        fixed, _, _ = items_of(T)[0], None, None
        # formula check: sites() at existing channel centre vs existing regs_um
        mx = 0
        for it in fixed:
            e = T["internal_stations"][it["idx"]]
            regs, L = entry_regs(it)
            d = max(max(abs(r[0]-q[0]), abs(r[1]-q[1])) for r, q in zip(regs, e["regs_um"]))
            mx = max(mx, d); rep.setdefault("formula_dev", {})[it["conn"]] = round(d, 2)
        res, fx, unfit, sk = pack(T, ignore_existing=True)
        allp = list(res.values())
        rep.update(formula_max_dev_um=round(mx, 2), packed=len(res), unfit=unfit, skipped=sk, overlaps=check(allp),
                   existing_overlaps=check(fixed),
                   bands={c: (v["lo"], v["hi"], v["how"]) for c, v in res.items()},
                   existing={i["conn"]: (i["lo"], i["hi"]) for i in fixed})
        hop = {c: round(entry_regs(v)[1] / (v["n"] + 1), 1) for c, v in res.items()}
        rep["max_hop"] = max(hop.values()); rep["hop"] = hop
        json.dump(rep, open(a.report, "w"), indent=1); print(json.dumps({k: v for k, v in rep.items() if k not in ("hop", "formula_dev", "bands", "existing")}, indent=1)); return
    types = a.types.split(",") if a.types else [t for t in pt if t.startswith(("sle_f", "slw_f"))]
    row = {"row": "FEFW-FAM-CHANNEL-FAM", "types": {}}; rep = {}
    for t in types:
        T = pt[t]; res, fixed, unfit, skipped = pack(T)
        ents = []; hopbad = []
        for c, it in sorted(res.items(), key=lambda kv: kv[1]["idx"]):
            e = T["internal_stations"][it["idx"]]
            regs, L = entry_regs(it)
            hop = L / (it["n"] + 1)
            if hop > KIT_LIMIT: hopbad.append((c, round(hop, 1), it["n"]))
            ch = [it["lo"], it["hi"]]
            note = (e.get("note", "") + " | " if e.get("note") else "") + \
                f"VISQC-FEFW-1 11-25 FEFW-FAM: spine de-stack, leg_order channel {ch[0]}-{ch[1]} (was {e.get('leg_order') or 'normal_first'}, regs re-sited on the channel centre)"
            ents.append({"conn": c, "set": {"regs_um": regs, "channel_um": ch, "leg_order": "channel", "note": note}})
        allp = list(res.values()) + fixed
        rep[t] = dict(packed=len(res), fixed=len(fixed), unfit=unfit, skipped=skipped, overlaps=check(allp), hop_over=hopbad)
        if ents: row["types"][t] = ents
    json.dump(row, open(a.out, "w"), indent=1); json.dump(rep, open(a.report, "w"), indent=1)
    for t, r in rep.items(): print(t, "packed", r["packed"], "fixed", r["fixed"], "unfit", r["unfit"], "ovl", len(r["overlaps"]), "hopover", r["hop_over"], "skipped", len(r["skipped"]))
main()
