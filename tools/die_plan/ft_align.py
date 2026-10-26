#!/usr/bin/env python3
"""Die-plan feed-through entry/exit alignment (opt-in, D-S81-B2 item A).

Problem (S81 die GRT 1.80M overflow): a north-south FT bit enters a partition on one
face and leaves it on the opposite face up to ~1 mm sideways. The die GRT must route
that lateral offset over the core field, where M6 is the only horizontal layer, and
spills the excess onto M7 wrong-way. Moving stations inside tiles cannot remove it,
because the offset is fixed by the partition FT windows (abstract pins).

Method: every N-S FT traversal (partition P, ft slot s: s_i on S/N face, s_o on the
opposite face) is linked into a chain through the ports that join consecutive
partitions. A chain ends at an anchor (a port whose other end is a functional bus,
e.g. a leaf DN/UP window, which is never moved) or at an E-W turn. Each chain gets a
target column = the centre of its anchor window (largest anchor if two differ), and
every movable port of the chain is placed at that column with the anchor's window
length, so bit b leaves at the x it entered. Where a seam is occupied the port takes
the nearest free hole (GAP spacing, MARGIN at seam ends). Ports of multi-instance
types are coupled (type-frame windows equal), so a placement is projected to every
instance and must be free there too. The residual lateral (anchor-to-anchor offsets
and blocked columns) is reported per traversal with its die rows, i.e. the H
corridors that must be reserved (--corridors).

Metric = sum over N-S traversals of width x |centre_in - centre_out| (die frame,
bit-um); `--measure` prints it without changing anything.

    ft_align.py PLAN --out OUT [--report R.json] [--types-only RE] [--min-len-frac F]
    ft_align.py PLAN --measure
Only port window_um and ft_slots in/out_window_um change. Stations / bit sites of the
changed types must be re-placed afterwards (ft_corridor.place), then gen latency + G0C.
"""
import argparse
import collections
import json
import math
import re
import sys
from pathlib import Path

OPP = dict(N="S", S="N", E="W", W="E")
MARGIN = 6.144
GAP = 3.072
PIN_UM_PER_LAYER = 1 / 5.8          # densest legal pin packing (um per pin per layer), = delta_dieft lower bound


