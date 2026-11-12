#!/usr/bin/env python3
"""svc_street_form.py PLAN_IN PLAN_OUT SPEC.json [--types RE] [--report OUT.json]

VL3-S81-SVCSTN positions/orientation-only street form for the S81 svc_rs family (64 x ot_s81c_attn_hcore in 8 rows x
8 columns + one row of 8 dsdv_svc_sx_hrow + an SRAM band above the top attn row).  Core shapes, pins, buses, ft slots,
stations counts, bands and widths are unchanged (core_place.eq_gate).

SPEC = {"pair_gap": 8.64, "top_gap": 43.2, "sram_gap": 43.2, "bottom_min": 43.2, "lattice": 4.32,
        "pair_rows": true, "x": null | {"cols_x": [8 x]} }
  pair_rows: the 8 attn rows form 4 pairs (r0,r1) (r2,r3) | hrow | (r4,r5) (r6,r7); the lower row of each pair is MX
  so the two 2-pin S faces (clk, rst_n) face each other across pair_gap and every 580-pin N face (ib) looks into a wide
  street.  The streets (bottom ring, P1|P2, P2|hrow, hrow|P3, P3|P4, P4|SRAM) share the free height equally on the
  lattice; the top ring gets top_gap.  pair_rows false = all rows R0, every gap equal (the uniform comparator).

Every plan coordinate of the type moves by ONE separable piecewise-translation map (x, y): a point on a core (or within
HALO um of one of its faces, i.e. its pin drivers / reset relays) rides the core (mirrored for an MX row), a point in a
street moves by the mean shift of its two neighbours (stays in the widened street, lattice kept), a point within FACE um
of the outline is never moved (face pins, edge clock taps), the bottom ring moves 0, the top ring rides the SRAM band.
Bus/ft windows, outline, pins files are not touched.  Checks: macro overlap / outline, every point that was outside the
macros is still outside, eq_gate.  Exit 1 on any failure."""
import argparse, copy, hashlib, json, math, re, sys
from pathlib import Path

FACE = 3.0
HALO = 8.64
PT_KEYS = {"xy", "xy_um", "pin_um", "pin_xy_um", "tap_um", "root"}
PTLIST_KEYS = {"regs_um", "outs", "sink_sites_um"}
RECT_KEYS = {"rect_um"}
RECTLIST_KEYS = {"rects_um"}
SKIP = {"buses", "outline_um", "face_layers", "window_um", "in_window_um", "out_window_um", "track_offset_um",
        "hard_cores", "contents", "bit_site_cell_um", "dead_inputs"}


