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


def side_map(P, part, df):
    """affine map (s, k) die coordinate along die face df of `part` -> coordinate along the face in its TYPE frame."""
    p = P.parts[part]
    w, h = P.ptype(part)["outline_um"]
    o = P.orient(part)
    if df in "EW":
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    else:
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    return (-1, base + ext) if flip else (1, -base)


def comp(f, g):
    """f o g for affine maps x -> s x + k."""
    return (f[0] * g[0], f[0] * g[1] + f[1])


def inv(f):
    return (f[0], -f[0] * f[1])


def app(f, x):
    return f[0] * x + f[1]


def map_iv(f, iv):
    a, b = app(f, iv[0]), app(f, iv[1])
    return (min(a, b), max(a, b))


# adjacent windows keep >= 2 M6/M7 pitches apart: two abutting windows can put their edge pins on one track
MIN_GAP = 0.2


def segment_mouths(P, s, d, f, clear, depth):
    ra, rb = P.rect(s), P.rect(d)
    ax = 1 if f in "EW" else 0
    lo, hi = max(ra[ax], rb[ax]) + EDGE_UM, min(ra[ax + 2], rb[ax + 2]) - EDGE_UM
    nax = 0 if f in "EW" else 1
    line = ra[nax + 2] if f in "EN" else ra[nax]
    blocks = []
    # per side, only the cores within `depth` of the boundary: a pin in front of a deeper core enters a free strip at
    # least `depth` wide (a channel) and turns there
    for inst in (s, d):
        for r in die_cores(P, inst):
            if min(abs(r[nax] - line), abs(r[nax + 2] - line)) <= depth:
                blocks.append((r[ax] - clear, r[ax + 2] + clear))
    return (lo, hi), subtract(lo, hi, blocks)


def free_from(forb, start, L, limit):
    """lowest r >= start with [r, r+L] clear of every forbidden interval and r+L <= limit (None if none)."""
    r = start
    for a, b in sorted(forb):
        if b <= r:
            continue
        if a >= r + L:
            break
        r = b
    return r if r + L <= limit + 1e-9 else None