class Plan:
    def __init__(self, raw, hub_re=None):
        self.raw = raw
        self.hub_re = re.compile(hub_re) if hub_re else None
        self.T = raw["partition_types"]
        self.PA = {p["name"]: p for p in raw["partitions"]}
        self.P = {pr["id"]: pr for pr in raw["ports"] if "window_um" in pr}
        self.inst = collections.defaultdict(list)
        for p in raw["partitions"]:
            self.inst[p["type"]].append(p["name"])

    # ---- geometry -------------------------------------------------------
    def rect(self, part):
        p = self.PA[part]
        w, h = self.T[p["type"]]["outline_um"]
        o = p.get("orient", "R0")
        assert o in ("R0", "MY", "MX", "R180"), (part, o)
        return p["origin_um"][0], p["origin_um"][1], p["origin_um"][0] + w, p["origin_um"][1] + h

    def _flip(self, part, df):
        o = self.PA[part].get("orient", "R0")
        return (df in "NS" and o in ("MY", "R180")) or (df in "EW" and o in ("MX", "R180"))

    def to_type(self, part, df, a, b):
        """die-frame window [a,b] on die face df -> type-frame window (coordinate along the face)."""
        x0, y0, x1, y1 = self.rect(part)
        lo, hi = (x0, x1) if df in "NS" else (y0, y1)
        if self._flip(part, df):
            return [round(hi - b, 3), round(hi - a, 3)]
        return [round(a - lo, 3), round(b - lo, 3)]

    def from_type(self, part, df, a, b):
        x0, y0, x1, y1 = self.rect(part)
        lo, hi = (x0, x1) if df in "NS" else (y0, y1)
        if self._flip(part, df):
            return [round(hi - b, 3), round(hi - a, 3)]
        return [round(lo + a, 3), round(lo + b, 3)]

    def slot(self, part, bus):
        if part not in self.PA:
            return None, None
        for s in self.T[self.PA[part]["type"]].get("ft_slots") or []:
            if bus == s["name"] + "_i":
                return s, "in_window_um"
            if bus == s["name"] + "_o":
                return s, "out_window_um"
        return None, None

    def die_face(self, pr, side):
        return pr["face"] if side == "src" else OPP[pr["face"]]

    def seam(self, pr):
        a, b = pr["src"]["part"], pr["dst"]["part"]
        return (a, b, pr["face"]) if a < b else (b, a, OPP[pr["face"]])

    def seam_span(self, key):
        a, b, f = key
        ra, rb = self.rect(a), self.rect(b)
        if f in "NS":
            return max(ra[0], rb[0]), min(ra[2], rb[2])
        return max(ra[1], rb[1]), min(ra[3], rb[3])

    # ---- traversals / chains -------------------------------------------
    def traversals(self):
        """(part, slot, in port, out port, ns?) for every ft slot with both ports present."""
        into, outof = {}, {}
        for pid, pr in self.P.items():
            into[(pr["dst"]["part"], pr["dst"]["bus"])] = pid
            outof[(pr["src"]["part"], pr["src"]["bus"])] = pid
        tr = []
        for part, p in self.PA.items():
            for s in self.T[p["type"]].get("ft_slots") or []:
                i, o = into.get((part, s["name"] + "_i")), outof.get((part, s["name"] + "_o"))
                if i and o:
                    ns = {s["in_face"], s["out_face"]} == {"N", "S"}
                    tr.append((part, s, i, o, ns))
        return tr

    def winref(self, part, bus):
        """(dict, key) holding the type-frame window of bus: ft slot in/out window, or (hub types only) a bus window."""
        s, k = self.slot(part, bus)
        if s is not None:
            return s, k
        if part in self.PA and self.hub_re and self.hub_re.search(self.PA[part]["type"]):
            for b in self.T[self.PA[part]["type"]].get("buses") or []:
                if b["name"] == bus and "window_um" in b:
                    return b, "window_um"
        return None, None

    def is_hub_bus(self, part, bus):
        return self.slot(part, bus)[0] is None and self.winref(part, bus)[0] is not None

    def movable(self, pid):
        """both ends are ft slots, or one end a slot and the other a functional bus of a hub type (--hub)."""
        pr = self.P[pid]
        ends = [(pr[sd]["part"], pr[sd]["bus"]) for sd in ("src", "dst")]
        if not all(self.winref(*e)[0] is not None for e in ends):
            return False
        return sum(self.is_hub_bus(*e) for e in ends) <= 1


def centre(w):
    return (w[0] + w[1]) / 2


def lateral_ew(plan):
    """E-W transits: y offset between entry and exit (vertical jog over the core field), bit-um."""
    tot = 0.0
    for part, s, i, o, ns in plan.traversals():
        if {s["in_face"], s["out_face"]} == {"E", "W"}:
            tot += abs(centre(plan.P[i]["window_um"]) - centre(plan.P[o]["window_um"])) * int(s["width"])
    return tot


def lateral(plan, wins=None, detail=False):
    wins = wins or {}
    tot, rows = 0.0, []
    for part, s, i, o, ns in plan.traversals():
        if not ns:
            continue
        wi = wins.get(i, plan.P[i]["window_um"]); wo = wins.get(o, plan.P[o]["window_um"])
        d = abs(centre(wi) - centre(wo)) * int(s["width"])
        tot += d
        if detail and d > 0:
            rows.append((d, part, plan.PA[part]["type"], s["name"], int(s["width"]), abs(centre(wi) - centre(wo)),
                         plan.rect(part)[1], plan.rect(part)[3]))
    rows.sort(reverse=True)
    return tot, rows


def chains(plan):
    """Ordered port lists linked through N-S traversals."""
    nxt, prv = {}, {}
    for part, s, i, o, ns in plan.traversals():
        if ns:
            nxt[i] = o; prv[o] = i
    out, seen = [], set()
    for pid in plan.P:
        if pid in prv or pid in seen or pid not in nxt:
            continue
        c = [pid]
        while c[-1] in nxt and nxt[c[-1]] not in seen and nxt[c[-1]] not in c:
            c.append(nxt[c[-1]])
        seen.update(c)
        out.append(c)
    for pid in plan.P:                    # pure cycles (none expected)
        if pid in nxt and pid not in seen:
            c = [pid]
            while nxt.get(c[-1]) and nxt[c[-1]] not in c:
                c.append(nxt[c[-1]])
            seen.update(c); out.append(c)
    return out


