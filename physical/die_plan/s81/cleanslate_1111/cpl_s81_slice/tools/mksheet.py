#!/usr/bin/env python3
"""CPL-S81-SLICE: family INTENT SHEET (markdown) from intent_i/<type>.json + a hand-written family intent text.
usage: mksheet.py INTENT_DIR SUMMARY_JSON OUTDIR"""
import json
import os
import sys

ID, SUMF, OUT = sys.argv[1:4]
SUM = json.load(open(SUMF))

TEXT = {
    "SLICE-C": """**Dataflow (bound netlist + LEF directions + plan buses/stations).** Ring side: leafup_i* face windows (279-668 b each,
the farthest one staged) -> u_xr (xrt ring core) <-> the slice content macros (2707 b in / 1240 b out, p2p) -> u_xr broadcasts
151 b to every leafdn_o* window and 312 b to u_cap (capc5r).  ret_i* windows -> u_cap.  u_eg.u_nh / u_eg.u_nk (egn) and
u_eg.u_gg (egg) sit one stage behind cap/xr.  Finish side: u_xf.g_cp[0..3].u_e (eng_finish) form a serial chain
(131 b per neighbour, 190-um pitch) closed by u_xf.u_f (norm_finish, 123 b).  Roles: face->xr and xr<->macros p2p;
xr->leafdn/cap broadcast; finish chain p2p neighbour links (+ skip links); cfg/status <=4 b serialisable.
**Timing-critical pairs:** the plan internal stations (leafup_i3/i4 -> xr staged, ~1190 um), xr<->macros (~800 um), and the
eng_finish chain neighbours.  **Intended layout:** the plan structure already follows this chain (finish row in chain
order, xr between its windows and the content macros, cap beside the ret windows), so it is kept: the search only
shifts cores <=250 um on the 8.64 lattice (no relocate, no flip), and no link >=32 b (or any station link) may grow beyond
1.2x+20 um or cross the 396.9-um reach.  **Composer gate (v2, DS85-COMPOSE-1111 dry-run FAIL of v1 6464cded):** every
search step must also pass the composer legality copied rule for rule (cgate.py): no new overlap or street <34.56 um
(abutted 0 allowed) against every hard core AND every lef content macro (the slice SRAM/em banks), no new station/ft
reg, tap or core tap strictly under any core or macro box (after the station re-site), and the kit tap rule
(taps.grid_explicit_taps load <=1500, radius <=1.10 x tap_radius_um) checked on 99f + the LP-W window.  Six types keep a
legal fine-tune (c1x t4/t8/t9, c3x, iq, lepe_mu_C); c1x t1/t3/t6/t7, kv512 and lepw_mus_C have no legal improvement
under the gate -> KEEP.  What it buys: face-window entry streets, lower route_supply p99 (c1x_t8 3.03 -> 2.69),
~0.5 % family bit-mm.""",
    "SLICE-LP-W": """**Dataflow.** S face coll_i<k> (514 b, staged) -> ln<k> (coll_lane, M5 OBS) -> lnl<k> (inland, 559 b, ~105 um) ->
the lep SRAM banks (558 b; banks broadcast 557 b back to every lnl) ; ln<k> -> coll_o<k> (512 b) back out of the S face.
E face lepk_i0/lepk_o0 (2 x 1104 b) + lepf/flt/lpc feed the lep SRAM banks directly (p2p, no core on the path).
**Timing-critical pairs:** coll_i -> ln stations, ln<->lnl (559 b), lnl<->lep banks (400-800 um, the longest).
**Intended layout:** four lanes side by side over their own S windows, each lnl directly above its ln, lep banks above the
lnl row, and the E-face lep windows AT the lep bank rows.  In lepw_mus_LP__t2 the E windows sit at y 6-538 against ln3
(15-um street, 86 um needed for 2212 b): the lep traffic must cross the lane row -> GRT 463k overflow (class F).
Placement cannot fix this without breaking the lane chain (intent search: no legal improvement) -> REDESIGN: move the
two 1104-b windows lepk_i0/lepk_o0 (and the abutting lepw_mus_C__t1 W-face lepk windows + the 2 die ports kd_s_0S__0 /
ku_s_0S__0, same y) up by 622.08 um (72 x 8.64) to y 628-1109, beside the lep banks; the 1-2 b lepf/flt/lpc control
windows stay at y 488-538 next to the lnl rs_k/flt pins (moving them too created R3 >405-um bundles in G0C).  With no core
move the entry jam is gone (entry 1.825 -> 0, model cost 2.825 -> 1.0) and the C partner's W jam over capc5r clears too.
lepw_mu_LP__t2: the fine-tune delta made G0C R3-INTERNAL bundles ln.rx -> lnl.n_rxv >= 499-577 um (worst bit) -> dropped, KEEP.""",
    "SLICE-LP-E": """**Dataflow.** Same lane structure as LP-W: S face coll_i<k> (staged) -> ln<k> -> lnl<k> (559 b) <-> lep SRAM banks;
ln<k> -> coll_o<k>.  **Timing-critical pairs:** coll_i -> ln stations, ln<->lnl, lnl<->lep banks.  **Intended layout:**
lanes over their S windows, lnl above its ln, banks above (= the plan).  The intent fine-tune (shift <=250 um, no flip,
links >=32 b within 1.2x+20 um and reach) found nothing for lepe_mu_LP__t2, and its lepe_nh_mus_LP__t1 result made G0C
R3-INTERNAL bundles (ln.rx -> lnl.n_rxv worst bit 572-607 um > 405) -> dropped: KEEP both.  Before evidence for
lepe_nh_mus_LP__t1: routed DB job 50acdf2cf527 (epyc2 kw43-wave-1109n attempt_7, 11-11 01:13) failed GRT-0116 with total
overflow 48123 (M6 46799), hot band between the lnl cores and the SRAM bank rows (the lnl<->bank links).  The failure is not a placement class: the signed coll_lane view (dsfd_coll_lane_e_safe8_ntf_signed_1107)
carries solid OBS on M1-M6 (COORD queue, DRT-0073 item), so over the two ln cores only M7 is left and every H route between
the lnl/bank row and the E/W faces detours around them -> fix in the view (OBS only to M5, like the plan assumes) or a
die-owner window move; no core move under the intent rule.""",
    "KVLEAF": """**Dataflow.** leafdn_i0 -> u_vs (scatter) and u_vn.u_a (arbiter, staged) -> the 16 vp lanes g_ln[k].u_l (266/257 b
each way, all staged) ; u_vs <-> u_vsw (365 b staged) ; u_ve.u_m -> u_ve.u_s (401 b, 55 um) ; u_rxsf -> u_rxsb (96 b) ;
u_vs -> leafup_o0.  **Timing-critical pairs:** the 60-150 plan stations (arbiter <-> lanes, vs <-> vsw).  **Intended
layout:** arbiter central to its 16 lanes, ve.m/ve.s abutted, vs between its face window and vsw.  The earlier free
search shortened bit-mm but broke ve.m->ve.s (55 -> 798 um) and other chain links; under the intent constraints no
legal move beats the plan -> KEEP (no delta).  KVLEAF-T2 (soft, 0 cores): N windows leafdn_i0 597 b / leafup_o0 668 b
have 60/181 um macro clearance (23/26 um needed), station bands macro-free (+10.8 halo), cuts 0.11/0.08 -> OK, no change.""",
}

