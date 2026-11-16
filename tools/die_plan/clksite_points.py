#!/usr/bin/env python3
"""FABLE-DIE-KV 11-16 (FABLE-PD-KV-HG1 B-2): planned register points against the reserved die clock sites.

clock.reserved_sites_um rects of kind die_clock_tree are placement blockages (and M1-M7 obstructions) in the type build.
A planned register point that lies in one, or within CLEAR_UM of it, cannot be placed where the plan says.  G0 does not
check that.  Point classes (type frame):
  ft        ft_slots[].regs_um                      station centres (face points on the outline are skipped)
  ft_bit    ft_slots[].bit_sites_um[stage][bit]     per-bit flop cells (lower-left + bit_site_cell_um): cell overlap, no clearance
  istation  internal_stations[].regs_um
  reader    clock.landing_reader_start.branches[].stages[].xy_um
  writer    clock.landing_writer_start.branches[].stages[].xy_um

  clksite_points.py check PLAN [--rows SITES.json] [--json OUT]     exit 1 when a point is blocked
  clksite_points.py fix   PLAN -o OUT.json --ledger L.json [--rows SITES.json] [--max-move-um 12]
        every blocked point moves to the nearest free point on the edge of the grown rect (free = clear of every reserved
        rect, outside every hard core + halo, inside the outline, not on another planned point of its class); ft_bit sites
        move along their row by whole sites only (x step = the slot's bit_site_cell_um width).  Exit 1 when a point cannot
        move within --max-move-um.  --rows applies a clksite_reserve row file first (check / fix before the rows are in).
"""
import argparse, copy, json, sys
from pathlib import Path

CLEAR_UM = 0.5
CORE_HALO_UM = 2.16


def _rects(t):
    return [tuple(r["rect_um"]) for r in (t.get("clock") or {}).get("reserved_sites_um", []) if r.get("kind") == "die_clock_tree"]


