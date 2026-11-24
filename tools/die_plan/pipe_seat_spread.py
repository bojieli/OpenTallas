#!/usr/bin/env python3
"""PIPE-SEAT-SPREAD (QC-CB-PIPESEAT 11-24, row CB-PIPESEAT-SPREAD): spread column-stacked delay-pipe seats across their street.

type_relay_sites.py --pipes seats every bit of a delay pipe (u_d<D>_*: r[j][b] .. q[b]) on that bit's own launch->capture
line, and relay_site_clear moves a seat that falls in a hard macro to the macro boundary.  All bits of one stage then land on
ONE x (the halo edge, e.g. x1155 in QC cbn_q00 cl622f65d2) over a 50-100 um y band: 514-3500 FIRM seats per 50-um column.
GRT overflows beside those columns (cl622f65d2 it10: x200 541, x1100 446 next to the x50 / x1150 stacks).  Seats left
inside a hard core (cleared against a stale content box: x98 inside u_t01 60.5-518.4) are legalised into the next column.

This tool keeps every stage's y band (so stage order along the chain is kept) and re-sites each stacked stage group on an
even x-pitch grid over the free street width beside it (hard_cores grown by --halo, outline margin --margin), bits in bit
order (bit b keeps the same column in every stage of one street, so stage-to-stage nets run straight along the street).
A group whose seats sit inside a grown core moves to the nearer free street.  Per bit the new hop (L1, launch/capture ends
extrapolated from the old even-hop line) must be <= max(--reach, old hop); a group that breaks it is retried on a narrower
window and otherwise left as it was.  Only relay_sites keys of pipe seats change; nothing else in the plan is touched.

  pipe_seat_spread.py PLAN OUT_DIR [--types T ...] [--reach 405] [--halo 6] [--margin 1.0] [--max-width 160]
                      [--strip Y0 Y1] [--out-plan PLAN_OUT]
OUT_DIR/<type>/pipeseat_sites.json  changed relay_sites keys (the row, merged like cb_pipe scoped_sites.json)
OUT_DIR/report.json                 per type: groups spread / kept, hop and order checks, density per 100-um bin
"""
import argparse, collections, json, math, re, sys
from pathlib import Path

PIPE = re.compile(r"^(?:u_bound\.)?(?P<inst>u_d(?P<D>\d+)_\w+?)[./](?:r\[(?P<j>\d+)\]\[(?P<b>\d+)\]|q\[(?P<qb>\d+)\])$")
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def boxes(t, halo):
    out = []
    for h in t.get("hard_cores") or []:
        o, s = h.get("origin_um"), h.get("outline_um")
        if o and s:
            out.append((o[0] - halo, o[1] - halo, o[0] + s[0] + halo, o[1] + s[1] + halo))
    return out


def inside(p, bx):
    return any(b[0] < p[0] < b[2] and b[1] < p[1] < b[3] for b in bx)


def free_intervals(bx, y0, y1, W, margin):
    """free x intervals over the y band [y0, y1] (every box that overlaps the band blocks its x range)"""
    cut = sorted((b[0], b[2]) for b in bx if b[1] < y1 and b[3] > y0)
    out, x = [], margin
    for a, c in cut:
        if a > x:
            out.append((x, min(a, W - margin)))
        x = max(x, c)
    if x < W - margin:
        out.append((x, W - margin))
    return [iv for iv in out if iv[1] - iv[0] > 0.5]


def pick_interval(ivs, x):
    best = None
    for iv in ivs:
        d = 0.0 if iv[0] <= x <= iv[1] else min(abs(x - iv[0]), abs(x - iv[1]))
        if best is None or d < best[0]:
            best = (d, iv)
    return best[1] if best else None


def chains(t):
    """{inst: {"D": D, "bits": {b: [key per stage 0..D]}}}  (stage D = q)"""
    ch = collections.defaultdict(lambda: {"D": 0, "bits": collections.defaultdict(dict)})
    for k in (t.get("relay_sites") or {}):
        m = PIPE.match(k)
        if not m:
            continue
        D = int(m.group("D"))
        c = ch[m.group("inst")]
        c["D"] = D
        if m.group("j") is not None:
            c["bits"][int(m.group("b"))][int(m.group("j"))] = k
        else:
            c["bits"][int(m.group("qb"))][D] = k
    return ch


