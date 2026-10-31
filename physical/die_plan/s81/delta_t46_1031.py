#!/usr/bin/env python3
"""DIE-S81-43 10-31 (COORD 13:03 ruling (1): leaf__t46 one-block fix GO, 2 variants, first to pass wins): one-block plan
fix (METHODOLOGY 12.20) for ot_s81sl_leaf__t46 plan_geom FAIL pin_reg_p90 115.65 / pin_reg_max 214.0 (> 150 hard) and
clock_tap_sinks 1704 (> 1500).

Root cause (CHECKED plan a83e52c0ae4e, intel1 die-s81-43): the N-face strip above the u_ve.u_m / u_ve.u_s hard cores
(core top 1183.68, halo 1188.0; face inset line 1209.6) is 21.6 um deep, and four landed-slot last-station bit-site blocks
sit in it right over the ft2_i pins (x 360.2-596.3): ft4[5] (442-472), ft3[0] (539-564), ft5[6] (565-573),
ft6[6] (582-590).  The 5155-um2 ft2_i ring band could not sit over its own pins and was packed west at x 163-400, so
1105 ft2_i pins are up to 214 um from their ring.  leafdn_i0 (2916 um2) has the same form behind g_ln[15] (band x
1013-1143 vs pins 1135-1264, max 139).  The tap overload: grid tap clk_t44 sits on the ft2 s3 station (380.16, 483.84,
1105 bits) and is also nearest to the ft3 s4 station (380.16, 457.92, 598 bits): 1704 plan sinks.

Variants (both: ft2_i band over its own pins, leafdn_i0 band over its own pins west of the ft7-ft10 last stations,
one explicit tap clk_t59 at the ft3 s4 station; variant a adds clk_t60 at the re-sited ft4 stage):
  a  u_ve.u_m and u_ve.u_s move down 8.64 um (the free gap to the u_vsw / u_vs halos; core tap u_lf.u_ve.u_m.clk
     follows) and the four site blocks are re-sited (RowAllocator, same 1.404 x 0.27 cells on the 2.16 x 0.27 lattice,
     nearest-first around the old station x) in the freed 6.48-um strip between the new halo (1179.36) and the band
     (1185.84); the ft2_i band keeps its inset and depth (variant-B form of delta_cland_band_1031: clamp to the pin
     span).
  b  cores stay; ft4[5] is re-sited west of the pins (x <= 358.5, hop from ft4 s5 254 um) and ft3[0] / ft5[6] / ft6[6]
     east of the pins (x >= 600, hops <= 381 um); ft2_i band [359, 1188, 598, 1209.6] (depth 21.6 forced by the halo).
Nothing else changes (asserted): other types, outline, pins, windows, slots except the 4 moved stages (bit_sites +
the matching regs_um entry), other bands, the other cores and taps.  The landed sidecar band copies are rewritten; the
collector is refreshed afterwards with delta_alltap_coll_1030.py (TYPES_RE = this type).
usage (repo root): delta_t46_1031.py PLAN_IN PLAN_OUT REPORT.json --variant a|b --sidecar SIDECAR_IN SIDECAR_OUT"""
import argparse
import copy
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import taps as TP  # noqa: E402
import plan_geom as PG  # noqa: E402
import compact_plan as CP  # noqa: E402
import delta_cland_band_1031 as D  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402

