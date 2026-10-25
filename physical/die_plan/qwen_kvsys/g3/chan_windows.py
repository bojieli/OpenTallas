#!/usr/bin/env python3
"""KV-PLAN 10-25 (plan v3.9c): face pins in CHANNEL MOUTHS.

Diagnosis (G2, results/arch/kv_plan_1025): the v3.9 face windows spread every port uniformly along the face, so ~60 %
of the hg/hgi/pv/hub face pins sit in front of a hard core.  The cores obstruct M1-M7 (signals <= M7), so those pins
can only escape along the 17-35 um strip between the face and the core row: PV v6 G2 421k and HGI v6 1.28M overflow
whatever the station sites.  The channel-lattice pilot (same probe, pins in the mouths, per-bit stations) routes
hgi_v6 / pv_v6 / pv_v4 / hgi_v8 / hub_C / hub_Wi / hub_Wo with GRT overflow 0.

This pass re-windows every partition-to-partition port: for each abutted boundary segment the mouths are the along-face
intervals that neither side's hard cores (projected on the face axis, +-CLEAR um) cover, and the segment's ports are
packed into them IN THEIR CURRENT ORDER (schema.window_for: <= per_um pins/um, <= pin_track_max of the PG-free
tracks; per_um raised step-wise only for a segment that does not fit at the budget, reported), with the largest uniform
gap between ports.  The packing direction follows side A's type frame, so mirrored instances stay identical.  Die IO windows and
partition placement are unchanged.  Ft slots then use per-bit station sites on each bit's own route (centroid regs_um
dropped: they stacked a whole slot on one point); a slot's station count is raised only where its new route needs it
for the 405-um hop rule (count never lowered: no lane gets faster by accident).
usage: chan_windows.py IN_PLAN > OUT_PLAN  [--report R.json] [--clear 4] [--per-um 6] [--depth 110]

STATUS 2026-10-25 (DRAFT, not a plan delta yet): on v3.9 it re-windows 2862 ports, 233/272 segments fit; G0 of the
draft = 313 latency (regen in run_v39c.sh), 242 face density > 6/um (budget question), 58 replicated-type mismatches
(kv3_hg, kv3_hroot: segments are packed in the die frame per boundary -- next: pack once per (type, type face) in the
type frame on the intersection of all instances' mouths), and 39 NO_FIT segments that need geometry (hg|hg N/S: the
881-um qkd_ectlk core spans the channel lattice; hub_Wi|hub_Wo; pv|pv N/S 24 pins/um of mouth).
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R / "tools/die_plan"))
import check  # noqa: E402
import schema as S  # noqa: E402

EDGE_UM = 6.0      # keep pins this far from a segment end (partition corner)
REACH = 405.0


def die_cores(P, inst):
    t = P.ptype(inst)
    out = []
    for c in t.get("hard_cores", []):
        if "origin_um" not in c or "outline_um" not in c:
            continue
        x0, y0 = c["origin_um"]
        w, h = c["outline_um"]
        if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        a, b = P.to_die(inst, (x0, y0)), P.to_die(inst, (x0 + w, y0 + h))
        out.append((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])))
    return out


def subtract(lo, hi, blocks):
    cur, out = lo, []
    for a, b in sorted(blocks):
        if b <= cur:
            continue
        if a > cur:
            out.append((cur, min(a, hi)))
        cur = max(cur, b)
        if cur >= hi:
            break
    if cur < hi:
        out.append((cur, hi))
    return [(a, b) for a, b in out if b - a > 1.0]


def _kth_track(L, ln, at, k, down):
    """coordinate of the k-th PG-free track of layer ln from `at` upward (downward when down), k >= 1."""
    p, off = L["pitch_um"], L["offset_um"]
    j = math.ceil((at - off) / p - 1e-9) if not down else math.floor((at - off) / p + 1e-9)
    step = -1 if down else 1
    c = 0
    while True:
        y = off + j * p
        if not S.pg_blocked(ln, y):
            c += 1
            if c >= k:
                return y
        j += step


def win_len(P, pr, at, per_um, down=False):
    """window [lo, hi] of port pr starting at `at` (ending at `at` when down) with <= per_um pins/um and <= pin_track_max
    of the PG-free tracks on each of its layers (the rule of schema.window_for, solved directly)."""
    names, n = pr["layers"], S.port_pins_count(pr)
    tm = P.budgets.get("pin_track_max", 0.6)
    nl = len(names)
    ext = max(n / per_um, 0.016)
    for i, ln in enumerate(names):
        k = len(range(i, n, nl))
        if k:
            t = _kth_track(P.layers[ln], ln, at, math.ceil(k / tm - 1e-9), down)
            ext = max(ext, abs(t - at) + 0.016)
    ext = math.ceil(ext / 0.016 - 1e-9) * 0.016
    return (round(at, 4), round(at + ext, 4)) if not down else (round(at - ext, 4), round(at, 4))


def pack(P, order, mouths, per_um, gap, down):
    """ports -> mouths by first-fit decreasing (a port never straddles a core), then inside each mouth in their
    original order, packed from the mouth's low end (high end when `down`, the mirrored type frame) with `gap` um
    between ports; None if they do not fit."""
    ms = list(reversed(mouths)) if down else list(mouths)
    est = {pid: n_len(P, pr, per_um) for pid, pr in order}
    free = [b - a_ for a_, b in ms]
    asg = defaultdict(list)
    rank = {pid: i for i, (pid, _) in enumerate(order)}
    for pid, pr in sorted(order, key=lambda x: (-est[x[0]], rank[x[0]])):
        for mi in range(len(ms)):
            if free[mi] >= est[pid] + 2 * gap + 0.05:
                free[mi] -= est[pid] + gap
                asg[mi].append((pid, pr))
                break
        else:
            return None
    res = {}
    for mi, lst in asg.items():
        lst.sort(key=lambda x: rank[x[0]], reverse=down)
        pos = (ms[mi][1] - gap) if down else (ms[mi][0] + gap)
        for pid, pr in lst:
            lo, hi = win_len(P, pr, pos, per_um, down)
            if lo < ms[mi][0] - 1e-9 or hi > ms[mi][1] + 1e-9:
                return None
            res[pid] = (lo, hi)
            pos = (lo - gap) if down else (hi + gap)
    return res


def n_len(P, pr, per_um):
    """position-free length estimate of a port window (+2 % for PG-band track loss)."""
    lo, hi = win_len(P, pr, 0.0, per_um)
    return (hi - lo) * 1.02


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--report")
    ap.add_argument("--clear", type=float, default=4.0)
    ap.add_argument("--per-um", type=float, default=6.0)
    ap.add_argument("--depth", type=float, default=110.0)
    a = ap.parse_args()
    raw = S.load(a.plan)
    P = S.Plan(raw, Path(a.plan).resolve())
    ports = {p["id"]: p for p in raw["ports"]}
    seg = defaultdict(list)
    for pid, pr in P.ports.items():
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s not in P.parts or d not in P.parts:
            continue
        # one boundary = one segment: ports of BOTH directions share its mouths (keyed from the lower name's side)
        seg[(s, d, pr["face"]) if s < d else (d, s, S.OPP[pr["face"]])].append(pid)
    rep = dict(schema="opentallas.kv_chan_windows.v1", clear_um=a.clear, per_um=a.per_um, segments=[])
    moved = 0
    for (s, d, f), pids in sorted(seg.items()):
        ra, rb = P.rect(s), P.rect(d)
        ax = 1 if f in "EW" else 0
        lo, hi = max(ra[ax], rb[ax]) + EDGE_UM, min(ra[ax + 2], rb[ax + 2]) - EDGE_UM
        blocks = []
        # the boundary line (die frame) and, per side, only the cores within --depth of it: a pin in front of a deeper
        # core enters a free strip at least --depth wide (a channel) and turns there
        nax = 0 if f in "EW" else 1
        line = ra[nax + 2] if f in "EN" else ra[nax]
        for inst in (s, d):
            for r in die_cores(P, inst):
                if min(abs(r[nax] - line), abs(r[nax + 2] - line)) <= a.depth:
                    blocks.append((r[ax] - a.clear, r[ax + 2] + a.clear))
        mouths = subtract(lo, hi, blocks)
        n = sum(ports[p]["width"] for p in pids)
        M = sum(b - a_ for a_, b in mouths)
        order = sorted(((p, ports[p]["width"]) for p in pids), key=lambda x: sum(ports[x[0]]["window_um"]) / 2)
        cov = sum(1 for p in pids if not any(m0 <= min(ports[p]["window_um"]) and max(ports[p]["window_um"]) <= m1
                                             for m0, m1 in mouths))
        rec = dict(a=s, b=d, face=f, ports=len(pids), pins=n, mouth_um=round(M, 1), seg_um=round(hi - lo, 1),
                   in_front_of_core_before=cov)
        if not mouths:
            rec["verdict"] = "NO_MOUTH"
            rep["segments"].append(rec)
            continue
        pr_ = {p: ports[p] for p in pids}
        order = [(p, pr_[p]) for p, _ in order]
        # canonical packing direction = the TYPE frame of side s: a mirrored instance packs mirrored, so replicated
        # types keep identical pin tables
        o = P.parts[s].get("orient", "R0")
        down = (o in ("MX", "R180")) if f in "EW" else (o in ("MY", "R180"))
        res, used_per = None, None
        for per_um in (a.per_um, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0, 24.0, 32.0, 48.0):
            res = pack(P, order, mouths, per_um, 0.0, down)
            if res:
                used_per = per_um
                break
        if not res:
            rec["verdict"] = "NO_FIT"
            rep["segments"].append(rec)
            continue
        # spread: the largest uniform gap that still fits (bisection), so pins use the whole mouth
        g0, g1 = 0.0, M / max(len(pids), 1)
        for _ in range(14):
            gm = (g0 + g1) / 2
            r2 = pack(P, order, mouths, used_per, gm, down)
            if r2:
                res, g0 = r2, gm
            else:
                g1 = gm
        rec["pins_per_um_budget_used"] = used_per
        dd = n / M
        for pid, (w0, w1) in res.items():
            ports[pid]["window_um"] = [round(w0, 4), round(w1, 4)]
            moved += 1
        rec.update(verdict="OK", pins_per_um=round(dd, 2))
        rep["segments"].append(rec)
    # ft slots: per-bit station sites on each bit's route; raise the count only where the new route needs it
    raw2 = raw
    P2 = S.Plan(raw2, Path(a.plan).resolve())
    need = defaultdict(int)
    for lid in P2.lanes:
        for part, slot, pa, pb in P2.lane_crossings(lid):
            s_ = P2.slot(part, slot) or {}
            seg_ = check.zroute(P2.port_point(pa), P2.port_point(pb), P2.die_face(part, s_.get("in_face", "W")),
                                P2.die_face(part, s_.get("out_face", "E")))
            L = check.plen(seg_)
            need[(P2.parts[part]["type"], slot)] = max(need[(P2.parts[part]["type"], slot)], math.ceil(L / REACH - 1e-9))
    raised = []
    for tn, t in raw2["partition_types"].items():
        for sl in t.get("ft_slots", []):
            for k in ("regs_um", "bit_sites_um", "bit_site_cell_um"):
                sl.pop(k, None)
            k0 = int(sl.get("stations", 1))
            k1 = max(k0, need.get((tn, sl["name"]), 0))
            if k1 != k0:
                sl["stations"] = k1
                raised.append(dict(type=tn, slot=sl["name"], before=k0, after=k1))
    rep.update(ports_rewindowed=moved, stations_raised=raised,
               worst=sorted((r for r in rep["segments"] if "pins_per_um" in r), key=lambda r: -r["pins_per_um"])[:20])
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(raw2, indent=1))
    bad = [r for r in rep["segments"] if r["verdict"] != "OK"]
    print(f"chan_windows: {len(rep['segments'])} segments, {moved} ports re-windowed, {len(bad)} not OK, "
          f"{len(raised)} slot station counts raised", file=sys.stderr)


if __name__ == "__main__":
    main()
