#!/usr/bin/env python3
"""S81 plan event XS4-CORE (HARD-S81-DSDV-1 11-13; COORD ruling R-CAP-3 point 3): the x streamer ot_s81sl_xs4 (u_c.u_xg.u_s,
173k cells + all 37 ROM/SRAM macros) becomes ONE hard core in the 16 dsdv_slice_*_C types, and the C rows are re-laid
out by hand on ONE family template (cores move / rotate, shapes frozen, outlines and type pins unchanged).

    python3 physical/die_plan/s81/delta_xs4_core_1113.py PLAN_IN PLAN_OUT [--report R.json] [--types RE]     (cwd = repo root)

WHY A TEMPLATE.  The xring W/E pin bars sit at y 6-487 in ALL 16 types, so the ring stop (soft, u_c.u_xg.u_r) is always
in the bottom band.  The generator mirrored cap / xr / xf / eg to the top in 7 types and left cap 34.6 um behind the W
ring bar in the other 9.  Template (type frame, 8.64 lattice so every core pin keeps its track):

    cap   W side, above the bars   (43.2, 535.68)     43.2 um off the W face (R-STREET-2 street), above the W ring bars
    xf    along the top, 3 + 2     e0 e1 f abutted at x 146.88 .. 691.2, e2 e3 abutted at x 734.4 .. 1097.28, y 993.6 .. 1183.68,
                                   MX (pin face down); the 43.2-um N-S street x 691.2 .. 734.4 breaks the wall (COORD / DIEVIEW-S81 F4)
    eg    under the xf row         egn nh | nk abutted (423.36 / 552.96, 604.8), egg (432.0, 794.88), R0, 43.2 streets around
    xs4   right, pin face DOWN     (734.4, 432.0) MX: the 4,365 pins look at the ring band (g_d from the ring stop), 43.2 under
                                   the xf row; x >= 734.4 keeps the type clock tap (725.76, 613.44) free
    xr    in the ring band         (475.2, 216.0): dl_e / ci_b face the ring stop home, is_d about 220 um from the xs4 pins

Per-row deltas (ROW): mirror = the template sites mirrored in x (cap on the E side, xs4 on the W side); shift = {inst: [dx, dy]}.
cap / xr take R0 or MX, whichever has the lower bit-um over core_conns + internal stations (core_place cost).
XFLIP: a core with pins on M3 AND M5 (cap, xr, egn, egg) can not be mirrored in x: the M3 plan tracks (offset 0.009, pitch
0.036) are not mirror-symmetric and the M5 tracks (0.024 / 0.048) are, so no offset puts both on track (MY / R180 are refused
by the track offset search).  xf and xs4 carry M5 pins only and may take any of the four.

WHAT FOLLOWS A CORE: clock taps, entry footprints, station end points (core_place.write_type).  ft stations and
internal stations whose registers now sit under a core, or whose ends moved, are re-routed (hub_repack.route_station,
reach 360); a station that needs a different register count gets it and is REPORTED (cycles change: lane tables are
refreshed by the next stages).  Added grid taps under a core go to the nearest clear edge (delta_xfin form).
The 37 u_xg.u_s macro contents leave the parent (they are inside the core).
"""
import argparse, collections, copy, gzip, inspect, json, re, sys, textwrap
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import numpy as np
import check as CK, schema as S, core_place as CP, hub_repack as HR, route_supply as RS
from plan_event_1104 import plan_text
from placement_obstacles import placement_boxes
from delta_xfin_split_1104 import offset

