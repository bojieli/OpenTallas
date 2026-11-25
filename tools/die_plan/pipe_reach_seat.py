#!/usr/bin/env python3
"""PIPE-REACH-SEAT (QC-CB-PIPESEAT 11-24, row CB-PIPEREACH): seat every bound delay pipe of a type on its street route.

The cb delay pipes (bind intra-partition ot_dp_dly u_d<D>_<src leaf>_<port>, kit-segmented u_..._sg<k> by kit_dly_lockup)
run core pin -> pipe -> u_pc_nk -> core pin, or column station xstn -> pipe -> xstn.  The C1j seats came from a straight
per-bit line cleared to the nearest macro edge (type_relay_sites --pipes on a placed C1h geometry): stages bunched at halo
edges, some seats inside a core whose box had moved, hops up to 470 um, and several pipes not seated at all.

Here, per pipe: launch A_b = source pin of bit b (core port pin from the core pins file, origin + orient) or the source xstn
(at its core's tap pin face), capture B_b likewise for the sink core port / xstn.  The pipe's centre route is the shortest
free-street path (grid BFS round the hard cores grown by --halo) from the A centroid to the B centroid; the D stage centres
sit at even arc length on it (k / (D + 1)); each stage is a bit grid across the free street at its centre (bit b keeps
its grid column in every stage), the stage band fitted between its neighbours.  Per bit every hop A_b -> s_1 .. s_D -> B_b
is checked at L1 <= --reach.  A pipe whose route needs more hops than D + 1 (route / (D + 1) > --reach - --margin-um) is
bucket b: `need_extra` stages are reported (relay_depth row), and with --extra its stages are seated for D + extra.

  pipe_reach_seat.py prep PLAN BIND_OUT OUT_DIR [--prefix cb]   -> OUT_DIR/topo.json (bound pipe source / sinks per type)
                                                                and OUT_DIR/kitseg.json (kit_dly_lockup segments per pipe)
  pipe_reach_seat.py PLAN KITSEG.json TOPO.json PLAN_DIR OUT_DIR [--types ..] [--reach 405] [--extra JSON]
OUT_DIR/<type>/pipereach_sites.json   relay_sites keys of every kit pipe flop (r[j][b] / q[b] per segment)
OUT_DIR/report.json                   per type and pipe: route length, hops, bucket, need_extra, max hop, buried
"""
import argparse, collections, json, math, re, sys
from pathlib import Path

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def grown(t, halo):
    return [(h["origin_um"][0] - halo, h["origin_um"][1] - halo, h["origin_um"][0] + h["outline_um"][0] + halo,
             h["origin_um"][1] + h["outline_um"][1] + halo) for h in t.get("hard_cores") or []]


def inside(p, bx):
    return any(b[0] < p[0] < b[2] and b[1] < p[1] < b[3] for b in bx)


def pin_xy(core, px, py):
    """core-frame pin (px, py) -> type frame for the core's origin / outline / orient"""
    (ox, oy), (w, h) = core["origin_um"], core["outline_um"]
    o = core.get("orient", "R0")
    if o in ("MY", "FN"):
        px = w - px
    elif o in ("MX", "FS"):
        py = h - py
    elif o in ("R180", "S"):
        px, py = w - px, h - py
    return (ox + px, oy + py)


class Pins:
    def __init__(self, plan_dir):
        self.dir = Path(plan_dir)
        self.cache = {}

    def port(self, core, port):
        f = core.get("pins_file")
        if f not in self.cache:
            d = json.loads((self.dir / f).read_text())
            by = collections.defaultdict(dict)
            for p in d["pins"]:
                m = re.match(r"(\w+)(?:\[(\d+)\])?$", p["name"])
                by[m.group(1)][int(m.group(2) or 0)] = (float(p["x"]), float(p["y"]))
            self.cache[f] = by
        return {b: pin_xy(core, *xy) for b, xy in self.cache[f].get(port, {}).items()}


