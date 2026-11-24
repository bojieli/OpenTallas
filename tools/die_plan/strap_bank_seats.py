#!/usr/bin/env python3
"""STRAP-BANK-SEATS (SEAT-MATCH-AUDIT 11-24): FIRM plan seats for the R8 strap-count banks of one bound type, from a placed geometry dump.

Why: the R8 strap pass (bind.py) replaces per-bit landing pads u_pd<D>_<bus>_<bit> by one bank per strap site: a fixed chain
u_r8b_<site>_f (ot_dp_dly, stages r[0..D-2] + q) and a count chain u_r8b_<site> (ot_dp_dly_cnt, r[0..DMAX-1], a mux picks stage strap_cnt).
The plan keeps the old u_pd<D> keys, which seat nothing, and the banks fall to free placement (QC sle_ctl: chd_q_1 3,216 of 3,216 f-bank
flops, 400 um from u_rp).  The old sites cannot be renamed: they end at the consumer's OLD position.  So the seats are derived from the
placed netlist of a kit of the same bound form: per bit, launch end = what feeds the first f stage, capture end = L1 minimax of every
register, macro or pin the count stages reach through logic (the mux may take any stage).  The f stages run evenly on the shortest
rectilinear way launch -> capture around the hard macros; the count stages stand at the capture end, so every strap count leaves at most
one short hop.  Old dead rows of the same buses are dropped in the same step (`--drop`).

  strap_bank_seats.py SRC GEOM BASE_PLAN TYPE OUT_PLAN REPORT_JSON [--banks RE] [--reach 380] [--macro-halo 6] [--cnt-span 40] [--lanes 32] [--replace]
                      [--bound-rtl DIR --drop]
REPORT: per bank: bits, stages, seats, hop_um (worst launch -> f -> count -> capture) on the NEW sites and `placed_hop_um` on the dump's
current placement; dropped: {old row group: {"rows", "banks", "new_hop_um", "placed_hop_um"}} (a dropped row shows its replacement's reach).
"""
import argparse
import heapq
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BANK = re.compile(r"^(?:u_bound[./])?(?P<site>u_r8b_\w+?)(?P<f>_f)?[./](?P<reg>r|q)(?P<idx>(?:\[\d+\])*)$")


def split_key(nm):
    """(site, is_f, reg, stage or None, bit or None) of one bank register name without the cell suffix, or None"""
    m = BANK.match(nm)
    if not m:
        return None
    ix = [int(x) for x in re.findall(r"\[(\d+)\]", m.group("idx"))]
    if m.group("reg") == "q":
        return m.group("site"), bool(m.group("f")), "q", None, ix[0] if ix else 0
    if not ix:
        return None
    return m.group("site"), bool(m.group("f")), "r", ix[0], ix[1] if len(ix) > 1 else 0


def route(a, b, rects, die, bend=10.0):
    """rectilinear polyline a -> b around the rects [(x0, y0, x1, y1)] inside die, shortest L1 with few bends; None: no way.  Grid = the rect
    edges and the end points, so the polyline runs along macro edges (grow the rects by a halo first)"""
    xs = sorted({a[0], b[0]} | {v for r in rects for v in (r[0], r[2]) if die[0] <= v <= die[2]})
    ys = sorted({a[1], b[1]} | {v for r in rects for v in (r[1], r[3]) if die[1] <= v <= die[3]})
    ix, iy = {v: i for i, v in enumerate(xs)}, {v: i for i, v in enumerate(ys)}

    def free(p, q):
        mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        return not any(r[0] < mx < r[2] and r[1] < my < r[3] for r in rects)
    start, goal = (ix[a[0]], iy[a[1]]), (ix[b[0]], iy[b[1]])
    best, heap = {(start, -1): 0.0}, [(0.0, start, -1, None)]
    back = {}
    while heap:
        d, n, o, prev = heapq.heappop(heap)
        if (n, o) in back:
            continue
        back[(n, o)] = prev
        if n == goal:
            pts, k = [], (n, o)
            while k is not None:
                pts.append((xs[k[0][0]], ys[k[0][1]]))
                k = back[k]
            return pts[::-1]
        for dx, dy, no in ((1, 0, 0), (-1, 0, 0), (0, 1, 1), (0, -1, 1)):
            m = (n[0] + dx, n[1] + dy)
            if not (0 <= m[0] < len(xs) and 0 <= m[1] < len(ys)):
                continue
            p, q = (xs[n[0]], ys[n[1]]), (xs[m[0]], ys[m[1]])
            if not free(p, q):
                continue
            nd = d + abs(p[0] - q[0]) + abs(p[1] - q[1]) + (bend if o not in (-1, no) else 0.0)
            if nd < best.get((m, no), 1e18):
                best[(m, no)] = nd
                heapq.heappush(heap, (nd, m, no, (n, o)))
    return None