def _cores(t):
    out = []
    for hc in t.get("hard_cores", []) or []:
        if "origin_um" in hc and "outline_um" in hc:
            (ox, oy), (w, h) = hc["origin_um"], hc["outline_um"]
            if str(hc.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
                w, h = h, w
            out.append((ox, oy, ox + w, oy + h))
    return out


class Index:
    def __init__(self, rects, grow, b=50.0):
        self.b, self.d = b, {}
        self.rs = [(r[0] - grow, r[1] - grow, r[2] + grow, r[3] + grow) for r in rects]
        for k, r in enumerate(self.rs):
            for i in range(int(r[0] // b), int(r[2] // b) + 1):
                for j in range(int(r[1] // b), int(r[3] // b) + 1):
                    self.d.setdefault((i, j), []).append(k)

    def hit(self, p):
        for k in self.d.get((int(p[0] // self.b), int(p[1] // self.b)), ()):
            r = self.rs[k]
            if r[0] < p[0] < r[2] and r[1] < p[1] < r[3]:
                return r
        return None


def points(t):
    """yield (class, container list, index, step or None): container[index] is the [x, y] point"""
    w, h = t["outline_um"]
    face = lambda p: p[0] <= 1e-6 or p[1] <= 1e-6 or p[0] >= w - 1e-6 or p[1] >= h - 1e-6
    for s in t.get("ft_slots", []) or []:
        for i, p in enumerate(s.get("regs_um") or []):
            if not face(p):
                yield "ft", s["regs_um"], i, None
        step = (s.get("bit_site_cell_um") or [None])[0]
        for st in s.get("bit_sites_um") or []:
            if st and isinstance(st[0], (list, tuple)):
                for i in range(len(st)):
                    yield "ft_bit", st, i, step
            elif st and len(st) == 2:
                pass
    for s in t.get("internal_stations", []) or []:
        for i, p in enumerate(s.get("regs_um") or []):
            if not face(p):
                yield "istation", s["regs_um"], i, None
    ck = t.get("clock") or {}
    for cls, key in (("reader", "landing_reader_start"), ("writer", "landing_writer_start")):
        for br in ((ck.get(key) or {}).get("branches") or {}).values():
            for sg in br.get("stages") or []:
                if isinstance(sg.get("xy_um"), list) and len(sg["xy_um"]) == 2:
                    yield cls, sg, "xy_um", None


def _get(c, i):
    return c[i]


def scan(t, fix=False, max_move=12.0):
    rs = _rects(t)
    if not rs:
        return {}, []
    w, h = t["outline_um"]
    rv, cv, rx = Index(rs, CLEAR_UM), Index(_cores(t), CORE_HALO_UM), Index(rs, 0.0)
    cell = {}
    for s in t.get("ft_slots", []) or []:
        for st in s.get("bit_sites_um") or []:
            cell[id(st)] = tuple(s.get("bit_site_cell_um") or (1.404, 0.27))
    used = {}
    pts = list(points(t))
    for cls, c, i, step in pts:
        p = _get(c, i)
        used.setdefault(cls, set()).add((round(p[0], 3), round(p[1], 3)))
    count, ledger = {}, []
    e = 0.01
    for cls, c, i, step in pts:
        p = _get(c, i)
        if cls == "ft_bit":                         # lower-left of a flop cell: blocked when the cell overlaps a rect
            cw, ch = cell.get(id(c), (1.404, 0.27))
            r = next((q for q in (rx.hit((p[0] + fx * cw, p[1] + fy * ch)) for fx in (0.02, 0.5, 0.98) for fy in (0.1, 0.9))
                      if q is not None), None)
        else:
            r = rv.hit(p)
        if r is None:
            continue
        count[cls] = count.get(cls, 0) + 1
        if not fix:
            continue
        cands = []
        if cls == "ft_bit":                         # flop cells are never moved here: the clock tree must avoid them
            ledger.append(dict(cls=cls, old=list(p), new=None))                 # (die_trial --clock-point-keepouts)
            continue
        else:
            seen, front = set(), [r]
            for _ in range(4):                      # edges of the grown rect, and of any rect met on the way
                nxt = []
                for q in front:
                    if q in seen:
                        continue
                    seen.add(q)
                    for cand in ((q[0] - e, p[1]), (q[2] + e, p[1]), (p[0], q[1] - e), (p[0], q[3] + e)):
                        cands.append(cand)
                        o = rv.hit(cand)
                        if o is not None:
                            nxt.append(o)
                front = nxt
        best = None
        for q in sorted(cands, key=lambda q: abs(q[0] - p[0]) + abs(q[1] - p[1])):
            q = (round(q[0], 3), round(q[1], 3))
            d = abs(q[0] - p[0]) + abs(q[1] - p[1])
            if d > max_move:
                break
            if not (0.0 < q[0] < w and 0.0 < q[1] < h) or rv.hit(q) or cv.hit(q) or q in used.get(cls, ()):
                continue
            best = (q, d)
            break
        if best is None:
            ledger.append(dict(cls=cls, old=list(p), new=None))
            continue
        used[cls].add(best[0])
        ledger.append(dict(cls=cls, old=list(p), new=list(best[0]), move_um=round(best[1], 3)))
        c[i] = list(best[0])
    return count, ledger


def run(plan, fix=False, max_move=12.0):
    total, per, led = {}, {}, {}
    for tn, t in sorted(plan["partition_types"].items()):
        c, l = scan(t, fix, max_move)
        if c:
            per[tn] = c
            for k, v in c.items():
                total[k] = total.get(k, 0) + v
        if l:
            led[tn] = l
    return total, per, led


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("check", "fix")); ap.add_argument("plan")
    ap.add_argument("--rows"); ap.add_argument("--json"); ap.add_argument("-o"); ap.add_argument("--ledger")
    ap.add_argument("--max-move-um", type=float, default=12.0)
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    if a.rows:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import die_rows
        die_rows.apply_rows(plan, json.load(open(a.rows)))
    if a.cmd == "check":
        total, per, _ = run(plan)
        rep = dict(blocked=total, per_type=per, clear_um=CLEAR_UM)
        if a.json:
            json.dump(rep, open(a.json, "w"), indent=1)
        print(json.dumps(dict(blocked=total, types=len(per))))
        return 1 if total else 0
    if not a.o or not a.ledger:
        ap.error("fix needs -o and --ledger")
    total, per, led = run(plan, True, a.max_move_um)
    left, _, _ = run(copy.deepcopy(plan))
    stuck = sum(1 for l in led.values() for x in l if x["new"] is None)
    moves = [x["move_um"] for l in led.values() for x in l if x["new"] is not None]
    json.dump(plan, open(a.o, "w"), indent=1)
    json.dump(dict(blocked_before=total, per_type=per, moved=len(moves), max_move_um=max(moves, default=0.0),
                   not_moved=stuck, blocked_after=left, ledger=led), open(a.ledger, "w"), indent=1)
    print(json.dumps(dict(blocked_before=total, moved=len(moves), max_move_um=max(moves, default=0.0), not_moved=stuck,
                          blocked_after=left)))
    return 1 if stuck or left else 0


if __name__ == "__main__":
    sys.exit(main())
