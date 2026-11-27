#!/usr/bin/env python3
"""rst_spread_placed.py -- post-place RESET-SPREAD check (CLASS-OWNERS-R2, class C-RST-RELAY-REACH, lane C-RST-PLACED). REPORT ONLY.

Reads the geom.tsv that the automated visual review already dumps from 3_place.odb (tools/autopilot/geom_dump.tcl), so it costs no
extra ODB pass.  Plan-seat checks (ADV-RSTSPREAD) cannot see a reset net whose spread exists only in the BOUND netlist (local_r
registers, u_xrl synchronisers, XG ring resets); this one measures the placed net.

Per reset net: driver xy, fanout, sink-bbox HPWL (um), farthest sink from the driver (L1, um), number of 405-um sink regions
(greedy k-cover of the sinks by 405-um boxes), sinks inside macro bodies.  A net is FLAGGED when fanout > FANOUT (3000), farthest
sink > FAR_UM (405), or HPWL > HPWL_UM (900); the thresholds are the ADV-RSTSPREAD ones (sister lane C-RST-RELAY-REACH-R3).

Reset nets: new dumps carry `RN net drv sink:pin ...` rows (nets named rst_n*/arst*/local_r*/xrl*/reset* or touching an async
RESETN/SETN pin).  Older dumps have no net names: a net is taken as a reset net when it has >= LEGACY_MIN sinks and >= 80% of them
are DFFASR* flops, or when its driver instance is named like a reset relay (u_xrl, local_r, rst).  Both are labelled in `src`.

Relay proposal per flagged net: one ot_rst_relay flop per sink region, seated at the nearest legal FREE site to the region
centroid (row grid from the core origin, never inside a macro body, never on an occupied span), and the list of sinks to re-home.
Every sink of the net moves behind a relay, so all sinks keep one equal relay depth (release only: rst_n is held >= 64 clocks).
Format (apply to the bound netlist): proposal["nets"][i]["relays"][j] = {name, x, y, row, region, sinks:[inst names]} and
["rehome"] = [{sink, pin, from_net, to_relay}].

    python3 -I rst_spread_placed.py GEOM.tsv [--json OUT] [--proposal OUT] [--all] [--min-fanout N]
"""
import bisect
import json
import math
import os
import re
import sys

CHECK = "RST-SPREAD-PLACED"
REACH_UM = 405.0
FAR_UM = float(os.environ.get("OT_RSTSPREAD_FAR_UM", "405"))
HPWL_UM = float(os.environ.get("OT_RSTSPREAD_HPWL_UM", "900"))
FANOUT = int(os.environ.get("OT_RSTSPREAD_FANOUT", "3000"))
LEGACY_MIN = 8
SITE_W = 0.054
ROW_H = 0.27
RELAY_W = 1.62                       # ot_rst_relay flop + site margin (um)
NAME_RE = re.compile(r"(^|[/._$\\])(rst|arst|local_r|u_xrl|xrl|reset)", re.I)
DRV_RE = re.compile(r"(u_xrl|local_r|rst_n|arst|rst_q|u_rstr|u_rr\b)", re.I)


def parse_geom(path):
    """-> dict(die, core, cells{id:(kind,master,x0,y0,x1,y1,name)}, pins{k:(name,x,y)}, nets[(drv,sinks)], rn[(net,drv,[(sink,pin)])],
    mr[(id,x,y,pin)])"""
    g = dict(die=None, core=None, cells={}, pins={}, nets=[], rn=[], mr=[])
    with open(path, errors="replace") as f:
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            t = p[0]
            try:
                if t == "C":
                    g["cells"][int(p[1])] = (p[2], p[3], float(p[4]), float(p[5]), float(p[6]), float(p[7]), p[8] if len(p) > 8 else "")
                elif t == "N":
                    g["nets"].append((p[2], p[3:]))
                elif t == "RN":
                    sk = []
                    for s in p[3:]:
                        a, _, b = s.partition(":")
                        sk.append((a, b))
                    g["rn"].append((p[1], p[2], sk))
                elif t == "P":
                    g["pins"][int(p[1])] = (p[2], float(p[6]), float(p[7]))
                elif t == "MR":
                    g["mr"].append((int(p[1]), float(p[2]), float(p[3]), p[4] if len(p) > 4 else ""))
                elif t == "D":
                    g["die"] = tuple(float(v) for v in p[1:5])
                elif t == "R":
                    g["core"] = tuple(float(v) for v in p[1:5])
            except (ValueError, IndexError):
                continue
    return g