def outside(p, rects, die):
    """p, or the nearest point on the edge of the rect that strictly holds it (inside the die, in no other rect)"""
    hit = [r for r in rects if r[0] < p[0] < r[2] and r[1] < p[1] < r[3]]
    if not hit:
        return p
    cand = [q for r in hit for q in ((r[0], p[1]), (r[2], p[1]), (p[0], r[1]), (p[0], r[3]))
            if die[0] <= q[0] <= die[2] and die[1] <= q[1] <= die[3] and not any(s[0] < q[0] < s[2] and s[1] < q[1] < s[3] for s in rects)]
    return min(cand, key=lambda q: abs(p[0] - q[0]) + abs(p[1] - q[1])) if cand else p


def lay(pts, nf, nc, cnt_span=40.0):
    """[(x, y)] of nf + nc stages on the polyline pts (launch end first): the f stages even, the count stages over the last
    min(cnt_span, one f hop) um, so any stage the mux taps is one short hop from the sink"""
    seg = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]
    span = sum(seg)
    tail = min(cnt_span, span / (nf + 1)) if nc else 0.0
    ds = [(span - tail) * (j + 1) / (nf + (0 if nc else 1)) for j in range(nf)] if nf else []
    ds += [span - tail + tail * (j + 1) / nc for j in range(nc)]
    out = []
    for d in ds:
        k = 0
        while k < len(seg) - 1 and d > seg[k]:
            d -= seg[k]
            k += 1
        f = min(1.0, d / seg[k]) if seg and seg[k] else 0.0
        p, q = pts[k], pts[min(k + 1, len(pts) - 1)]
        out.append((round(p[0] + (q[0] - p[0]) * f, 3), round(p[1] + (q[1] - p[1]) * f, 3)))
    return out