VIEW = "physical/die_plan/s81/cores/views/xs4_prov_1113/ot_s81sl_xs4"
MOD, INST = "ot_s81sl_xs4", "u_c.u_xg.u_s"
XW, XH, TW = 648.0, 518.4, 1442.88
R = lambda v: round(v, 3)
XF = ("g_cp[0].u_e", "g_cp[1].u_e", "u_f", "g_cp[2].u_e", "g_cp[3].u_e")
# per core: origin + orient (None = the lowest bit-um flip).  Abutted groups (closer than 4.32) would move rigidly by their anchor.
# DSDV-FORMS-2 11-13 (R-STREET as posted 06:52): cap and xs4 one lattice step lower (43.2 street under the xf row, was 34.56);
# egn nh | nk abutted (0 facing pins, was an 8.64 sliver) and both 34.56 lower (43.2 street under egg: 33-35 facing pins).
TEMPLATE = {"u_c.u_cap": (43.2, 535.68, None), "u_c.u_xr": (475.2, 216.0, None),
            "u_c.u_eg.u_nh": (423.36, 604.8, "R0"), "u_c.u_eg.u_nk": (552.96, 604.8, "R0"), "u_c.u_eg.u_gg": (432.0, 794.88, "R0"),
            INST: (734.4, 432.0, "MX")}
# xf: the row of five is BROKEN 3 + 2 (COORD / DIEVIEW-S81 F4): e0 e1 f | 43.2-um N-S street x 691.2-734.4 | e2 e3.  The street
# is the same one that runs between eg and xs4 below, so it is open from the N face to the ring band.
# DSDV-FORMS-2 11-13: the cores of each group ABUT (0 pins on their E/W faces; R-STREET-6: no 8.64 slivers), pitch 181.44;
# group 1 at x 146.88 .. 691.2, group 2 at 734.4 .. 1097.28, so the street stays 43.2.
TEMPLATE.update({"u_c.u_xf." + n: (R((146.88 if i < 3 else 734.4 - 3 * 181.44) + i * 181.44), 993.6, "MX") for i, n in enumerate(XF)})
ROW = {
    # lepw_mus (die W end): no xring on W; the W face carries the lepk bars at y 488-1077 and the S face the x_o bars at x 6-484.
    # cap goes to the lower-left quadrant 129.6 um off both faces (no core within 129 um of a pin bar); xr steps 43.2 right
    "dsdv_slice_lepw_mus_C__t1": dict(shift={"u_c.u_cap": (86.4, -406.08), "u_c.u_xr": (51.84, 0)}),  # xr 60.48 E of cap (R-STREET-1: 2,070 facing pins)
    # c1x t3: type clock tap at (682.56, 1123.2): the left xf group stops 8.64 short of it
    "dsdv_slice_c1x_C__t3": dict(shift={"u_c.u_xf." + n: (-25.92, 0) for n in XF[:3]}),
    # c1x t1: ft0 (S > N, 132 b) runs at x 993.6, through the xs4 site -> template mirrored (xs4 on the W side)
    # (cap / eg keep R0 / MX at the mirrored sites; xr goes to the W part of the ring band so its E face still looks at the ring stop)
    # (xr 34.56 lower: its N face (1,658 pins) faces the xs4 pin face (1,428 in span) -> R-STREET-1 street 86.4)
    "dsdv_slice_c1x_C__t1": dict(mirror=True, shift={"u_c.u_xr": (-630.72, -34.56)}),
}
REACH = 360.0


class TM(CP.TypeModel):
    """core_place model with every core its own move unit (cap and xr abut in some rows and must separate)"""
    ns = {}
    exec(textwrap.dedent(inspect.getsource(CP.TypeModel._clusters)).replace("< G - EPS", "< -1e9"), vars(CP), ns)
    _clusters = ns["_clusters"]


