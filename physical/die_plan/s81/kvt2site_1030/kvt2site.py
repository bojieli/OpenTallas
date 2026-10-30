#!/usr/bin/env python3
"""DIE-S81-34/KVT2-SITE (OWNER 12.20a form ii): kv_leaf__t2 SITE-RULE EXCEPTION packer, current slot (1442.88 x 1226.88).

Exception (declared per type, plan field partition_types.ot_s81sl_kv_leaf__t2.macro_under_ft): SRAM macros may sit
UNDER the type's ft corridors because every macro blocks only M1-M4 (LEF OBS M1/M2/M3/M4, all signal + PG pins on M4 at
the W/E macro edges) while the corridors run on M5/M7 (plan ft_slots[].layers, partition_signal_max M7).  Kept:
  * ft STATIONS j >= 1 (the check.py / face_flops.tcl point L*j/k on the slot route, per bit): station band = per-(slot,j)
    bbox of the bit points +STATION_RES, macros +HALO (10.8) clear of it;
  * station 0 (face flops) + landing bands (clock.landing_contract.bands, +10.8) + clock tap / landing pins / collector
    relays (+21.6) + 43.2 edge band, 10.8 channels (kit_contract MIN_CHANNEL_UM) -- the DIE-S81-32 packer rules unchanged.
Bus-first: the type is y-mirrored so the bottom-up mixed-column packer fills rows nearest the N-face leafdn/leafup
windows first; sites mirrored back and re-checked by the packer's own check() on the unmirrored type.

usage: kvt2site.py OUTDIR"""
import copy, json, os, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import place_sites as PS  # noqa: E402
import mixed  # noqa: E402

WT = PS.WT
sys.path.insert(0, str(WT / "tools/die_plan"))
sys.path.insert(0, str(WT))
import schema as S  # noqa: E402
import gen_phys  # noqa: E402
import check as CK  # noqa: E402

TN = "ot_s81sl_kv_leaf__t2"
PLAN = WT / "physical/die_plan/s81/plan_h2_2249.json"
STATION_RES = 10.8     # station cell reserve around the bit-point bbox (spiral occupancy ~3 um for 1104 b / 240 um)
HALO = PS.HALO
LEF_DIR = "physical/asap7_memory_macros_v2"


def station_bands(P, t):
    pins = defaultdict(dict)
    for bus, bit, _l, x, y, face in gen_phys.type_pins(P, TN):
        pins[bus][bit] = (x, y, face)
    bands = []
    for slot in t["ft_slots"]:
        k = int(slot.get("stations", 1))
        pi, po = pins[slot["name"] + "_i"], pins[slot["name"] + "_o"]
        pts = defaultdict(list)
        for bit in sorted(set(pi) | set(po)):
            ap = pi.get(bit) or po[bit]; bp = po.get(bit) or pi[bit]
            ins = lambda p: {"E": (p[0] - 1, p[1]), "W": (p[0] + 1, p[1]), "N": (p[0], p[1] - 1), "S": (p[0], p[1] + 1)}[p[2]]
            a, b = ins(ap), ins(bp)
            r = CK.zroute(a, b, ap[2], bp[2]); L = CK.plen(r)
            for j in range(1, k):
                pts[j].append(CK.point_at(r, L * j / k))
        for j, v in sorted(pts.items()):
            xs = [p[0] for p in v]; ys = [p[1] for p in v]
            bands.append(dict(slot=slot["name"], j=j, bits=len(v),
                              points_bbox_um=[round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)],
                              rect_um=[round(min(xs) - STATION_RES, 3), round(min(ys) - STATION_RES, 3),
                                       round(max(xs) + STATION_RES, 3), round(max(ys) + STATION_RES, 3)]))
    return bands


def install_exception(bands_by_H):
    orig = PS.keepouts

    def keepouts(t):
        t2 = dict(t); t2["ft_slots"] = []          # corridors are NOT macro keepouts under the exception
        rects, pts = orig(t2)
        H = t["outline_um"][1]
        for b in bands_by_H[round(H, 3)] if t.get("_mirrored") else bands_by_H["real"]:
            r = b["rect_um"]
            rects.append([r[0] - HALO, r[1] - HALO, r[2] + HALO, r[3] + HALO])
        return rects, pts
    PS.keepouts = keepouts