def banks_of(names):
    """{site: {bit: {"f": [(order, cell, key)], "c": [...]}}}, names {cell: name}"""
    out = defaultdict(lambda: defaultdict(lambda: {"f": [], "c": []}))
    for c, nm in names.items():
        k = re.sub(r"^u_bound[./]", "", re.sub(r"\$_[A-Za-z0-9_]*$", "", nm))
        s = split_key(k)
        if not s:
            continue
        site, is_f, reg, j, b = s
        out[site][b]["f" if is_f else "c"].append((j if reg == "r" else 10 ** 6, c, k))
    for s in out.values():
        for e in s.values():
            e["f"].sort()
            e["c"].sort()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in "src geom base type out report".split():
        ap.add_argument(a)
    ap.add_argument("--banks", default=".*")
    ap.add_argument("--reach", type=float, default=380.0)
    ap.add_argument("--macro-halo", type=float, default=6.0)
    ap.add_argument("--cnt-span", type=float, default=40.0)
    ap.add_argument("--lanes", type=int, default=32, help="bits spread over this many 1-um lanes beside a macro edge")
    ap.add_argument("--replace", action="store_true", help="also move bank rows the plan already seats (default: those rows stay)")
    ap.add_argument("--bound-rtl")
    ap.add_argument("--drop", action="store_true")
    A = ap.parse_args(argv)
    sys.path.insert(0, A.src + "/tools/autopilot")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import geom_rules as G
    from relay_site_clear import clear_sites
    from type_relay_seat_io import style_of

    D = G.Design(A.geom)
    name = {c: v[6].replace("\\", "") for c, v in D.cells.items() if v[0] == "S"}
    kind = {c: v[0] for c, v in D.cells.items()}
    banks = {s: e for s, e in banks_of(name).items() if re.search(A.banks, s)}
    L1 = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])  # noqa: E731
    xy = lambda c: G.ctr(D.cells[c])  # noqa: E731

    def walk(start, fwd):
        """sequential cells, macros and pins reached from cell `start` through combinational cells (fwd: captures, else launches)"""
        res, seen, front = set(), set(), [start]
        while front:
            nf = []
            for u in front:
                if fwd:
                    for n in D.drives.get(u, []):
                        for s in D.nets[n][2]:
                            if s[0] == "p":
                                res.add(("p", s[1]))
                            elif not s[2]:
                                if kind.get(s[1]) in ("S", "M"):
                                    res.add(("i", s[1]))
                                elif s[1] not in seen:
                                    seen.add(s[1])
                                    nf.append(s[1])
                else:
                    for n, ck in D.cell_in.get(u, []):
                        d = None if ck else D.nets[n][1]
                        if d is None:
                            continue
                        if d[0] == "p":
                            res.add(("p", d[1]))
                        elif kind.get(d[1]) in ("S", "M"):
                            res.add(("i", d[1]))
                        elif d[1] not in seen:
                            seen.add(d[1])
                            nf.append(d[1])
            front = nf
        return res

    def point(r, toward):
        if r[0] == "p":
            p = D.pin_by_k[r[1]]
            return float(p["x"]), float(p["y"])
        v = D.cells[r[1]]
        if v[0] == "M":
            return min(max(toward[0], v[2]), v[4]), min(max(toward[1], v[3]), v[5])
        return G.ctr(v)

    def minimax(pts):
        us, vs = [p[0] + p[1] for p in pts], [p[0] - p[1] for p in pts]
        u, v = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
        return (u + v) / 2, (u - v) / 2

    rects = [tuple(v[2:6]) for v in D.cells.values() if v[0] == "M"] if A.macro_halo >= 0 else []
    sites, rep = {}, {"type": A.type, "reach_um": A.reach, "banks": {}, "skipped": Counter()}
    rep_hop = {}
    for site, bits in sorted(banks.items()):
        r = {"bits": len(bits), "f_stages": 0, "cnt_stages": 0, "seats": 0, "hop_um": 0.0, "placed_hop_um": 0.0, "moved_off_macro": 0}
        for b, e in sorted(bits.items()):
            ch = [c for _, c, _ in e["f"]] + [c for _, c, _ in e["c"]]
            ks = [k for _, _, k in e["f"]] + [k for _, _, k in e["c"]]
            nf, nc = len(e["f"]), len(e["c"])
            own = set(ch)
            la = [x for x in walk(ch[0], False) if not (x[0] == "i" and x[1] in own)]
            caps = set()
            for c in ([x for _, x, _ in e["c"]] or ch[-1:]):
                caps |= {x for x in walk(c, True) if not (x[0] == "i" and x[1] in own)}
            if not la or not caps:
                rep["skipped"][site + (":no_launch" if not la else ":no_capture")] += 1
                continue
            # a hard-macro capture counts at its edge point nearest the other captures (else nearest the launch): the bank's
            # count stages sit with the register sinks, and the macro input is reached from that side
            here = xy(ch[0])
            regs = [point(x, here) for x in caps if not (x[0] == "i" and kind.get(x[1]) == "M")]
            here_b = minimax(regs) if regs else here
            a0 = minimax([point(x, here_b) for x in caps])
            pa = [point(x, a0) for x in la]
            a = minimax(pa)
            pb = [point(x, here_b if regs else a) for x in caps]
            bb = minimax(pb)
            h = A.macro_halo + b % A.lanes                   # one lane per bit beside a macro edge
            grown = [(q[0] - h, q[1] - h, q[2] + h, q[3] + h) for q in rects]
            a, bb = outside(a, grown, D.die), outside(bb, grown, D.die)
            path = lay(route(a, bb, grown, D.die) or [a, bb], nf, nc, A.cnt_span)
            if rects:
                path, mv = clear_sites(path, pa, pb, rects, D.die, halo=A.macro_halo)
                r["moved_off_macro"] += mv
            hop = max([max(L1(path[0], p) for p in pa)] + [L1(path[j], path[j + 1]) for j in range(len(path) - 1)]
                      + [max(max(L1(q, p) for p in pb) for q in (path[nf:] or path[-1:]))])
            now = [xy(c) for c in ch]
            ph = max([max(L1(now[0], p) for p in pa)] + [L1(now[j], now[j + 1]) for j in range(len(now) - 1)]
                     + [max(max(L1(q, p) for p in pb) for q in (now[nf:] or now[-1:]))])
            r["f_stages"], r["cnt_stages"] = max(r["f_stages"], nf), max(r["cnt_stages"], nc)
            r["hop_um"], r["placed_hop_um"] = max(r["hop_um"], hop), max(r["placed_hop_um"], ph)
            r["seats"] += len(ks)
            if hop > A.reach:
                r.setdefault("over_bits", []).append([b, round(hop, 1), len(pb), [round(v, 1) for v in a], [round(v, 1) for v in bb]])
            for k, s in zip(ks, path):
                sites[k] = [s[0], s[1]]
        r["hop_um"], r["placed_hop_um"] = round(r["hop_um"], 1), round(r["placed_hop_um"], 1)
        r["over_reach"] = r["hop_um"] > A.reach
        rep["banks"][site] = r
        rep_hop[site] = r
    raw_b = Path(A.base).read_bytes()
    raw = json.loads(raw_b)
    t = raw["partition_types"][A.type]
    merged = dict(t.get("relay_sites") or {})
    rep["dropped"] = {}
    if A.drop:
        import seat_match as SM
        f = SM._bound_file(A.bound_rtl, A.type)
        text = f.read_text(errors="replace")
        v = SM.judge(merged, text, SM.ist_buses(t))
        dead = [k for k, x in v.items() if x in ("DEAD-INST", "DEAD-REG") and re.match(r"u_pd\d+_", k)]
        hints = SM.hint(dead, text)
        g = defaultdict(list)
        for k in dead:
            m = re.match(r"u_pd\d+_(.+?)_\d+[./]", k)
            g[m.group(1) if m else "?"].append(k)
        for bus, ks in g.items():
            bk = sorted({re.sub(r"_f$", "", x) for x in hints.get(bus, [])})
            hit = [rep_hop[x] for x in bk if x in rep_hop]
            rep["dropped"][bus] = {"rows": len(ks), "groups": dict(SM.group(ks)), "banks": bk,
                                   "new_hop_um": max((x["hop_um"] for x in hit), default=None),
                                   "placed_hop_um": max((x["placed_hop_um"] for x in hit), default=None)}
            if not hit:
                rep["skipped"][f"drop:{bus}: no seated bank, rows KEPT"] += len(ks)
                continue
            for k in ks:
                merged.pop(k)
    rep["kept_plan_seats"] = 0 if A.replace else sum(k in merged for k in sites)
    new = {k: v for k, v in sites.items() if A.replace or k not in merged}
    rep["seats_added"] = len(new)
    merged.update(new)
    t["relay_sites"] = dict(sorted(merged.items()))
    Path(A.out).write_text(style_of(raw_b)(raw))
    rep["seats"] = len(sites)
    rep["plan_keys"] = len(t["relay_sites"])
    Path(A.report).write_text(json.dumps(rep, indent=1, default=dict) + "\n")
    print(json.dumps({k: rep[k] for k in ("seats", "seats_added", "plan_keys", "banks", "dropped", "skipped")}, default=dict))
    return 0


if __name__ == "__main__":
    sys.exit(main())