for fam, s in SUM.items():
    od = os.path.join(OUT, fam)
    os.makedirs(od, exist_ok=True)
    L = ["# INTENT SHEET %s (CPL-S81-SLICE, plan 99f40d35071d)" % fam, "",
         "Delta: `%s` sha256 `%s`; adopted types %d/%d." % (os.path.basename(s["path"]), s["sha256"], len(s["adopted"]), len(s["types"])),
         "", TEXT[fam], "", "## Per type", ""]
    L.append("| type | moved | bit-mm | worst cut V/H | entry | rs p99 | chain corr | longer links | SVG |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for t in s["types"]:
        r = s["rows"][t]
        it = json.load(open(os.path.join(ID, t + ".json")))
        a = r["after"] or r["before"]
        L.append("| %s | %d | %s -> %s | %s/%s -> %s/%s | %s -> %s | %s -> %s | %s -> %s | %d | %s_after.svg |" % (
            t, r["moved"], r["before"]["bitmm"], a["bitmm"], r["before"]["cutV"], r["before"]["cutH"], a["cutV"], a["cutH"],
            r["before"]["entry"], a["entry"], r["before"]["rs_p99"], a["rs_p99"], it["chain_order_corr_before"],
            it["chain_order_corr_after"] if r["moved"] else it["chain_order_corr_before"],
            len(it["edges_longer_after"]) if r["moved"] else 0, t))
    rep = s["types"][0]
    it = json.load(open(os.path.join(ID, rep + ".json")))
    L += ["", "## Dataflow links of %s (top 30 by bits; length um before -> after)" % rep, "",
          "| src | dst | bits | role | len |", "|---|---|---|---|---|"]
    for e in it["edges"][:30]:
        L.append("| %s | %s | %s | %s | %s -> %s |" % (e["src"], e["dst"], e["bits"], e["role"], e["len_before"], e["len_after"]))
    L += ["", "## Timing-critical pairs of %s" % rep, ""]
    for c in it["critical"][:40]:
        L.append("- " + json.dumps(c))
    open(os.path.join(od, "INTENT_%s.md" % fam), "w").write("\n".join(L) + "\n")
    print(od)
