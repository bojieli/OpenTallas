#!/usr/bin/env python3
"""S81-GEOM-2 FTREGS0LM-1111 (least-move form of FTREGS0-1111; COORD 03:0x hop audit, positions only, DO_NOT_COUNT):
re-derive the station sites of the S81 ft slots whose regs_um[0] sits off their in window, moving each station as
little as possible.

WHY a second form: FTREGS0-1111 (delta_s81_ftregs0_1111.py) re-spaces the stations evenly on check.zroute.  That fixes
the hop audit but route_supply (PLAN-ROUTE-1 model) gets worse in 5 of its 10 types (on BASE_1200: t44 clf6cf8492 p99
1.733 -> 2.636, t53 cl958451dd 1.535 -> 2.327, t54 cl501e5681 1.921 -> 2.470, slice_station__t45 0.749 -> 1.029),
because the zroute legs leave the street paths the plan stations followed.  This form keeps the planned path: the
route is the polyline in-face -> old regs_um[1:] -> out-face, and the DP cost is the arc distance from each OLD site
(not from L*j/k on a zroute), so a station only moves as far as the reach bound forces it.  A slot whose polyline is
longer than stations x station_max falls back to the FTREGS0 zroute rule (reported per slot as sites_on).\nClock taps: if the new sites push an added grid+explicit tap of a touched type over tap_max_sinks (taps.py kit split;\nseen on r1: t43 clk_t20 1810/1500), that type's slots take the FTREGS0 zroute rule instead (sites_on zroute-tap).  Cause: an ft station is ~600\nclocked flops; the S-face band of t43 already loads clk_t20/t38/t40 with face flops, so a station on the old S-face\npath has no tap with room.

--- FTREGS0-1111 notes (unchanged rules below) ---

Finding (explorer hop audit die_s81_64eb2c89__hop_audit.tsv, from_kind=slot rows): the kit builds station 0 of an ft
slot as the in-port face flop (face_flops.tcl; explorer ft_slot_stages) and station j >= 1 at regs_um[j].  These 18
slots carry a regs_um[0] 166-343 um inside the type, so their planned sites were spaced from that point, not from the
face: the real face-flop -> regs_um[1] hop is 480-745 um (> 405 reach).  All 18 are the crossings of the four L0 relay
lanes up_s_2N_L0 / dn_s_2N_L0 / up_s_4N_L0 / dn_s_4N_L0 (single-instance types), selected here by that rule
(regs_um[0] > TOL from the in window), and the selection is asserted to be exactly the lanes' crossings.

Fix per slot, type frame: regs_um[0] = the in-window centre, 1 um inside the in face (die_hop_scan.input_site, where
the kit puts the face flop); regs_um[j], j = 1..k-1, evenly at L*j/k on the slot's check.zroute from the in-window
centre to the out-window centre; a site inside a hard core (+4.32 halo), a landing ring band or a reset/collector site
moves along the route (1.08-um arc grid, DP: least total slide with every arc gap <= reach - 2); when no route\nchain exists, the same DP on a free 4.32-um 2-D lattice with true Manhattan FF hops <= reach - 2.  Every
FF hop (face flop -> sites -> out pin -> next slot's face flop) is asserted <= reach; R3 (route / stations <= 405) too.
Station counts, windows, faces, ports, lanes and every other key are byte-identical (asserted); lane_natural of every
lane is unchanged (asserted) -> EQ by construction (positions only).

Base-agnostic: BASE_1200 b5faa1bacc5f (default) or a later event (r1 / r2 of S4N-FTLANE): the selection rule picks the
slots that are still off-window on that base.
usage: delta_s81_ftregs0lm_1111.py PLAN_IN PLAN_OUT [REPORT.json] [--base-sha SHA]
       delta_s81_ftregs0lm_1111.py --check PLAN_IN PLAN_OUT [--base-sha SHA]"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[2] / "tools" / "die_plan")]
import schema as S  # noqa: E402
import check as C  # noqa: E402
import clock_landing_plan as CLP  # noqa: E402
from die_hop_scan import INSET  # noqa: E402

EVENT = "FTREGS0LM-1111"
BASE_SHA = "b5faa1bacc5f6e80c6167856ee1597a7a775ea81dad9305424a3c47de0786d7b"   # BASE_1200
LANES = ("up_s_2N_L0", "dn_s_2N_L0", "up_s_4N_L0", "dn_s_4N_L0")
TOL = 5.0          # um: regs_um[0] farther than this from its in window = off window
HALO = 4.32
STEP = 1.08


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def face_pt(t, face, win, inset=0.0):
    w, h = t["outline_um"]
    c = (win[0] + win[1]) / 2
    p = {"E": (w, c), "W": (0.0, c), "N": (c, h), "S": (c, 0.0)}[face]
    dx, dy = INSET[face]
    return (p[0] + dx * inset, p[1] + dy * inset)


def off_window(t, s):
    x, y = s["regs_um"][0]
    w, h = t["outline_um"]
    lo, hi = s["in_window_um"]
    f = s["in_face"]
    if f in "NS":
        return max(lo - x, 0.0, x - hi) + abs(y - (0.0 if f == "S" else h))
    return max(lo - y, 0.0, y - hi) + abs(x - (0.0 if f == "W" else w))


def blockers(t):
    out = [list(b) for b in S.placed_macro_boxes(t, halo=HALO).values()]
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    for b in (lc.get("bands") or {}).values():
        out += [list(r) for r in (b.get("rects_um") or ([b["rect_um"]] if b.get("rect_um") else []))]
    out += CLP.reset_site_rects(lc.get("collector_tree"))
    return out


def free(t, p, bl):
    w, h = t["outline_um"]
    if not (HALO <= p[0] <= w - HALO and HALO <= p[1] <= h - HALO):
        return False
    return not any(b[0] - 1e-6 <= p[0] <= b[2] + 1e-6 and b[1] - 1e-6 <= p[1] <= b[3] + 1e-6 for b in bl)


def md(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def site_dp(t, route, L, k, bl, R, ideal=None):
    """k-1 station sites on the slot route (1.08-um arc grid, free of cores+halo / ring bands / reset sites) with every
    arc gap face -> site -> ... -> out face <= R (arc >= Manhattan, so every FF hop <= R), minimising the summed
    distance from the even positions L*j/k.  Returns [(s, point)]."""
    fr = []
    for i in range(1, int(L / STEP) + 1):
        s_ = i * STEP
        if s_ < L:
            q = C.point_at(route, s_)
            if free(t, q, bl):
                fr.append((s_, (round(q[0], 4), round(q[1], 4))))
    layer = {-1: (0.0, None)}            # index -> (cost, back); -1 = the in face (s = 0)
    pos = lambda ix: 0.0 if ix == -1 else fr[ix][0]
    hist = []
    for j in range(1, k):
        nxt = {}
        prev = sorted(layer, key=pos)
        for ci, (sc, _) in enumerate(fr):
            best = None
            for pi in prev:
                g = sc - pos(pi)
                if 0.0 < g <= R + 1e-6:
                    c = layer[pi][0]
                    if best is None or c < best[0]:
                        best = (c, pi)
            if best is not None:
                nxt[ci] = (best[0] + abs(sc - (ideal[j - 1] if ideal else L * j / k)), best[1])
        hist.append(nxt)
        layer = nxt
        assert layer, ("no feasible station chain", j)
    ends = [ci for ci in layer if L - fr[ci][0] <= R + 1e-6]
    assert ends, "no feasible station chain to the out face"
    ci = min(ends, key=lambda c: layer[c][0])
    out = []
    for j in range(k - 1, 0, -1):
        out.append(fr[ci])
        ci = hist[j - 1][ci][1]
    return out[::-1]


def site_dp2(t, route, L, k, bl, R, a, b, pitch=4.32, ideal_pts=None):
    """fallback when no route chain exists: the same DP over a free 2-D lattice (pitch um) inside the Manhattan
    ellipse md(a,p)+md(p,b) <= k*R; hops are true Manhattan FF distances <= R.  Returns [(slide, point)]."""
    import numpy as np
    w, h = t["outline_um"]
    xs = np.arange(HALO, w - HALO, pitch)
    ys = np.arange(HALO, h - HALO, pitch)
    X, Y = np.meshgrid(xs, ys)
    X, Y = X.ravel(), Y.ravel()
    m = (np.abs(X - a[0]) + np.abs(Y - a[1]) + np.abs(X - b[0]) + np.abs(Y - b[1])) <= k * R
    for bb in bl:
        m &= ~((X >= bb[0] - 1e-6) & (X <= bb[2] + 1e-6) & (Y >= bb[1] - 1e-6) & (Y <= bb[3] + 1e-6))
    X, Y = X[m], Y[m]
    ideal = ideal_pts or [C.point_at(route, L * j / k) for j in range(1, k)]
    cost = np.abs(X - a[0]) + np.abs(Y - a[1])
    cost = np.where(cost <= R, 0.0, np.inf)          # layer 0 = reachability from the in face
    backs = []
    for j in range(1, k):
        dev = np.abs(X - ideal[j - 1][0]) + np.abs(Y - ideal[j - 1][1])
        if j == 1:
            new, back = cost + dev, np.full(len(X), -1)
        else:
            src = np.flatnonzero(np.isfinite(cost))
            new = np.full(len(X), np.inf)
            back = np.full(len(X), -1)
            for c0 in range(0, len(src), 512):
                sl = src[c0:c0 + 512]
                d = np.abs(X[None, :] - X[sl, None]) + np.abs(Y[None, :] - Y[sl, None])
                cc = np.where(d <= R, cost[sl, None], np.inf)
                arg = np.argmin(cc, axis=0)
                val = cc[arg, np.arange(len(X))]
                better = val < new
                new = np.where(better, val, new)
                back = np.where(better, sl[arg], back)
            new = new + dev
        backs.append(back)
        cost = new
        assert np.isfinite(cost).any(), ("no feasible 2-D station chain", j)
    endok = (np.abs(X - b[0]) + np.abs(Y - b[1])) <= R
    cost = np.where(endok, cost, np.inf)
    assert np.isfinite(cost).any(), "no feasible 2-D station chain to the out face"
    ci = int(np.argmin(cost))
    out = []
    for j in range(k - 1, 0, -1):
        q = (round(float(X[ci]), 4), round(float(Y[ci]), 4))
        out.append((abs(q[0] - ideal[j - 1][0]) + abs(q[1] - ideal[j - 1][1]), q))
        ci = int(backs[j - 1][ci])
    return out[::-1]


MAX_TAP_TRIES = 2


def tap_overload(raw, ppath, types):
    """{type: [(x, y) of each added clock tap the trial sites push over tap_max_sinks]} with the taps.py kit-split rule
    (grid_explicit_taps: nearest + cap, the check the kit and compose phys run)."""
    import re as _re
    import taps as TP
    PP = S.Plan(json.loads(json.dumps(raw)), ppath)
    out = {}
    for tn in types:
        if (PP.types[tn].get("clock") or {}).get("tap_mode") != "grid+explicit":
            continue
        try:
            TP.grid_explicit_taps(PP, tn)
        except ValueError as e:
            m = _re.search(r"tap (clk_t\d+) load=", str(e))
            assert m, str(e)
            xy = {n: (x, y) for n, x, y in TP.grid_explicit_sites(PP, tn)}
            out[tn] = [xy[m.group(1)]]
    return out


def derive(pin_path, base_sha):
    text = open(pin_path).read()
    assert sha(text) == base_sha, f"base sha {sha(text)[:12]} != {base_sha[:12]}"
    assert json.dumps(json.loads(text)) + "\n" == text, "base is not in the compact json.dumps form"
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    ppath = HERE / "die_plan.json"
    P = S.Plan(json.loads(text), ppath)
    T = raw["partition_types"]
    cnt = {}
    for p in raw["partitions"]:
        cnt[p["type"]] = cnt.get(p["type"], 0) + 1
    # selection: every ft slot with regs_um whose regs_um[0] is off its in window
    sel = []
    for tn, t in T.items():
        for s in t.get("ft_slots", []):
            if s.get("regs_um") and s.get("in_window_um") and off_window(t, s) > TOL:
                sel.append((tn, s["name"]))
    xing = {(P.parts[part]["type"], slot): (lid, part) for lid in LANES for part, slot, _, _ in P.lane_crossings(lid)}
    assert set(sel) <= set(xing), sorted(set(sel) - set(xing))
    for tn, _ in sel:
        assert cnt[tn] == 1, (tn, "shared type")
    reach = P.reach
    smax = C.station_max(P)
    rows = {}
    old_regs = {(tn, sn): copy.deepcopy(next(x for x in T[tn]["ft_slots"] if x["name"] == sn)["regs_um"]) for tn, sn in sel}
    zr = set()                # types whose least-move sites push an added clock tap over the cap -> zroute rule
    for attempt in range(MAX_TAP_TRIES + 1):
        rows = {}
        for tn, sn in sorted(sel):
            t = T[tn]
            s = next(x for x in t["ft_slots"] if x["name"] == sn)
            s["regs_um"] = copy.deepcopy(old_regs[(tn, sn)])
            k = int(s["stations"])
            a = face_pt(t, s["in_face"], s["in_window_um"])
            b = face_pt(t, s["out_face"], s["out_window_um"])
            bl = blockers(P.types[tn])
            r0 = face_pt(t, s["in_face"], s["in_window_um"], inset=1.0)
            regs, slides = [r0], []
            R = reach - 2.0
            oldp = [tuple(map(float, r)) for r in s["regs_um"][1:]]
            route = [a]
            for q in oldp + [b]:
                if C.plen([route[-1], q]) > 1e-6:
                    route.append(q)
            L = C.plen(route)
            ideal, acc = [], 0.0          # arc position of each old site j = 1..k-1 on the old-path polyline
            for i, q in enumerate(oldp):
                ideal.append(C.plen([a] + oldp[:i + 1]))
            how = "path"
            if L / k > smax + 1e-6 or tn in zr:   # old path too long for the station budget, or it overloads a clock
                how, ideal = ("zroute-tap" if tn in zr else "zroute"), None   # tap of this type: FTREGS0 zroute rule
                route = C.zroute(a, b, s["in_face"], s["out_face"])
                L = C.plen(route)
            try:
                sites = site_dp(P.types[tn], route, L, k, bl, R, ideal) if k > 1 else []
                slides = [round(abs(sc - (ideal[j] if ideal else L * (j + 1) / k)), 2) for j, (sc, _) in enumerate(sites)]
            except AssertionError:
                how += "+lattice"
                sites = site_dp2(P.types[tn], route, L, k, bl, R, a, b, ideal_pts=(oldp if ideal else None))
                slides = [round(d, 2) for d, _ in sites]
            regs += [q for _, q in sites]
            chain = [a] + regs[1:] + [b]
            hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(chain, chain[1:])]
            assert max(hops) <= reach - 2.0 + 1e-6, (tn, sn, hops)       # 2 um: the next face flop's inset + pin offset
            assert L / k <= smax + 1e-6, (tn, sn, L, k)
            rows[f"{tn}.{sn}"] = dict(lane=xing[(tn, sn)][0], part=xing[(tn, sn)][1], stations=k, route_um=round(L, 1),
                                      regs0_off_window_um=round(off_window(t, s), 1), old_regs_um=s["regs_um"],
                                      new_regs_um=[[round(v, 4) for v in r] for r in regs], max_slide_um=max(slides or [0]), sites_on=how,
                                      max_in_slot_hop_um=round(max(hops), 1))
            s["regs_um"] = [[round(v, 4) for v in r] for r in regs]
            assert len(s["regs_um"]) == k
        over = tap_overload(raw, ppath, sorted({tn for tn, _ in sel}))
        if not over:
            break
        assert not (set(over) <= zr), ("clock tap over cap with the zroute rule too", over)
        zr |= set(over)
    out_text = json.dumps(raw) + "\n"
    # ---- EQ gate: only regs_um of the selected slots moved
    touched = sorted({tn for tn, _ in sel})
    for k_ in raw:
        if k_ != "partition_types":
            assert raw[k_] == orig[k_], k_
    for tn in raw["partition_types"]:
        a_, o_ = raw["partition_types"][tn], orig["partition_types"][tn]
        if tn not in touched:
            assert a_ == o_, tn
            continue
        assert {k_: v for k_, v in a_.items() if k_ != "ft_slots"} == {k_: v for k_, v in o_.items() if k_ != "ft_slots"}, tn
        for x, y in zip(a_["ft_slots"], o_["ft_slots"]):
            assert {k_: v for k_, v in x.items() if k_ != "regs_um"} == {k_: v for k_, v in y.items() if k_ != "regs_um"}
            if (tn, x["name"]) not in sel:
                assert x == y, (tn, x["name"])
    P2 = S.Plan(json.loads(out_text), ppath)
    for lid in P.lanes:
        assert P2.lane_natural(lid) == P.lane_natural(lid), lid
    # explorer-model lane hops (face flop at each in window, regs_um[1:], out pin) before / after
    def lane_hops(PP, lid):
        pts = []
        for part, slot, pa, pb in PP.lane_crossings(lid):
            sl = PP.slot(part, slot)
            pts.append(PP.port_point(pa))
            pts += [PP.to_die(part, tuple(r)) for r in sl["regs_um"][1:]]
        pts.append(PP.port_point(PP.lanes[lid]["ports"][-1]))
        return max(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))
    rep = dict(event=EVENT, base_plan_sha256=base_sha, rule=f"regs_um[0] > {TOL} um from the in window", slots=len(sel),
               touched_types=touched, lanes=list(LANES), reach_um=reach,
               lane_max_hop_um={lid: [round(lane_hops(P, lid), 1), round(lane_hops(P2, lid), 1)] for lid in LANES},
               per_slot=rows,
               eq_gate=dict(positions_only=True, station_counts_identical=True, lane_natural_identical=True,
                            changed_paths=[f"partition_types.{tn}.ft_slots[{sn}].regs_um" for tn, sn in sorted(sel)]))
    return out_text, rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--base-sha", default=BASE_SHA)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("report", nargs="?")
    a = ap.parse_args()
    text, rep = derive(a.plan_in, a.base_sha)
    if a.check:
        assert open(a.plan_out).read() == text, "output differs from re-derivation"
        print("CHECK PASS", sha(text))
        return
    open(a.plan_out, "w").write(text)
    rep["output_plan_sha256"] = sha(text)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(out=rep["output_plan_sha256"], slots=rep["slots"], types=rep["touched_types"],
                          lane_max_hop_um=rep["lane_max_hop_um"])))


if __name__ == "__main__":
    main()