def _ref(g, tok):
    """i<id> / i<id>c / p<k> -> (x, y, cell id or None)"""
    if tok.startswith("p"):
        pn = g["pins"].get(int(tok[1:]))
        return (pn[1], pn[2], None) if pn else None
    s = tok[1:].rstrip("c")
    c = g["cells"].get(int(s)) if s.isdigit() else None
    if not c:
        return None
    return ((c[2] + c[4]) / 2.0, (c[3] + c[5]) / 2.0, int(s))


BUF_RE = re.compile(r"^(BUF|INV|HB|CKINV|CKBUF|CLKBUF)")


def reset_nets(g, legacy_min=LEGACY_MIN):
    """reset TREES: -> [(root name, root driver token, leaf sink tokens, leaf pins, src)].
    A leaf net is an RN net with an async RESETN/SETN (or macro) sink, or (older dumps, no net names) a net with >= legacy_min sinks of
    which >= 80% are DFFASR* flops.  Leaf nets are climbed through buffers / inverters to the first non-buffer driver (the relay flop,
    u_xrl synchroniser, logic gate or top pin): that is the root, and its leaves are every leaf sink below it (a net that repair_design
    split into a buffer tree is ONE reset net: the spread of its leaves is what the recovery path sees)."""
    cells = g["cells"]
    nets = []                                    # (drv, [sink tokens], [pins], src, name)
    pins_by = {}
    if g["rn"]:
        rnd = {}
        for name, drv, sk in g["rn"]:
            rnd[(drv, tuple(s.rstrip("c") for s, _ in sk))] = name
        for drv, sk in g["nets"]:
            nm = rnd.get((drv, tuple(x.rstrip("c") for x in sk)))
            nets.append((drv, sk, [""] * len(sk), "RN" if nm else "", nm or ""))
        for name, drv, sk in g["rn"]:             # token -> async pin name when the sink has one, else its first pin
            d = {}
            for t, p in sk:
                if p in ("RESETN", "SETN") or t not in d:
                    d[t] = p
            pins_by[name] = d
    else:
        for drv, sk in g["nets"]:
            nets.append((drv, sk, [""] * len(sk), "", ""))
    out_net = {}                                 # driver instance id -> net index
    in_net = {}                                  # buffer instance id -> the net index it is a sink of
    for i, (drv, sk, _, _, _) in enumerate(nets):
        if drv[:1] == "i" and drv[1:].isdigit():
            out_net.setdefault(int(drv[1:]), i)
        for s in sk:
            if s[0] == "i" and s[1:].isdigit():
                c = cells.get(int(s[1:]))
                if c and BUF_RE.match(c[1]):
                    in_net[int(s[1:])] = i

    def leafs(i):
        drv, sk, _, src, nm = nets[i]
        if src == "RN":
            pn = pins_by.get(nm, {})
            ls = []
            for s in sk:
                p = pn.get(s, pn.get(s.rstrip("c"), ""))
                c = cells.get(int(s[1:].rstrip("c"))) if s[0] == "i" and s[1:].rstrip("c").isdigit() else None
                if p in ("RESETN", "SETN") or (c and c[0] == "M" and NAME_RE.search(p or "")):
                    ls.append((s, p))
            return ls
        cs = [(s, cells.get(int(s[1:]))) for s in sk if s[0] == "i" and s[1:].isdigit()]
        asr = [s for s, c in cs if c and c[1].startswith("DFFASR")]
        return [(s, "") for s in asr] if (len(sk) >= legacy_min and len(asr) >= 0.8 * len(sk)) else []

    seeds = {i: leafs(i) for i in range(len(nets))}
    seeds = {i: l for i, l in seeds.items() if l}
    groups = {}                                  # root net idx -> {seed idx}
    for i in seeds:
        r, guard = i, 0
        drv = nets[r][0]
        while drv[:1] == "i" and drv[1:].isdigit() and guard < 64:
            c = cells.get(int(drv[1:]))
            nx = in_net.get(int(drv[1:])) if c and BUF_RE.match(c[1]) else None
            if nx is None:
                break
            r, drv, guard = nx, nets[nx][0], guard + 1
        groups.setdefault(r, set()).add(i)
    out = []
    for r, ss in groups.items():
        lv, seen = [], set()
        for i in ss:
            for s, p in seeds[i]:
                if s not in seen:
                    seen.add(s)
                    lv.append((s, p))
        drv = nets[r][0]
        d = cells.get(int(drv[1:])) if drv[:1] == "i" and drv[1:].isdigit() else None
        nm = nets[r][4] or ("drv:" + (d[6] if d else drv))
        out.append((nm, drv, [s for s, _ in lv], [p for _, p in lv], "RN" if any(nets[i][3] == "RN" for i in ss) else "LEGACY"))
    return out


