#!/usr/bin/env python3
"""S81 event3 H2FIX delta (DIE-S81-34/H2FIX 2026-10-30, OWNER 12.20a event3 = LP H2 + kv_leaf__t2; GEOM-72/74 02:07
FAIL STRUCTURAL on the H2 dsfd_coll_lane_w/e_safe8_ntf PLACE).  Touches ONLY the two coll lane types
(h2_2249/coll_{w,e}/spec.json + slices/<type>.json) and adds their family to core_lat/families_r13.json; it composes
with the kv_leaf__t2 delta (disjoint files / types).  Asserts the H2 source forms (sha256) and refuses a second run.

Root causes (CHECKED on Codex geom_w/geom.tsv, intel2 codex-s81types-2249, 3_place of 295.92x444.96):
 (A) r2r 518.99 (333 captures > 405) and the 12 "collapsed relay chains" are ONE plan defect: the kit's
     macro_place.tcl binds the sites of one master to its instances in INSTANCE-NAME order (gen_core_kit_legacy:
     "several instances of one master take the listed sites in instance-name order"), while the H2 spec listed the
     256x64 sites replay-first.  Name order puts u_ep.g_fifo_safe (RX FIFO, read by u_sko -> li_d on the N face)
     on the SOUTH rows y 75.8-221.7 and u_ep.g_rb_safe (replay, TX -> gearbox on the S face) on the NORTH rows
     y 287-433 -- the inverse of the spec's own inst/at pairs.  Measured: g_slice select_r/hi_r beside the FIFO at
     (10,86) -> u_sko.l_data at the N face (175,440) 519 um (248 captures); u_sko.i_ready -> FIFO g_address 432
     (41); u_ep.f_tx beside the N replay (191,276) -> u_gb.u_sf.mwd (19,12) 436 (= the 12 collapsed chains).
     Fix (plan, no RTL / cycle change): the spec macro list is re-ordered per master into instance-name order with
     every (inst, at, orient) pair UNCHANGED, so the name-order binding lands each instance on its declared site:
     RX FIFO north beside li_d, replay south beside the gearbox.  The exact 55-SRAM lattice is unchanged.
 (B) clock_reach 374.78: one centre entry cannot reach a 296x445 tile within 220.  Fix (12.2a1 / 12.8b): six
     plan-fixed IN-CORE clock islands (3 per side) at macro-street crossings, node-legal against the 4.32-um kit
     macro halo; the core tree is the S81 family path (core_family_slice.py, family "s81_coll", s81sl_macro
     parameters: macro leaves, macro keep-out, node-legal entry) hung below these islands.  Centre entry kept.
 (C) stage sites: with (A) the TX frame stage (u_ep.f_tx), the replay and the gearbox store sit in one S half and
     the read side (FIFO slices, u_sko) in the N half; the remaining long S->N write path keeps its existing declared
     stages (lr landing 2, RX_STAGES 5, WRL 2).  Per-chain stage estimates are printed (--estimate).

usage: delta_h2fix_coll_1030.py [--estimate]   (run from the repo root; writes in place, refuses a second run)
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S81 = ROOT / "physical/die_plan/s81"
EVENT = "event3-h2fix-1030"
SIDES = ("w", "e")
SRC_SHA = {   # codex/s81-lp-plan-2249@1837506a6 H2 forms
    "h2_2249/coll_w/spec.json": "46e5bdc3032ae2e941d1af5f77009cd26f3c23444843376ec6e84b01cfb9ae67",
    "h2_2249/coll_e/spec.json": "c98af5d4d6b3d5a4d2706d931be6521d937d99f5525b9efb0246cf3f4953056d",
    "h2_2249/coll_w/slices/dsfd_coll_lane_w_safe8_ntf.json": "d2e59d4911ed3865d7a076ace3f83853929ba49b8ac4bb744ed5a7170a31387f",
    "h2_2249/coll_e/slices/dsfd_coll_lane_e_safe8_ntf.json": "4381538fa8ed92616509d028f134145d38742d29c275fd12071f0af1e0fca272",
    "core_lat/families_r13.json": "b6273e98f5b21aa87fe3c2b320591115a48d83eb61f043e418e41a8209137d44",
}
OUTLINE = (295.92, 444.96)
CORE = (4.32, 4.32, 291.6, 440.64)
HALO = 4.32                       # kit MACRO_ROWS_HALO_X/Y and family keepout_halo_um
NODE_W, NODE_H = 1.62, 0.27       # BUFx24 footprint (island driver)
REACH_MAX = 220.0                 # geom_rules CLK_REACH_MAX * CLK_REACH_TOL
R2R_MAX = 405.0
SIZE = {"ot_sram_1r1w2c_256x64_m1": (34.584, 41.352), "ot_sram_1r1w2c_32x64_m1": (31.992, 17.304)}
# six islands: x = centres of the 2nd and 6th vertical macro streets (50.136-61.128, 234.816-245.808),
# y = centres of the horizontal streets 64.824-75.84, 221.736-232.752, 380.616-391.536
ISL_X = (55.632, 240.312)
ISL_Y = (70.332, 227.244, 386.076)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rects(spec):
    out = []
    for m in spec["macros"]:
        w, h = SIZE[m["view"].rsplit("/", 1)[1]]
        x, y = m["at"]
        out.append((x, y, x + w, y + h, m["inst"]))
    return out


def islands():
    return [dict(name=f"ck_isl{i}", xy_um=[x, y]) for i, (y, x) in enumerate((y, x) for y in ISL_Y for x in ISL_X)]


def node_legal(xy, mr):
    x0, y0, x1, y1 = xy[0] - NODE_W / 2, xy[1] - NODE_H / 2, xy[0] + NODE_W / 2, xy[1] + NODE_H / 2
    if not (CORE[0] <= x0 and x1 <= CORE[2] and CORE[1] <= y0 and y1 <= CORE[3]):
        return False, 0.0
    clear = min(max(a - x1, x0 - c, b - y1, y0 - d) for a, b, c, d, _ in mr)   # box separation (>0 = apart)
    return clear >= HALO, clear


def free(x, y, mr):
    return all(not (a - HALO < x < c + HALO and b - HALO < y < d + HALO) for a, b, c, d, _ in mr)


def estimate(spec):
    mr = rects(spec)
    isl = [i["xy_um"] for i in islands()]
    est = {}
    est["islands"] = []
    for i in islands():
        ok, cl = node_legal(i["xy_um"], mr)
        est["islands"].append(dict(i, node_legal=ok, macro_clearance_um=round(cl, 3)))
    # clock reach: every std-cell-legal point of a 0.54-um grid -> nearest island (Manhattan, = geom_rules metric)
    worst, far, n = 0.0, None, 0
    worst1, far1 = 0.0, None
    y = CORE[1]
    while y <= CORE[3]:
        x = CORE[0]
        while x <= CORE[2]:
            if free(x, y, mr):
                n += 1
                d = min(abs(x - a) + abs(y - b) for a, b in isl)
                if d > worst:
                    worst, far = d, (round(x, 2), round(y, 2))
                d1 = abs(x - 147.948) + abs(y - 236.52)
                if d1 > worst1:
                    worst1, far1 = d1, (round(x, 2), round(y, 2))
            x += 0.54
        y += 0.54
    est["clock_reach"] = dict(points=n, single_entry_max=round(worst1, 2), single_entry_far=far1,
                              islands_max=round(worst, 2), islands_far=far, limit=REACH_MAX, ok=worst <= REACH_MAX)
    # r2r read side: FIFO bank b slice regs anywhere in the streets around its two depth macros (box of the pair +
    # halo street) -> u_sko.l_data at the li_d pin of each of its 64 bits (lsb_low, 0.24 pitch from x 157.932,
    # register at the N face band y 440); + the macro Q pin edge itself (typed-memory reach, opt-in in AUTO-GEOM)
    fifo = {}
    for a, b, c, d, inst in mr:
        if "g_fifo_safe" in inst:
            bank = int(inst.split("g_bank?")[1].split("?")[0])
            fifo.setdefault(bank, []).append((a, b, c, d))
    rr = []
    for bank, bx in sorted(fifo.items()):
        x0 = min(r[0] for r in bx) - 11.0; x1 = max(r[2] for r in bx) + 11.0
        y0 = min(r[1] for r in bx) - 11.0
        bits = range(64 * bank, min(64 * bank + 64, 553))
        lid = [157.932 + 0.24 * i for i in bits]
        dmax = max(max(abs(x0 - lx), abs(x1 - lx)) + (440.0 - y0) for lx in lid)
        rr.append(dict(bank=bank, slice_box=[round(x0, 2), round(y0, 2), round(x1, 2)], li_d_x=[round(lid[0], 2), round(lid[-1], 2)],
                       worst_um=round(dmax, 2)))
    est["r2r_read"] = dict(per_bank=rr, worst_um=max(r["worst_um"] for r in rr), limit=R2R_MAX,
                           ok=max(r["worst_um"] for r in rr) <= R2R_MAX)
    # TX stage: replay (south rows) -> u_ep.f_tx -> u_gb.u_sf.mwd beside the gearbox banks (y 21.6-64.8)
    rb = [r for r in mr if "g_rb_safe" in r[4]]
    gb = [r for r in mr if "u_gb.u_sf" in r[4]]
    ski = [r for r in mr if "u_ski" in r[4]]
    span = lambda A, B: max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p in A for q in B)
    corners = lambda R: [(r[0], r[1]) for r in R] + [(r[2], r[3]) for r in R] + [(r[0], r[3]) for r in R] + [(r[2], r[1]) for r in R]
    est["tx_stage"] = dict(replay_y=[min(r[1] for r in rb), max(r[3] for r in rb)], gearbox_y=[min(r[1] for r in gb), max(r[3] for r in gb)],
                           replay_to_gearbox_max_um=round(span(corners(rb), corners(gb)), 2),
                           ski_to_gearbox_max_um=round(span(corners(ski), corners(gb)), 2),
                           note="f_tx is the TX_STAGES register between the endpoint TX mux (replay / u_ski in_data) and "
                                "the gearbox store: one stage splits ski->gearbox into two hops; replay->gearbox alone <= the max")
    return est


def main(argv):
    est_only = "--estimate" in argv
    paths = {k: S81 / k for k in SRC_SHA}
    for s in SIDES:
        sl = json.loads((S81 / f"h2_2249/coll_{s}/slices/dsfd_coll_lane_{s}_safe8_ntf.json").read_text())
        if sl.get("h2fix_event") == EVENT:
            raise SystemExit(f"{EVENT} already applied to coll_{s} (refusing a second run)")
    bad = {k: sha(p) for k, p in paths.items() if sha(p) != SRC_SHA[k]}
    if bad:
        raise SystemExit(f"H2 source forms differ (not codex/s81-lp-plan-2249@1837506a6): {bad}")
    out = {}
    for s in SIDES:
        sp_p = S81 / f"h2_2249/coll_{s}/spec.json"
        sl_p = S81 / f"h2_2249/coll_{s}/slices/dsfd_coll_lane_{s}_safe8_ntf.json"
        spec = json.loads(sp_p.read_text()); sl = json.loads(sl_p.read_text())
        # --- assert old forms
        assert len(spec["macros"]) == 55 and sum(1 for m in spec["macros"] if "256x64" in m["view"]) == 36
        assert [i["name"] for i in sl["islands"]] == ["ck_entry"] and sl["pushdown"]["islands"] == [] \
            and sl["pushdown"]["clock_repeaters"] == [], "H2 slice is not the single-entry form"
        assert sl["islands"][0]["clock_pin"] == {"layer": "M5", "xy_um": [147.948, 236.52]}
        # the defect: name-order binding differs from the declared (inst, at) pairs
        by_master = {}
        for m in spec["macros"]:
            by_master.setdefault(m["view"], []).append(m)
        moved = 0
        for v, ms in by_master.items():
            order = sorted(ms, key=lambda m: m["inst"])
            moved += sum(1 for a, b in zip(ms, order) if a["at"] != b["at"])
        assert moved > 0, "spec macro order already matches name-order binding"
        # --- (A) macro list in instance-name order per master, pairs unchanged
        pairs0 = sorted((m["inst"], tuple(m["at"]), m["orient"], m["view"]) for m in spec["macros"])
        new = []
        for v in by_master:        # master groups keep their first-appearance order (kit file order unchanged)
            new += sorted(by_master[v], key=lambda m: m["inst"])
        spec["macros"] = new
        assert sorted((m["inst"], tuple(m["at"]), m["orient"], m["view"]) for m in new) == pairs0
        spec["macro_bind"] = dict(rule="instance-name order per master (gen_core_kit_legacy macro_place.tcl)",
                                  event=EVENT, moved_instances=moved,
                                  why="H2 listed 256x64 sites replay-first; name order put the RX FIFO south and the "
                                      "replay north (GEOM-72 r2r 519 / relay_collapse 12). Pairs unchanged.")
        spec["structural_change"] = spec["structural_change"] + (" | " + EVENT + ": macro list in name order (FIFO N / "
                                                                 "replay S as declared), 6 in-core clock islands, family s81_coll.")
        # --- (B) in-core islands (12.2a1), plan-fixed coordinates, node-legal against the macro halo
        e = estimate(spec)
        assert all(i["node_legal"] for i in e["islands"]), e["islands"]
        assert "core_islands" not in sl
        sl["core_islands"] = [dict(name=i["name"], xy_um=i["xy_um"], use="core_tree_island",
                                   rect_um=[round(i["xy_um"][0] - 1.08, 3), round(i["xy_um"][1] - 1.08, 3),
                                            round(i["xy_um"][0] + 1.08, 3), round(i["xy_um"][1] + 1.08, 3)],
                                   macro_clearance_um=i["macro_clearance_um"])
                              for i in e["islands"]]
        sl["core_islands_note"] = ("12.2a1/12.8b in-core tree islands (event3 H2FIX): plan-fixed node sites of the core "
                                   "clock tree (centre entry -> these six islands -> CTS-open local trees), built by the "
                                   "S81 family path (core_family_slice.py family s81_coll -> core_tree nodes at these "
                                   "coordinates); node-legal vs the 4.32-um kit macro halo. Not die feedthrough islands "
                                   "(pushdown stays empty: no ft ports)")
        sl["core_tree_family"] = "s81_coll"
        sl["h2fix_event"] = EVENT
        sl["event"] = sl["event"] + " | " + EVENT
        if not est_only:
            sp_p.write_text(json.dumps(spec, indent=1) + "\n")
            sl_p.write_text(json.dumps(sl, indent=1) + "\n")
        out[s] = e
    fam_p = S81 / "core_lat/families_r13.json"
    fam = json.loads(fam_p.read_text())
    assert not any("dsfd_coll_lane" in m for f in fam["families"] for m in f["members"])
    base = next(f for f in fam["families"] if f["name"] == "s81sl_macro")
    nf = {k: v for k, v in base.items() if k not in ("members", "macro_keepout", "why")}
    nf.update(name="s81_coll", members=["dsfd_coll_lane_w_safe8_ntf", "dsfd_coll_lane_e_safe8_ntf"],
              macro_keepout={"dsfd_coll_lane_w_safe8_ntf": True, "dsfd_coll_lane_e_safe8_ntf": True},
              islands_xy=[i["xy_um"] for i in islands()],
              why=f"{EVENT} (GEOM-72 02:07 clock_reach 374.78): 55-SRAM H2 coll lanes; s81sl_macro parameters (macro leaves, "
                  "kit halo 4.32 node keep-out, node-legal entry) with the six plan-fixed islands of the slice; "
                  "W and E share one placement (GEOM-72: geom.tsv byte-identical)")
    fam["families"].append(nf)
    if not est_only:
        fam_p.write_text(json.dumps(fam, indent=1) + "\n")
    if not est_only:
        (S81 / "delta_h2fix_coll_1030.json").write_text(json.dumps(dict(event=EVENT, source="codex/s81-lp-plan-2249@1837506a6",
            src_sha256=SRC_SHA, w_equals_e=out["w"] == out["e"], estimate=out["w"],
            status="PLAN ESTIMATE (geometry only); PLACE/AUTO-GEOM evidence reported separately"), indent=1) + "\n")
    print(json.dumps(out["w"], indent=1))
    print("E estimate identical to W:", out["w"] == out["e"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