def isnum(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def snap(v, q):
    return round(round(v / q) * q, 4)


class Form:
    def __init__(self, t, spec):
        self.t = t
        self.W0, self.H0 = t["outline_um"]
        g = spec.get("grow") or [0.0, 0.0]
        self.dxg, self.dyg = float(g[0]), float(g[1])
        self.W, self.H = self.W0 + self.dxg, self.H0 + self.dyg
        hc = t["hard_cores"]
        self.attn = [i for i, h in enumerate(hc) if "attn_hcore" in h["lef"]]
        self.hrow = [i for i, h in enumerate(hc) if "hrow" in h["lef"]]
        assert len(self.attn) == 64 and len(self.hrow) == 8, (len(self.attn), len(self.hrow))
        assert all(hc[i].get("orient", "R0") == "R0" for i in self.attn + self.hrow)
        ah = hc[self.attn[0]]["outline_um"][1]
        rows = sorted(set(hc[i]["origin_um"][1] for i in self.attn))
        assert len(rows) == 8
        hy = set(hc[i]["origin_um"][1] for i in self.hrow)
        assert len(hy) == 1
        hy = hy.pop(); hh = hc[self.hrow[0]]["outline_um"][1]
        top = rows[-1] + ah
        self.cx0 = min(hc[i]["origin_um"][0] for i in self.attn)
        self.cx1 = max(hc[i]["origin_um"][0] + hc[i]["outline_um"][0] for i in self.attn)
        cs = [c for c in t.get("contents") or [] if "origin_um" in c and "outline_um" in c]
        band = [c for c in cs if c["origin_um"][1] >= top - 0.01]
        assert len(band) == len(cs), "contents below the top attn row"
        sy0 = min(c["origin_um"][1] for c in band); sy1 = max(c["origin_um"][1] + c["outline_um"][1] for c in band)
        # y solids in order
        sol = [(r, r + ah, "r%d" % k) for k, r in enumerate(rows[:4])] + [(hy, hy + hh, "hrow")] + \
              [(r, r + ah, "r%d" % (k + 4)) for k, r in enumerate(rows[4:])] + [(sy0, sy1, "sram")]
        for a, b in zip(sol, sol[1:]):
            assert a[1] <= b[0] + 1e-6, (a, b)
        self.sol = sol
        L = spec.get("lattice", 4.32)
        sizes = [b - a for a, b, _ in sol]
        free = self.H - sum(sizes)
        names = [n for _, _, n in sol]
        orient = {n: "R0" for n in names}
        gaps = [None] * (len(sol) + 1)   # gaps[k] = gap below solid k; gaps[-1] = top
        if spec.get("pair_rows", True):
            pg = spec.get("pair_gap", 8.64)
            for lo, hi in (("r0", "r1"), ("r2", "r3"), ("r4", "r5"), ("r6", "r7")):
                orient[lo] = "MX"
                gaps[names.index(hi)] = pg
        gaps[-1] = spec.get("top_gap", 43.2)
        if spec.get("sram_gap") is not None:
            gaps[names.index("sram")] = spec["sram_gap"]
        if spec.get("hrow_street") is not None:          # both hrow streets set explicitly
            gaps[names.index("hrow")] = spec["hrow_street"]; gaps[names.index("hrow") + 1] = spec["hrow_street"]
        rest = [k for k, g in enumerate(gaps) if g is None]
        left = free - sum(g for g in gaps if g is not None)
        each = math.floor(left / len(rest) / L + 1e-9) * L
        for k in rest:
            gaps[k] = each
        if spec.get("remainder_to") == "top":           # keeps every core origin on the lattice
            gaps[-1] += round(left - each * len(rest), 4)
        else:
            gaps[0] += round(left - each * len(rest), 4)    # remainder to the bottom ring (keeps the top on the outline)
        self.gaps = gaps
        y = gaps[0]; newy = []
        for k, (a, b, n) in enumerate(sol):
            newy.append(round(y, 4)); y += (b - a) + gaps[k + 1]
        assert abs(y - self.H) < 1e-3, (y, self.H)
        self.newy = newy
        self.dy = [ny - a for ny, (a, b, n) in zip(newy, sol)]
        self.orient = orient
        self.names = names
        self.row_of = {}
        for i in self.attn:
            self.row_of[i] = names.index("r%d" % rows.index(hc[i]["origin_um"][1]))
        for i in self.hrow:
            self.row_of[i] = names.index("hrow")
        self.L = L
        # x: optional column re-pitch inside the growth (spec col_pitch): column k shifts by m0 + k*(P - P0), the
        # W ring keeps m0 = the remainder split evenly on the lattice, the E ring takes the rest
        self.cols = sorted(set(round(hc[i]["origin_um"][0], 4) for i in self.attn))
        self.cw = hc[self.attn[0]]["outline_um"][0]
        P0 = self.cols[1] - self.cols[0]
        P = float(spec.get("col_pitch") or P0)
        ex = P - P0; n = len(self.cols)
        m0 = math.floor((self.dxg - (n - 1) * ex) / 2 / L + 1e-9) * L if spec.get("col_pitch") else snap(self.dxg / 2, L / 2)
        assert m0 >= -1e-6, ("col_pitch needs more growth", self.dxg, ex)
        self.colshift = [round(m0 + k * ex, 4) for k in range(n)]
        self.boxes0 = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
                        h["origin_um"][1] + h["outline_um"][1]) for h in hc]

    def report(self):
        return dict(gaps=self.gaps, solids=[(n, a, b, round(ny, 4), self.orient[n]) for (a, b, n), ny in
                                             zip(self.sol, self.newy)])

    # -------- maps
    def fy_free(self, y):
        """y map of a point in no core (street / ring / face)."""
        sol = self.sol
        if y <= sol[0][0]:
            return y                                   # bottom ring stays on the outline
        if y >= sol[-1][1]:
            # top ring: rides the SRAM band if nearer to it than to the face, else stays
            # top ring: linear map [old band top, H0] -> [new band top, H], on the 0.27 um row grid (relays, capture
            # bands, ring pins between the SRAM band and the N face keep their order and stay clear of the band)
            a0, a1 = sol[-1][1], sol[-1][1] + self.dy[-1]
            v = a1 + (y - a0) * (self.H - a1) / (self.H0 - a0)
            return min(max(snap(v, 0.27), a1), self.H - FACE)
        for k, (a, b, n) in enumerate(sol):
            if a <= y <= b:
                return y + self.dy[k]
            if k + 1 < len(sol) and b < y < sol[k + 1][0]:
                s = (self.dy[k] + self.dy[k + 1]) / 2.0
                return y + snap(s, self.L / 2)
        raise AssertionError(y)

    def owner(self, p, halo=0.0):
        x, y = p
        best = None
        for i in self.attn + self.hrow:
            x0, y0, x1, y1 = self.boxes0[i]
            if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - halo <= y <= y1 + halo:
                d = 0 if y0 <= y <= y1 else min(abs(y - y0), abs(y - y1))
                if best is None or d < best[0]:
                    best = (d, i)
        return None if best is None else best[1]

    def fx(self, x):
        if x > self.W0 - FACE:
            return x + self.dxg
        if x < self.cx0:
            return x
        if x > self.cx1:
            return x + self.dxg
        for k, c in enumerate(self.cols):
            if c - 1e-6 <= x <= c + self.cw + 1e-6:
                return x + self.colshift[k]
            if k + 1 < len(self.cols) and c + self.cw < x < self.cols[k + 1]:
                return x + snap((self.colshift[k] + self.colshift[k + 1]) / 2, self.L / 2)
        return x + self.colshift[-1]

    def fx_core(self, x0, w):
        """a core / macro origin rides the column under its centre"""
        return x0 + (self.fx(x0 + w / 2) - (x0 + w / 2))

    def pt(self, p, halo=0.0):
        x, y = p
        if x < FACE or y < FACE or x > self.W0 - FACE or y > self.H0 - FACE:
            return [round(self.fx(x), 4), y + self.dyg if y > self.H0 - FACE else y]
        i = self.owner(p, halo)
        if i is not None:
            k = self.row_of[i]
            x0, y0, x1, y1 = self.boxes0[i]
            v = y - y0
            if self.orient[self.names[k]] == "MX":
                v = (y1 - y0) - v
            return [round(x + self.fx_core(x0, x1 - x0) - x0, 4), round(self.newy[k] + v, 4)]
        return [round(self.fx(x), 4), round(self.fy_free(y), 4)]

    def rect(self, r):
        a = self.pt(r[:2]); b = self.pt(r[2:4])
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]

    def walk(self, x, key=None):
        if isinstance(x, dict):
            for k, v in list(x.items()):
                if k in SKIP:
                    continue
                if k in PT_KEYS and isinstance(v, list) and len(v) == 2 and all(isnum(a) for a in v):
                    # a core reset driver sits next to its core's rst_n pin: it rides that core (HALO), mirrored with it
                    x[k] = self.pt(v, HALO if key == "core_resets" else 0.0)
                elif k in PTLIST_KEYS and isinstance(v, list) and all(isinstance(p, list) and len(p) == 2 for p in v):
                    x[k] = [self.pt(p) for p in v]
                elif k == "bit_sites_um" and isinstance(v, list):
                    x[k] = [[self.pt(p) for p in g] for g in v]
                elif k in RECT_KEYS and isinstance(v, list) and len(v) == 4:
                    x[k] = self.rect(v)
                elif k in RECTLIST_KEYS and isinstance(v, list):
                    x[k] = [self.rect(r) for r in v]
                else:
                    self.walk(v, k)
        elif isinstance(x, list):
            for v in x:
                self.walk(v, key)

    def apply(self):
        t = copy.deepcopy(self.t)
        for i, h in enumerate(t["hard_cores"]):
            k = self.row_of[i]
            h["origin_um"] = [round(self.fx_core(h["origin_um"][0], h["outline_um"][0]), 4), round(self.newy[k], 4)]
            o = self.orient[self.names[k]]
            if o != "R0" or "orient" in h:
                h["orient"] = o
        for c in t.get("contents") or []:
            if "origin_um" in c:
                c["origin_um"] = [round(self.fx_core(c["origin_um"][0], c["outline_um"][0]) if "outline_um" in c else self.fx(c["origin_um"][0]), 4),
                                  round(c["origin_um"][1] + self.dy[-1], 4)]
        if self.dxg or self.dyg:
            t["outline_um"] = [round(self.W, 4), round(self.H, 4)]
        self.walk(t)
        return t