def macros(g):
    return [(c[2], c[3], c[4], c[5], c[6]) for c in g["cells"].values() if c[0] == "M"]


def kcover(pts, reach=REACH_UM):
    """greedy clusters of points (x, y, tag): each cluster fits one reach x reach box.  -> list of lists"""
    left = sorted(pts, key=lambda p: (p[0], p[1]))
    out = []
    while left:
        x0 = left[0][0]
        col = [p for p in left if p[0] <= x0 + reach]          # x-slab from the leftmost point
        col.sort(key=lambda p: p[1])
        rest = [p for p in left if p[0] > x0 + reach]
        i = 0
        while i < len(col):                                   # slice the slab by y
            y0 = col[i][1]
            j = i
            while j < len(col) and col[j][1] <= y0 + reach:
                j += 1
            out.append(col[i:j])
            i = j
        left = rest
    return out


def measure(g, net, mac=None):
    name, drv, sinks, pins, src = net
    mac = macros(g) if mac is None else mac
    pts = []
    for s, pn in zip(sinks, pins):
        r = _ref(g, s)
        if r:
            pts.append((r[0], r[1], s, pn, r[2]))
    d = _ref(g, drv) if drv != "-" else None
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    hp = (max(xs) - min(xs)) + (max(ys) - min(ys))
    dxy = (d[0], d[1]) if d else (sum(xs) / len(xs), sum(ys) / len(ys))
    far = max(abs(p[0] - dxy[0]) + abs(p[1] - dxy[1]) for p in pts)
    regs = kcover([(p[0], p[1], p) for p in pts])
    inm = []
    for p in pts:
        c = g["cells"].get(p[4]) if p[4] is not None else None
        if c and c[0] == "M":
            continue
        for m in mac:
            if m[0] < p[0] < m[2] and m[1] < p[1] < m[3]:
                inm.append(p[2])
                break
    fl = []
    if len(pts) > FANOUT:
        fl.append("fanout")
    if far > FAR_UM:
        fl.append("far")
    if hp > HPWL_UM:
        fl.append("hpwl")
    return dict(net=name, src=src, drv=drv, drv_xy=[round(dxy[0], 2), round(dxy[1], 2)], fanout=len(pts), hpwl_um=round(hp, 1),
                far_um=round(far, 1), regions=len(regs), in_macro=len(inm), in_macro_sinks=inm[:20], flags=fl,
                _pts=pts, _regs=regs)


class Grid:
    """free-site finder: occupied spans per row (std cells + macro bodies), row grid from the core origin"""

    def __init__(self, g):
        core = g["core"] or g["die"] or (0, 0, 0, 0)
        self.x0, self.y0, self.x1, self.y1 = core
        self.occ = {}
        self.mac = macros(g)
        for c in g["cells"].values():
            if c[0] == "M":
                continue
            r0 = int((c[3] - self.y0) / ROW_H + 1e-6)
            r1 = int((c[5] - self.y0) / ROW_H - 1e-6)
            for r in range(r0, max(r0, r1) + 1):
                self.occ.setdefault(r, []).append((c[2], c[4]))
        self.starts = {}
        for r, v in self.occ.items():
            v.sort()
            self.starts[r] = [a for a, _ in v]

    def _free(self, r, x, w):
        y = self.y0 + r * ROW_H
        if x < self.x0 or x + w > self.x1 or y < self.y0 or y + ROW_H > self.y1:
            return False
        for m in self.mac:
            if m[0] < x + w and x < m[2] and m[1] < y + ROW_H and y < m[3]:
                return False
        sp = self.occ.get(r)
        if sp:
            i = bisect.bisect_left(self.starts[r], x + w)       # spans starting at or after x + w cannot overlap
            for a, b in sp[max(0, i - 3):i]:
                if a < x + w and x < b:
                    return False
        return True

    def nearest(self, x, y, w=RELAY_W, rmax=600, xmax_um=250.0):
        """nearest free span of width w to (x, y): (L1 distance, x, y, row) or None"""
        r0 = int(round((y - self.y0) / ROW_H))
        best = None
        for dr in range(rmax):
            if best and dr * ROW_H - ROW_H >= best[0]:
                break
            for r in ((r0 + dr, r0 - dr) if dr else (r0,)):
                if r < 0:
                    continue
                dyv = abs(self.y0 + r * ROW_H - y)
                if best and dyv >= best[0]:
                    continue
                base = self.x0 + round((x - self.x0) / SITE_W) * SITE_W
                for step in range(int(xmax_um / SITE_W)):
                    dx = step * SITE_W
                    if best and dx + dyv >= best[0]:
                        break
                    hit = False
                    for cx in ((base + dx, base - dx) if step else (base,)):
                        if self._free(r, cx, w):
                            cand = (abs(cx - x) + dyv, round(cx, 4), round(self.y0 + r * ROW_H, 4), r)
                            if best is None or cand < best:
                                best = cand
                            hit = True
                    if hit:
                        break
        return best


