#!/usr/bin/env python3
"""CLOCK-KV-R12 10-26: minimal-move re-site of ft station cells that a plan delta put inside moved hard cores.

When a plan delta moves cores (KV headmirror mirror flips / slides), ft stations planned on the old geometry can land
inside a core (check.py geometry: "actual-bit station cells/sites intersect physical macros").  ft_corridor.py re-plans
a whole type and needs the full bit band in free space at every station, which fails on the dense KV pv/hgi fields
with fixed (static-schedule) station counts.  This tool changes only the stations that hit a core, the least possible:
  implicit slots (no regs_um): the even-spaced station centres on the check.py route become explicit regs_um; a centre
      inside a core (+1.08-um keep-off) slides along the route to the nearest free point (<= MAX_SLIDE um);
  explicit bit sites: only the bit cells that intersect a core are re-sited to the nearest free legal row site
      (RowAllocator, cores blocked, existing station sites reserved), every other bit stays.
Station counts (static schedule), windows, pins, outlines and cores never change.  Hops are re-checked by check.py
(G0 hops/stations); the tool reports the max centre slide and max bit move per slot.
    ft_nudge.py PLAN OUT LEDGER
"""
import json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import schema as S  # noqa: E402
import check as C  # noqa: E402
import ft_corridor as FC  # noqa: E402
from gen_phys import type_pins  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from tools.die_trial.legal_sites import RowAllocator  # noqa: E402

KEEPOFF = 1.08
MAX_SLIDE = 150.0
CELL_DEFAULT = (1.404, .27)


def inside(pt, boxes):
    return any(x0 < pt[0] < x1 and y0 < pt[1] < y1 for x0, y0, x1, y1 in boxes)


def clock_points(t):
    """DIE-HBM-60 d44v: the type's clock branch buffers + leg repeaters (check.py clock: no FT bit site / station cell
    within CLOCK_BUF_HALO_UM of one) -- a re-site must keep off them like it keeps off the macros."""
    ck = t.get("clock") or {}
    pts = []
    for b in ck.get("branch_buffers") or []:
        pts.append(tuple(b["xy"]))
        pts += [tuple(r["xy"]) for r in b.get("leg_repeaters") or []]
    return pts


def near_clock(x, y, wh, pts, h=C.CLOCK_BUF_HALO_UM, eps=1e-6):
    return any(x - h - eps < q[0] < x + wh[0] + h + eps and y - h - eps < q[1] < y + wh[1] + h + eps for q in pts)


def rect_hits(r, boxes):
    return any(min(r[2], x1) - max(r[0], x0) > 1e-6 and min(r[3], y1) - max(r[1], y0) > 1e-6 for x0, y0, x1, y1 in boxes)



def nudge_explicit(regs, boxes, w, h, A, B, max_slide=None, step=8.0):
    """DIE-HBM-75 11-05: re-site an EXPLICIT regs_um chain (threaded / non-straight slots, e.g. HBM C-form) with the
    least change.  A station whose centre is free stays exactly where it is; a centre inside a core gets candidates =
    the nearest free box sides + free grid points <= max_slide away.  A DP picks one candidate per moved station that
    minimises the worst hop touching a MOVED station (hops between two kept stations are the route's own and are not
    scored), then the total slide.  A / B are the in / out face anchors (pin means).  Returns (regs, worst, max_slide).
    The plain z-route re-spacing of such a slot stretched hub hops to 780 um on HBM ev74f."""
    max_slide = MAX_SLIDE if max_slide is None else max_slide
    man = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])
    pts = [tuple(map(float, r)) for r in regs]
    cand, moved = [], []
    for q0 in pts:
        if not inside(q0, boxes):
            cand.append([(0.0, q0)]); moved.append(False); continue
        cs = []
        for x0, y0, x1, y1 in boxes:
            if x0 < q0[0] < x1 and y0 < q0[1] < y1:
                for e in ((x0 - .01, q0[1]), (x1 + .01, q0[1]), (q0[0], y0 - .01), (q0[0], y1 + .01)):
                    if 5.32 <= e[0] <= w - 5.32 and 5.32 <= e[1] <= h - 5.32 and not inside(e, boxes) \
                            and man(q0, e) <= max_slide:
                        cs.append((man(q0, e), e))
        for dx in np.arange(-max_slide, max_slide + .1, step):
            for dy in np.arange(-max_slide, max_slide + .1, step):
                e = (q0[0] + dx, q0[1] + dy)
                if abs(dx) + abs(dy) <= max_slide and 5.32 <= e[0] <= w - 5.32 and 5.32 <= e[1] <= h - 5.32 \
                        and not inside(e, boxes):
                    cs.append((abs(dx) + abs(dy), e))
        if not cs:
            raise SystemExit(f"explicit station at {q0} has no free point within {max_slide} um")
        cand.append(cs); moved.append(True)
    hop = lambda u, v, scored: man(u, v) if scored else 0.0
    back = [[((hop(A, q, moved[0]), d), None) for d, q in cand[0]]]
    for j in range(1, len(cand)):
        sc = moved[j] or moved[j - 1]
        back.append([min(((max(c[0][0], hop(cand[j - 1][i][1], q, sc)), c[0][1] + d), i) for i, c in enumerate(back[-1]))
                     for d, q in cand[j]])
    fin = min(((max(c[0][0], hop(cand[-1][i][1], B, moved[-1])), c[0][1]), i) for i, c in enumerate(back[-1]))
    idx = [fin[1]]
    for j in range(len(cand) - 1, 0, -1):
        idx.append(back[j][idx[-1]][1])
    idx = idx[::-1]
    out = [[round(cand[j][i][1][0], 4), round(cand[j][i][1][1], 4)] if moved[j] else list(pts[j]) for j, i in enumerate(idx)]
    return out, fin[0][0], max(cand[j][i][0] for j, i in enumerate(idx))