TN = "ot_s81sl_leaf__t46"
CELL = (1.404, 0.27)
SHIFT = 8.64                        # variant a: core move (gap from the ve halo 833.76 to the vsw/vs halo 825.12)
CORES = ("u_lf.u_ve.u_m", "u_lf.u_ve.u_s")
MOVE = [("ft4", 5), ("ft3", 0), ("ft5", 6), ("ft6", 6)]         # (slot, bit_sites index = regs index - 1)
LEAFDN = [1088.0, 1190.16, 1238.4, 1209.6]                     # g_ln[15] halo top .. inset line; west of ft7[5]
NEW_TAP = (380.16, 457.92)                                      # ft3 s4 station (598 bits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("report")
    ap.add_argument("--variant", choices=("a", "b"), required=True)
    ap.add_argument("--sidecar", nargs=2, required=True)
    a = ap.parse_args()
    text = open(a.plan_in).read()
    raw = json.loads(text); orig = copy.deepcopy(raw)
    t = raw["partition_types"][TN]
    W, H = t["outline_um"]
    ck = t["clock"]; lc = ck["landing_contract"]; bands = lc["bands"]
    P0 = S.Plan(copy.deepcopy(raw), Path(a.plan_in).resolve())
    m0 = PG.type_metrics(P0, TN)
    rep = dict(lane="DIE-S81-43", type=TN, variant=a.variant, plan_in=a.plan_in,
               before={k: m0.get(k) for k in ("pin_reg_p90", "pin_reg_max", "pin_reg_worst", "grid_tap_sinks_max",
                                              "grid_tap_sinks_worst", "clock_reach_max", "r2r_max")})
    # ---- (a) cores down
    if a.variant == "a":
        for hc in t["hard_cores"]:
            if hc["inst"] in CORES:
                hc["origin_um"] = [hc["origin_um"][0], round(hc["origin_um"][1] - SHIFT, 6)]
        for tp in ck["taps"]:
            if tp["name"].startswith(tuple(c + "." for c in CORES)):
                tp["xy"] = [tp["xy"][0], round(tp["xy"][1] - SHIFT, 6)]
        rep["core_shift_um"] = -SHIFT
    blk = [list(o) for o in D.RT.blockages(t)]
    ve_top = max(o[3] for o, hc in zip(D.RT.blockages(t), t["hard_cores"]) if hc["inst"] in CORES)
    # ---- ft2_i band rect
    old2 = list(bands["ft2_i"]["rect_um"]); need2 = bands["ft2_i"]["area_reserve_um2"]
    g2 = D.slot_side(t, "ft2_i")
    if a.variant == "a":
        nr2, _ = D.new_rect(t, "N", g2["win"], old2, "B")
    else:
        nr2 = [359.0, ve_top, 598.0, old2[3]]
    # ---- re-site the 4 station blocks (obstacles: cores, other sites, all bands incl. the new ones)
    slots = {s["name"]: s for s in t["ft_slots"]}
    moving = {(n, j) for n, j in MOVE}
    al_blocks = [tuple(o) for o in blk]
    al_blocks += [tuple(r) for r in ck.get("die_islands_um", [])]
    al_blocks += [tuple(r["rect_um"]) for r in ck.get("reserved_sites_um", []) if r.get("kind") == "die_clock_tree"]
    for bn, b in bands.items():
        r = nr2 if bn == "ft2_i" else (LEAFDN if bn == "leafdn_i0" else b["rect_um"])
        al_blocks.append(tuple(r))
    if a.variant == "a":
        bounds = [(400.0, ve_top, 765.0, nr2[1])] * 4
        targets = [(457.92, ve_top), (552.96, ve_top), (590.0, ve_top), (600.0, ve_top)]
    else:
        top = H - 4.32
        bounds = [(300.0, 1188.0, 358.5, top), (600.0, 1188.0, 765.0, top), (600.0, 1188.0, 765.0, top),
                  (600.0, 1188.0, 765.0, top)]
        targets = [(358.5, 1200.96), (600.0, 1200.96), (640.0, 1200.96), (660.0, 1200.96)]
    rep["moved"] = []
    # all other site blocks are reserved; moved blocks are re-sited one by one (each a reserved obstacle for the next)
    placed = []
    for (n, j), bd, tg in zip(MOVE, bounds, targets):
        al = RowAllocator(bd, blocked=al_blocks, cell_size=CELL, column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
        for s in t["ft_slots"]:
            for jj, st in enumerate(s.get("bit_sites_um") or []):
                if (s["name"], jj) in moving:
                    continue
                for x, y in st:
                    al.reserve_rectangle((x, y, x + CELL[0], y + CELL[1]))
        for st in placed:
            for x, y in st:
                al.reserve_rectangle((x, y, x + CELL[0], y + CELL[1]))
        s = slots[n]; old = s["bit_sites_um"][j]
        q, info = al.allocate(tg, len(old), max_radius_um=400.)
        new = [[round(x - CELL[0] / 2, 6), round(y - CELL[1] / 2, 6)] for x, y in q]
        placed.append(new)
        s["bit_sites_um"][j] = new
        oreg = list(s["regs_um"][j + 1]); s["regs_um"][j + 1] = list(new[0])
        bb = [min(p[0] for p in new), min(p[1] for p in new), max(p[0] for p in new) + CELL[0],
              max(p[1] for p in new) + CELL[1]]
        hops = [round(abs(s["regs_um"][k][0] - s["regs_um"][k + 1][0]) + abs(s["regs_um"][k][1] - s["regs_um"][k + 1][1]), 2)
                for k in (j, j + 1) if k + 1 < len(s["regs_um"])]
        rep["moved"].append(dict(slot=n, stage=j, bits=len(new), reg_old=oreg, reg_new=s["regs_um"][j + 1], rect=bb,
                                 hops_um=hops, max_site_dist_um=round(info["max_distance_um"], 2)))
        assert max(hops) <= 405, (n, hops)
    # ---- bands: ft2_i, leafdn_i0 (+ copies)
    rep["bands"] = []
    for bus, nr in (("ft2_i", nr2), ("leafdn_i0", LEAFDN)):
        b = bands[bus]; old = list(b["rect_um"]); g = D.slot_side(t, bus) if bus != "leafdn_i0" else None
        hits = [o for o in D.obstacles(t, bus) if D._ov(nr, o) and o != old]
        assert not hits, (bus, nr, hits[:4])
        assert nr[0] >= D.MARGIN - 1e-6 and nr[3] <= H - D.MARGIN + 1e-6, (bus, nr)
        narea = (nr[2] - nr[0]) * (nr[3] - nr[1])
        assert narea + 1e-6 >= b["area_reserve_um2"], (bus, narea)
        pins = [(x, y) for nm, bit, _l, x, y, f in PG.type_sites(P0, TN)["pins"] if nm == bus]
        px = (min(p[0] for p in pins), max(p[0] for p in pins))
        nh = D.hop(t, "N", px, nr)
        b["rect_um"] = nr; b["max_pin_to_band_hop_um"] = nh
        nc = 0
        for s in lc.get("collector_local_sources", []):
            if s.get("name") == bus and s.get("band", {}).get("rect_um") == old:
                s["band"]["rect_um"] = nr; s["band"]["max_pin_to_band_hop_um"] = nh; nc += 1
        rep["bands"].append(dict(bus=bus, old=old, new=nr, area=round(narea, 2), need=b["area_reserve_um2"],
                                 pins_x=px, hop_um=nh, copies=nc))
    fin = [(o, bands[o]["rect_um"]) for o in bands]
    for i, (n1, r1) in enumerate(fin):
        for n2, r2 in fin[i + 1:]:
            assert not D._ov(r1, r2), (n1, r1, n2, r2)
    for (n, j), st in zip(MOVE, placed):
        bb = [min(p[0] for p in st), min(p[1] for p in st), max(p[0] for p in st) + CELL[0], max(p[1] for p in st) + CELL[1]]
        for bn, r in fin:
            assert not D._ov(bb, r), (n, bb, bn, r)
        for o in D.RT.blockages(t):
            assert not D._ov(bb, o), (n, bb, o)
    # ---- tap clk_t59 at the ft3 s4 station
    taken = [tuple(p["xy"]) for p in ck["taps"]] + [tuple(p["xy"]) for p in ck["added_taps"]]
    q = S.tap_clear(t, NEW_TAP[0], NEW_TAP[1], taken, strict=True)
    names = [p["name"] for p in ck["added_taps"]]
    nxt = max(int(re.fullmatch(r"clk_t(\d+)", x).group(1)) for x in names) + 1
    ck["added_taps"].append(dict(name=f"clk_t{nxt}", xy=[round(q[0], 4), round(q[1], 4)]))
    rep["tap_added"] = [ck["added_taps"][-1]]
    if a.variant == "a":
        # the re-sited ft4/ft3 stages (1267 bits) and the ft2_i ring reads now share grid tap clk_t13: one more tap
        # at the ft4 stage (variant b keeps them on clk_t36 / the west taps)
        taken.append(tuple(q))
        rx, ry = rep["moved"][0]["reg_new"]
        q = S.tap_clear(t, rx, ry, taken, strict=True)
        ck["added_taps"].append(dict(name=f"clk_t{nxt + 1}", xy=[round(q[0], 4), round(q[1], 4)]))
        rep["tap_added"].append(ck["added_taps"][-1])
    # ---- metrics after
    P = S.Plan(copy.deepcopy(raw), Path(a.plan_in).resolve())
    m1 = PG.type_metrics(P, TN)
    rep["after"] = {k: m1.get(k) for k in rep["before"]}
    rep["verdict"] = [(r["rule"], r["status"], r["value"]) for r in PG.judge(m1, P.name)]
    # ---- nothing else changed
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn != TN:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
    o = orig["partition_types"][TN]
    for k in t:
        if k not in ("clock", "ft_slots", "hard_cores"):
            assert t[k] == o[k], k
    for hc, oh in zip(t["hard_cores"], o["hard_cores"]):
        if hc["inst"] not in CORES or a.variant == "b":
            assert hc == oh, hc["inst"]
    for s, os_ in zip(t["ft_slots"], o["ft_slots"]):
        for j, (st, ost) in enumerate(zip(s.get("bit_sites_um") or [], os_.get("bit_sites_um") or [])):
            if (s["name"], j) not in moving:
                assert st == ost, (s["name"], j)
        x = {k: v for k, v in s.items() if k not in ("bit_sites_um", "regs_um")}
        y = {k: v for k, v in os_.items() if k not in ("bit_sites_um", "regs_um")}
        assert x == y, s["name"]
        for i, (r, orr) in enumerate(zip(s["regs_um"], os_["regs_um"])):
            if (s["name"], i - 1) not in moving:
                assert r == orr, (s["name"], i)
    for k in ck:
        if k not in ("landing_contract", "added_taps", "taps"):
            assert ck[k] == o["clock"][k], k
    for k in lc:
        if k not in ("bands", "collector_local_sources"):
            assert lc[k] == o["clock"]["landing_contract"][k], k
    m = re.search(r'^  "' + re.escape(TN) + r'": ', text, re.M)
    _, j = json.JSONDecoder().raw_decode(text, m.end())
    text = text[:m.end()] + CP._d(t, 2) + text[j:]
    assert json.loads(text) == raw
    open(a.plan_out, "w").write(text)
    # ---- sidecar band copies
    stext = open(a.sidecar[0]).read(); side = json.loads(stext); sorig = copy.deepcopy(side)
    assert json.dumps(side, separators=(",", ":")) + "\n" == stext
    st = side["collector"]["types"][TN]; n = 0
    for r in rep["bands"]:
        b = st["bands"][r["bus"]]; assert b["rect_um"] == r["old"], r["bus"]
        b["rect_um"] = r["new"]; b["max_pin_to_band_hop_um"] = r["hop_um"]; n += 1
        for src in st.get("local_sources", []):
            if src.get("name") == r["bus"] and src.get("band", {}).get("rect_um") == r["old"]:
                src["band"]["rect_um"] = r["new"]; src["band"]["max_pin_to_band_hop_um"] = r["hop_um"]; n += 1
    for tn in side["collector"]["types"]:
        if tn != TN:
            assert side["collector"]["types"][tn] == sorig["collector"]["types"][tn]
    open(a.sidecar[1], "w").write(json.dumps(side, separators=(",", ":")) + "\n")
    rep["sidecar_band_copies"] = n
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("before", "after", "verdict", "moved", "bands", "tap_added")}, indent=None)[:4000])


if __name__ == "__main__":
    main()