def proposal(g, res, grid=None):
    """relay proposal for flagged nets: one relay per region at the nearest free site; every sink re-homed"""
    grid = grid or Grid(g)
    nets = []
    for r in res:
        if not r["flags"]:
            continue
        relays, rehome = [], []
        for k, reg in enumerate(sorted(r["_regs"], key=lambda c: (c[0][0], c[0][1]))):
            cx = sum(p[0] for p in reg) / len(reg)
            cy = sum(p[1] for p in reg) / len(reg)
            site = grid.nearest(cx, cy)
            nm = re.sub(r"[^A-Za-z0-9_]+", "_", f"{r['net']}").strip("_")[:80] + f"_rr{k}"
            sinks = [p[2][2] for p in reg]
            names = []
            for p in reg:
                c = g["cells"].get(p[2][4]) if p[2][4] is not None else None
                names.append(c[6] if c else p[2][2])
            relays.append(dict(name=nm, region=k, centroid=[round(cx, 2), round(cy, 2)],
                               x=site[1] if site else None, y=site[2] if site else None, row=site[3] if site else None,
                               snap_um=round(site[0], 2) if site else None, n=len(reg), sinks=names))
            for p, nmz in zip(reg, names):
                rehome.append(dict(sink=nmz, pin=p[2][3], from_net=r["net"], to_relay=nm))
        nets.append(dict(net=r["net"], driver=r["drv"], driver_xy=r["drv_xy"], flags=r["flags"], kind="ot_rst_relay", depth=1,
                         equal_depth=True, relays=relays, rehome=rehome))
    return dict(check=CHECK, schema=1, thresholds=dict(fanout=FANOUT, far_um=FAR_UM, hpwl_um=HPWL_UM, reach_um=REACH_UM), nets=nets)


def analyse(path, min_fanout=2):
    g = parse_geom(path)
    res = []
    mac = macros(g)
    for n in reset_nets(g):
        m = measure(g, n, mac)
        if m and m["fanout"] >= min_fanout:
            res.append(m)
    res.sort(key=lambda r: (-len(r["flags"]), -r["hpwl_um"]))
    return g, res


def summary(res, maxn=8):
    """one report-only line + compact rows for the visual review"""
    fl = [r for r in res if r["flags"]]
    rows = [dict((k, v) for k, v in r.items() if not k.startswith("_")) for r in fl[:maxn]]
    return dict(nets=len(res), flagged=len(fl), in_macro=sum(r["in_macro"] for r in res), worst=rows)


def line(s):
    if not s:
        return ""
    w = "; ".join(f"{r['net'][-40:]} fo{r['fanout']} hpwl{r['hpwl_um']:.0f} far{r['far_um']:.0f} reg{r['regions']} inM{r['in_macro']}"
                  for r in s["worst"][:3])
    return f"RST-SPREAD (report-only) {s['flagged']}/{s['nets']} reset nets over 405/900/3000" + (f": {w}" if w else "")


def main(argv=None):
    a = list(argv if argv is not None else sys.argv[1:])
    if not a or a[0].startswith("-"):
        print(__doc__)
        return 2
    path, js, prop = a[0], None, None
    allr = "--all" in a
    mf = int(a[a.index("--min-fanout") + 1]) if "--min-fanout" in a else 2
    if "--json" in a:
        js = a[a.index("--json") + 1]
    if "--proposal" in a:
        prop = a[a.index("--proposal") + 1]
    g, res = analyse(path, mf)
    s = summary(res)
    if js:
        rows = [dict((k, v) for k, v in r.items() if not k.startswith("_")) for r in (res if allr else [r for r in res if r["flags"]])]
        json.dump(dict(check=CHECK, geom=path, summary=s, nets=rows), open(js, "w"), indent=1)
    if prop:
        json.dump(proposal(g, res), open(prop, "w"), indent=1)
    print(json.dumps(s) if js is None and prop is None else line(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
