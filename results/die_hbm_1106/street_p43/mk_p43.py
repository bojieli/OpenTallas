#!/usr/bin/env python3
"""DIE-HBM-82-G0C d44v part 43: G0C class F (street_die_leg) -- die lane stations off the hard cores, least move.

G0C street_die_leg (streets.py, 12.10c) flags 75 lane stations whose lane-geometry point lies inside a hard core or a
type clock keep-out.  Three sub-classes on main:
  F1 (46 points, q_b000/001/010/011 + __physical_v1): explicit bit-site slots whose regs_um[j] is a stale band
     centroid inside a core while EVERY bit cell of that stage is already on a free legal site.  Fix (least move):
     regs_um[j] = centre of one of that stage's real bit sites (a real free site), the one that minimises the worst
     centre-level hop to its neighbours (regs_um[j-1] or the in-face anchor, regs_um[j+1] or the out-face anchor), then
     the move.  No cell moves.  (The ft_s0_resite middle-bit medoid moved q_b000 points up to 392 um and the plain
     nearest site stretched lane hops past 0.9 x reach on G0C; both tried on this event.)
  F3 (7 points, q_b102 + __physical_v1): bit-site-less normal slots whose last explicit station sits in the type's
     N-edge clock keep-out strip (y 1491.56-1555.2).  Fix = ft_nudge.nudge_explicit (route kept, only stations inside
     an obstacle move, DP on the worst touched hop); obstacles = placement boxes + hard cores + clock keep-outs, 1.08 keep-off.
  F2 (22 points): S0 of a NORMAL slot = the input-face site 1 um inside the pin (die_hop_scan.input_site, never regs_um[0])
     falls in a core that abuts the partition face under the in-window (q_b111 sfucore lanes W/E, q_b102 idx ra S) or in
     the q_b102 N-edge clock keep-out.  No station move can fix it (S0 is at the pin); it needs a window re-pin.
     NOT changed here (listed in the event record).
Station counts, windows, pins, outlines and cores never change: 0 pin cycles.
    mk_p43.py POR_PLAN.json D44V_DIR LEDGER.json   (POR_PLAN = the materialized d44v POR, used for pins only)"""
import gzip, json, sys
from pathlib import Path
HERE = Path(sys.argv[0]).resolve()
sys.path.insert(0, "tools/die_plan"); sys.path.insert(0, ".")
import schema as S  # noqa: E402
import check as C  # noqa: E402
from gen_phys import type_pins  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402
from die_hop_scan import normal_slot  # noqa: E402
from ft_nudge import nudge_explicit, KEEPOFF  # noqa: E402

por, D, ledger_f = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
P = S.Plan(S.load(por), Path(por))
raw = json.loads(gzip.decompress((D / "die_plan.json.gz").read_bytes()))


def obstacles(t):
    o = [tuple(h["origin_um"][:2]) + (h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
         for h in t.get("hard_cores") or []]
    o += [tuple(k) for k in (t.get("clock") or {}).get("keepouts_um") or []]
    return o


def inn(p, boxes):
    return any(a < p[0] < c and b < p[1] < d for a, b, c, d in boxes)


PINS = {}


def anchors(tn, s):
    """in / out face anchors of a slot = mean of its pins 1 um inside the face (ft_nudge convention)."""
    if tn not in PINS:
        PINS[tn] = {}
        for bus, bit, _l, x, y, face in type_pins(P, tn):
            PINS[tn].setdefault(bus, {})[bit] = (x, y, face)
    pi, po = PINS[tn][s["name"] + "_i"], PINS[tn][s["name"] + "_o"]
    bits = sorted(set(pi) | set(po))
    ins = lambda p: {'E': (p[0] - 1, p[1]), 'W': (p[0] + 1, p[1]), 'N': (p[0], p[1] - 1), 'S': (p[0], p[1] + 1)}[p[2]]
    A = tuple(sum(ins(pi.get(b) or po[b])[i] for b in bits) / len(bits) for i in (0, 1))
    B = tuple(sum(ins(po.get(b) or pi[b])[i] for b in bits) / len(bits) for i in (0, 1))
    return A, B


ledger, f2 = [], []
for tn in sorted(raw["partition_types"]):
    t = raw["partition_types"][tn]
    if tn not in P.types:
        continue
    ko = obstacles(t)
    for s in t.get("ft_slots") or []:
        regs = s.get("regs_um")
        if not regs:
            continue
        norm = normal_slot(P, tn, s["name"])
        bad = [j for j, r in enumerate(regs) if inn(r, ko) and not (j == 0 and norm)]
        if not bad:
            continue
        before = [list(r) for r in regs]
        if s.get("bit_sites_um"):
            cw, ch = s.get("bit_site_cell_um", (1.404, .27))
            assert len(s["bit_sites_um"]) == len(regs) - 1, (tn, s["name"])
            A, B = anchors(tn, s)
            man = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])
            new = [list(r) for r in regs]
            for j in range(1, len(regs)):
                if j not in bad:
                    continue
                prev = A if j == 1 else new[j - 1]
                nxt = B if j == len(regs) - 1 else new[j + 1]
                cs = [(x + cw / 2, y + ch / 2) for x, y in s["bit_sites_um"][j - 1]]
                cs = [c for c in cs if not inn(c, ko)]
                q = min(cs, key=lambda c: (round(max(man(prev, c), man(c, nxt)), 1), man(c, regs[j])))
                new[j] = [round(q[0], 4), round(q[1], 4)]
            s["regs_um"] = new
            mv = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(before, s["regs_um"]))
            ledger.append(dict(type=tn, slot=s["name"], sub="F1", mode="bit_site_minmax_hop", stations=s["stations"], bad=bad,
                               max_move_um=round(mv, 2)))
        else:
            A, B = anchors(tn, s)
            boxes = [(a - KEEPOFF, b - KEEPOFF, c + KEEPOFF, d + KEEPOFF) for a, b, c, d in list(placement_boxes(t).values()) + ko]
            w, h = t["outline_um"]
            keep0 = list(regs[0])
            new, worst, smax = nudge_explicit(regs, boxes, w, h, A, B)
            if norm:
                new[0] = keep0                     # S0 of a normal slot is the input-face site, regs_um[0] is not used
            s["regs_um"] = new
            ledger.append(dict(type=tn, slot=s["name"], sub="F3", mode="nudge_explicit", stations=s["stations"], bad=bad,
                               worst_moved_hop_um=round(worst, 1), max_slide_um=round(smax, 1),
                               moved=[[j, before[j], new[j]] for j in range(len(new)) if new[j] != before[j]]))
        s["note"] = (s.get("note", "") + " | DIE-HBM-82-G0C d44v part 43: regs_um station off the core/keep-out (street_die_leg)").lstrip(" |")
b = (json.dumps(raw) + "\n").encode()
with open(D / "die_plan.json.gz", "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
    g.write(b)
Path(ledger_f).write_text(json.dumps(ledger, indent=1) + "\n")
print("P43 slots", len(ledger), {k: sum(1 for r in ledger if r["sub"] == k) for k in ("F1", "F3")})