def macro_boxes(t):
    b = [(h["inst"], h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0],
          h["origin_um"][1] + h["outline_um"][1]) for h in t["hard_cores"]]
    b += [(c["inst"], c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
           c["origin_um"][1] + c["outline_um"][1]) for c in t.get("contents") or [] if "origin_um" in c and "outline_um" in c]
    return b


def points(x, key=None, out=None, path=""):
    """(path, point) of every plan coordinate the form moves (same key set as Form.walk)."""
    if out is None:
        out = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k in SKIP:
                continue
            q = path + "/" + k
            if k in PT_KEYS and isinstance(v, list) and len(v) == 2 and all(isnum(a) for a in v):
                out.append((q, v))
            elif k in PTLIST_KEYS and isinstance(v, list) and all(isinstance(p, list) and len(p) == 2 for p in v):
                out += [(q, p) for p in v]
            elif k == "bit_sites_um" and isinstance(v, list):
                out += [(q, p) for g in v for p in g]
            elif k in RECT_KEYS and isinstance(v, list) and len(v) == 4:
                out.append((q + "#rect", v))
            elif k in RECTLIST_KEYS and isinstance(v, list):
                out += [(q + "#rect", r) for r in v]
            else:
                points(v, k, out, q)
    elif isinstance(x, list):
        for v in x:
            points(v, key, out, path)
    return out