def main():
    plan, out, ledger_f = sys.argv[1:4]
    raw = json.loads(Path(plan).read_text()); P = S.Plan(raw)
    R = C.Report(True); C.check_ft_macro_sites(P, R)
    hit = {}
    for x in R.items:
        m = re.search(r"type (\S+) slot (\S+):", x["msg"])
        if m:
            hit.setdefault(m.group(1), set()).add(m.group(2))
    for tn, t in raw["partition_types"].items():           # bit sites inside a clock buffer / leg repeater halo
        pts = clock_points(t)
        for s in t.get("ft_slots") or [] if pts else []:
            wh = s.get("bit_site_cell_um", CELL_DEFAULT)
            if any(near_clock(x, y, wh, pts) for st in s.get("bit_sites_um") or [] for x, y in st):
                hit.setdefault(tn, set()).add(s["name"])
    ledger = []
    for tn, slots in sorted(hit.items()):
        t = raw["partition_types"][tn]; w, h = t["outline_um"]
        # DIE-HBM-59: the same obstacle union as check.py geometry (placed macros + G2 probe blockages of reuse leaves)
        macro = list(placement_boxes(t).values())
        boxes = [(a - KEEPOFF, b - KEEPOFF, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in macro]
        cpts = clock_points(t); hh = C.CLOCK_BUF_HALO_UM + 0.01
        cw0, ch0 = CELL_DEFAULT                            # a site whose cell LL is in this box is in the halo
        boxes += [(q[0] - hh - cw0, q[1] - hh - ch0, q[0] + hh, q[1] + hh) for q in cpts]
        pins = {}
        for bus, bit, _l, x, y, face in type_pins(P, tn):
            pins.setdefault(bus, {})[bit] = (x, y, face)
        alloc = RowAllocator((4.32, 4.32, w - 4.32, h - 4.32), blocked=boxes, cell_size=CELL_DEFAULT,
                             column_pitch=2.16, row_pitch=.27, origin=(4.32, 4.32))
        for s in t["ft_slots"]:                       # reserve every existing explicit site of the type
            cw_, ch_ = s.get("bit_site_cell_um", CELL_DEFAULT)
            for st in s.get("bit_sites_um") or []:
                for x, y in st:
                    alloc.reserve_rectangle((x, y, x + cw_, y + ch_))
        for s in t["ft_slots"]:
            if s["name"] not in slots:
                continue
            k = int(s.get("stations", 1)); rec = dict(type=tn, slot=s["name"], width=s["width"], stations=k)
            if s.get("bit_sites_um"):
                cw_, ch_ = s.get("bit_site_cell_um", CELL_DEFAULT); moved, dmax = 0, 0.0
                for j, st in enumerate(s["bit_sites_um"]):
                    for bi, (x, y) in enumerate(st):
                        if rect_hits((x, y, x + cw_, y + ch_), macro) or near_clock(x, y, (cw_, ch_), cpts):
                            c = np.array([x + cw_ / 2, y + ch_ / 2])
                            p, _ = alloc.allocate(c, 1, max_radius_um=MAX_SLIDE)
                            st[bi] = [round(float(p[0][0] - cw_ / 2), 6), round(float(p[0][1] - ch_ / 2), 6)]
                            moved += 1; dmax = max(dmax, float(np.abs(p[0] - c).sum()))
                rec.update(mode="bit_sites", bits_moved=moved, max_move_um=round(dmax, 2))
            else:
                pi, po = pins[s["name"] + "_i"], pins[s["name"] + "_o"]
                bits = sorted(set(pi) | set(po))
                def inset(p):
                    x, y, f = p
                    return {'E': (x - 1, y), 'W': (x + 1, y), 'N': (x, y - 1), 'S': (x, y + 1)}[f]
                A = np.mean([inset(pi.get(b_) or po[b_]) for b_ in bits], axis=0)
                B = np.mean([inset(po.get(b_) or pi[b_]) for b_ in bits], axis=0)
                fin = (pi.get(bits[0]) or po[bits[0]])[2]; fout = (po.get(bits[0]) or pi[bits[0]])[2]
                route = C.zroute(tuple(A), tuple(B), fin, fout); L = C.plen(route)
                if len(s.get("regs_um") or []) == k:     # explicit chain: keep the route, move only stations in a core
                    regs, worst, smax = nudge_explicit(s["regs_um"], boxes, w, h, A, B)
                    s["regs_um"] = regs
                    rec.update(mode="regs_explicit", max_hop_moved_um=round(worst, 1), max_slide_um=round(smax, 1))
                    ledger.append(rec)
                    continue
                # DP over free candidate points per station: minimise the worst hop (face pin register -> stations ->
                # face pin register; the faces are registered so the slot's hops are the lane's hops), then total slide
                hop0 = 0.0
                man = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])
                cand = []
                for j in range(1, k):
                    s0 = L * j / k
                    cs = [(abs(d), C.point_at(route, s0 + d)) for d in np.arange(-MAX_SLIDE, MAX_SLIDE + 0.1, 1.0)
                          if 0.0 <= s0 + d <= L]
                    free = [(d, q) for d, q in cs if not inside(q, boxes)]
                    # a route point inside a core may also step sideways out of it (nearest box side, ft_corridor.project)
                    for d, q in cs[::2]:
                        for x0, y0, x1, y1 in boxes:
                            if x0 < q[0] < x1 and y0 < q[1] < y1:
                                for e in ((x0 - .01, q[1]), (x1 + .01, q[1]), (q[0], y0 - .01), (q[0], y1 + .01)):
                                    if 5.32 <= e[0] <= w - 5.32 and 5.32 <= e[1] <= h - 5.32 and not inside(e, boxes):
                                        free.append((d + man(q, e), e))
                                break
                    cs = free
                    if not cs:
                        raise SystemExit(f"{tn}/{s['name']}: station {j} has no free point within {MAX_SLIDE} um")
                    cand.append(cs)
                prev_cost = [((max(0.0, man(A, q) - hop0), d), None) for d, q in cand[0]]
                back = [prev_cost]
                for j in range(1, len(cand)):
                    cur = []
                    for d, q in cand[j]:
                        best = min(((max(c[0][0], man(cand[j - 1][i][1], q) - hop0), c[0][1] + d), i)
                                   for i, c in enumerate(back[-1]))
                        cur.append(best)
                    back.append(cur)
                fin_ = min(((max(c[0][0], man(cand[-1][i][1], B) - hop0), c[0][1]), i) for i, c in enumerate(back[-1]))
                idx = [fin_[1]]
                for j in range(len(cand) - 1, 0, -1):
                    idx.append(back[j][idx[-1]][1])
                idx = idx[::-1]
                regs = [list(map(float, A))] + [[round(cand[j][i][1][0], 4), round(cand[j][i][1][1], 4)]
                                                for j, i in enumerate(idx)]
                smax = max(cand[j][i][0] for j, i in enumerate(idx))
                rec["max_hop_um"] = round(fin_[0][0], 1)
                s["regs_um"] = regs
                rec.update(mode="regs", len_um=round(L, 1), max_slide_um=round(smax, 1))
            ledger.append(rec)
    raw["note"] = "CLOCK-KV-R12 ft_nudge <- " + raw.get("note", "")[:200]
    Path(out).write_text(json.dumps(raw) + "\n")
    Path(ledger_f).write_text(json.dumps(ledger, indent=1) + "\n")
    print(f"slots {len(ledger)}; max slide {max([r.get('max_slide_um', 0) for r in ledger] or [0])} um; "
          f"max bit move {max([r.get('max_move_um', 0) for r in ledger] or [0])} um")


if __name__ == "__main__":
    main()
