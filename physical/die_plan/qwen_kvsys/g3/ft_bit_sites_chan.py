#!/usr/bin/env python3
"""PATH-KV 10-25: channel-aware per-bit FT station sites for CORED KV types (hgi / hub / hg family).

Diagnosis (kv3_hgi_v3 f7 G2, iteration-0 congestion render): every straight-through W<->E slot jogs at the partition
middle (check.zroute xm = W/2 = 639 um), i.e. ft27 (1056 b), ft4 (908 b), ft3, ft2, ft24 all shift vertically in the ONE
104-um channel between core columns 2 and 3 (M3 overflow 1.40M), and S<->N slots jog at H/2 = 760 um, which is INSIDE
the third head-core row (cores obstruct M1-M7: capacity 0).  ft_bit_sites_gen.Jogs picks the jog in the middle half of
the span with no knowledge of the hard-core lattice.

Here the jog centre of every straight-through slot is chosen ONLY inside a core-free channel of the jog axis (hard
cores of the type projected on that axis, +-CLEAR), widest slot first, minimising the summed cross-track demand
(bits x |shift|) per channel; the slot's stagger band is fitted inside the channel (stagger compressed if the channel
is narrower than n x STAGGER_UM).  Turning slots keep the L route.  Stations: L_i*j/k on each bit's own route, legal
free sites outside cores (ft_bit_sites_gen.Sites), as the main ft_bit_sites contract.  Latency/station counts and pin
windows are unchanged (Z length is independent of the jog position).
usage: ft_bit_sites_chan.py die_plan.json TYPE[,TYPE..] OUT_plan.json [--report R.json] [--png-dir D]"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ft_bit_sites_gen as F  # noqa: E402

R = HERE.parents[3]
sys.path.insert(0, str(R / "tools/die_plan"))
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

CLEAR = 6.0


def free_iv(spans, lo, hi):
    sp = sorted((a - CLEAR, b + CLEAR) for a, b in spans)
    out, cur = [], lo
    for a, b in sp:
        if a > cur:
            out.append((cur, min(a, hi)))
        cur = max(cur, b)
    if cur < hi:
        out.append((cur, hi))
    return [(a, b) for a, b in out if b - a > 8.0]


class ChanJogs:  # noqa: E302
    def __init__(self, W, H, blocks):
        self.iv = {"x": free_iv([(b[0], b[2]) for b in blocks], 20.0, W - 20.0),
                   "y": free_iv([(b[1], b[3]) for b in blocks], 20.0, H - 20.0)}
        self.d = {"x": defaultdict(float), "y": defaultdict(float)}
        self.size = {"x": W, "y": H}
        self.rects = None
        self.cur = None
        self.core_span = {"x": (min((b[0] for b in blocks), default=W), max((b[2] for b in blocks), default=0)),
                          "y": (min((b[1] for b in blocks), default=H), max((b[3] for b in blocks), default=0))}

    def pick(self, axis, lo, hi, n, shift):
        """jog centre on a 10-um grid inside a channel of [lo, hi]; the stagger band (n x STAGGER, compressed to the
        channel width) must lie inside the channel; least peak per-column cross-track demand density wins"""
        G = 10.0
        best = None
        for k, (a, b) in enumerate(self.iv[axis]):
            if b < lo or a > hi:
                continue
            a2, b2 = max(a, lo), min(b, hi)
            cap = b - a
            stag = min(F.STAGGER_UM, max(0.0, cap - 2.0) / max(n, 1))
            band = max(G, n * stag)
            cands = [(a2 + b2) / 2] if b2 - a2 <= band else \
                [a2 + band / 2 + j * G for j in range(int((b2 - a2 - band) // G) + 1)]
            for c in cands:
                cols = range(int((c - band / 2) // G), int((c + band / 2) // G) + 1)
                cost = max(self.d[axis][q] for q in cols) + n * abs(shift) / band + 1e-3 * abs(c - (lo + hi) / 2)
                if best is None or cost < best[0]:
                    best = (cost, k, c, stag, cols, band)
        if best is None and self.rects is not None:
            best = self.pick_free(axis, lo, hi, n, shift)
        if best is None:
            raise SystemExit(f"no {axis} channel in [{lo:.1f},{hi:.1f}]")
        _, k, c, stag, cols, band = best
        for q in cols:
            self.d[axis][q] += n * abs(shift) / band
        return c, stag, k


def _hit(boxes, x0, y0, x1, y1):
    return any(a - CLEAR < x1 and x0 < c + CLEAR and b - CLEAR < y1 and y0 < d + CLEAR for a, b, c, d in boxes)


def pick_free(self, axis, lo, hi, n, shift):
    """irregular core field (no straight channel across the whole type, e.g. kv3_hub_Wi): the jog band at c is legal
    when the in-leg, the jog and the out-leg rectangles of the whole slot (all bits) miss every core (+CLEAR)"""
    G = 2.0
    A, B, fin = self.cur
    stag = F.STAGGER_UM
    band = max(G, n * stag)
    best = None
    ai = [q[1 if axis == "x" else 0] for q in A.values()]
    bi = [q[1 if axis == "x" else 0] for q in B.values()]
    ax0 = [q[0 if axis == "x" else 1] for q in A.values()]
    bx0 = [q[0 if axis == "x" else 1] for q in B.values()]
    a_lo, a_hi, b_lo, b_hi = min(ai), max(ai), min(bi), max(bi)
    c = lo + band / 2
    while c <= hi - band / 2:
        m0, m1 = c - band / 2, c + band / 2
        legs = [(min(ax0 + [m0]), a_lo, max(ax0 + [m1]), a_hi), (min(bx0 + [m0]), b_lo, max(bx0 + [m1]), b_hi),
                (m0, min(a_lo, b_lo), m1, max(a_hi, b_hi))]
        if axis == "y":
            legs = [(y0, x0, y1, x1) for x0, y0, x1, y1 in legs]
        if not any(_hit(self.rects, *r) for r in legs):
            cols = range(int((c - band / 2) // 10), int((c + band / 2) // 10) + 1)
            cost = max(self.d[axis][q] for q in cols) + n * abs(shift) / band + 1e-3 * abs(c - (lo + hi) / 2)
            if best is None or cost < best[0]:
                best = (cost, -1, c, stag, cols, band)
        c += G
    return best


def shadow(J, axis, v):
    """v lies in the shadow of a core column (axis x) / core row (axis y) or in a corner strip narrower than the station
    keep-out: not inside any free channel -> nearest channel centre"""
    iv = J.iv[axis]
    lo, hi = iv[0][0], iv[-1][1]
    if v < lo or v > hi:          # edge strip between a face and the first core column/row: a routing channel itself
        return None
    if any(a - 2.5 <= v <= b + 2.5 for a, b in iv):     # pins packed into mouths at core +-4 um (chan_windows)
        return None
    return min(((a + b) / 2 for a, b in iv), key=lambda c: abs(c - v))


def strip(face, W, H):
    """centre line of the core-free strip between a face and the first core row/column"""
    return {"S": 8.0, "N": H - 8.0, "W": 8.0, "E": W - 8.0}[face]


def detour(a, b, fin, fout, m, J, W, H):
    """straight-through route a -> b with the jog at m; a leg whose pin sits in a core shadow first runs along the face
    strip to the nearest channel (cores obstruct M1-M7: a leg through a core has no track)"""
    if fin in "EW":
        ca, cb = shadow(J, "y", a[1]), shadow(J, "y", b[1])
        r = [a]
        if ca is not None:
            r += [(strip(fin, W, H), a[1]), (strip(fin, W, H), ca)]
        ya = ca if ca is not None else a[1]
        yb = cb if cb is not None else b[1]
        r += [(m, ya), (m, yb)]
        if cb is not None:
            r += [(strip(fout, W, H), cb), (strip(fout, W, H), b[1])]
        return r + [b]
    ca, cb = shadow(J, "x", a[0]), shadow(J, "x", b[0])
    r = [a]
    if ca is not None:
        r += [(a[0], strip(fin, W, H)), (ca, strip(fin, W, H))]
    xa = ca if ca is not None else a[0]
    xb = cb if cb is not None else b[0]
    r += [(xa, m), (xb, m)]
    if cb is not None:
        r += [(cb, strip(fout, W, H)), (b[0], strip(fout, W, H))]
    return r + [b]


def in_edge_strip(J, axis, v):
    """v lies in a NARROW strip (< 2 x FACE_KEEP) between a face and the first / last core column (row)"""
    lo, hi = J.core_span[axis]
    L = J.size[axis]
    return (v < lo and lo < 2 * F.FACE_KEEP_UM) or (v > hi and L - hi < 2 * F.FACE_KEEP_UM)


class StripSites(F.Sites):
    """F.Sites keeps FACE_KEEP_UM (20 um) free along every face for the face-register bands.  Face pins of a cored KV
    type sit only in channel mouths (chan_windows), so in front of a hard core (core shadow on that face) the strip
    between the face and the core holds no face register: a station may use it (x/y >= ORIGIN, core +CLEAR)."""

    def __init__(self, W, H, blocks, J):
        super().__init__(W, H, blocks)
        self.J = J
        self.relax = False

    def ok(self, c, r):
        if not self.relax:
            return F.Sites.ok(self, c, r)
        if c < 0 or r < 0 or c > self.nx or r > self.ny or (c, r) in self.used:
            return False
        x, y = self.x0 + c * F.COL_UM, self.y0 + r * F.ROW
        K = F.FACE_KEEP_UM
        near_x = x < K or x + F.CELL[0] > self.W - K
        near_y = y < K or y + F.CELL[1] > self.H - K
        if near_x and shadow(self.J, "y", y + F.CELL[1] / 2) is None:
            return False
        if near_y and shadow(self.J, "x", x + F.CELL[0] / 2) is None:
            return False
        return not any(a - F.CLEAR < x + F.CELL[0] and x < c2 + F.CLEAR and b - F.CLEAR < y + F.CELL[1] and y < d + F.CLEAR
                       for a, b, c2, d in self.blocks)


ChanJogs.pick_free = pick_free


def run(raw, P, tn, png=None):
    t = raw["partition_types"][tn]
    W, H = t["outline_um"]
    blocks = []
    for c in (t.get("hard_cores") or []) + [c for c in t.get("contents", []) if "origin_um" in c]:
        (ox, oy), (cw, ch) = c["origin_um"], c.get("outline_um", [4.32, 4.32])
        blocks.append((ox, oy, ox + cw, oy + ch))
    for e in t.get("internal_stations", []):
        for x, y in e["regs_um"]:
            blocks.append((x - 3, y - 3, x + 3, y + 3))
    J = ChanJogs(W, H, [b for b in blocks if (b[2] - b[0]) > 20])
    J.rects = [b for b in blocks if (b[2] - b[0]) > 20]
    St = StripSites(W, H, blocks, J)
    pins = defaultdict(dict)
    for bus, bit, ln, x, y, f in gen_phys.type_pins(P, tn):
        pins[bus][bit] = (x, y)
    rep = dict(type=tn, channels=J.iv, slots={})
    draw = []
    for s in sorted(t["ft_slots"], key=lambda s: -s["width"]):
        k = int(s.get("stations", 1))
        if k < 2:
            continue
        nm = s["name"]
        A, B = pins[nm + "_i"], pins[nm + "_o"]
        n = s["width"] + 1
        if len(A) != n or len(B) != n:
            raise SystemExit(f"{tn} {nm}: {len(A)}/{len(B)} pins for width+1 = {n}")
        fin, fout = s.get("in_face", "W"), s.get("out_face", "E")
        ax = 1 if fin in "EW" else 0
        order = sorted(range(n), key=lambda i: A[i][ax])
        rank = {i: r for r, i in enumerate(order)}
        dshift = sum(B[i][ax] - A[i][ax] for i in range(n)) / n
        sgn = 1 if dshift < 0 else -1
        jog, stag, ch = None, F.STAGGER_UM, None
        # strip stations only for a slot whose pins sit in an edge strip (its straight leg runs in that strip)
        St.relax = any(in_edge_strip(J, "x" if f in "NS" else "y", q[0] if f in "NS" else q[1])
                       for f, Q in ((fin, A), (fout, B)) for q in Q.values())
        if (fin in "EW") == (fout in "EW"):
            lo, hi = (min(A[0][0], B[0][0]), max(A[0][0], B[0][0])) if fin in "EW" else \
                     (min(A[0][1], B[0][1]), max(A[0][1], B[0][1]))
            J.cur = (A, B, fin)
            jog, stag, ch = J.pick("x" if fin in "EW" else "y", lo, hi, n, dshift)
        stages = [[None] * n for _ in range(k - 1)]
        disp = hop = 0.0
        for i in order:
            if jog is None:
                r = F.bit_routes(A[i], B[i], fin, fout, rank[i], n, sgn, jog)
            else:
                off = (rank[i] - (n - 1) / 2) * stag * sgn
                r = detour(A[i], B[i], fin, fout, jog + off, J, W, H)
            L = F.plen(r)
            pts = [A[i]]
            for j in range(1, k):
                p = F.at(r, L * j / k)
                seg = next(((u, v) for u, v in zip(r, r[1:]) if min(u[0], v[0]) - 1e-6 <= p[0] <= max(u[0], v[0]) + 1e-6
                            and min(u[1], v[1]) - 1e-6 <= p[1] <= max(u[1], v[1]) + 1e-6), (r[0], r[1]))
                horiz = abs(seg[0][1] - seg[1][1]) < 1e-6
                xy = St.take(p[0], p[1], horiz)
                stages[j - 1][i] = [xy[0], xy[1]]
                c = (xy[0] + F.CELL[0] / 2, xy[1] + F.CELL[1] / 2)
                disp = max(disp, F.man(c, p))
                pts.append(c)
            pts.append(B[i])
            hop = max(hop, max(F.man(u, v) for u, v in zip(pts, pts[1:])))
            if i % 16 == 0:
                draw.append((r, pts[1:-1]))
        s["bit_sites_um"] = stages
        s["bit_site_cell_um"] = list(F.CELL)
        s.pop("regs_um", None)
        rep["slots"][nm] = dict(width=s["width"], faces=fin + fout, stations=k, jog_um=jog, channel=ch,
                                stagger_um=stag, max_disp_um=round(disp, 2), max_bit_hop_um=round(hop, 1))
    rep["max_bit_hop_um"] = max((v["max_bit_hop_um"] for v in rep["slots"].values()), default=0)
    rep["sites"] = len(St.used)
    if png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, axp = plt.subplots(figsize=(12, 12 * H / W + 1))
        axp.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2))
        for b in blocks:
            axp.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], color="#ddd"))
        for r, st in draw:
            axp.plot([q[0] for q in r], [q[1] for q in r], color="#47a", lw=0.3)
        xs = [St.x0 + c * F.COL_UM for (c, r_) in St.used]
        ys = [St.y0 + r_ * F.ROW for (c, r_) in St.used]
        axp.plot(xs, ys, ",", color="tab:red")
        axp.set_aspect("equal")
        axp.set_title(f"{tn}: {len(St.used)} ft station sites (red), every 16th bit route (blue), cores grey", fontsize=8)
        fig.tight_layout()
        fig.savefig(png, dpi=130)
    return rep


def main():
    pf, tns, outf = sys.argv[1:4]
    rep_f = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    pdir = sys.argv[sys.argv.index("--png-dir") + 1] if "--png-dir" in sys.argv else None
    raw = json.load(open(pf))
    P = S.Plan(S.load(pf), Path(pf).resolve())
    reps = {}
    for tn in tns.split(","):
        try:
            reps[tn] = run(raw, P, tn, png=f"{pdir}/{tn}_ftsites.png" if pdir else None)
        except SystemExit as e:
            print(tn, "SKIPPED (type left unchanged):", e)
            raw["partition_types"][tn] = json.loads(json.dumps(S.load(pf)["partition_types"][tn]))
            continue
        print(tn, json.dumps({k: reps[tn][k] for k in ("sites", "max_bit_hop_um")}),
              {s: (v["faces"], v["width"], v["jog_um"] and round(v["jog_um"], 1)) for s, v in reps[tn]["slots"].items()
               if v["width"] > 100})
    Path(outf).write_text(json.dumps(raw, indent=1) + "\n")
    if rep_f:
        Path(rep_f).write_text(json.dumps(reps, indent=1) + "\n")


if __name__ == "__main__":
    main()