def inside(p, boxes, tol=0.05):
    for b in boxes:
        if b[1] + tol < p[0] < b[3] - tol and b[2] + tol < p[1] < b[4] - tol:
            return b[0]
    return None


def rect_hits(r, boxes, tol=0.05):
    for b in boxes:
        if min(r[2], b[3]) - max(r[0], b[1]) > tol and min(r[3], b[4]) - max(r[1], b[2]) > tol:
            return b[0]
    return None


def check(t0, t1, log):
    bad = 0
    W, H = t1["outline_um"]
    B1 = macro_boxes(t1); B0 = macro_boxes(t0)
    for i, a in enumerate(B1):
        if a[1] < -1e-6 or a[2] < -1e-6 or a[3] > W + 1e-6 or a[4] > H + 1e-6:
            log("OUT_OF_OUTLINE %s" % (a,)); bad += 1
        for b in B1[i + 1:]:
            if min(a[3], b[3]) - max(a[1], b[1]) > 0.01 and min(a[4], b[4]) - max(a[2], b[2]) > 0.01:
                log("OVERLAP %s %s" % (a[0], b[0])); bad += 1
    P0 = points(t0); P1 = points(t1)
    assert len(P0) == len(P1)
    newly = 0; ex = []
    for (q, a), (_, b) in zip(P0, P1):
        if q.endswith("#rect"):
            h0, h1 = rect_hits(a, B0), rect_hits(b, B1)
        else:
            h0, h1 = inside(a, B0), inside(b, B1)
        if h0 is None and h1 is not None:
            newly += 1
            if len(ex) < 12:
                ex.append((q, a, b, h1))
    if newly:
        log("NEWLY_UNDER_MACRO %d e.g. %s" % (newly, ex)); bad += 1
    return bad, len(P0)


def strip_ft(t):
    """ft slots with their station coordinates blanked: the form may move station sites, nothing else of a slot."""
    t = dict(t)
    t["ft_slots"] = [{k: v for k, v in f.items() if k not in ("regs_um", "bit_sites_um")} for f in t.get("ft_slots") or []]
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("spec")
    ap.add_argument("--types", default=r"^svc_(hi|lo)_dsdv_svc_rs(_w)?__t\d+$")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--report")
    a = ap.parse_args()
    sys.path.insert(0, a.repo + "/tools/die_plan")
    import core_place as C
    P = json.load(open(a.plan_in)); spec = json.load(open(a.spec))
    rx = re.compile(a.types); rep = {"spec": spec, "plan_in_sha256": hashlib.sha256(open(a.plan_in, "rb").read()).hexdigest(),
                                     "types": {}}
    bad = 0
    for tn in sorted(P["partition_types"]):
        if not rx.search(tn):
            continue
        t0 = P["partition_types"][tn]
        F = Form(t0, spec)
        t1 = F.apply()
        msgs = []
        b, npts = check(t0, t1, msgs.append)
        eq = C.eq_gate(strip_ft(t0), strip_ft(t1))
        for f0, f1 in zip(t0.get("ft_slots") or [], t1.get("ft_slots") or []):
            if len(f0.get("regs_um") or []) != len(f1.get("regs_um") or []) or \
                    [len(g) for g in f0.get("bit_sites_um") or []] != [len(g) for g in f1.get("bit_sites_um") or []]:
                eq.append("ft_slots %s station count" % f0.get("name"))
        if eq:
            msgs.append("EQ_GATE %s" % eq); b += 1
        rep["types"][tn] = dict(F.report(), points=npts, problems=msgs)
        print(tn, "gaps", F.gaps, "colshift", F.colshift, "points", npts, "OK" if not b else "BAD %s" % msgs)
        bad += b
        P["partition_types"][tn] = t1
    json.dump(P, open(a.plan_out, "w"), indent=1)
    rep["plan_out_sha256"] = hashlib.sha256(open(a.plan_out, "rb").read()).hexdigest()
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print("wrote", a.plan_out, rep["plan_out_sha256"][:12], "bad", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