def core_side_limits(P, plan_dir, types=None):
    """{(type, bus): [(type face, lo, hi)]}: a face bus wired to a hard-core port must keep its window on the side of the
    core that the port's pins face (check.py core_faces: mean cos(pin face normal, core centre -> window) >= 0), else the
    route wraps the core.  A port with pins on a face perpendicular to the bus face bounds the window by the core
    centre (type frame); pins facing the bus face or the opposite face add no bound."""
    side = check.load_core_conns(plan_dir, None)
    out = defaultdict(list)
    for tn, t in P.types.items():
        if types is not None and tn not in types:
            continue
        for hc in t.get("hard_cores", []):
            ports = side.get(tn, {}).get(hc["inst"], {})
            if not ports:
                continue
            try:
                pins = check.core_pins(hc, plan_dir)
            except (OSError, ValueError, KeyError):
                continue
            cw, ch = hc["outline_um"]
            o = hc.get("orient", "R0")
            dx, dy = hc.get("track_offset_um", [0.0, 0.0])
            cx, cy = hc["origin_um"][0] + dx + cw / 2, hc["origin_um"][1] + dy + ch / 2
            faces = defaultdict(set)
            for nm, _ln, x, y in pins:
                faces[nm.split("[")[0]].add(check._core_face(o, x, y, cw, ch))
            for lp, tg in ports.items():
                fs = faces.get(lp)
                if not fs or len(fs) != 1:
                    continue
                g = next(iter(fs))
                for v in tg:
                    k, _, bus = v.partition(":")
                    if k != "bus":
                        continue
                    for tf in "NSEW":
                        if (tf in "NS") == (g in "NS"):
                            continue          # parallel or opposite face: no bound
                        c = cx if tf in "NS" else cy
                        lo, hi = (c, 1e9) if g in "EN" else (-1e9, c)
                        out[(tn, bus)].append((tf, lo, hi))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--report")
    ap.add_argument("--clear", type=float, default=4.0)
    ap.add_argument("--per-um", type=float, default=6.0)
    ap.add_argument("--depth", type=float, default=110.0)
    # types whose face windows must respect their hard-core port sides (core_side_limits): the unbounded v3.9d pass
    # fails G0C core_faces only on the astk strip ports of hub_Wo / hub_Eo (the windows left the 41-um mouth beside the
    # astk core); bounding every core-bound bus over-constrains the pc/pv/hg mouths (21 NO_FIT)
    ap.add_argument("--core-bound-types", nargs="*", default=["kv3_hub_Wo", "kv3_hub_Eo"])
    a = ap.parse_args()
    raw = S.load(a.plan)
    P = S.Plan(raw, Path(a.plan).resolve())
    ports = {p["id"]: p for p in raw["ports"]}
    ninst = defaultdict(int)
    for pn, p in P.parts.items():
        ninst[p["type"]] += 1
    # --- segments (one abutted boundary) and their die-frame mouths
    seg_of, seg = {}, defaultdict(list)
    for pid, pr in P.ports.items():
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s not in P.parts or d not in P.parts:
            continue
        k = (s, d, pr["face"]) if s < d else (d, s, S.OPP[pr["face"]])
        seg_of[pid] = k
        seg[k].append(pid)
    mouths, span = {}, {}
    for k in seg:
        span[k], mouths[k] = segment_mouths(P, *k, a.clear, a.depth)
    # a feed-through port (lane entering / leaving a partition's ft slot) must sit in a THROUGH channel of its host:
    # its per-bit stations run straight across the host, so every host core along the face axis blocks it, at any
    # depth (v3.9d G2: kv3_pv_v7 ft26_o over the pv column at 216 um depth -> stations inside the core, 1332 M3 ovf)
    thru = defaultdict(set)
    for lid in P.lanes:
        for part, slot, pa, pb in P.lane_crossings(lid):
            if slot and part in P.parts and P.slot(part, slot):
                thru[pa].add(part)
                thru[pb].add(part)

    def port_mouths(pid):
        ms = mouths[seg_of[pid]]
        if pid not in thru:
            return ms
        ax = 1 if P.ports[pid]["face"] in "EW" else 0
        bl = [(r[ax] - a.clear, r[ax + 2] + a.clear) for h in thru[pid] for r in die_cores(P, h)]
        return [iv for lo, hi in ms for iv in subtract(lo, hi, bl)]
    # --- classes: ports that must share ONE window in a type frame.  A port side on a replicated type keys
    # (type, bus); every port with that key carries the same type-frame window, so the pin table is a type property.
    key_ports = defaultdict(list)          # key -> [(pid, die->key-frame map)]
    port_keys = defaultdict(list)
    for pid in seg_of:
        pr = P.ports[pid]
        for side, df in (("src", pr["face"]), ("dst", S.OPP[pr["face"]])):
            part = pr[side]["part"]
            tn = P.parts[part]["type"]
            if ninst[tn] > 1:
                kk = (tn, P.type_face(part, df), pr[side]["bus"])
                m = side_map(P, part, df)
                key_ports[kk].append((pid, m))
                port_keys[pid].append((kk, m))
    cls_of, classes, incons = {}, [], []
    for pid0 in sorted(seg_of):
        if pid0 in cls_of:
            continue
        # root frame: the type frame of the class's most replicated key (canonical: every type face packs from its
        # own low end), else the die frame
        ks = sorted(port_keys[pid0], key=lambda x: (-ninst[x[0][0]], x[0]))
        M = {pid0: ks[0][1] if ks else (1, 0.0)}
        st, members = [pid0], []
        cid = len(classes)
        cls_of[pid0] = cid
        while st:
            p = st.pop()
            members.append(p)
            for kk, m in port_keys[p]:
                k2root = comp(M[p], inv(m))
                for q, mq in key_ports[kk]:
                    Mq = comp(k2root, mq)
                    if q in M:
                        if Mq[0] != M[q][0] or abs(Mq[1] - M[q][1]) > 1e-3:
                            incons.append((p, q, kk))
                        continue
                    M[q] = Mq
                    cls_of[q] = cid
                    st.append(q)
        classes.append(dict(ports=sorted(members), M=M))
    lim = core_side_limits(P, Path(a.plan).resolve().parent, set(a.core_bound_types))
    # current root-frame windows must agree (the v3.9 pin tables are consistent)
    for c in classes:
        w = {p: map_iv(c["M"][p], ports[p]["window_um"]) for p in c["ports"]}
        v = list(w.values())
        c["cur"] = v[0]
        if any(abs(x[0] - v[0][0]) > 2e-3 or abs(x[1] - v[0][1]) > 2e-3 for x in v):
            incons.append(("window", c["ports"][0], len(c["ports"])))
        # allowed: intersection over member ports of their segments' mouths, root frame
        al = None
        for p in c["ports"]:
            ms = [map_iv(c["M"][p], m) for m in port_mouths(p)]
            al = ms if al is None else [(max(x0, y0), min(x1, y1)) for x0, x1 in al for y0, y1 in ms
                                        if min(x1, y1) - max(x0, y0) > 0.5]
        # hard-core port side bounds (type frame -> die -> root)
        for p in c["ports"]:
            pr = P.ports[p]
            for sd, df in (("src", pr["face"]), ("dst", S.OPP[pr["face"]])):
                part = pr[sd]["part"]
                for tf, lo, hi in lim.get((P.parts[part]["type"], pr[sd]["bus"]), []):
                    if tf != P.type_face(part, df):
                        continue
                    b = map_iv(comp(c["M"][p], inv(side_map(P, part, df))), (lo, hi))
                    al = [(max(x0, b[0]), min(x1, b[1])) for x0, x1 in (al or []) if min(x1, b[1]) - max(x0, b[0]) > 0.5]
                    c["bounded"] = True
        c["allowed"] = sorted(al or [])
        c["segs"] = sorted({seg_of[p] for p in c["ports"]})
    # packing components: classes sharing a boundary segment
    par = list(range(len(classes)))

    def fnd(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    by_seg = defaultdict(list)
    for i, c in enumerate(classes):
        for s_ in c["segs"]:
            by_seg[s_].append(i)
    for lst in by_seg.values():
        for i in lst[1:]:
            par[fnd(i)] = fnd(lst[0])
    comps = defaultdict(list)
    for i in range(len(classes)):
        comps[fnd(i)].append(i)

    def rep_port(c):
        """(port, its die->root map): the member whose window length is computed on its own die tracks."""
        p = c["ports"][0]
        return p, c["M"][p]

    def mirror_ok(c, rw):
        if len({c["M"][p][0] for p in c["ports"]}) < 2:
            return True
        ref = None
        for p in c["ports"]:
            dw = map_iv(inv(c["M"][p]), rw)
            q = dict(ports[p], window_um=[round(dw[0], 6), round(dw[1], 6)])
            try:
                pins = frozenset((b, ln, round(app(c["M"][p], x), 3)) for b, ln, x in S.pin_positions(q, P.layers))
            except ValueError:
                return False
            if ref is None:
                ref = pins
            elif pins != ref:
                return False
        return True

    def place(ci_list, per_um, gap, ffd):
        occ = defaultdict(list)            # seg -> [die intervals]
        res = {}
        order = sorted(ci_list, key=(lambda i: (-(classes[i]["est"]), classes[i]["cur"][0])) if ffd
                       else (lambda i: (classes[i]["segs"][0], classes[i]["cur"][0])))
        for i in order:
            c = classes[i]
            p0, M0 = rep_port(c)
            pr0 = ports[p0]
            L = c["est"]
            forb = []
            for p in c["ports"]:
                Mp = c["M"][p]
                for o0, o1 in occ[seg_of[p]]:
                    forb.append(map_iv(Mp, (o0 - gap, o1 + gap)))
            if not c["allowed"]:
                return None
            done = None
            for m0, m1 in c["allowed"]:
                r = m0 + gap
                while True:
                    r = free_from(forb, r, L, m1 - gap)
                    if r is None:
                        break
                    # exact window on the representative port's own die tracks
                    dlo = app(inv(M0), r)
                    w0, w1 = win_len(P, pr0, dlo, per_um, down=(M0[0] < 0))
                    rw = map_iv(M0, (w0, w1))
                    # mirrored members must get the mirrored pins (schema.spread has no mirror-symmetric pick for
                    # some odd-pin / even-track windows): grow the window one 0.016 step until they agree
                    for _ in range(40):
                        if mirror_ok(c, rw):
                            break
                        rw = (rw[0], round(rw[1] + 0.016, 4))
                    else:
                        r = r + 0.016
                        continue
                    if rw[1] > m1 - gap + 1e-9:
                        r = None
                        break
                    if any(x0 < rw[1] and rw[0] < x1 for x0, x1 in forb):
                        r = r + 0.016
                        continue
                    done = rw
                    break
                if done:
                    break
            if not done:
                return None
            for p in c["ports"]:
                dw = map_iv(inv(c["M"][p]), done)
                res[p] = dw
                occ[seg_of[p]].append(dw)
        return res

    rep = dict(schema="opentallas.kv_chan_windows.v2", mode="type_frame_classes", clear_um=a.clear, per_um=a.per_um,
               classes=len(classes), core_bounded=sum(1 for c in classes if c.get("bounded")), inconsistent=[list(map(str, x)) for x in incons[:20]], n_inconsistent=len(incons),
               components=[])
    moved = 0
    for root, cl in sorted(comps.items()):
        segs = sorted({s_ for i in cl for s_ in classes[i]["segs"]})
        pins = sum(ports[p]["width"] for i in cl for p in classes[i]["ports"])
        rec = dict(segments=len(segs), seg_names=["|".join(s_[:2]) + "." + s_[2] for s_ in segs[:6]],
                   classes=len(cl), ports=sum(len(classes[i]["ports"]) for i in cl), pins=pins)
        res = used = None
        for per_um in [a.per_um + 0.5 * i for i in range(int((16.0 - a.per_um) / 0.5) + 1)]:
            for i in cl:
                classes[i]["est"] = n_len(P, ports[classes[i]["ports"][0]], per_um)
            for ffd in (False, True):
                res = place(cl, per_um, MIN_GAP, ffd)
                if res:
                    used = (per_um, ffd)
                    break
            if res:
                break
        if not res:
            rec["verdict"] = "NO_FIT"
            rep["components"].append(rec)
            continue
        per_um, ffd = used
        # spread: the largest uniform gap that still fits
        mx = max((m1 - m0) for i in cl for m0, m1 in classes[i]["allowed"])
        g0, g1 = MIN_GAP, max(MIN_GAP, mx / 2)
        for _ in range(12):
            gm = (g0 + g1) / 2
            r2 = place(cl, per_um, gm, ffd)
            if r2:
                res, g0 = r2, gm
            else:
                g1 = gm
        for pid, (w0, w1) in res.items():
            ports[pid]["window_um"] = [round(w0, 4), round(w1, 4)]
            moved += 1
        rec.update(verdict="OK", per_um_budget=per_um, ffd=ffd, gap_um=round(g0, 3))
        rep["components"].append(rec)
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
    rep.update(ports_rewindowed=moved, stations_raised=raised)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(raw2, indent=1))
    bad = [r for r in rep["components"] if r["verdict"] != "OK"]
    print(f"chan_windows: {len(rep['components'])} packing components ({len(classes)} classes, {len(incons)} "
          f"inconsistent), {moved} ports re-windowed, {len(bad)} not OK, "
          f"{len(raised)} slot station counts raised", file=sys.stderr)


if __name__ == "__main__":
    main()