def flip(t):
    t = copy.deepcopy(t)
    W, H = t["outline_um"]

    def fy(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "rect_um" and isinstance(v, list) and len(v) == 4:
                    o[k] = [v[0], H - v[3], v[2], H - v[1]]
                elif k in ("xy", "xy_um", "tap_um", "root", "pin_xy_um") and isinstance(v, list) and len(v) == 2 \
                        and all(isinstance(a, (int, float)) for a in v):
                    o[k] = [v[0], H - v[1]]
                else:
                    fy(v)
        elif isinstance(o, list):
            for v in o:
                fy(v)
    fy(t["clock"]); fy(t.get("reset", {})); fy(t.get("internal_stations", []))
    for b in t["buses"]:
        b["face"] = {"N": "S", "S": "N"}.get(b["face"], b["face"])
    t["_mirrored"] = True
    return t


def lef_layers(path):
    import re
    txt = (WT / path).read_text()
    W, H = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt).groups())
    obs = re.search(r"^\s*OBS(.*?)^\s*END\s*$", txt, re.M | re.S).group(1)
    ol = {}
    lay = None
    for m in re.finditer(r"LAYER\s+(\S+)|RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", obs):
        if m.group(1):
            lay = m.group(1)
        else:
            ol.setdefault(lay, []).append(list(map(float, m.groups()[1:])))
    sig, pg, edge_ok, n = set(), set(), True, 0
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", txt, re.M | re.S):
        isp = re.search(r"USE\s+(POWER|GROUND)", pm.group(2))
        lay = None
        for m in re.finditer(r"LAYER\s+(\S+)\s*;|RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", pm.group(2)):
            if m.group(1):
                lay = m.group(1); (pg if isp else sig).add(lay)
            elif not isp:
                x0, _, x1, _ = map(float, m.groups()[1:]); n += 1
                m4 = [r for r in ol.get(lay, [])]
                # pin must reach outside the same-layer OBS (access from the W/E channel)
                if not any(x0 < r[0] - 1e-6 or x1 > r[2] + 1e-6 for r in m4) and m4:
                    edge_ok = False
    return dict(size=[W, H], obs_layers=sorted(ol), obs_full_cover={k: [min(r[0] for r in v), min(r[1] for r in v),
                max(r[2] for r in v), max(r[3] for r in v)] for k, v in ol.items()},
                signal_pin_layers=sorted(sig), pg_pin_layers=sorted(pg), signal_pin_rects=n,
                all_signal_pins_outside_same_layer_obs=edge_ok)