def align(plan, min_len_frac=1.0, type_re=None, target_mode="anchor"):
    P = plan.P
    # couple keys: (type, bus) -> [(pid, part, die face)]
    tb = collections.defaultdict(list)
    for pid, pr in P.items():
        for sd in ("src", "dst"):
            part = pr[sd]["part"]
            if part in plan.PA:
                tb[(plan.PA[part]["type"], pr[sd]["bus"])].append((pid, part, plan.die_face(pr, sd)))
    # seam occupancy: free holes after fixed windows
    seam_ports = collections.defaultdict(list)
    for pid, pr in P.items():
        seam_ports[plan.seam(pr)].append(pid)
    allowed = None
    if type_re:
        allowed = set()
        for pid, pr in P.items():
            if all(re.search(type_re, plan.PA[pr[sd]["part"]]["type"]) for sd in ("src", "dst")):
                allowed.add(pid)
    mov = {pid for pid in P if plan.movable(pid) and plan.seam(P[pid])[2] in "NS" and (allowed is None or pid in allowed)}
    # whole coupling classes must be movable together
    changed = True
    while changed:
        changed = False
        for k, lst in tb.items():
            ids = {x[0] for x in lst}
            if ids & mov and not ids <= mov:
                mov -= ids; changed = True
    free = {}
    for key, ids in seam_ports.items():
        s0, s1 = plan.seam_span(key)
        holes = [[s0 + MARGIN, s1 - MARGIN]]
        for pid in ids:
            if pid in mov:
                continue
            lo, hi = sorted(P[pid]["window_um"])
            rest = []
            for x, y in holes:
                if lo - GAP / 2 > x: rest.append([x, min(y, lo - GAP / 2)])
                if hi + GAP / 2 < y: rest.append([max(x, hi + GAP / 2), y])
            holes = [h for h in rest if h[1] - h[0] > 1e-6]
        free[key] = holes

    def take(key, lo, hi):
        fl = free[key]
        for j, (x, y) in enumerate(fl):
            if x - 1e-6 <= lo and hi <= y + 1e-6:
                fl.pop(j)
                if lo - GAP / 2 > x: fl.append([x, lo - GAP / 2])
                if hi + GAP / 2 < y: fl.append([hi + GAP / 2, y])
                return True
        return False

    def fits(key, lo, hi):
        return any(x - 1e-6 <= lo and hi <= y + 1e-6 for x, y in free[key])

    def images(pid, lo, hi):
        """die windows of every port coupled to pid when pid sits at [lo,hi]."""
        pr = P[pid]; out = {pid: [lo, hi]}; todo = [pid]
        while todo:
            q = todo.pop(); qr = P[q]; ql, qh = out[q]
            for sd in ("src", "dst"):
                part = qr[sd]["part"]; df = plan.die_face(qr, sd)
                tw = plan.to_type(part, df, ql, qh)
                for (y, opart, odf) in tb[(plan.PA[part]["type"], qr[sd]["bus"])]:
                    if y in out:
                        continue
                    out[y] = sorted(plan.from_type(opart, odf, *tw)); todo.append(y)
        return out

    def min_len(pid):
        pr = P[pid]
        nl = len(pr.get("layers") or [1])
        return math.ceil((int(pr["width"]) + 1) / nl) * nl * PIN_UM_PER_LAYER

    win = {}
    stats = collections.Counter()
    near = []
    def cur_lat(c):
        return sum(abs(centre(P[a]["window_um"]) - centre(P[b]["window_um"])) for a, b in zip(c, c[1:])) * int(P[c[0]]["width"])
    # chains with an anchor first (their column is forced), heaviest current jog first; free chains last
    order = sorted(chains(plan), key=lambda c: (0 if any(x not in mov for x in c) else 1, -cur_lat(c), -int(P[c[0]]["width"])))
    for c in order:
        anchors = [x for x in c if x not in mov]
        tgt_src = anchors or [x for x in c if x in win]
        if tgt_src:
            # largest-width anchor wins; ties -> the downstream (last) anchor
            a = max(tgt_src, key=lambda x: (int(P[x]["width"]), c.index(x)))
            aw = win.get(a, P[a]["window_um"])
            tgt, L0 = centre(aw), abs(aw[1] - aw[0])
            stats["anchored"] += 1
        else:
            ws = [P[x]["window_um"] for x in c]
            tgt = sum(centre(w) for w in ws) / len(ws); L0 = min(abs(w[1] - w[0]) for w in ws)
            stats["free"] += 1
        for x in c:
            if x not in mov or x in win:
                continue
            cur = abs(P[x]["window_um"][1] - P[x]["window_um"][0])
            L = max(min_len(x), min(cur, L0) if min_len_frac >= 1 else max(min_len(x), L0 * min_len_frac))
            if L0 >= min_len(x):
                L = L0                                          # same pin pitch as the anchor -> bit-exact column
            placed = False
            # candidate centres: target first, then nearest hole edges on this seam
            key = plan.seam(P[x])
            cands = [tgt]
            for hx, hy in free[key]:
                if hy - hx >= L - 1e-9:
                    cands.append(min(max(tgt, hx + L / 2), hy - L / 2))
            cands = sorted(set(round(v, 3) for v in cands), key=lambda v: abs(v - tgt))
            for cc in cands:
                lo, hi = round(cc - L / 2, 3), round(cc + L / 2, 3)
                im = images(x, lo, hi)
                if any(y in win or y not in mov for y in im if y != x):
                    if any((y in win and (abs(win[y][0] - im[y][0]) > 2e-3 or abs(win[y][1] - im[y][1]) > 2e-3)) or y not in mov
                           for y in im if y != x):
                        continue
                if all(fits(plan.seam(P[y]), *im[y]) for y in im if y not in win):
                    for y in im:
                        if y not in win:
                            take(plan.seam(P[y]), *im[y]); win[y] = im[y]
                    near.append(abs(cc - tgt)); placed = True
                    stats["moved_ports"] += len(im)
                    break
            if not placed:
                # keep current window if still free; else count as unplaced
                lo, hi = sorted(P[x]["window_um"])
                im = images(x, lo, hi)
                if all(y in win or fits(plan.seam(P[y]), *im[y]) for y in im):
                    for y in im:
                        if y not in win:
                            take(plan.seam(P[y]), *im[y]); win[y] = im[y]
                    stats["kept"] += 1
                else:
                    stats["unplaced"] += 1
    # any movable port not yet placed keeps its window if free
    for x in sorted(mov):
        if x not in win:
            lo, hi = sorted(P[x]["window_um"])
            if fits(plan.seam(P[x]), lo, hi):
                take(plan.seam(P[x]), lo, hi); win[x] = [lo, hi]
            else:
                stats["unplaced_tail"] += 1
    stats["near_max_um"] = round(max(near or [0]), 1)
    return win, stats


