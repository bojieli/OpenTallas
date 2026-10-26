#!/usr/bin/env python3
"""geom_rules.py -- AUTO-GEOM rule check of a placed / CTS checkpoint (OWNER 2026-10-25 ~20:25).

Owner decision: a part built from a template that already has a visual GEOM PASS may pass on automated rule checks,
with visual review sampled ~1 in 10; new templates, failures and die-level items stay visual.  This module judges the
geom_dump.tcl dump of the replica's 3_place / 4_cts ODB with the rules the visual reviewers already enforce.  Every
threshold below names its source; nothing here is a new gate.  A rule that cannot be evaluated is NA (never PASS by
default for a required rule: a required NA makes the verdict FAIL -> visual review).

    python3 geom_rules.py DUMP.tsv [--json OUT.json] [--template TEMPLATE_auto_geom.json] [--outline WxH]
                                   [--strap-re REGEX] [--title T]

Rules (id: limit -- source):
  outline   : W x H == parent slot (plan outline / template outline) within 0.01 um; aspect <= 2.0 unless the slot
              itself is the visually passed template outline -- METHODOLOGY 1.14 ("outline derived from the parent slot",
              "aspect <= ~2:1"); memory tile-outline-from-parent-slot-1023 (A0 820x907 vs 611x1307 slot)
  fill      : std-cell fill of the free (non-macro) area >= 20 % -- tools/ref_tile/layout_review.py FILL_FREE_FAIL (main
              pre-route gate, TILE-REVIEW 10-23); METHODOLOGY 1.14 (target 40-60 %); GEOM-REVIEW qkd_ahub 12 % FAIL
  empty     : share of macro-free density bins below 5 % density <= 50 % -- layout_review.py EMPTY_FLAG/EMPTY_BIN_DENSITY;
              GEOM-REVIEW qkd_ahub "W/N thirds empty" FAIL
  pin_reg   : every signal pin registered (flop within <= 4 buffers, or a hard-macro pin) and pin->register p90
              <= 30 um -- METHODOLOGY 1.9 (R2 face flops, "pin-to-reg p90 <= 30 um"); layout_review.py PIN_REG_P90_FAIL
              150 um is the hard backstop; clock ports and declared strap_* pins are exempt (METHODOLOGY 1.8 R7 note)
  r2r       : max register->register Manhattan distance (flop centre to flop centre through combinational logic and
              buffers, data and reset pins) <= 405 um -- METHODOLOGY 1.3 / 4.2 (reach 405 per cycle; reset relays every
              <= 405 um); GEOM-REVIEW 10-24 g3k5 FAIL "u_s0->u_t0.c0 905 um"; results/geom_review/s81_head_kits_1025
              hk_ana.py rr_gt405
  pin_density: peak pins in any 10-um face window <= 6 pins/um (covers partial-face pin clusters) -- METHODOLOGY 5.2;
              memory tile-review-pin-clustering-1017 (bf_cl_fp 9/um, pegress 10/um partial faces)
  pin_table : pins (name, face, layer, position +-0.05 um) == template pin table up to strap_* pins -- METHODOLOGY 1.5
              (one type = one view; replica shares the lattice) + owner 10-25 template rule ("same pin table up to
              straps")
  macros    : hard macros / hardened children at the template's positions (+-0.01 um, same masters) -- memory
              tile-review-pin-clustering-1017 (macros on the 43.2-um lattice), METHODOLOGY 5.6 (macros on the lattice)
  std_band  : with macros: the largest connected macro-free region holds >= 95 % of the std-cell area (one contiguous
              std-cell band, no cells in slivers between macros) -- memory tile-review-pin-clustering-1017 (NL c1 62k
              cells in slivers, DPL-0033).  The 95 % figure is this tool's reading of "one contiguous band"; it can only
              FAIL a replica towards visual review, never pass something the template did not.
  clock_taps: with >= 2 grid taps (clk|ck, clk_t<i>): no grid tap with 0 sinks and <= 1500 sinks per tap -- METHODOLOGY
              3.3 (~1000-1500 sinks/tap, no taps over empty area); GEOM-REVIEW 10-24 g3k5 FAIL "0..3007 sinks/tap",
              "4 empty N taps", KV hub_Ei vC FAIL "empty taps".  Sinks: actual tree (CTS checkpoint) or the nearest-tap
              split tools/die_plan/clock_taps.tcl applies before CTS (placed checkpoint).
  tap_set   : same tap ports (names, faces) as the template -- template rule (same pin table)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict, deque

INF = float("inf")
R2R_MAX = 405.0
PINREG_P90 = 30.0
PINREG_HARD = 150.0
PINREG_DEPTH = 4
FILL_MIN = 0.20
EMPTY_MAX = 0.50
EMPTY_BIN_DENSITY = 0.05
PIN_WIN_MAX = 6.0
TAP_SINKS_MAX = 1500
BAND_MIN = 0.95
ASPECT_MAX = 2.0
POS_TOL = 0.05
OUTLINE_TOL = 0.01
GRID_TAP_RE = re.compile(r"^(clk|ck)(_t\d+)?$")
CLOCK_PIN_RE = re.compile(r"(^|_)(clk|ck)(_[tc]\d+)?(\[\d+\])?$|^clk_|^tile_clk$")
STRAP_RE_DEFAULT = r"^strap_"


def load(path):
    die = None
    cells, pins, nets = {}, [], []
    with open(path) as fh:
        for ln in fh:
            f = ln.rstrip("\n").split("\t")
            t = f[0]
            if t == "C":
                cells[int(f[1])] = (f[2], f[3], float(f[4]), float(f[5]), float(f[6]), float(f[7]), f[8] if len(f) > 8 else "")
            elif t == "N":
                nets.append((f[1], f[2], f[3:]))
            elif t == "P":
                pins.append(dict(k=int(f[1]), name=f[2], io=f[3], sig=f[4], layer=f[5], x=float(f[6]), y=float(f[7])))
            elif t == "D":
                die = tuple(map(float, f[1:5]))
    return die, cells, pins, nets


def ctr(c):
    return (c[2] + c[4]) / 2, (c[3] + c[5]) / 2


def q(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def face_of(x, y, die, tol=2.0):
    X0, Y0, X1, Y1 = die
    if x < X0 + tol:
        return "W"
    if x > X1 - tol:
        return "E"
    if y < Y0 + tol:
        return "S"
    if y > Y1 - tol:
        return "N"
    return "area"


def ref(s):
    """'i12' -> ('i', 12, False); 'i12c' -> ('i', 12, True); 'p3' -> ('p', 3, False); '-' -> None"""
    if s == "-" or not s:
        return None
    if s[0] == "p":
        return ("p", int(s[1:]), False)
    clk = s.endswith("c")
    return ("i", int(s[1:-1] if clk else s[1:]), clk)


class Design:
    def __init__(self, path):
        self.die, self.cells, self.pins, raw = load(path)
        self.pin_by_k = {p["k"]: p for p in self.pins}
        self.nets = []            # (sig, drv ref, [sink refs])
        self.drives = defaultdict(list)    # cell id -> [net idx]
        self.pin_net = {}          # pin k -> net idx
        self.cell_in = defaultdict(list)   # cell id -> [(net idx, is_clock_pin)]
        for sig, d, ss in raw:
            n = len(self.nets)
            dr = ref(d)
            sk = [ref(s) for s in ss if ref(s)]
            self.nets.append((sig, dr, sk))
            if dr and dr[0] == "i":
                self.drives[dr[1]].append(n)
            elif dr:
                self.pin_net[dr[1]] = n
            for s in sk:
                if s[0] == "p":
                    self.pin_net[s[1]] = n
                else:
                    self.cell_in[s[1]].append((n, s[2]))

    def kind(self, cid):
        c = self.cells.get(cid)
        return c[0] if c else None


# ------------------------------------------------------------------------------------------------ metrics
def area_metrics(D, bins=80):
    X0, Y0, X1, Y1 = D.die
    W, H = X1 - X0, Y1 - Y0
    macros = [c for c in D.cells.values() if c[0] == "M"]
    std = [c for c in D.cells.values() if c[0] in "SBKL"]

    def clip(c):
        return max(0.0, min(c[4], X1) - max(c[2], X0)) * max(0.0, min(c[5], Y1) - max(c[3], Y0))
    marea = sum(clip(c) for c in macros)
    free = max(0.0, W * H - marea)
    sarea = sum((c[4] - c[2]) * (c[5] - c[3]) for c in std)
    bw = max(max(W, H) / bins, 2.0)
    nx, ny = max(1, int(math.ceil(W / bw))), max(1, int(math.ceil(H / bw)))
    grid = [0.0] * (nx * ny)
    for c in std:
        x, y = ctr(c)
        i = min(nx - 1, max(0, int((x - X0) / bw)))
        j = min(ny - 1, max(0, int((y - Y0) / bw)))
        grid[j * nx + i] += (c[4] - c[2]) * (c[5] - c[3])
    cov = [False] * (nx * ny)
    for m in macros:
        for j in range(max(0, int((m[3] - Y0) / bw)), min(ny, int(math.ceil((m[5] - Y0) / bw)))):
            cy = Y0 + (j + .5) * bw
            if not m[3] <= cy <= m[5]:
                continue
            for i in range(max(0, int((m[2] - X0) / bw)), min(nx, int(math.ceil((m[4] - X0) / bw)))):
                if m[2] <= X0 + (i + .5) * bw <= m[4]:
                    cov[j * nx + i] = True
    freeb = emptyb = 0
    usable = [False] * (nx * ny)
    for j in range(ny):
        for i in range(nx):
            k = j * nx + i
            a = (min(X1, X0 + (i + 1) * bw) - (X0 + i * bw)) * (min(Y1, Y0 + (j + 1) * bw) - (Y0 + j * bw))
            if cov[k] or a < 0.25 * bw * bw:
                continue
            usable[k] = True
            freeb += 1
            if grid[k] / a < EMPTY_BIN_DENSITY:
                emptyb += 1
    # largest 4-connected macro-free component and its share of the std-cell area
    comp = [-1] * (nx * ny)
    best = 0.0
    tot = sum(grid[k] for k in range(nx * ny) if usable[k]) or 0.0
    for s in range(nx * ny):
        if not usable[s] or comp[s] >= 0:
            continue
        comp[s] = s
        dq, acc = deque([s]), 0.0
        while dq:
            k = dq.popleft()
            acc += grid[k]
            i, j = k % nx, k // nx
            for ii, jj in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= ii < nx and 0 <= jj < ny:
                    kk = jj * nx + ii
                    if usable[kk] and comp[kk] < 0:
                        comp[kk] = s
                        dq.append(kk)
        best = max(best, acc)
    return dict(outline=[round(W, 4), round(H, 4)], aspect=round(max(W, H) / max(1e-9, min(W, H)), 3),
                macros=len(macros), macro_area_pct=round(100 * marea / max(1e-9, W * H), 2),
                std_cells=len(std), ff=sum(1 for c in std if c[0] == "S"),
                fill_of_free=round(sarea / free, 4) if free > 1 and std else None,
                empty_area=round(emptyb / freeb, 4) if freeb and std else None,
                band_share=round(best / tot, 4) if tot > 0 else None, density_bin_um=round(bw, 3),
                macro_list=sorted([c[1], round(c[2] - X0, 3), round(c[3] - Y0, 3)] for c in macros))


def pin_metrics(D, strap_re):
    X0, Y0, X1, Y1 = D.die
    W, H = X1 - X0, Y1 - Y0
    faces, pos, table = Counter(), defaultdict(list), []
    for p in D.pins:
        if p["sig"] in ("POWER", "GROUND"):
            continue
        f = face_of(p["x"], p["y"], D.die)
        p["face"] = f
        faces[f] += 1
        pos[f].append(p["x"] if f in "NS" else p["y"])
        if not strap_re.search(p["name"]):
            table.append([p["name"], f, p["layer"], round(p["x"] - X0, 3), round(p["y"] - Y0, 3)])
    peak = {}
    for f, v in pos.items():
        if f == "area":
            continue
        v.sort()
        j = best = 0
        for i in range(len(v)):
            while v[i] - v[j] > 10.0:
                j += 1
            best = max(best, i - j + 1)
        peak[f] = round(best / 10.0, 2)
    flen = {"N": W, "S": W, "E": H, "W": H}
    span = {f: round((max(v) - min(v)) / flen[f], 3) for f, v in pos.items() if f != "area" and v and flen[f] > 0}
    return dict(pins_per_face=dict(faces), pin_peak_per_um_10um=peak, face_span=span, pin_table=sorted(table))


def pin_reg_metrics(D, strap_re, clock_pins=frozenset()):
    """pin -> nearest register through <= PINREG_DEPTH buffers (layout_review.tcl semantics, directional)"""
    dist, unreg, macro, exempt = [], [], 0, 0
    worst = []
    for p in D.pins:
        if p["sig"] in ("POWER", "GROUND"):
            continue
        if (p["sig"] == "CLOCK" or p["name"] in clock_pins or CLOCK_PIN_RE.search(p["name"])
                or strap_re.search(p["name"])):
            exempt += 1
            continue
        n = D.pin_net.get(p["k"])
        if n is None:
            unreg.append(p["name"] + "(no net)")
            continue
        best, hit_m = INF, False
        if p["io"] == "OUTPUT":
            cur, depth = n, 0
            while depth <= PINREG_DEPTH:
                dr = D.nets[cur][1]
                if not dr or dr[0] != "i":
                    break
                k = D.kind(dr[1])
                if k == "S":
                    x, y = ctr(D.cells[dr[1]])
                    best = abs(x - p["x"]) + abs(y - p["y"])
                    break
                if k == "M":
                    hit_m = True
                    break
                if k != "B" or not D.cell_in.get(dr[1]):
                    break
                cur = D.cell_in[dr[1]][0][0]
                depth += 1
        else:
            front, seen, depth = [n], {n}, 0
            while front and depth <= PINREG_DEPTH and best == INF and not hit_m:
                nf = []
                for nn in front:
                    for s in D.nets[nn][2]:
                        if s[0] != "i" or s[2]:
                            continue
                        k = D.kind(s[1])
                        if k == "S":
                            x, y = ctr(D.cells[s[1]])
                            best = min(best, abs(x - p["x"]) + abs(y - p["y"]))
                        elif k == "M":
                            hit_m = True
                        elif k == "B":
                            for on in D.drives.get(s[1], []):
                                if on not in seen:
                                    seen.add(on)
                                    nf.append(on)
                front = nf
                depth += 1
        if best < INF:
            dist.append(best)
            worst.append((best, p["name"]))
        elif hit_m:
            macro += 1
        else:
            unreg.append(p["name"])
    worst.sort(reverse=True)
    return dict(pins_registered=len(dist), pins_to_macro=macro, pins_exempt=exempt, pins_unregistered=len(unreg),
                unregistered_sample=unreg[:8], pin_reg_p50=None if not dist else round(q(dist, .5), 2),
                pin_reg_p90=None if not dist else round(q(dist, .9), 2),
                pin_reg_max=None if not dist else round(max(dist), 2), pin_reg_worst=[f"{d:.1f} {n}" for d, n in worst[:5]])


def r2r_metrics(D):
    """max Manhattan launch-flop -> capture-flop distance over every combinational path (data + reset pins, clock pins
    excluded), exact: per node keep min/max of u = x + y and v = x - y over the launching flops (Manhattan distance =
    max(|du|, |dv|)), propagated in topological order through the combinational cells."""
    comb = {cid for cid, c in D.cells.items() if c[0] in "BLK"}
    # per comb cell: [umin, umax, vmin, vmax, src_umin, src_umax, src_vmin, src_vmax]
    st = {}
    indeg = Counter()
    succ = defaultdict(list)          # comb cell -> comb cells it feeds (data pins)
    for cid in comb:
        for n in D.drives.get(cid, []):
            for s in D.nets[n][2]:
                if s[0] == "i" and not s[2] and s[1] in comb:
                    succ[cid].append(s[1])
                    indeg[s[1]] += 1

    def merge(dst, u0, u1, v0, v1, a, b, c_, d_):
        e = st.get(dst)
        if e is None:
            st[dst] = [u0, u1, v0, v1, a, b, c_, d_]
            return
        if u0 < e[0]:
            e[0], e[4] = u0, a
        if u1 > e[1]:
            e[1], e[5] = u1, b
        if v0 < e[2]:
            e[2], e[6] = v0, c_
        if v1 > e[3]:
            e[3], e[7] = v1, d_
    caps = defaultdict(list)          # capture flop -> [(umin, umax, vmin, vmax, srcs...)]
    for cid, c in D.cells.items():
        if c[0] != "S":
            continue
        x, y = ctr(c)
        u, v = x + y, x - y
        for n in D.drives.get(cid, []):
            for s in D.nets[n][2]:
                if s[0] != "i" or s[2]:
                    continue
                k = D.kind(s[1])
                if k == "S":
                    caps[s[1]].append((u, u, v, v, cid, cid, cid, cid))
                elif s[1] in comb:
                    merge(s[1], u, u, v, v, cid, cid, cid, cid)
    dq = deque(cid for cid in comb if indeg[cid] == 0)
    done = 0
    while dq:
        cid = dq.popleft()
        done += 1
        e = st.get(cid)
        for n in D.drives.get(cid, []):
            for s in D.nets[n][2]:
                if s[0] != "i" or s[2]:
                    continue
                if e is not None:
                    if D.kind(s[1]) == "S":
                        caps[s[1]].append(tuple(e))
                    elif s[1] in comb:
                        merge(s[1], *e)
        for t in succ.get(cid, []):
            indeg[t] -= 1
            if indeg[t] == 0:
                dq.append(t)
    loops = len(comb) - done
    best, arg, n_gt = 0.0, None, 0
    for cap, lst in caps.items():
        x, y = ctr(D.cells[cap])
        u, v = x + y, x - y
        mx, src = 0.0, None
        for e in lst:
            for val, s in ((u - e[0], e[4]), (e[1] - u, e[5]), (v - e[2], e[6]), (e[3] - v, e[7])):
                if val > mx:
                    mx, src = val, s
        if mx > R2R_MAX:
            n_gt += 1
        if mx > best:
            best, arg = mx, (src, cap)
    name = lambda i: D.cells[i][6] if i in D.cells else str(i)
    return dict(r2r_max=round(best, 2), r2r_captures_gt405=n_gt, r2r_captures=len(caps), comb_loop_cells=loops,
                r2r_worst=None if not arg else f"{name(arg[0])} -> {name(arg[1])}")


def clock_metrics(D):
    """clock sinks (seq / macro clock pins) traced up through buffers / clock cells to the input port that roots them.
    Taps = input ports that root clock sinks (or carry sig CLOCK / a clk name); grid taps = clk|ck, clk_t<i>.  Sinks
    per tap: actual tree (CTS checkpoint) or, when every sink still hangs on one root while >= 2 grid taps exist (placed
    checkpoint, before tools/die_plan/clock_taps.tcl), the nearest-tap split that hook applies.  Tree shape (INFO, and
    compared with the template): clock cells, levels root -> sink (max, spread), sinks per leaf driver, clock-net HPWL."""
    sinks = []
    for cid, c in D.cells.items():
        if c[0] not in "SM":
            continue
        for n, is_clk in D.cell_in.get(cid, []):
            if is_clk:
                sinks.append((cid, n))
    memo = {}                                          # net -> (root pin k | None, depth in cells)
    clk_nets, clk_cells = set(), set()

    def trace(n):
        path, cur, r, base = [], n, None, 0
        while len(path) < 64:
            if cur in memo:
                r, base = memo[cur][0], memo[cur][1] + 1
                break
            path.append(cur)
            dr = D.nets[cur][1]
            if dr is None:
                break
            if dr[0] == "p":
                r = dr[1]
                break
            k = D.kind(dr[1])
            ins = D.cell_in.get(dr[1], [])
            if k not in ("B", "K") or not ins:
                break
            clk_cells.add(dr[1])
            ck = [x for x, c in ins if c]
            cur = ck[0] if ck else ins[0][0]
        for i, pnet in enumerate(reversed(path)):
            memo[pnet] = (r, base + i)
            clk_nets.add(pnet)
        return memo[n]
    roots, depth_of = {}, {}
    for cid, n in sinks:
        r, d = trace(n)
        roots[cid] = r
        depth_of[cid] = d
    rooted = {r for r in roots.values() if r is not None}
    taps = {p["k"]: p for p in D.pins if p["io"] == "INPUT" and (p["k"] in rooted or p["sig"] == "CLOCK" or
                                                                 GRID_TAP_RE.match(p["name"]))}
    grid = {k for k, p in taps.items() if GRID_TAP_RE.match(p["name"])}
    cnt = Counter(r for r in roots.values() if r is not None)
    mode = "tree"
    if len(grid) >= 2 and len({r for r in cnt if r in grid}) <= 1 and sum(cnt.values()) > 0:
        mode = "nearest"
        new = Counter({k: 0 for k in grid})
        for cid, r in roots.items():
            if r is None:
                continue
            if r not in grid:
                new[r] += 1
                continue
            x, y = ctr(D.cells[cid])
            new[min(grid, key=lambda k: abs(taps[k]["x"] - x) + abs(taps[k]["y"] - y))] += 1
        cnt = new
    gvals = [cnt.get(k, 0) for k in grid]
    # tree shape
    leaf = Counter()
    for cid, n in sinks:
        dr = D.nets[n][1]
        if dr and dr[0] == "i":
            leaf[dr[1]] += 1
    hp = []
    for n in clk_nets:
        pts = []
        sig, dr, sk = D.nets[n]
        for e in ([dr] if dr else []) + sk:
            if e[0] == "p":
                p = D.pin_by_k.get(e[1])
                if p:
                    pts.append((p["x"], p["y"]))
            elif e[1] in D.cells:
                pts.append(ctr(D.cells[e[1]]))
        if len(pts) >= 2:
            xs, ys = [a for a, _ in pts], [b for _, b in pts]
            hp.append(max(xs) - min(xs) + max(ys) - min(ys))
    depths = [depth_of[c] for c, _ in sinks if roots.get(c) is not None]
    lv = list(leaf.values())
    return dict(taps=len(taps), grid_taps=len(grid), tap_mode=mode, clock_sinks=len(sinks),
                unrooted_sinks=sum(1 for r in roots.values() if r is None),
                grid_tap_sinks_min=min(gvals) if gvals else None, grid_tap_sinks_max=max(gvals) if gvals else None,
                grid_taps_empty=sorted(taps[k]["name"] for k in grid if cnt.get(k, 0) == 0),
                tap_sinks={taps[k]["name"]: cnt.get(k, 0) for k in taps},
                tap_set=sorted([taps[k]["name"], face_of(taps[k]["x"], taps[k]["y"], D.die)] for k in taps),
                clock_cells=len(clk_cells), clock_depth_max=max(depths) if depths else None,
                clock_depth_spread=(max(depths) - min(depths)) if depths else None,
                leaf_sinks_p90=None if not lv else round(q(lv, .9), 1), leaf_sinks_max=max(lv) if lv else None,
                clock_net_hpwl_max=round(max(hp), 2) if hp else None,
                clock_net_hpwl_p90=round(q(hp, .9), 2) if hp else None,
                stage="cts" if clk_cells else "placed")


# ------------------------------------------------------------------------------------------------ rules
TOL_REL = 0.02            # replica vs template: numerical noise of a re-place of identical inputs (not a design margin)
TOL_CLOCK = 0.10          # clock-tree shape vs the template's tree (CTS is less repeatable than placement)


def judge(m, template=None, outline=None):
    """[rule dicts], verdict.  Absolute limit first; with a template (the visually passed part), a value outside the
    absolute limit still passes ONLY when the template carried the same violation through its visual PASS and the
    replica is not worse than the template (TOL_REL) -- the layout_review.py principle that a GEOM-REVIEW PASS for the
    reviewed content excuses low fill / far pin registers, narrowed to 'no worse than what the reviewer saw'."""
    R = []
    t = template["metrics"] if template else None

    def add(rule, status, value, limit, src, detail=""):
        R.append(dict(rule=rule, status=status, value=value, limit=limit, source=src, detail=detail))

    def lim(rule, key, limit, src, higher_bad=True, detail="", absent_ok=False):
        v = m.get(key)
        if v is None:
            add(rule, "INFO" if absent_ok else "NA", v, limit, src, detail or "not measurable")
            return
        ok = v <= limit if higher_bad else v >= limit
        if ok:
            add(rule, "PASS", v, f"{'<=' if higher_bad else '>='}{limit}", src, detail)
            return
        tv = t.get(key) if t else None
        if tv is not None and not (tv <= limit if higher_bad else tv >= limit):
            worse = v > tv * (1 + TOL_REL) + 1e-6 if higher_bad else v < tv * (1 - TOL_REL) - 1e-6
            if not worse:
                add(rule, "PASS", v, f"template {tv} (visually passed with it)", src, "template-accepted; " + detail)
                return
            detail = f"worse than template {tv}; " + detail
        add(rule, "FAIL", v, f"{'<=' if higher_bad else '>='}{limit}", src, detail)
    if m.get("stage") not in ("placed", "cts"):
        add("checkpoint", "NA", m.get("stage"), "3_place or 4_cts", "AUTO-GEOM scope (pre-route review points only)")
    W, H = m["outline"]
    slot = outline or (t["outline"] if t else None)
    if slot:
        ok = abs(W - slot[0]) <= OUTLINE_TOL and abs(H - slot[1]) <= OUTLINE_TOL
        add("outline", "PASS" if ok else "FAIL", f"{W}x{H}", f"=={slot[0]}x{slot[1]}",
            "METHODOLOGY 1.14; tile-outline-from-parent-slot-1023")
    else:
        add("outline", "NA", f"{W}x{H}", "slot", "METHODOLOGY 1.14", "no parent slot / template outline given")
    lim("aspect", "aspect", ASPECT_MAX, "METHODOLOGY 1.14 aspect <= ~2:1")
    lim("fill", "fill_of_free", FILL_MIN, "layout_review.py FILL_FREE_FAIL; METHODOLOGY 1.14", higher_bad=False)
    lim("empty", "empty_area", EMPTY_MAX, "layout_review.py EMPTY_FLAG (bins < 5 %)")
    lim("pin_reg_p90", "pin_reg_p90", PINREG_P90, "METHODOLOGY 1.9 (R2 p90 <= 30)", detail=", ".join(m["pin_reg_worst"][:2]))
    lim("pin_reg_max", "pin_reg_max", PINREG_HARD, "layout_review.py PIN_REG_P90_FAIL 150 (backstop)")
    lim("pin_unreg", "pins_unregistered", 0, "METHODOLOGY 1.9 register every partition pin",
        detail=", ".join(m["unregistered_sample"][:4]))
    if m["r2r_captures"]:
        lim("r2r", "r2r_max", R2R_MAX, "METHODOLOGY 1.3/4.2 reach 405",
            detail=f"{m['r2r_captures_gt405']} captures > 405; worst {m['r2r_worst']}")
        lim("r2r_count", "r2r_captures_gt405", 0, "METHODOLOGY 1.3 (count of captures > 405 um)")
    else:
        add("r2r", "NA", None, f"<={R2R_MAX}", "METHODOLOGY 1.3", "no register-to-register path found")
    pk = m["pin_peak_per_um_10um"]
    m["_pin_peak"] = max(pk.values()) if pk else 0.0
    if t is not None and "_pin_peak" not in t:
        tp = t.get("pin_peak_per_um_10um") or {}
        t["_pin_peak"] = max(tp.values()) if tp else 0.0
    lim("pin_density", "_pin_peak", PIN_WIN_MAX, "METHODOLOGY 5.2; tile-review-pin-clustering-1017", detail=str(pk))
    if m["macros"]:
        lim("std_band", "band_share", BAND_MIN, "tile-review-pin-clustering-1017 (one contiguous std-cell band)",
            higher_bad=False)
    if m["grid_taps"] >= 2:
        m["_empty_taps"] = len(m["grid_taps_empty"])
        if t is not None:
            t["_empty_taps"] = len(t.get("grid_taps_empty") or [])
        lim("clock_tap_empty", "_empty_taps", 0, "METHODOLOGY 3.3 (no empty taps); GEOM-REVIEW g3k5 / hub_Ei vC",
            detail=",".join(m["grid_taps_empty"][:6]))
        lim("clock_tap_sinks", "grid_tap_sinks_max", TAP_SINKS_MAX, "METHODOLOGY 3.3 (~1000-1500 sinks/tap); g3k5 3007",
            detail=f"{m['grid_taps']} taps {m['grid_tap_sinks_min']}..{m['grid_tap_sinks_max']} ({m['tap_mode']})")
    else:
        add("clock_taps", "INFO", f"{m['grid_taps']} grid taps, {m['clock_sinks']} sinks", "n/a (< 2 grid taps)",
            "METHODOLOGY 3.3")
    if m["unrooted_sinks"]:
        lim("clock_unrooted", "unrooted_sinks", 0, "METHODOLOGY 6.3 (no unclocked registers)")
    if t is not None:
        add("pin_table", "PASS" if _close_table(m["pin_table"], t["pin_table"]) else "FAIL", len(m["pin_table"]),
            f"== template ({len(t['pin_table'])})", "owner 10-25 template rule; METHODOLOGY 1.5",
            _table_diff(m["pin_table"], t["pin_table"]))
        add("macros", "PASS" if _close_macros(m["macro_list"], t["macro_list"]) else "FAIL", m["macros"],
            f"== template ({t['macros']})", "tile-review-pin-clustering-1017; METHODOLOGY 5.6")
        add("tap_set", "PASS" if m["tap_set"] == t["tap_set"] else "FAIL", m["taps"], f"== template ({t['taps']})",
            "owner 10-25 template rule")
        add("stage", "PASS" if m.get("stage") == t.get("stage") else "FAIL", m.get("stage"), f"== template ({t.get('stage')})",
            "a CTS checkpoint is compared with a reviewed CTS checkpoint (GEOM-REVIEW post-CTS reviews)")
        if m.get("stage") == "cts" and t.get("stage") == "cts":
            for key in ("clock_depth_max", "clock_depth_spread", "leaf_sinks_max", "leaf_sinks_p90", "clock_net_hpwl_max",
                        "clock_net_hpwl_p90", "clock_cells"):
                v, tv = m.get(key), t.get(key)
                if v is None or tv is None:
                    add("clk_" + key, "NA", v, f"template {tv}", "GEOM-REVIEW post-CTS reviews (tree shape)")
                    continue
                ok = v <= tv * (1 + TOL_CLOCK) + 1 if key != "clock_cells" else abs(v - tv) <= tv * TOL_CLOCK + 1
                add("clk_" + key, "PASS" if ok else "FAIL", v, f"template {tv} +{int(TOL_CLOCK * 100)}%",
                    "GEOM-REVIEW E5-CTS01 / ASTK3 FAIL (tap loads, trunk legs, branch length)")
    else:
        for r in ("pin_table", "macros", "tap_set", "stage"):
            add(r, "NA", "", "template", "owner 10-25 template rule", "no template metrics")
    req_fail = [r for r in R if r["status"] in ("FAIL", "NA")]
    return R, ("FAIL" if req_fail else "PASS")


def _close_table(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x[:3] != y[:3] or abs(x[3] - y[3]) > POS_TOL or abs(x[4] - y[4]) > POS_TOL:
            return False
    return True


def _table_diff(a, b):
    na, nb = {x[0]: x for x in a}, {x[0]: x for x in b}
    only_a, only_b = sorted(set(na) - set(nb)), sorted(set(nb) - set(na))
    moved = [n for n in set(na) & set(nb) if na[n][1:3] != nb[n][1:3] or abs(na[n][3] - nb[n][3]) > POS_TOL
             or abs(na[n][4] - nb[n][4]) > POS_TOL]
    if not (only_a or only_b or moved):
        return ""
    return f"extra {only_a[:3]} missing {only_b[:3]} moved {sorted(moved)[:3]} ({len(only_a)}/{len(only_b)}/{len(moved)})"


def _close_macros(a, b):
    if len(a) != len(b):
        return False
    return all(x[0] == y[0] and abs(x[1] - y[1]) <= OUTLINE_TOL and abs(x[2] - y[2]) <= OUTLINE_TOL for x, y in zip(a, b))


def stage_of_odb(name):
    """checkpoint stage from the ORFS file name: AUTO-GEOM judges only the pre-route review points (3_place / 4_cts);
    GRT / routed checkpoints carry timing verdicts (GEOM-REVIEW 13:52 elemB_if2e 5_1_grt FAIL on clock timing)"""
    b = (name or "").rsplit("/", 1)[-1]
    return "placed" if b.startswith("3_place") else "cts" if b.startswith("4_cts") else "other" if b else ""


def metrics(path, strap_re=STRAP_RE_DEFAULT, odb=""):
    D = Design(path)
    sr = re.compile(strap_re)
    m = area_metrics(D)
    m.update(pin_metrics(D, sr))
    ck = clock_metrics(D)
    m.update(pin_reg_metrics(D, sr, frozenset(ck["tap_sinks"])))
    m.update(r2r_metrics(D))
    m.update(ck)
    st = stage_of_odb(odb)
    if st:
        m["stage"] = st
    return m


def verdict_line(verdict, rules, title=""):
    short = {"PASS": "ok", "FAIL": "FAIL", "NA": "NA", "INFO": "info"}
    parts = [f"{r['rule']}={short[r['status']]}({r['value'] if not isinstance(r['value'], dict) else max(r['value'].values() or [0])})"
             for r in rules if r["status"] != "INFO"]
    return f"AUTO-GEOM {verdict}" + (f" {title}" if title else "") + " " + " ".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dump")
    ap.add_argument("--json")
    ap.add_argument("--template", help="the template checkpoint's auto_geom.json (metrics of the visually passed part)")
    ap.add_argument("--outline", help="parent slot WxH (um)")
    ap.add_argument("--strap-re", default=STRAP_RE_DEFAULT)
    ap.add_argument("--title", default="")
    ap.add_argument("--odb", default="", help="checkpoint file name (stage: 3_place / 4_cts)")
    a = ap.parse_args(argv)
    m = metrics(a.dump, a.strap_re, a.odb)
    tmpl = json.load(open(a.template)) if a.template else None
    outline = [float(x) for x in a.outline.lower().split("x")] if a.outline else None
    rules, verdict = judge(m, tmpl, outline)
    line = verdict_line(verdict, rules, a.title)
    out = dict(schema="opentallas.auto_geom.v1", dump=a.dump, verdict=verdict, line=line, rules=rules, metrics=m)
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)
    print("AP_AUTO_GEOM " + line)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