def ends(pts):
    """launch / capture ends extrapolated from the old even-hop line"""
    if len(pts) < 2:
        return pts[0], pts[-1]
    a = (2 * pts[0][0] - pts[1][0], 2 * pts[0][1] - pts[1][1])
    b = (2 * pts[-1][0] - pts[-2][0], 2 * pts[-1][1] - pts[-2][1])
    return a, b


def density(sites, y0, y1, W):
    c = collections.Counter()
    for p in sites:
        if y0 <= p[1] <= y1:
            c[int(p[0] // 100) * 100] += 1
    return {str(x): c.get(x, 0) for x in range(0, int(math.ceil(W / 100)) * 100, 100)}


def cell_max(sites, cell=10.0):
    c = collections.Counter((int(p[0] // cell), int(p[1] // cell)) for p in sites)
    return max(c.values()) if c else 0


def spread_type(t, A):
    W, H = t["outline_um"]
    rs = t["relay_sites"]
    bx = boxes(t, A.halo)
    ch = chains(t)
    new = {}                       # key -> [x, y]
    rep = dict(groups_spread=0, groups_kept=0, seats_moved=0, buried_before=0, buried_after=0, kept=[], hop_worse=0,
               order_flip=0, preexisting_over_reach=0)
    # stage groups: (inst, stage, cluster) of crowded seats.  A cluster is a connected set of --col-um cells holding seats of
    # one stage; it is crowded when its densest 10-um cell holds more than --cell-cap seats (a column or row stack).
    groups = []
    for inst, c in ch.items():
        D = c["D"]
        for s in range(D + 1):
            cells = collections.defaultdict(list)
            for b, ks in c["bits"].items():
                if s in ks:
                    p = rs[ks[s]]
                    cells[(int(p[0] // A.col_um), int(p[1] // A.col_um))].append((b, ks[s]))
            seen = set()
            for c0 in cells:
                if c0 in seen:
                    continue
                comp, front = [], [c0]
                seen.add(c0)
                while front:
                    q = front.pop()
                    comp.extend(cells[q])
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nb = (q[0] + dx, q[1] + dy)
                            if nb in cells and nb not in seen:
                                seen.add(nb)
                                front.append(nb)
                if len(comp) >= A.min_bits:
                    groups.append((inst, s, sorted(comp)))
    rep["buried_before"] = sum(1 for k in rs if PIPE.match(k) and inside(rs[k], bx))

    def inside_free(ps):
        return not any(inside(p, bx) for p in ps)

    def pos(k):
        return new.get(k, rs[k])

    def legal(p):
        """where the placer puts a FIRM seat that sits in a grown hard core: the nearest point on that box's edge"""
        for b in bx:
            if b[0] < p[0] < b[2] and b[1] < p[1] < b[3]:
                c = min(((p[0] - b[0], (b[0], p[1])), (b[2] - p[0], (b[2], p[1])),
                         (p[1] - b[1], (p[0], b[1])), (b[3] - p[1], (p[0], b[3]))))[1]
                return [round(c[0], 3), round(c[1], 3)]
        return p

    def bit_path(inst, b):
        """(old points, new points) of one bit's seated stages in stage order; an end (launch before stage 0, capture after
        stage D) is extrapolated from the old even-hop line when that end stage is seated; an unseated stage (e.g. q left
        to the placer) cuts the path there, its hops are not judged"""
        ks = ch[inst]["bits"][b]
        D = ch[inst]["D"]
        js = sorted(ks)
        old = [legal(rs[ks[j]]) for j in js]          # an old seat in a core is judged where the placer puts it
        new_ = [pos(ks[j]) for j in js]
        if len(js) >= 2 and js[0] == 0:
            a, _ = ends(old)
            old, new_ = [a] + old, [a] + new_
            js = [-1] + js
        if len(js) >= 2 and js[-1] == D:
            _, z = ends(old[1:] if js[0] == -1 else old)
            old, new_ = old + [z], new_ + [z]
            js = js + [D + 1]
        return js, old, new_

    def bit_ok(inst, b, s_list=None):
        js, oldp, newp = bit_path(inst, b)
        for i in range(len(oldp) - 1):
            if js[i + 1] != js[i] + 1:
                continue
            if L1(newp[i], newp[i + 1]) > max(A.reach, L1(oldp[i], oldp[i + 1])) + 1e-6:
                return False
            if 0 <= js[i] and js[i + 1] <= ch[inst]["D"]:          # stage order between two seated stages
                do = (oldp[i + 1][0] - oldp[i][0], oldp[i + 1][1] - oldp[i][1])
                dn = (newp[i + 1][0] - newp[i][0], newp[i + 1][1] - newp[i][1])
                if abs(do[0]) + abs(do[1]) > A.order_um and do[0] * dn[0] + do[1] * dn[1] < 0:
                    return False
        return True

    # runs: consecutive stages of one pipe seated close together (centres within --run-um: a pure-latency pipe whose ends
    # meet, stages 0 and 1 on one point, a 10-deep pipe over 100 um) share one region; each stage gets its own slice of
    # it, in stage order along the run's own direction (x or y), instead of each stage spreading over the shared region
    def bbox(mem):
        pts = [rs[k] for _, k in mem]
        return min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)
    def centre(mem):
        return (sum(rs[k][0] for _, k in mem) / len(mem), sum(rs[k][1] for _, k in mem) / len(mem))
    cen = [centre(g[2]) for g in groups]
    stagger = {}
    byinst = collections.defaultdict(list)
    for gi, (inst, s, mem) in enumerate(groups):
        byinst[inst].append(gi)
    runs = []
    for inst, gis in byinst.items():
        par = {i: i for i in gis}
        def find(i):
            while par[i] != i:
                i = par[i]
            return i
        for i in gis:
            for j in gis:
                if groups[j][1] == groups[i][1] + 1 and L1(cen[i], cen[j]) <= A.run_um:
                    par[find(j)] = find(i)
        comp = collections.defaultdict(list)
        for i in gis:
            comp[find(i)].append(i)
        runs += [sorted(c, key=lambda i: groups[i][1]) for c in comp.values() if len(c) >= 2]
    for cl in runs:
        bb = [bbox(groups[i][2]) for i in cl]
        U = (min(x[0] for x in bb), max(x[1] for x in bb), min(x[2] for x in bb), max(x[3] for x in bb))
        c0, c1 = cen[cl[0]], cen[cl[-1]]
        stages = sorted({groups[i][1] for i in cl})
        rank = {st: r for r, st in enumerate(stages)}
        m = len(stages)
        if abs(c1[0] - c0[0]) > abs(c1[1] - c0[1]):
            sgn = 1 if c1[0] >= c0[0] else -1
            lo, hi = U[0], max(U[1], U[0] + m * A.min_width)
            for i in cl:
                r = rank[groups[i][1]] if sgn > 0 else m - 1 - rank[groups[i][1]]
                stagger[i] = ("x", lo + r * (hi - lo) / m, lo + (r + 1) * (hi - lo) / m, U[2], U[3])
        else:
            sgn = 1 if c1[1] >= c0[1] else -1
            tot = min(max(U[3] - U[2], m * A.min_band / 2), m * A.max_band)
            ymid = (U[2] + U[3]) / 2
            for i in cl:
                r = rank[groups[i][1]] if sgn > 0 else m - 1 - rank[groups[i][1]]
                stagger[i] = ("y", ymid - tot / 2 + r * tot / m, ymid - tot / 2 + (r + 1) * tot / m)
    # crowded groups only: on their own, or together with the stages of their run
    crowd = [cell_max([rs[k] for _, k in g[2]]) > A.cell_cap or any(inside(rs[k], bx) for _, k in g[2]) for g in groups]
    for cl in runs:
        if cell_max([rs[k] for i in cl for _, k in groups[i][2]]) > A.cell_cap:
            for i in cl:
                crowd[i] = True
    keep = [i for i in range(len(groups)) if crowd[i]]
    stagger = {keep.index(i): v for i, v in stagger.items() if crowd[i]}
    groups = [groups[i] for i in keep]
    rep["staggered_groups"] = len(stagger)

    for gi, (inst, s, mem) in enumerate(groups):
        pts = [rs[k] for _, k in mem]
        n = len(mem)
        X0, X1 = min(p[0] for p in pts), max(p[0] for p in pts)
        Y0, Y1 = min(p[1] for p in pts), max(p[1] for p in pts)
        x, ym = (X0 + X1) / 2, (Y0 + Y1) / 2
        h = min(max(Y1 - Y0, A.min_band), max(Y1 - Y0, A.max_band))
        sg = stagger.get(gi)
        if sg and sg[0] == "y":
            ym, h = (sg[1] + sg[2]) / 2, sg[2] - sg[1]
        elif sg:
            ym, h = (sg[3] + sg[4]) / 2, max(sg[4] - sg[3], A.min_band)
        y0, y1 = max(A.margin, ym - h / 2), min(H - A.margin, ym + h / 2)
        iv = pick_interval(free_intervals(bx, y0, y1, W, A.margin), x)
        if iv:
            x = min(max(x, iv[0]), iv[1])              # a buried group moves to the nearer free street
        if iv and iv[1] - iv[0] > A.channel_um:
            # a horizontal channel (free across core columns): the window is the seats' own x span (at least --min-band),
            # and the band grows over the channel height (free y over that x span), at most --max-band
            w = max(X1 - X0, A.min_band)
            wl = max(iv[0], x - w / 2)
            wr = min(iv[1], wl + w)
            ys = free_intervals([(b[1], b[0], b[3], b[2]) for b in bx], wl, wr, H, A.margin)
            jv = pick_interval(ys, ym)
            if jv:
                yc = min(max(ym, jv[0]), jv[1])
                y0, y1 = max(jv[0], yc - A.max_band / 2), min(jv[1], yc + A.max_band / 2)
            iv = (wl, wr)
        # stage order: the window stays on this stage's side of the midpoints to the neighbour stages of the same bits
        # (a pipe that steps along x across a street keeps its x steps; one that steps along y keeps its y steps)
        cx0 = sum(p[0] for p in pts) / n
        cy0 = sum(p[1] for p in pts) / n
        D = ch[inst]["D"]
        if sg and sg[0] == "x" and iv:
            iv = (max(iv[0], sg[1]), min(iv[1], sg[2]))
        biv, by0, by1 = iv, y0, y1
        for s2 in (s - 1, s + 1):
            if sg or not 0 <= s2 <= D or not iv:
                continue
            nb = [rs[ch[inst]["bits"][b][s2]] for b, _ in mem if s2 in ch[inst]["bits"][b]]
            if not nb:
                continue
            nx, ny = sum(p[0] for p in nb) / len(nb), sum(p[1] for p in nb) / len(nb)
            same_street = iv[0] - A.order_um <= nx <= iv[1] + A.order_um
            if same_street and y0 <= ny <= y1 and abs(nx - cx0) > A.order_um:
                mid = (nx + cx0) / 2
                biv = (max(biv[0], mid), biv[1]) if nx < cx0 else (biv[0], min(biv[1], mid))
            if same_street and abs(ny - cy0) > A.order_um:
                mid = (ny + cy0) / 2
                by0, by1 = (max(by0, mid), by1) if ny < cy0 else (by0, min(by1, mid))
        if biv and biv[1] - biv[0] >= A.min_width and by1 - by0 >= A.min_width:
            iv, y0, y1 = biv, by0, by1
        done = False
        width = A.max_width
        while iv and y1 - y0 >= 1.0 and width >= A.min_width and not done:
            xl, xr = iv
            if xr - xl > width:                           # window of `width` around the column, inside the street
                xl = min(max(xl, x - width / 2), xr - width)
                xr = xl + width
            w = xr - xl
            if w <= 0.5:
                break
            cell = math.sqrt(w * (y1 - y0) / n)
            ncol = max(1, min(n, int(round(w / max(cell, A.pitch_min)))))
            nrow = int(math.ceil(n / ncol))
            trial = {}
            for i, (b, k) in enumerate(mem):
                cx, ry = i % ncol, i // ncol
                trial[k] = [round(xl + (cx + 0.5) * w / ncol, 3), round(y0 + (ry + 0.5) * (y1 - y0) / nrow, 3)]
            saved = {k: new.get(k) for _, k in mem}
            new.update(trial)
            # per bit: a bit whose hop or order breaks on its grid seat moves only part of the way (lam 1/2, 1/4, 0)
            part = 0
            for b, k in mem:
                if bit_ok(inst, b) and not inside(new[k], bx):
                    continue
                o = saved[k] if saved[k] is not None else legal(rs[k])
                t1 = trial[k]
                for lam in (0.5, 0.25, 0.0):
                    new[k] = [round(o[0] + lam * (t1[0] - o[0]), 3), round(o[1] + lam * (t1[1] - o[1]), 3)]
                    if lam == 0.0 or (bit_ok(inst, b) and not inside(new[k], bx)):
                        break
                part += 1
                if lam == 0.0 and saved[k] is None and new[k] == rs[k]:
                    new.pop(k, None)
            if part <= A.max_partial * n:
                done = True
                rep["groups_spread"] += 1
                rep["seats_moved"] += n
                rep["bits_partial"] = rep.get("bits_partial", 0) + part
            else:
                for k, v in saved.items():
                    if v is None:
                        new.pop(k, None)
                    else:
                        new[k] = v
                width /= 2
        if not done:
            rep["groups_kept"] += 1
            rep["kept"].append(f"{inst} stage {s} n {n}")
    # distinct seats: a moved seat that lands on another seat (two groups' grids over one region) steps by one row pitch
    occ = collections.Counter((round(v[0], 2), round(v[1], 2)) for k, v in rs.items() if k not in new)
    for k in sorted(new):
        v = new[k]
        for step in range(400):
            q = (round(v[0], 2), round(v[1] + step * A.nudge_um, 2))
            if occ[q] == 0 and not inside(q, bx) and q[1] <= H - A.margin:
                break
        else:
            q = (round(v[0], 2), round(v[1], 2))
        occ[q] += 1
        new[k] = [q[0], q[1]]
    # final whole-chain check: a later group can break an earlier bit's hop -> revert that bit's stages
    for inst, c in ch.items():
        D = c["D"]
        for b, ks in c["bits"].items():
            js, oldp, _ = bit_path(inst, b)
            rep["preexisting_over_reach"] += sum(1 for i in range(len(oldp) - 1)
                                                 if js[i + 1] == js[i] + 1 and L1(oldp[i], oldp[i + 1]) > A.reach)
            if not bit_ok(inst, b):
                rep["hop_worse"] += 1
                for j in ks:
                    if legal(rs[ks[j]]) != rs[ks[j]]:
                        new[ks[j]] = legal(rs[ks[j]])
                    else:
                        new.pop(ks[j], None)
    rep["buried_after"] = sum(1 for k in rs if PIPE.match(k) and inside(pos(k), bx))
    new = {k: v for k, v in new.items() if v != rs[k]}
    allbefore = list(rs.values())
    allafter = [new.get(k, v) for k, v in rs.items()]
    pipe_b = [rs[k] for k in rs if PIPE.match(k)]
    pipe_a = [new.get(k, rs[k]) for k in rs if PIPE.match(k)]
    st = [p for s0 in (t.get("internal_stations") or []) for p in (s0.get("regs_um") or [])]
    rep["strip"] = A.strip
    rep["strip_pipe_per100_before"] = density(pipe_b, *A.strip, W)
    rep["strip_pipe_per100_after"] = density(pipe_a, *A.strip, W)
    rep["strip_all_relay_per100_before"] = density(allbefore, *A.strip, W)
    rep["strip_all_relay_per100_after"] = density(allafter, *A.strip, W)
    rep["pipe_max_per_10um_cell_before"] = cell_max(pipe_b)
    rep["pipe_max_per_10um_cell_after"] = cell_max(pipe_a)
    rep["pipe_max_per_50um_cell_before"] = cell_max(pipe_b, 50.0)
    rep["pipe_max_per_50um_cell_after"] = cell_max(pipe_a, 50.0)
    rep["station_points"] = len(st)
    rep["pipes"] = len(ch)
    rep["pipe_seats"] = len(pipe_b)
    rep["keys_changed"] = len(new)
    return new, rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out_dir")
    ap.add_argument("--types", nargs="*")
    ap.add_argument("--prefix", default="cb", help="default type set: partition types with this prefix that have pipe seats")
    ap.add_argument("--reach", type=float, default=405.0)
    ap.add_argument("--halo", type=float, default=6.0)
    ap.add_argument("--margin", type=float, default=1.0)
    ap.add_argument("--max-width", type=float, default=160.0)
    ap.add_argument("--min-width", type=float, default=10.0)
    ap.add_argument("--min-band", type=float, default=60.0, help="a stage band thinner than this grows to it (around its centre)")
    ap.add_argument("--pitch-min", type=float, default=1.08)
    ap.add_argument("--col-um", type=float, default=20.0, help="seats of one stage within this x bin form one column group")
    ap.add_argument("--cell-cap", type=int, default=24, help="a stage cluster is crowded when a 10-um cell holds more seats")
    ap.add_argument("--channel-um", type=float, default=300.0, help="a free x interval wider than this is a horizontal channel")
    ap.add_argument("--max-band", type=float, default=120.0, help="largest y band (vertical street) or channel height a group grows to")
    ap.add_argument("--min-bits", type=int, default=32)
    ap.add_argument("--run-um", type=float, default=60.0, help="consecutive stages of one pipe this close (centre L1) form a run (sliced)")
    ap.add_argument("--max-partial", type=float, default=1.0, help="a group is retried narrower when more of its bits than this fraction move only part way")
    ap.add_argument("--nudge-um", type=float, default=0.27, help="step that separates two moved seats landing on one point")
    ap.add_argument("--order-um", type=float, default=25.0)
    ap.add_argument("--strip", type=float, nargs=2, default=[1990.0, 2110.0])
    ap.add_argument("--out-plan")
    A = ap.parse_args(argv)
    plan = json.loads(Path(A.plan).read_text())
    pt = plan["partition_types"]
    names = A.types or sorted(n for n, t in pt.items() if n.startswith(A.prefix)
                              and any(PIPE.match(k) for k in (t.get("relay_sites") or {})))
    out = Path(A.out_dir)
    report = {"plan": A.plan, "reach": A.reach, "halo": A.halo, "types": {}}
    for n in names:
        new, rep = spread_type(pt[n], A)
        report["types"][n] = rep
        (out / n).mkdir(parents=True, exist_ok=True)
        (out / n / "pipeseat_sites.json").write_text(json.dumps(new, indent=0, sort_keys=True) + "\n")
        pt[n]["relay_sites"].update(new)
        print(f"{n}: pipes {rep['pipes']} seats {rep['pipe_seats']} spread {rep['groups_spread']} kept {rep['groups_kept']} "
              f"moved {rep['seats_moved']} changed {rep['keys_changed']} buried {rep['buried_before']}->{rep['buried_after']} "
              f"stagger {rep['staggered_groups']} partial {rep.get('bits_partial', 0)} reverted_bits {rep['hop_worse']} max10 {rep['pipe_max_per_10um_cell_before']}->"
              f"{rep['pipe_max_per_10um_cell_after']} max50 {rep['pipe_max_per_50um_cell_before']}->{rep['pipe_max_per_50um_cell_after']}")
    (out / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    if A.out_plan:
        Path(A.out_plan).write_text(json.dumps(plan, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