def main():
    outdir = Path(sys.argv[1]); outdir.mkdir(parents=True, exist_ok=True)
    raw = S.load(PLAN)
    P = S.Plan(raw, None)
    t = raw["partition_types"][TN]
    W, H = t["outline_um"]
    bands = station_bands(P, t)
    mb = [dict(b, rect_um=[b["rect_um"][0], H - b["rect_um"][3], b["rect_um"][2], H - b["rect_um"][1]]) for b in bands]
    install_exception({"real": bands, round(H, 3): mb})
    mixed.install()
    if os.environ.get("COL_XC"):
        PS.COL_XC = float(os.environ["COL_XC"])
    # ---- layer proof
    masters = PS.masters_of(TN)
    proof = {}
    for m, (lef, lib) in sorted(masters.items()):
        proof[m] = dict(lef=lef, **lef_layers(lef))
    top = raw["layer_budget"]["partition_signal_max"] if "layer_budget" in raw else None
    corr = []
    for s in t["ft_slots"]:
        wd = s["in_window_um"][1] - s["in_window_um"][0]
        corr.append(dict(slot=s["name"], faces=s["in_face"] + "->" + s["out_face"], bits=s["width"], layers=s["layers"],
                         window_um=s["in_window_um"], m7_only_track_use=round(s["width"] / (wd / 0.064), 3),
                         m5m7_track_use=round(s["width"] / (wd / 0.048 + wd / 0.064), 3)))
    # ---- pack (bus-first: mirrored)
    tf = flip(t)
    items = []
    lefc = {}
    for i, m in PS.instances(TN):
        lef, lib = masters[m]
        if lef not in lefc:
            wh, pins = PS.lef_info(lef)
            lefc[lef] = (wh, PS.track_offset(pins))
        items.append((i, m, lefc[lef][0]))
    order = os.environ.get("ORDER", "size")
    rank = os.environ.get("RANK", "")
    if rank:
        rk = rank.split(",")
        key = lambda m: next((i for i, r in enumerate(rk) if r in m), len(rk))
        grp = [("kv", [it for it in items if key(it[1]) == g], None) for g in range(len(rk) + 1)]
        grp = [g for g in grp if g[1]]
    else:
        grp = [("kv", items, None)]
    sites, rects, pts, left = PS.place(TN, tf, grp)
    real = []
    for s in sites:
        x, y = s["xy"]; w, h = s["wh"]
        real.append(dict(s, xy=(x, round(H - y - h, 4))))
    bad, ncol = PS.check(TN, t, real)
    rects0, pts0 = PS.keepouts(t)
    PS.render(TN, t, real, rects0, pts0, str(outdir / "kvt2site.png"))
    bw = [b["window_um"] for b in t["buses"] if b["name"] in ("leafdn_i0", "leafup_o0")]

    def dist(s):
        cx = s["xy"][0] + s["wh"][0] / 2; cy = s["xy"][1] + s["wh"][1] / 2
        return min(max(0, lo - cx, cx - hi) + (H - cy) for lo, hi in bw)
    per = defaultdict(list)
    for s in real:
        per[s["module"]].append(dist(s))
    # station-vs-macro (G0C check_ft_macro_sites form, centres) + band clearance
    boxes = [(s["xy"][0], s["xy"][1], s["xy"][0] + s["wh"][0], s["xy"][1] + s["wh"][1]) for s in real]
    band_hits = sum(1 for b in bands for x0, y0, x1, y1 in boxes
                    if x0 < b["rect_um"][2] + HALO and b["rect_um"][0] - HALO < x1 and y0 < b["rect_um"][3] + HALO and b["rect_um"][1] - HALO < y1)
    under = sum(1 for x0, y0, x1, y1 in boxes if any(x0 < s["in_window_um"][1] + HALO and s["in_window_um"][0] - HALO < x1 for s in t["ft_slots"]))
    out_sites = []
    for s in real:
        lef, lib = masters[s["module"]]
        (w, h), (dx, dy) = lefc[lef]
        out_sites.append(dict(inst=s["inst"], module=s["module"], lef=lef, lib=lib,
                              origin_um=[round(s["xy"][0] + dx, 4), round(s["xy"][1] + dy, 4)], outline_um=[w, h],
                              track_offset_um=[dx, dy]))
    res = dict(type=TN, outline_um=[W, H], partition_signal_max=top, placed=len(real), total=len(items),
               unplaced=[list(x[:2]) for x in left], problems=bad, columns=ncol, station_band_overlaps=band_hits,
               macros_under_corridors=under,
               worst_bus_macro_um=round(max(dist(s) for s in real), 1) if real else None,
               worst_by_master={m: round(max(v), 1) for m, v in per.items()},
               mean_by_master={m: round(sum(v) / len(v), 1) for m, v in per.items()},
               masters={m: len(v) for m, v in per.items()},
               layer_proof=dict(macros=proof, corridors=corr), station_bands=bands, sites=out_sites)
    (outdir / "kvt2site.json").write_text(json.dumps(res, indent=1))
    print("RESULT", json.dumps({k: v for k, v in res.items() if k not in ("sites", "station_bands", "layer_proof", "unplaced")}))
    print("UNPLACED", len(left), sorted({u[1] for u in left}))


if __name__ == "__main__":
    main()