def apply(plan, win):
    """write port + type windows; check type-frame consistency."""
    newtype, changed = {}, set()
    for pid, w in win.items():
        pr = plan.P[pid]
        old = pr["window_um"]
        pr["window_um"] = list(w) if old[0] <= old[1] else list(w[::-1])
        for sd in ("src", "dst"):
            part = pr[sd]["part"]
            s, key = plan.winref(part, pr[sd]["bus"])
            if s is None:
                continue
            tw = plan.to_type(part, plan.die_face(pr, sd), *sorted(w))
            k = (plan.PA[part]["type"], pr[sd]["bus"])
            if k in newtype and any(abs(u - v) > 0.0025 for u, v in zip(newtype[k], tw)):
                raise SystemExit(f"type window conflict {k}: {newtype[k]} vs {tw} ({part})")
            newtype[k] = tw
            if [round(v, 3) for v in s[key]] != tw:
                s[key] = tw
                changed.add(plan.PA[part]["type"])
    return changed


def corridors(plan, rows, top=40):
    """residual lateral grouped by die row band (y of the partition) -> H corridor demand."""
    band = collections.defaultdict(lambda: [0.0, 0, set()])
    for d, part, t, sn, w, dx, y0, y1 in rows:
        k = (round(y0, 1), round(y1, 1))
        band[k][0] += d; band[k][1] += w; band[k][2].add(f"{t}/{sn}")
    out = []
    for (y0, y1), (d, bits, fams) in sorted(band.items(), key=lambda kv: -kv[1][0])[:top]:
        out.append(dict(y_um=[y0, y1], bit_um=round(d), bits=bits, tracks_needed=bits, families=sorted(fams)[:12]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--types-only", help="regex: only ports whose both partition types match move")
    ap.add_argument("--min-len-frac", type=float, default=1.0)
    ap.add_argument("--hub", help="regex of partition types whose functional bus windows may move to the chain column "
                                  "(top-down pin assignment of unkitted hub partitions); the moved distance is reported "
                                  "as hub-internal lateral")
    ap.add_argument("--gate-mbitum", type=float, default=5.0)
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    plan = Plan(raw, a.hub)
    old_hub = {}
    for pid, pr in plan.P.items():
        for sd in ("src", "dst"):
            if a.hub and plan.is_hub_bus(pr[sd]["part"], pr[sd]["bus"]):
                old_hub[pid] = (list(pr["window_um"]), int(pr["width"]), pr[sd]["part"], pr[sd]["bus"])
    before, rows0 = lateral(plan, detail=True)
    tr = plan.traversals()
    print(f"N-S lateral before {before / 1e6:.2f} M bit-um ({sum(1 for r in rows0)} of {sum(1 for t in tr if t[4])} N-S traversals offset; "
          f"{len(tr)} traversals); E-W lateral (dy) {lateral_ew(plan) / 1e6:.2f} M bit-um")
    if a.measure:
        for r in rows0[:25]:
            print("  %6.2fM %-12s %-32s %-5s w %4d dx %7.1f y %.0f-%.0f" % (r[0] / 1e6, *r[1:]))
        return
    win, stats = align(plan, a.min_len_frac, a.types_only)
    changed = apply(plan, win)
    plan2 = Plan(raw, a.hub)
    hub_lat = sum(abs(centre(plan2.P[p]["window_um"]) - centre(w)) * n for p, (w, n, _, _) in old_hub.items())
    hub_moves = sorted(((abs(centre(plan2.P[p]["window_um"]) - centre(w)) * n, part, bus) for p, (w, n, part, bus) in old_hub.items()), reverse=True)
    print(f"hub bus windows moved: {sum(1 for m in hub_moves if m[0] > 0)}, hub-internal lateral moved in {hub_lat / 1e6:.2f} M bit-um")
    after, rows = lateral(plan2, detail=True)
    gate = after / 1e6 <= a.gate_mbitum
    print(f"N-S lateral after {after / 1e6:.2f} M bit-um ({'PASS' if gate else 'FAIL'} gate {a.gate_mbitum}M); "
          f"changed types {len(changed)}; E-W lateral {lateral_ew(plan2) / 1e6:.2f} M; {dict(stats)}")
    for r in rows[:20]:
        print("  %6.2fM %-12s %-32s %-5s w %4d dx %7.1f y %.0f-%.0f" % (r[0] / 1e6, *r[1:]))
    if a.out:
        sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(a.plan).resolve().parent)]
        try:
            import compact_plan
            Path(a.out).write_text(compact_plan.dumps(raw))
        except ImportError:
            Path(a.out).write_text(json.dumps(raw, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps(dict(
            before_mbitum=round(before / 1e6, 3), after_mbitum=round(after / 1e6, 3), gate_mbitum=a.gate_mbitum,
            gate="PASS" if gate else "FAIL", stats=dict(stats), hub=a.hub, hub_internal_mbitum=round(hub_lat / 1e6, 3),
            hub_moves=[dict(bit_um=round(m[0]), part=m[1], bus=m[2]) for m in hub_moves if m[0] > 0], changed_types=sorted(changed),
            residual_top=[dict(bit_um=round(r[0]), part=r[1], type=r[2], slot=r[3], width=r[4], dx_um=round(r[5], 1),
                               y_um=[r[6], r[7]]) for r in rows[:60]],
            corridors=corridors(plan2, rows)), indent=1) + "\n")


if __name__ == "__main__":
    main()
