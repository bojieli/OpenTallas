#!/usr/bin/env python3
"""S81 hierarchy contract v16 -> v17 (one-shot, idempotent).  Folds the die lead's 2026-10-13 evening decisions:

  capture  sp_capture slot made consistent with its cluster kit (gate replay main 0e0c2e958: slot_fit mismatch on outline,
           ports, layers, clock entry): outline 1728 x 561.6 (the kit's lattice outline; the hub column is 1,728 wide),
           ports + ckv / rsv (S, M5), layer rule `cluster` (PG M7, strap M8, signals <= M6), clock entry N / M5,
           clock level early_tap with the MEASURED insertion as target once the boundary spread is <= 80 ps
  field    generator plan v17 (--pin-align --xb-rgap-first --fwd-negcap): q-bank pins on the q element pins, return-tree
           node pins in fixed slots, x relay site beside the slot station, station xai / xbi at the E end, forwarded-lane
           ends on the falling forwarded edge
  relays   dsfd_rly_283_EW / dsfd_rly_266_EW kits (x512 each)
  SU       the tile bill does not fit sp_su_s (21.151 mm2 in 18.942): decision record + the SU owner's authorised route
  timing   c6p STA by path class: where the die timing gate stands

Usage: contract_v17.py [--check]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CON = ROOT / "results/arch/hier_contract_1011/s81.json"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    c = json.loads(CON.read_text())
    if c["version"] >= 17:
        print("already v%d" % c["version"]); return 0
    assert c["version"] == 16, c["version"]
    by = {s["name"]: s for s in c["slots"]}

    # ---- capture
    cp = by["sp_capture"]
    assert (cp["outline"]["w"], cp["outline"]["h"]) == (1727.976, 561.6), cp["outline"]
    cp["outline"] = {"w": 1728.0, "h": 561.6}
    cp["clock_entry"] = {"pin": "ck", "face": "N", "layer": "M5"}
    cp.update(layer_rule="cluster", pg_layer="M7", strap_layer="M8", signal_max_layer="M6", version=17)
    for k in ("view_layers", "view_cap", "view_status", "layer_cap"):
        cp.pop(k, None)
    have = {p["name"].split("[")[0] for p in cp["pins"]}
    for n, off in (("ckv", 864.0), ("rsv", 866.16)):
        if n not in have:
            cp["pins"].append({"name": n, "face": "S", "layer": "M5", "offset": off, "width": 0.024})
    cp["clock_level"] = {
        "level": "early_tap", "hop_skew_ps": 150.0, "measured_tt_boundary_mean_ps": 1029.0, "measured_tt_spread_ps": 226.2,
        "source": "results/rtl/ref_tile/s81sp_capc_cl/gate_replay_1013_pm (pre-route --cts, spine ck[0] 2,102 buffers / 889 sinks)",
        "rule": "die clock delivery: the die delivers ck at phi - R; R > 300 ps = an earlier trunk tap and SKEW 150 on the slab's "
                "hops (budget 623.3 ps).  A spread above 80 ps is a tile defect and is NOT compensated by the die.",
        "owed_by_cluster": "boundary spread 226 -> <= 80 ps and an insertion.json with the routed view; then target_insertion_ps := "
                           "the measured boundary mean (+-100).  Until then the slot keeps 250 and the kit does not fit."}
    cp["notes"] = cp.get("notes", "") + (
        " v17: slot = the kit's 1728 x 561.6 (0.024 um wider than the generated slab frame: the hub column is 1,728 wide, the "
        "column's neighbours are routing corridors); ckv / rsv are slot pins (S, M5); cluster layers (PG M7 pins, die strap M8, "
        "signals <= M6: the kit routed M2-M7 and must cap signals at M6); clock entry N / M5.")
    cp["pin_request"]["status"] = ("OPEN in the generator (v17): f_gather / t_vm are still one centred group each; the 8-bundle "
                                   "split at the g2 / x column centres + ckv / rsv die pins are owed before the cluster binds")

    # ---- queued requests of 2026-10-13 (coordinator 18:10: ONE revision a day)
    # capture (s81-spwfc 17:58): no cluster tree; one clock entry pin per child, every R <= 300 ps = one clock level
    cp.pop("clock_level", None)
    cp["pins"] = [p_ for p_ in cp["pins"] if p_["name"].split("[")[0] not in ("ck", "ckv", "t_cd")]
    g2x = (189.0, 361.8, 534.6, 707.4, 1009.8, 1182.6, 1355.4, 1528.2)
    cp["pins"] += [{"name": f"ck_g[{i}]", "face": "N", "layer": "M5", "offset": x_, "width": 0.024} for i, x_ in enumerate(g2x)]
    cp["pins"] += [{"name": f"ck_x[{i}]", "face": "N", "layer": "M5", "offset": x_ + 2.16, "width": 0.024} for i, x_ in enumerate(g2x)]
    cp["pins"] += [{"name": f"ck_s[{i}]", "face": "N", "layer": "M5", "offset": x_, "width": 0.024}
                   for i, x_ in enumerate((470.0, 576.0, 681.0, 787.0, 1013.0, 1118.0, 1224.0, 1329.0, 865.0))]
    cp["pins"] += [{"name": "ck_c", "face": "N", "layer": "M5", "offset": 852.0, "width": 0.024},
                   {"name": "ckv_r", "face": "N", "layer": "M5", "offset": 925.0, "width": 0.024},
                   {"name": "t_cd[11:0]", "face": "N", "layer": "M5", "offset": 915.0, "width": 0.552},
                   {"name": "ckv_d", "face": "S", "layer": "M5", "offset": 850.0, "width": 0.024}]
    cp["pins"] += [{"name": f"ckv_x[{i}]", "face": "S", "layer": "M5", "offset": x_, "width": 0.024} for i, x_ in enumerate(g2x)]
    cp["clock_entry"] = {"pins": "ck_g[7:0], ck_x[7:0], ck_c, ck_s[8:0], ckv_r (N, M5); ckv_x[7:0], ckv_d (S, M5)",
                         "delivery": "the die delivers each pin at phi - R of its child: g2 208, x 269, ctl 90, relays 32-62 ps (TT, routed): one clock level"}
    cp["target_insertion_ps"] = 250.0
    cp["notes"] += (" v17 (17:58 request): the cluster has NO clock tree (the one-pin spine measured 1,029 ps / spread 226 ps): one clock "
                    "entry pin per child; t_cd leaves from a dsfd_rly_15_SN stage at x ~915 (+1 serial cycle on the DONE word, once a field "
                    "phase); g2 row y 336.96, relay row y 519.552, dsfd_capt_cd at (842.4, 86.4).")
    for n_, h_ in (("sp_gather", None), ("sp_wfc", 328.32)):
        s_ = by[n_]
        s_["outline"] = {"w": 1728.0, "h": h_ or s_["outline"]["h"]}
        s_.update(layer_rule="cluster", pg_layer="M7", strap_layer="M8", signal_max_layer="M6", version=17)
        for k in ("view_layers", "view_cap", "view_status", "layer_cap"):
            s_.pop(k, None)
        s_["notes"] = s_.get("notes", "") + " v17: hub cluster over M5 leaves: 8.64-um lattice outline, signals <= M6, PG M7 pins, strap M8."
    by["sp_wfc"]["pin_request"] = {
        "E face by tile": "y 216..324 f_lid f_liv t_lir t_lod t_lov f_lor (dsfd_wfc_lnk_e); y 43..216 every other die pin (dsfd_wfc_vmx_p), "
                          "t_ks / f_kd moved under y 216, t_hep[35:0] / t_ft[3:0] in the vmx_p range",
        "width": "full slot width kept (the 1,123.2-um option is not taken in v17: the slab stack and its lanes stay)",
        "status": "OPEN in the generator"}
    # HC column roots: crooty_y -> 11 x ot_s81_hc_cryys (s81hc 17:50)
    out = []
    for s_ in c["slots"]:
        if s_["name"] in ("sp_hc_s/crooty_c0/y", "sp_hc_s/crooty_c2/y"):
            base, col = s_["origin"], s_["name"].split("/")[1]
            for k in range(11):
                r = json.loads(json.dumps(s_))
                r.update(name=f"sp_hc_s/{col}/ys{k}", cell="ot_s81_hc_cryys", outline={"w": 32.4, "h": 300.24}, version=17,
                         origin={"x": round(base["x"] + 32.4 * k, 3), "y": base["y"], "orient": "R0"}, layer_cap="M5")
                r.pop("layer_cap_grant", None); r.pop("pins", None)
                r["notes"] = ("v17: slice k of the y tile (11 x 32.4 = 356.4 in the 369.36-um rectangle, 12.96 um spare at the E end); "
                              "y_s / p_y[256 k +: 256] N / S at the same x (M5 / M3); own sk / srs / yacc / p_req pins and clock root; "
                              "p_flt from slice 0 only; insertion 260 ps, spread 23 ps (pre-route)")
                out.append(r)
            continue
        out.append(s_)
    c["slots"] = out
    # collective lane slices: hardened clusters of the seven closed M5 leaves (s81 parents 18:45)
    for i, (x_, y_) in enumerate(((604.8, 1017.36), (1058.4, 1017.36), (604.8, 1406.16), (1058.4, 1406.16))):
        s_ = by[f"sp_collective/ce_s{i}"]
        s_.update(outline={"w": 432.0, "h": 345.6}, origin={"x": x_, "y": y_, "orient": "R0"}, layer_rule="cluster", pg_layer="M7",
                  strap_layer="M8", signal_max_layer="M6", assembly="cluster", version=17,
                  clock_level={"level": "early_tap", "R_tt_ps": 700.0, "hop_skew_ps": 150.0, "child_arrival_spread_ps": 24.7})
        s_["notes"] = s_.get("notes", "") + (" v17: 302.4 x 341.28 flat -> 432.0 x 345.6 cluster (2 x 2 block re-pitched to 453.6 / 388.8 inside "
                                             "sp_collective; the collective owner's sub_layout must confirm the neighbours); pins N q_* / W xl_* / E pt_*, tx_*, cr_* / S bw_*.")
    c["v17_queue"] = {
        "taken": ["capture per-child clock pins + cluster rule", "gather / wfc cluster rule and 1728.0 (wfc 328.32) outlines",
                  "crooty_y -> 11 x ot_s81_hc_cryys", "ce_s0..3 432.0 x 345.6 clusters", "dsfd_rly_283_EW 23.76 x 30.24"],
        "bf_tiles_direct": "views physical/s81_die_views/bf_compact199 + compose_1013 are on main: rows dsfd_bf_col (450.144 x 198.72, x1024, "
                           "R 499-681 ps = early tap) and dsfd_bf_front (100.224 x 198.72, x512, R 237-307) with two 1.188-um seams fold into "
                           "the FRAME generator (--bf-hier-compact) in v18: the v17 GEN still places the one-piece dsfd_bf frame",
        "bgq28_NOT_TAKEN": "367.2 x 725.76 x16 (4 x 4 in sp_vm) needs sp_vm +414.72 um N (4 x 103.68); the hub column has 2.2 um left "
                           "(host top 22,746.9 of 22,749.1).  The +21.6-um W strap column fits (4 x 367.2 = 1,468.8 <= 1,520.064).  Height comes "
                           "only with the v18 column move below.",
        "hub_column_v18": "the only free length is BELOW sp_su_s: its S edge 3,369.6 can go to 2,073.6 (1,296 um, above the selector band "
                          "at y 1,464-1,786) if the S strip / tier channel 0 crossing at x 13.78-15.67 mm stays legal (GEN trial owed). "
                          "Budget of those 1,296 um: VM +414.72 (bgq28) leaves 881.28 um = +1.666 mm2 of SU slab",
        "su_what_the_floorplan_gives": "bill 21.151 mm2, slab 18.942.  Slab growth in the column: at most +2.449 mm2 (1,296 x 1,890), +1.666 "
                                       "with the bgq28 height = 20.608 mm2: still under the bill (fill 1.026).  At fill 0.80 the bill needs "
                                       "26.44 mm2 (+7.50): the rest (5.05-5.83 mm2) exists only as wings of the slab in the free S band "
                                       "(x 11.39-21.63 mm, y 1.81-3.05 mm: ~10 mm2 beside the footprint), 2-10 relay stages from the SU "
                                       "lanes, unpriced.  So: slab growth alone does NOT close SU; growth + the pin-tile re-shape (-0.94) "
                                       "gives 20.21 in 20.61-21.39 (fill 0.94-0.98, no channels): not buildable either.  The die lead "
                                       "takes growth FIRST (v18 GEN: S growth + wings for the swe rows) and keeps the util-0.65 re-routes "
                                       "(-4.14 mm2) as the fallback if the wing lanes price above 5 % of the SU path"}

    # ---- field plan v17
    c["field_plan_v17"] = {
        "options": "s81_layer1_v17.opts = v16 + --pin-align --xb-rgap-first --fwd-negcap, --rly-face-reach 450 -> 400",
        "qbank": "dsfd_qbank_S / _N element-side pins (o_x0, o_x1, o_cfg, o_go / e_r0, e_r1, e_st) at the EXACT x of the q "
                 "element pin of the same bit (M5, exact rectangles); the bank stands under the extent of its pins "
                 "(S bank 213.84 -> 225.07 from the element origin)",
        "node": "dsfd_node_*: fixed slots on the N / S faces (child o <-> parent a / b at w/2 - 12, fault chain fo <-> fi at "
                "w/2, own o at w/2 + 12): the abutted stack is bit-aligned",
        "x_relay_site": "right lane cfg row: slot station | x relay site (25.92) | pair sequencer | ROM 0..6 (was station | "
                        "sequencer | site | ROMs): the x relays stand 38 um nearer the next station and the left bank; the "
                        "station takes xbi / xai at the E end of its S face",
        "sstn_relay": "a station port whose one load is a column relay within 30 um of its N face takes the relay's pin x and pitch",
        "link_end": "hend face with one port toward stations: on the stations' pin group; un-split UCIe end stations 10 um farther out",
        "fwd_negcap": "dsfd_cfifo.xd and the m2l / r2l end relays' di<j> are captured on the FALLING forwarded-clock edge "
                      "(half-cycle hop as station -> station; the posedge capture coincided with the station's launch: FF hold "
                      "-94..-206 ps).  cfifo: the FIFO write is half a cycle after the pin register = 1 cycle less than v16 "
                      "(field round trip -1); end relays: same write edge as before",
        "why": "pin_align gate: v16 7,045 FAIL bundles in 19 classes, all on generated field-frame pins; per-pair gate: 128 hops "
               "y_xa.o -> bank i_x0 at 440 um against 406.5, hr_E3.o 147.9 against 92.9; and with the EW relay kits bound "
               "1,024 hops relay -> next station at 490.1 / 426.4 um against 398-401"}
    rm = c["relay_masters"]
    rm.setdefault("v17_added", {
        "dsfd_rly_283_EW": {"instances": 512, "job": "s81_rly_283_ew-v2-4a5563ab5", "kit": "physical/ref_tile/s81_rly_283_ew",
                            "outline_um": [23.76, 30.24], "area_mm2_x512": 0.368,
                            "why": "v1 at the E/W class outline 21.6 x 30.24 was refused at floorplan (util 66.3 % with the hold "
                                   "cells, limit 60 / 65); 23.76 x 30.24 = 58.9 %; it stands in the 25.49 x 62.95 x relay site "
                                   "(two stacked: 60.48), +0.196 mm2 against the generated 17.256 x 19.416 outline, inside the sites"},
        "dsfd_rly_266_EW": "withdrawn: not in the v17 plan (the xb relay of the site is dsfd_rly_266_WE)",
        "note": "RTL rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv; the closed _WE / _SN wide masters (62-66 % by the same count) stand",
        "real_dims_owed": "the generator still places W >= 266 relays as 17.256 x 19.416: binding the 6 wide masters (3,584 "
                          "instances) needs the real 21.6 x 30.24 (E/W) / 34.56 x 19.44 (N/S) outlines in _col_relays; the "
                          "x relay site (25.92 x 62.95) holds two E/W relays stacked (2 x 30.24)"})

    # ---- SU (options table; the decision of record is v17_queue.su_what_the_floorplan_gives)
    c.setdefault("sub_layouts", {})["sp_su_s_v17_options"] = {
        "measured": "SU owner 2026-10-13 17:45 (el1011-s81-suhc-hier-1011.log (8)): routed tile bill 21.151 mm2 (KV 2.276, QN 2.204, "
                    "QB 0.571, SW 6.543, SM 8.346, IO 1.212) in the 1,890 x 10,022.4 slab = 18.942 mm2: fill 1.117; "
                    "standard-cell content 9.66 mm2",
        "options": {
            "A_grow_N": "+7.5 mm2 at fill 0.80 = +3,950 um of slab length: NOT available (hub column full: host top 22,746.9 of 22,749.1)",
            "B_resize_util_0p65": "swe, sml, smd, qne, kve re-routed at util 0.65 (closed at 0.46-0.52): 17.013 mm2 = fill 0.898",
            "C_pin_tile": "dsfd_su_t_pin x4 572.4 x 475.2 (util 0.033) -> 572.4 x 64.8 with the buses on N / S (M3 + M5): -0.94 mm2",
            "D_B_plus_C": "16.07 mm2 = fill 0.848 in the unchanged slab",
            "E_grow_S": "sp_su_s south edge 3,369.6 -> 2,073.6 (600 rows) under its own footprint: +2.45 mm2 -> slab 21.39 mm2; "
                        "with D: fill 0.751.  The band below (gapS, x 11.39-21.63 mm, y 1.81-3.05 mm) is free on the 1- and "
                        "2-stack layer dies; the S strip / tier channel 0 crossing at the hub column is not yet checked by a GEN",
            "F_annex": "sw lanes (swe x128) in a second slab in gapS: fits (14.8 mm2 free) but adds 4-12 relay stages per sw lane; not priced"},
        "recommendation": "coordinator 18:10: slab growth preferred over re-routing closed SU tiles.  Growth first (E + wings, v18 GEN "
                          "trial); C (pin tile re-shape, a new slot shape, no closed engine touched) with it; B (five util-0.65 "
                          "re-routes) only if the wing lanes price above 5 % of the SU path.  A is impossible."}

    # ---- timing
    c["die_timing_v16_pathfinding"] = {
        "source": "results/physical/die_iter_1012/s81/c6p_sta_classes_1013/README.md (c6p: GRT congestion 0, 6,136,530 nets)",
        "tt_setup_ps": -1426.8, "ff_hold_ps": -576.9,
        "real_to_real": {"tt_setup_worst_ps": 169.3, "ff_hold_worst_ps": 131.1, "endpoints": 882944},
        "placeholder": "all 9,071 TT violators and the 72,192 FF endpoints below -500 ps end on / start from the interim "
                       "single-clock dsfd_cfifo; 1.01 M FF endpoints at >= -33.3 ps are the interim cq 32 ps against hold 15 + 50",
        "next": "bind the colck cfifo view after its capture-edge re-route; interim lib FF clk->q >= 65 ps (contract minimum of "
                "a pin-registered tile) so a placeholder hop is not reported as a die hold failure"}
    c["pair_gate"]["v17"] = ("plan v17 (GEN g17): see results/physical/die_iter_1012/s81/v17_plan_1013/README.md for the measured "
                             "pin_align and per-pair figures; hold races of dsfd_cfifo x128 and the 8 m221pq end relays stay until "
                             "their --fwd-negcap re-routes close")
    c["open_items"] = [o for o in c.get("open_items", []) if not (isinstance(o, str) and o.startswith("v16 capture / gather bundle pins"))] + [
        "v17 capture / gather bundle pins (8 f_gather bundles over the g2 columns, t_vm under the x columns, ckv / rsv die pins): generator change owed.",
        "v17 capture cluster clock: boundary spread 226 ps > 80 (tile defect); R ~1,029 ps accepted as an early tap only with spread <= 80 and insertion.json.",
        "v17 wide relays at real dims (--rly-real-dims) + binding of dsfd_rly_266 / 283 _{SN,WE,EW} (3,584 instances).",
        "v17 SU: slab growth first (v18 GEN trial: S growth 1,296 um + wings); v17_queue.su_what_the_floorplan_gives; bgq28 height waits for the same move.",
        "v17 capture-edge re-routes: dsfd_cfifo x128 and 8 m221pq end relays (hl_E0 / E2 / W1, hco / hix / hqe_SW, hcol, hsel) on the --fwd-negcap RTL."]
    c["version"] = 17; c["updated"] = "2026-10-13 PT (evening)"
    c["changelog"].append({"version": 17, "when": "2026-10-13 PT", "change":
        "s81-die: (1) sp_capture slot = its cluster kit: 1728 x 561.6, + ckv / rsv (S, M5), cluster layers (PG M7, strap M8, signals <= M6), "
        "clock entry N / M5, clock level early_tap owed with spread <= 80 ps. (2) field plan v17: q-bank pins on the q element pins, "
        "node pins in fixed slots, x relay site beside the slot station, station xai / xbi at the E end, falling-edge capture at the "
        "forwarded-lane ends. (3) relay masters dsfd_rly_283_EW / 266_EW (kits submitted). (4) SU does not fit (fill 1.117): the column gives at most +2.45 mm2 "
        "below the slab (v18 trial), wings beyond; bgq28 height not taken (column full); capture per-child clock pins, hub cluster rule, crooty_y 11 slices, ce_s clusters taken. (5) c6p pathfinding STA read by path class: real "
        "to real TT +169.3 / FF +131.1; every violator is a placeholder lib. NEIGHBOUR COST: none (no slab moved; the capture slot is "
        "0.024 um wider inside the 1,728-um hub column). No price changed; cfifo: -1 cycle on the field round trip."})
    if a.check:
        print("ok (check only)", len(c["slots"]), "slots"); return 0
    CON.write_text(json.dumps(c, indent=1) + "\n"); print("v17 written", len(c["slots"]), "slots"); return 0


if __name__ == "__main__":
    sys.exit(main())