def seed(tn, inst, w):
    """template bbox origin + orient of the cluster anchored by inst (w = bbox width), with the row delta"""
    row = ROW.get(tn, {})
    x, y, o = TEMPLATE[inst]
    if row.get("mirror"):
        x = R(TW - x - w)
        if o and (inst == INST or inst.startswith("u_c.u_xf.")):
            o = CP.comp(o, "MY")          # M5-only pin faces may mirror in x; cap / xr / eg may not (see XFLIP)
    dx, dy = (row.get("shift") or {}).get(inst, (0, 0))
    return R(x + dx), R(y + dy), o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--report"); ap.add_argument("--types", default=r"dsdv_slice_\w+_C__t\d+$")
    a = ap.parse_args()
    raw = Path(a.src).read_bytes()
    P = json.loads(gzip.decompress(raw) if a.src.endswith(".gz") else raw)
    Ps = S.Plan(S.load(a.src), a.src)
    repo = Path(".").resolve(); die_dir = repo / "physical/die_plan/s81"
    doc = json.loads((die_dir / f"inputs/core_pins/{MOD}.json").read_text())
    ins = json.loads(Path(f"{VIEW}/insertion_provisional.json").read_text())
    RS.REF_DIRS[:] = [str(die_dir)]
    rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"])
    for k, f in (("views", "route_supply_views.json"), ("kit_views", "route_supply_kit_views.json")):
        try:
            v = json.loads((repo / "tools/die_plan" / f).read_text())
            rs_cfg[k] = v.get("views", {}) if k == "views" else v.get("s81", {})
        except (OSError, ValueError):
            rs_cfg[k] = {}
    conns = RS.load_conns(die_dir, None, die_dir, [])
    cfg = dict(gap=8.64, sweeps=0, topk=1, lam=4.0, reach=REACH, grid_um=21.6, grt_halving="full", fixed_re="", rs=rs_cfg,
               flips_only=False, gap_pinface=None, face_clear=[])
    rx = re.compile(a.types)
    report = {}
    for tn in sorted(P["partition_types"]):
        t = P["partition_types"][tn]
        if not rx.match(tn) or not any(c.get("inst") == "u_c.u_cap" for c in t.get("hard_cores") or []):
            continue
        rep = report[tn] = dict(mirror=bool(ROW.get(tn, {}).get("mirror")))
        # 1 macros leave the parent
        n0 = len(t["contents"])
        t["contents"] = [c for c in t["contents"] if "u_xg.u_s." not in c.get("inst", "")]
        rep["macros_removed"] = n0 - len(t["contents"])
        # 2 place the existing cores on the template (core_place model: everything that rides on a core follows it)
        M = TM(tn, copy.deepcopy(t), die_dir, repo, conns, cfg)
        for k in range(M.m):
            names = [M.inst[i] for i in M.CL[k]]
            anc = next((n for n in names if n in TEMPLATE), None)
            assert anc, (tn, names)
            x, y, o = seed(tn, anc, float(M.cbb[k, 2]))
            M.cpos[k] = (x, y)
            if o:
                M.cflip[k] = CP.comp(M.ori0[M.idx[anc]], o)
        allq = range(len(M.L))
        flips = {}
        for inst in ("u_c.u_cap", "u_c.u_xr"):
            k = M.cid[M.idx[inst]]
            best = None
            for fl in ("R0", "MX"):            # XFLIP: no mirror in x for a core with M3 AND M5 pins (see the module text)
                M.cflip[k] = fl
                c = M.cost(allq)
                if best is None or c < best[0] - 1e-6:
                    best = (c, fl)
            M.cflip[k] = best[1]
            flips[inst] = CP.comp(M.ori0[M.idx[inst]], best[1])
        rep.update(bit_mm=R(M.cost(allq) / 1e3), flips=flips)
        base_cores = {c["inst"]: (list(c["origin_um"]), c.get("orient", "R0"), c["outline_um"]) for c in t["hard_cores"]}
        base_taps = {q["name"]: list(q["xy"]) for q in t["clock"]["taps"]}
        base_tap = list(t["clock"]["tap_um"])
        srep = CP.write_type(M, t, cfg, lambda s: None)
        t["clock"]["tap_um"] = base_tap          # the type (die) clock tap never rides on a core (c1x t3: it sat over egg)
        # track offsets: a moved / flipped core takes the offset that puts every pin on the plan tracks again (type frame and
        # every instance frame, delta_xfin offset()); its core taps (on the body or beside it) follow rigidly with it
        tf = 0
        for c in t["hard_cores"]:
            (bx, by), bo, (w, h) = base_cores[c["inst"]]
            if [bx, by] == c["origin_um"] and bo == c.get("orient", "R0"):
                continue
            pj = json.loads((die_dir / c["pins_file"]).read_text())
            old = list(c.get("track_offset_um") or [0.0, 0.0])
            dx, dy = offset(Ps, tn, dict(c, orient=c.get("orient", "R0")), [(q["name"], q["layer"], q["x"], q["y"]) for q in pj["pins"]])
            assert dx is not None and dy is not None, (tn, c["inst"], dx, dy)
            c["track_offset_um"] = [dx, dy]
            for q in t["clock"]["taps"]:
                if q.get("kind") != "core" or not q["name"].startswith(c["inst"] + "."):
                    continue
                if any(o_ is not c and q["name"].startswith(o_["inst"] + ".") and len(o_["inst"]) > len(c["inst"]) for o_ in t["hard_cores"]):
                    continue
                p0 = base_taps[q["name"]]
                u, v = CK._orient_pt(bo, w, h, p0[0] - bx - old[0], p0[1] - by - old[1])          # the four orients are involutions
                x_, y_ = CK._orient_pt(c.get("orient", "R0"), w, h, u, v)
                q["xy"] = [R(c["origin_um"][0] + dx + x_), R(c["origin_um"][1] + dy + y_)]
                tf += 1
        rep["core_taps_followed"] = tf
        # 3 the xs4 core
        x0, y0, o = seed(tn, INST, XW)
        core = dict(inst=INST, module=MOD, lib=f"{VIEW}/{MOD}_tt.lib", lef=f"{VIEW}/{MOD}.lef", origin_um=[x0, y0], outline_um=[XW, XH],
                    orient=o, track_offset_um=[0.0, 0.0], pins_file=f"inputs/core_pins/{MOD}.json", obs_max="M5")
        pins = [(q["name"], q["layer"], q["x"], q["y"]) for q in doc["pins"]]
        dx, dy = offset(Ps, tn, core, pins)
        assert dx is not None and dy is not None, (tn, dx, dy)
        core["track_offset_um"] = [dx, dy]
        xr_i = next(i for i, c in enumerate(t["hard_cores"]) if c["inst"] == "u_c.u_xr")
        t["hard_cores"].insert(xr_i + 1, core)
        ck = next(q for q in doc["pins"] if q["name"] == "clk")
        ax, ay = CK._orient_pt(o, XW, XH, ck["x"], ck["y"])
        ot = next(x for x in t["clock"]["taps"] if x["name"] == "u_c.u_xr.clk")
        tt = t["clock"]["taps"]
        tt.insert(tt.index(ot) + 1, dict(ot, name=f"{INST}.clk", xy=[R(x0 + dx + ax), R(y0 + dy + ay)],
                                        insertion_ps=ins["tt"]["boundary"]["mean"], insertion_ff_ps=ins["ff"]["boundary"]["mean"],
                                        budget_owner=f"parent_budget pin_register_mean {VIEW}/insertion_provisional.json",
                                        note="XS4-CORE 11-13: early core tap at the boundary-register mean (PROVISIONAL until the xs4 kit signs off)"))
        rects = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1]) for c in t["hard_cores"]]
        rep["cores"] = {c["inst"]: [c["origin_um"], c.get("orient", "R0")] for c in t["hard_cores"]}
        # pairwise gaps
        mg = min(max(b[0] - a_[2], a_[0] - b[2], b[1] - a_[3], a_[1] - b[3]) for i, a_ in enumerate(rects) for b in rects[i + 1:])
        rep["min_core_gap"] = R(mg)
        # DSDV-FORMS-2 11-13: a pair either ABUTS (gap 0, R-STREET-1/6: xf groups, egn nh|nk) or keeps >= 8.64; never overlaps
        gaps = [max(b[0] - a_[2], a_[0] - b[2], b[1] - a_[3], a_[1] - b[3]) for i, a_ in enumerate(rects) for b in rects[i + 1:]]
        bad = [g for g in gaps if g < -1e-6 or 1e-6 < g < 8.64 - 1e-6]
        assert not bad, (tn, "core overlap / sub-lattice gap", min(bad))
        Rr = HR.Raster(M.W, M.H, rects)
        # 4 internal stations: re-route every chain with a moved end or a register under a core
        chg = []
        for s in t.get("internal_stations") or []:
            regs = s.get("regs_um") or []
            n_old = len(regs)
            hops = [s["from_um"]] + regs + [s["to_um"]]
            worst = max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(hops, hops[1:]))
            if all(Rr.free(*r[:2]) for r in regs) and worst <= 405.0:
                continue
            r = HR.route_station(Rr, tuple(s["from_um"]), tuple(s["to_um"]), n_old, REACH)
            if r is None:
                chg.append((s["conn"], n_old, None)); continue
            s["regs_um"] = [[R(p[0]), R(p[1])] for p in r["regs"]]
            if len(r["regs"]) != n_old:
                chg.append((s["conn"], n_old, len(r["regs"])))
                s["note"] = (s.get("note", "") + " | XS4-CORE 11-13 re-laid row: %d -> %d registers (%s um)" % (n_old, len(r["regs"]), r["length_um"]))
            else:
                s["note"] = (s.get("note", "") + " | XS4-CORE 11-13 re-sited (%s um)" % r["length_um"])
        rep["stations"] = dict(n=srep["stations"], count_changed=chg)
        # 5 ft slots: a slot with a register under a core is re-routed whole (first station = the in-face flop, kept;
        #   the others from it to the out-face window, same count, hop <= 405); its per-bit sites are regenerated by ft_spread
        ftc = []
        for f in t.get("ft_slots") or []:
            regs = f.get("regs_um") or []
            inner = lambda p: 0.5 < p[0] < M.W - 0.5 and 0.5 < p[1] < M.H - 0.5
            bad = [j for j, p in enumerate(regs) if inner(p) and not Rr.free(*p[:2])]
            if not bad:
                continue
            lo, hi = f["out_window_um"]
            of = f["out_face"]
            b_ = {"N": ((lo + hi) / 2, M.H), "S": ((lo + hi) / 2, 0.0), "E": (M.W, (lo + hi) / 2), "W": (0.0, (lo + hi) / 2)}[of]
            k0 = 0 if inner(regs[0]) else 1
            if k0:
                a_ = tuple(regs[0][:2])
            else:
                lo, hi = f["in_window_um"]
                a_ = {"N": ((lo + hi) / 2, M.H), "S": ((lo + hi) / 2, 0.0), "E": (M.W, (lo + hi) / 2), "W": (0.0, (lo + hi) / 2)}[f["in_face"]]
            n = len(regs) - k0
            r = HR.route_station(Rr, a_, b_, n, 405.0)
            ok = r is not None and len(r["regs"]) == n
            if ok:
                regs[k0:] = [[R(p[0]), R(p[1])] for p in r["regs"]]
                f.pop("bit_sites_um", None); f.pop("bit_site_cell_um", None)
            pts = [a_] + [tuple(p) for p in regs[k0:]] + [b_]
            hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]
            ftc.append((f["name"], len(bad), "ok" if ok else "FAILED need %s" % (None if r is None else len(r["regs"])), R(max(hops))))
        rep["ft"] = ftc
        # 6 added grid taps under a core / macro: nearest clear edge (delta_xfin form)
        boxes = placement_boxes(t, halo=S.TAP_CLEAR_UM); clear = S.TAP_CLEAR_UM; mv = []
        for q in t["clock"].get("added_taps", []):
            x, y = q["xy"]
            for bb in boxes.values():
                if bb[0] < x < bb[2] and bb[1] < y < bb[3]:
                    cs = sorted([(x - bb[0], R(bb[0] - .01), y), (bb[2] - x, R(bb[2] + .01), y), (y - bb[1], x, R(bb[1] - .01)), (bb[3] - y, x, R(bb[3] + .01))])
                    for _, nx, ny in cs:
                        if 8.64 < nx < M.W - 8.64 and 8.64 < ny < M.H - 8.64 and not any(b[0] < nx < b[2] and b[1] < ny < b[3] for b in boxes.values()) and \
                                not any(o_ is not q and abs(nx - o_["xy"][0]) < clear and abs(ny - o_["xy"][1]) < clear for o_ in t["clock"]["added_taps"]):
                            break
                    else:
                        raise SystemExit(("no tap site", tn, q))
                    mv.append((q["name"], [x, y], [nx, ny])); q["xy"] = [nx, ny]; break
        rep["taps_moved"] = len(mv)
        # 7 landing bands under a core: the band slides (same size) to the nearest clear spot; every copy of its rect follows
        left = []
        bands = (t["clock"].get("landing_contract") or {}).get("bands") or {}
        hit = lambda b, rs: any(b[0] < r_[2] and r_[0] < b[2] and b[1] < r_[3] and r_[1] < b[3] for r_ in rs)
        bmv = []
        for bn, bd in bands.items():
            b = bd.get("rect_um")
            if not b or not hit(b, rects):
                continue
            others = [o_["rect_um"] for on, o_ in bands.items() if on != bn and o_.get("rect_um")]
            grown = [(r_[0] - 1.08, r_[1] - 1.08, r_[2] + 1.08, r_[3] + 1.08) for r_ in rects]
            best = None
            for i in range(-112, 113):
                for j in range(-112, 113):
                    nb = [R(b[0] + i * 1.08), R(b[1] + j * 1.08), R(b[2] + i * 1.08), R(b[3] + j * 1.08)]
                    if nb[0] < 4.32 or nb[1] < 4.32 or nb[2] > M.W - 4.32 or nb[3] > M.H - 4.32 or hit(nb, grown) or hit(nb, others):
                        continue
                    d = abs(i) + abs(j)
                    if best is None or d < best[0]:
                        best = (d, nb)
            if best is None:
                left.append("band " + bn); continue
            old_b = list(b)

            def swap(x):
                if isinstance(x, list):
                    if x == old_b:
                        return list(best[1])
                    return [swap(v_) for v_ in x]
                if isinstance(x, dict):
                    return {k_: swap(v_) for k_, v_ in x.items()}
                return x
            t["clock"] = swap(t["clock"])
            bands = t["clock"]["landing_contract"]["bands"]
            bmv.append((bn, old_b, best[1]))
        rep["bands_moved"] = bmv
        for e in t["clock"].get("edge_clocks") or []:
            if not Rr.free(*e["tap_um"]) and 4.32 < e["tap_um"][0] < M.W - 4.32 and 4.32 < e["tap_um"][1] < M.H - 4.32:
                left.append("edge " + e["port"])
        cx, cy = t["clock"]["tap_um"]
        if any(r_[0] - 8.64 < cx < r_[2] + 8.64 and r_[1] - 8.64 < cy < r_[3] + 8.64 for r_ in rects):
            left.append("type clock tap")
        rep["left_under_core"] = left
        rep["tap_um"] = t["clock"]["tap_um"]
        t["note"] = (t.get("note", "") + " | XS4-CORE 11-13 (HARD-S81-DSDV-1, R-CAP-3 point 3): u_c.u_xg.u_s = ot_s81sl_xs4 hard core, row re-laid on the family template" +
                     (" (mirrored)" if rep["mirror"] else ""))
        print(tn, json.dumps({k: v for k, v in rep.items() if k != "cores"})[:600], flush=True)
    # DSDV-FORMS-2 11-13: the re-routed stations change internal_stations depths on C-row buses; price them in the lanes
    # (reach_fix FIXED-CYCLES form: fixed_cycles += depth change at each lane end, native rule re-checked, latency table
    # refreshed).  Without it strict bind stops: "native stations <lane>: fixed_cycles must equal source + destination".
    import reach_fix as RF
    fc = RF.sync_fixed_cycles(json.loads(gzip.decompress(raw) if a.src.endswith(".gz") else raw), P, a.src)
    report["_fixed_cycles"] = fc
    print("FIXED-CYCLES lanes %d, lane cycles added %d, rule broken %s" % (len(fc["lanes"]), fc["lane_cycles_added"],
          fc["rule_broken"][:8]), flush=True)
    if fc["rule_broken"]:
        raise SystemExit("REFUSE: native station rule broken on %s" % fc["rule_broken"][:20])
    Path(a.out).write_text(plan_text(P))
    if a.report:
        Path(a.report).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