class Grid:
    def __init__(self, W, H, bx, g):
        self.W, self.H, self.g = W, H, g
        self.nx, self.ny = int(math.ceil(W / g)), int(math.ceil(H / g))
        self.block = bytearray(self.nx * self.ny)
        for b in bx:
            for ix in range(max(0, int(b[0] // g)), min(self.nx, int(math.ceil(b[2] / g)))):
                for iy in range(max(0, int(b[1] // g)), min(self.ny, int(math.ceil(b[3] / g)))):
                    self.block[iy * self.nx + ix] = 1

    def snap(self, p):
        ix = min(self.nx - 1, max(0, int(p[0] // self.g)))
        iy = min(self.ny - 1, max(0, int(p[1] // self.g)))
        if not self.block[iy * self.nx + ix]:
            return ix, iy
        best = None
        for r in range(1, 400):
            for dx in range(-r, r + 1):
                for dy in {-r + abs(dx), r - abs(dx)}:
                    jx, jy = ix + dx, iy + dy
                    if 0 <= jx < self.nx and 0 <= jy < self.ny and not self.block[jy * self.nx + jx]:
                        best = (jx, jy)
                        break
                if best:
                    break
            if best:
                return best
        return ix, iy

    def path(self, a, b):
        """shortest 4-connected free path a -> b as a list of points (cell centres), plus its length"""
        ca, cb = self.snap(a), self.snap(b)
        nx = self.nx
        s, t = ca[1] * nx + ca[0], cb[1] * nx + cb[0]
        prev = {s: -1}
        q = collections.deque([s])
        while q:
            u = q.popleft()
            if u == t:
                break
            ux, uy = u % nx, u // nx
            for v, ok in ((u + 1, ux < nx - 1), (u - 1, ux > 0), (u + nx, uy < self.ny - 1), (u - nx, uy > 0)):
                if ok and v not in prev and not self.block[v]:
                    prev[v] = u
                    q.append(v)
        if t not in prev:
            return None, float("inf")
        cells = []
        u = t
        while u != -1:
            cells.append(((u % nx + 0.5) * self.g, (u // nx + 0.5) * self.g))
            u = prev[u]
        cells.reverse()
        pts = [tuple(a)] + cells + [tuple(b)]
        return pts, sum(L1(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def at_arc(pts, s):
    acc = 0.0
    for i in range(len(pts) - 1):
        d = L1(pts[i], pts[i + 1])
        if acc + d >= s and d > 0:
            f = (s - acc) / d
            return (pts[i][0] + f * (pts[i + 1][0] - pts[i][0]), pts[i][1] + f * (pts[i + 1][1] - pts[i][1]))
        acc += d
    return pts[-1]


def free_iv(bx, lo, hi, axis_len, margin, transpose=False):
    """free intervals along x (or y when transpose) over the band [lo, hi] of the other axis"""
    cut = sorted(((b[1], b[3]) if transpose else (b[0], b[2])) for b in bx
                 if ((b[0] < hi and b[2] > lo) if transpose else (b[1] < hi and b[3] > lo)))
    out, x = [], margin
    for a, c in cut:
        if a > x:
            out.append((x, min(a, axis_len - margin)))
        x = max(x, c)
    if x < axis_len - margin:
        out.append((x, axis_len - margin))
    return [iv for iv in out if iv[1] - iv[0] > 1.0]


def containing(ivs, v):
    for iv in ivs:
        if iv[0] - 1e-6 <= v <= iv[1] + 1e-6:
            return iv
    return min(ivs, key=lambda iv: min(abs(v - iv[0]), abs(v - iv[1]))) if ivs else None


def leaf_core(t):
    """bound leaf name (u_t_0_1) -> hard core record"""
    hc = {h["inst"]: h for h in t.get("hard_cores") or []}
    out = {}
    for c in t.get("contents") or []:
        if c.get("parent_id_leaf") and c["inst"] in hc:
            out[c["parent_id_leaf"]] = hc[c["inst"]]
    for inst, h in hc.items():                       # u_t01 <-> u_t_0_1
        m = re.match(r"u_t(\d)(\d)$", inst)
        if m:
            out.setdefault(f"u_t_{m.group(1)}_{m.group(2)}", h)
    return out


def seat_type(tn, t, segs, topo, pins, A):
    W, H = t["outline_um"]
    bx = grown(t, A.halo)
    G = Grid(W, H, bx, A.grid)
    cores = leaf_core(t)
    trow = {}
    sites = {}
    byinst = {r["inst"]: r for r in topo}
    for pipe, seglist in segs.items():
        row = byinst.get(pipe)
        if row is None:
            trow[pipe] = dict(skip="not in bound topology")
            continue
        width = row["W"]
        D = sum(s[1] for s in seglist)
        extra = int((A.extra_map.get(tn) or {}).get(pipe, 0))

        def end(ref, side):
            inst, port = ref.split(".") if "." in ref else (ref, None)
            m = re.match(r"u_pc_nk_(u_t_\d+_\d+)_(\w+)$", ref)
            if m:                                           # the sink core input port behind its lockup pipe
                inst, port = "u_" + m.group(1), m.group(2)
            inst = inst[2:] if inst.startswith("u_u_") else inst
            m = re.match(r"u_fab_u_x_(\d+)_(\d+)$", inst)
            if m:                                           # column station xstn: at its core's tap pin face
                c = cores.get(f"u_t_{m.group(1)}_{m.group(2)}")
                tp = pins.port(c, "tap") if c else {}
                if not tp:
                    return None
                cx = sum(p[0] for p in tp.values()) / len(tp)
                cy = sum(p[1] for p in tp.values()) / len(tp)
                return {b: (cx, cy) for b in range(width)}
            c = cores.get(inst)
            if c is None or port is None:
                return None
            return pins.port(c, port)
        Ab = end(row["src"], "src")
        sink = next((c for c in row["cons"] if not c.startswith("u_cland")), None)
        Bb = end(sink, "sink") if sink else None
        if not Ab or not Bb:
            trow[pipe] = dict(skip=f"no ends src {row['src']} sink {sink}")
            continue
        ac = (sum(p[0] for p in Ab.values()) / len(Ab), sum(p[1] for p in Ab.values()) / len(Ab))
        bc = (sum(p[0] for p in Bb.values()) / len(Bb), sum(p[1] for p in Bb.values()) / len(Bb))
        route, L = G.path(ac, bc)
        if route is None:
            trow[pipe] = dict(skip="no free route")
            continue
        Dt = D + extra
        hops = Dt + 1
        need = max(0, int(math.ceil(L / (A.reach - A.margin_um))) - (D + 1))
        centres = [at_arc(route, L * k / hops) for k in range(1, Dt + 1)]
        spacing = L / hops

        def stage_grid(c, shrink):
            yiv = free_iv(bx, c[1] - 1, c[1] + 1, W, A.margin)
            xs = containing(yiv, c[0])
            xiv = free_iv(bx, c[0] - 1, c[0] + 1, H, A.margin, transpose=True)
            ys = containing(xiv, c[1])
            wx = (xs[1] - xs[0]) if xs else 0.0
            wy = (ys[1] - ys[0]) if ys else 0.0
            vertical = wx <= wy                           # the street runs along y: spread across x
            span_w = max(2.0, min(wx if vertical else wy, A.max_width) * shrink)
            if vertical:
                band = max(2.0, min(max(A.min_band, width * A.seat_area / max(span_w, 1.0)), max(A.min_band, 0.8 * spacing),
                                    A.max_band) * shrink)
            else:                                         # a horizontal margin / channel: spread along its length
                band = max(2.0, max(A.min_band, min(A.h_band_frac * spacing, A.max_band_h)) * shrink)
            if vertical:
                lo = min(max(xs[0], c[0] - span_w / 2), xs[1] - span_w)
                rx, ry = (lo, lo + span_w), (c[1] - band / 2, c[1] + band / 2)
            else:
                lo = min(max(ys[0], c[1] - span_w / 2), ys[1] - span_w)
                ry, rx = (lo, lo + span_w), (c[0] - band / 2, c[0] + band / 2)
            wa, wb = (rx[1] - rx[0], ry[1] - ry[0]) if vertical else (ry[1] - ry[0], rx[1] - rx[0])
            cell = math.sqrt(max(wa * wb, 1.0) / width)
            na = max(1, min(width, int(wa / max(cell, A.pitch_min))))
            nb = int(math.ceil(width / na))
            st = {}
            for b in range(width):
                ua, ub = (b % na + 0.5) / na, (b // na + 0.5) / nb
                if vertical:
                    p = (rx[0] + ua * (rx[1] - rx[0]), ry[0] + ub * (ry[1] - ry[0]))
                else:
                    p = (rx[0] + ub * (rx[1] - rx[0]), ry[0] + ua * (ry[1] - ry[0]))
                p = legal(p)
                st[b] = (round(p[0], 3), round(p[1], 3))
            return st

        def legal(p):
            for bb in bx:
                if bb[0] < p[0] < bb[2] and bb[1] < p[1] < bb[3]:
                    return min(((p[0] - bb[0], (bb[0] - 0.01, p[1])), (bb[2] - p[0], (bb[2] + 0.01, p[1])),
                                (p[1] - bb[1], (p[0], bb[1] - 0.01)), (bb[3] - p[1], (p[0], bb[3] + 0.01))))[1]
            return p

        shrink = [1.0] * Dt
        for _it in range(A.iters):
            seats = [stage_grid(c, shrink[k]) for k, c in enumerate(centres)]
            bad = set()
            for b in range(width):
                ch = [Ab.get(b, ac)] + [s[b] for s in seats] + [Bb.get(b, bc)]
                for i in range(len(ch) - 1):
                    if L1(ch[i], ch[i + 1]) > A.target:
                        bad.update(k for k in (i - 1, i) if 0 <= k < Dt)
            if not bad:
                break
            for k in bad:
                shrink[k] *= 0.6
        worst, over, buried = 0.0, 0, 0
        for b in range(width):
            ch = [Ab.get(b, ac)] + [s[b] for s in seats] + [Bb.get(b, bc)]
            hs = [L1(ch[i], ch[i + 1]) for i in range(len(ch) - 1)]
            worst = max(worst, max(hs))
            over += sum(1 for h in hs if h > A.reach)
            buried += sum(1 for s in seats if inside(s[b], bx))
        bucket = "ok" if over == 0 and buried == 0 and need == 0 else ("a" if need == 0 and over == 0 else "b")
        trow[pipe] = dict(D=D, extra=extra, route_um=round(L, 1), hops=hops, hop_avg=round(spacing, 1), need_extra=need,
                          worst_hop=round(worst, 1), bits_over=over, buried=buried, bucket=bucket, A=[round(v, 1) for v in ac],
                          B=[round(v, 1) for v in bc], src=row["src"], sink=sink)
        if extra:
            continue                                      # an extended pipe's names come from the bind of its relay_depth row
        # names: kit segments in order, r[0..Dseg-2] + q per segment
        k = 0
        for inst, Dseg, _sg, _w in seglist:
            for j in range(Dseg):
                key = f"{inst}.q[{{b}}]" if j == Dseg - 1 else f"{inst}.r[{j}][{{b}}]"
                for b in range(width):
                    sites[key.format(b=b)] = list(seats[k][b])
                k += 1
    return sites, trow


def bound_rtl(rtl, tn, t):
    import seat_match as SM
    f = SM._bound_file(Path(rtl), tn)
    if f is None:
        for c in (Path(rtl) / f"{t.get('module')}__{tn}.sv", Path(rtl) / f"{t.get('module')}.sv"):
            if c.is_file():
                return c
    return f


DLY = re.compile(r"ot_dp_dly #\(\.W\((\d+)\), \.D\((\d+)\)\) (u_d\d+_\w+) \(\.clk\(clk\), \.d\(([^)]*)\), \.q\(([^)]*)\)\);")
INST = re.compile(r"\n\s+(\w+)(?: #\([^;]*?\))? (\w+) \(\n")


def topology(src):
    """bound delay pipes of one type: [{inst, W, D, src 'inst.port', cons ['inst.port' | flop inst]}]"""
    rows = []
    for m in DLY.finditer(src):
        W, D, inst, d, q = m.groups()
        cons = [mm.group(1) for mm in re.finditer(r"(\w+) \(\.clk\(clk\), \.d\(" + re.escape(q) + r"\[", src)]
        for mm in re.finditer(r"\.(\w+)\(" + re.escape(q) + r"\[", src):
            im = list(INST.finditer(src[:mm.start()]))
            if im:
                cons.append(f"{im[-1].group(2)}.{mm.group(1)}")
        drv = None
        for mm in re.finditer(r"\.(\w+)\(" + re.escape(d) + r"\)", src):
            im = list(INST.finditer(src[:mm.start()]))
            if im and im[-1].group(2) != inst:
                drv = f"{im[-1].group(2)}.{mm.group(1)}"
        rows.append(dict(inst=inst, W=int(W), D=int(D), src=drv, cons=cons))
    return rows


def prep(argv):
    ap = argparse.ArgumentParser(prog="pipe_reach_seat.py prep")
    ap.add_argument("plan")
    ap.add_argument("bind_out", help="strict bind dir (rtl/<type>.sv)")
    ap.add_argument("out_dir")
    ap.add_argument("--prefix", default="cb")
    A = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kit_dly_lockup, seat_match as SM
    from gen_phys import dly_lockup_cfg
    P = json.loads(Path(A.plan).read_text())
    topo, kseg = {}, {}
    for tn, t in sorted(P["partition_types"].items()):
        if not tn.startswith(A.prefix) or not isinstance(t, dict):
            continue
        f = bound_rtl(Path(A.bind_out) / "rtl", tn, t)
        if f is None:
            print("NO-RTL", tn)
            continue
        src = f.read_text()
        topo[tn] = topology(src)
        cfg = dly_lockup_cfg(P["budgets"], tn)
        macros = {r["module"] for r in t.get("hard_cores", []) if "module" in r}
        kit = kit_dly_lockup.apply(src, core_types=macros, **cfg)[0] if cfg else src
        segs = {}
        for i, (mod, par) in SM.bound_instances(kit).items():
            m = re.match(r"(u_d\d+_\w+?)(?:_sg(\d+))?$", i)
            if mod in ("ot_dp_dly", "ot_dp_dly_keep") and m:
                segs.setdefault(m.group(1), []).append([i, int(par.get("D", 1)), int(m.group(2) or 0), int(par.get("W", 1))])
        for v in segs.values():
            v.sort(key=lambda r: r[2])
        kseg[tn] = segs
        print("PREP", tn, "pipes", len(topo[tn]), "kit segments", sum(len(v) for v in segs.values()))
    out = Path(A.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "topo.json").write_text(json.dumps(topo, indent=1) + "\n")
    (out / "kitseg.json").write_text(json.dumps(kseg, indent=1) + "\n")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["prep"]:
        return prep(argv[1:])
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("kitseg")
    ap.add_argument("topo")
    ap.add_argument("plan_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--types", nargs="*")
    ap.add_argument("--reach", type=float, default=405.0)
    ap.add_argument("--margin-um", type=float, default=110.0, help="route / hops must stay this far below reach (grid offsets)")
    ap.add_argument("--halo", type=float, default=6.0)
    ap.add_argument("--margin", type=float, default=1.0)
    ap.add_argument("--grid", type=float, default=5.0)
    ap.add_argument("--max-width", type=float, default=110.0)
    ap.add_argument("--min-band", type=float, default=30.0)
    ap.add_argument("--max-band", type=float, default=120.0)
    ap.add_argument("--seat-area", type=float, default=10.0, help="um^2 per seat that sizes the stage band")
    ap.add_argument("--pitch-min", type=float, default=1.08)
    ap.add_argument("--iters", type=int, default=8)
    ap.add_argument("--h-band-frac", type=float, default=0.9, help="stage band along a horizontal street, x hop spacing")
    ap.add_argument("--max-band-h", type=float, default=360.0)
    ap.add_argument("--nudge-um", type=float, default=0.27)
    ap.add_argument("--target", type=float, default=380.0, help="the grid shrinks until every hop is <= this (slack under --reach)")
    ap.add_argument("--extra", help="JSON {type: {pipe: extra stages}} (bucket b, after the relay_depth row binds)")
    A = ap.parse_args(argv)
    A.extra_map = json.loads(Path(A.extra).read_text()) if A.extra else {}
    P = json.loads(Path(A.plan).read_text())
    KS = json.loads(Path(A.kitseg).read_text())
    TP = json.loads(Path(A.topo).read_text())
    pins = Pins(A.plan_dir)
    out = Path(A.out_dir)
    rep = {}
    for tn in sorted(KS):
        if A.types and tn not in A.types:
            continue
        t = P["partition_types"][tn]
        sites, trow = seat_type(tn, t, KS[tn], TP.get(tn, []), pins, A)
        # distinct seats: off every other plan site and every other pipe seat (one row pitch at a time, outside the cores)
        bx = grown(t, A.halo)
        occ = collections.Counter((round(v[0], 2), round(v[1], 2)) for k, v in (t.get("relay_sites") or {}).items()
                                  if not re.match(r"(?:u_bound\.)?u_d\d+_", k))
        for e in t.get("internal_stations") or []:
            for p in e.get("regs_um") or []:
                occ[(round(p[0], 2), round(p[1], 2))] += 1
        moved = 0
        for k in sorted(sites):
            v = sites[k]
            for step in range(400):
                q = (round(v[0], 2), round(v[1] + step * A.nudge_um * (1 if step % 2 else -1) * ((step + 1) // 2) / max(step, 1), 2))
                if occ[q] == 0 and not inside(q, bx) and A.margin <= q[1] <= t["outline_um"][1] - A.margin:
                    break
            else:
                q = (round(v[0], 2), round(v[1], 2))
            moved += q != (round(v[0], 2), round(v[1], 2))
            occ[q] += 1
            sites[k] = [q[0], q[1]]
        old = {k for k in (t.get("relay_sites") or {}) if re.match(r"(?:u_bound\.)?u_d\d+_", k)}
        stale = sorted(old - set(sites))
        (out / tn).mkdir(parents=True, exist_ok=True)
        (out / tn / "pipereach_sites.json").write_text(json.dumps(sites, sort_keys=True) + "\n")
        rep[tn] = dict(pipes=trow, nudged=moved, keys=len(sites), old_keys=len(old), new_keys=len(set(sites) - old), stale_old_keys=len(stale))
        for p, r in trow.items():
            print(tn, p, {k: r.get(k) for k in ("skip", "D", "route_um", "hop_avg", "worst_hop", "bits_over", "buried",
                                                  "bucket", "need_extra")})
        print(tn, "keys", len(sites), "new", len(set(sites) - old), "stale_old", len(stale))
    (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
