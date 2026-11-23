#!/usr/bin/env python3
"""hotspot_census.py -- whole-type hotspot census (HOTSPOT-CENSUS, COORD 11-23 PROBE-PASS redefinition fe8a2a5).

Owner 11-23: visual-review fixes targeted the most visible hotspot of a type, not every cause.  PROBE-PASS now needs a
census of ALL causes.  For one kit (or one set of reports) this lists:
  (a) every GRT overflow cluster: connected components (8-neighbour, after closing gaps of --gap gcells) of gcells over
      100% capacity, H and V separately, kept when overflow >= --min-ov (50) or >= 1% of that direction's total; per
      cluster bbox, overflow, layer mix (when the report names layers), and what sits inside / next to it: hard macros,
      blockage / reserved (cell-free, non-macro) area, top pins, station / relay cells, clock cells, placement density;
  (b) timing path classes from the latest STA reports (setup and hold, top --top paths each), grouped by
      start group -> end group, with worst slack, count and the clock-insertion share (launch / capture latency, skew);
  (c) a cause guess per cluster and per class (visual_brief classes: MACRO-CHANNEL, OVER-MACRO, MACRO-PIN-FACE,
      BLOCKAGE-RESERVED, PIN-ROW, STATION-CLUSTER, CLOCK-TAP, LOCAL-DENSITY, THIN-ASPECT, GLOBAL-DEMAND; timing:
      CLOCK-SKEW, HOLD-SKEW, REACH, LOGIC-DEPTH, IO-BOUNDARY, MACRO-IO, RESET-ASYNC).
Outputs OUT/census.json, OUT/census.tsv (one row per item) and OUT/census.png (every cluster numbered).
Advisory estimator, never a gate.

  hotspot_census.py analyze --out DIR [--geom geom.tsv] [--cong congestion.rpt ...] [--sta RPT ...] [--name N] [--bound-ps B]
  hotspot_census.py run --kit KITDIR --out DIR [--name N] [--docker-image IMG]   (find reports + latest DB in a kit run dir,
        dump geometry read-only with tools/autopilot/geom_dump.tcl in docker when no geom.tsv is given, then analyze)

Sources: congestion reports are ORFS `global_route -congestion_report_file` marker lists (direction-level gcells; the
report is capped at 20000 markers -- the census then says CAPPED and scales nothing).  The newest congestion-N.rpt /
congestion.rpt of the latest GRT round is used.  STA: report_checks text (full or full_clock_expanded); POST-hook CTS
report (4_cts_post_hook.rpt) is preferred over 4_cts_final.rpt (rules: read the post-hook report only).
"""
import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys

MIN_OV = 50
MIN_FRAC = 0.01
GAP = 2                 # gcells: two overflow gcells this close are one cluster (closing)
CHANNEL_UM = 30.0
STATION_RE = re.compile(r"(stn|station|relay|_rly|(^|[._/])u?_?ft[_\d]|pipe_?st|hop_?reg|_st\d|istn)", re.I)
CLOCK_MASTER_RE = re.compile(r"^(ICG|CKINV|CKBUF|CLKBUF)")
CLOCK_NAME_RE = re.compile(r"(^|[./])(clkbuf_|clkinv_|clkload|clk_t\d+_tb|delaybuf_otstb|cts_|ot_tap|tapbuf)", re.I)


# ----------------------------------------------------------------------------------------------- inputs
def parse_cong(path):
    """ORFS congestion report -> list of dict(d, x0, y0, x1, y1, cap, use, ov, layer, nets)."""
    out = []
    with open(path, errors="replace") as f:
        txt = f.read()
    for blk in txt.split("violation type:")[1:]:
        d = "H" if blk.lstrip().startswith("Horiz") else "V"
        m = re.search(r"capacity:\s*(-?\d+)\s*usage:\s*(-?\d+)(?:\s*congestion:\s*(-?\d+))?", blk)
        b = re.search(r"bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\)(?: on Layer (\S+))?", blk)
        if not b:
            continue
        cap, use = (int(m.group(1)), int(m.group(2))) if m else (0, 1)
        ov = int(m.group(3)) if m and m.group(3) else max(1, use - cap)
        s = re.search(r"srcs:(.*)", blk)
        nets = re.findall(r"net:(\S+)", s.group(1)) if s else []
        x0, y0, x1, y1 = map(float, b.groups()[:4])
        out.append(dict(d=d, x0=x0, y0=y0, x1=x1, y1=y1, cap=cap, use=use, ov=ov,
                        layer=(b.group(5) if b.group(5) and b.group(5) != "-" else None), nets=nets))
    return out


def load_geom(path):
    """geom_dump.tcl dump (D/R/C/P/Q rows; N rows skipped) -> dict."""
    g = dict(die=None, core=None, macros=[], cells=[], pins=[], fixed=set())
    with open(path, errors="replace") as f:
        for ln in f:
            t = ln.rstrip("\n").split("\t")
            k = t[0]
            if k == "C":
                kind = t[2]
                bb = tuple(map(float, t[4:8]))
                name = t[8] if len(t) > 8 else ""
                if kind == "M":
                    g["macros"].append(dict(id=t[1], master=t[3], bbox=bb, name=name))
                else:
                    g["cells"].append((kind, t[3], bb, name))
            elif k == "P":
                try:
                    g["pins"].append(dict(name=t[2], io=t[3], sig=t[4], layer=t[5], x=float(t[6]), y=float(t[7])))
                except (IndexError, ValueError):
                    pass
            elif k == "D":
                g["die"] = tuple(map(float, t[1:5]))
            elif k == "R":
                g["core"] = tuple(map(float, t[1:5]))
            elif k == "Q":
                g["fixed"].add(t[1])
    return g


# ----------------------------------------------------------------------------------------------- clusters
def gcell_pitch(markers):
    ws = sorted(round(m["x1"] - m["x0"], 4) for m in markers if m["x1"] > m["x0"])
    hs = sorted(round(m["y1"] - m["y0"], 4) for m in markers if m["y1"] > m["y0"])
    return (ws[len(ws) // 2] if ws else 1.0), (hs[len(hs) // 2] if hs else 1.0)


def clusters(markers, min_ov=MIN_OV, min_frac=MIN_FRAC, gap=GAP):
    """-> (list of cluster dicts sorted by overflow, totals per direction)."""
    res, totals = [], {}
    gx, gy = gcell_pitch(markers) if markers else (1.0, 1.0)
    for d in ("H", "V"):
        cells = {}
        for m in markers:
            if m["d"] != d:
                continue
            k = (int(round(m["x0"] / gx)), int(round(m["y0"] / gy)))
            c = cells.setdefault(k, dict(ov=0, cap=0, use=0, layers=collections.Counter(), nets=collections.Counter(),
                                         box=(m["x0"], m["y0"], m["x1"], m["y1"])))
            c["ov"] += m["ov"]; c["cap"] += m["cap"]; c["use"] += m["use"]
            if m["layer"]:
                c["layers"][m["layer"]] += m["ov"]
            for ln_, v_ in (m.get("layers") or {}).items():
                c["layers"][ln_] += v_
            for n in m["nets"]:
                c["nets"][n] += 1
        tot = sum(c["ov"] for c in cells.values())
        totals[d] = dict(overflow=tot, gcells=len(cells))
        seen = set()
        comps = []
        for k in sorted(cells):
            if k in seen:
                continue
            stack, comp = [k], []
            seen.add(k)
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx in range(-gap - 1, gap + 2):
                    for dy in range(-gap - 1, gap + 2):
                        n = (cx + dx, cy + dy)
                        if n in cells and n not in seen:
                            seen.add(n)
                            stack.append(n)
            comps.append(comp)
        for comp in comps:
            ov = sum(cells[k]["ov"] for k in comp)
            if ov < min_ov and ov < min_frac * max(1, tot):
                continue
            bx = [cells[k]["box"] for k in comp]
            lay = collections.Counter()
            nets = collections.Counter()
            for k in comp:
                lay.update(cells[k]["layers"]); nets.update(cells[k]["nets"])
            res.append(dict(d=d, ov=ov, gcells=len(comp), frac=round(ov / max(1, tot), 4),
                            bbox=(min(b[0] for b in bx), min(b[1] for b in bx), max(b[2] for b in bx), max(b[3] for b in bx)),
                            layers=dict(lay.most_common(6)), top_hier=hier_counts(nets).most_common(4),
                            pts=[((cells[k]["box"][0] + cells[k]["box"][2]) / 2, (cells[k]["box"][1] + cells[k]["box"][3]) / 2,
                                  cells[k]["ov"]) for k in comp]))
    res.sort(key=lambda c: -c["ov"])
    for i, c in enumerate(res, 1):
        c["id"] = i
    return res, totals


def hier(name, depth=2):
    n = name.replace("\\", "")
    toks = [t for t in re.split(r"[./]", n) if t]
    if len(toks) <= 1:
        return "(top)"
    toks = toks[:-1]
    if toks and toks[0] == "u_bound" and len(toks) > 1:
        toks = toks[1:]
    return re.sub(r"\[\d+\]", "[]", ".".join(toks[:depth]))


def hier_counts(nets):
    h = collections.Counter()
    for n, c in nets.items():
        if re.fullmatch(r"(net\d+|_\d+_)", n):
            continue
        h[hier(n + ".x", 2)] += c
    return h


# ----------------------------------------------------------------------------------------------- context + cause
def _ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _grow(b, r):
    return (b[0] - r, b[1] - r, b[2] + r, b[3] + r)


def _area(b):
    return max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])


def _in(b, x, y):
    return b[0] <= x <= b[2] and b[1] <= y <= b[3]


def context(c, g):
    """What sits inside / next to cluster c (geometry g may be None)."""
    bb = c["bbox"]
    pts = c["pts"]
    tot = max(1, c["ov"])
    ctx = dict()
    if not g:
        return ctx
    die = g["die"] or bb
    W, H = die[2] - die[0], die[3] - die[1]
    near = _grow(bb, 5.0)
    macs = [m for m in g["macros"] if _ov(m["bbox"], near) > 0]
    ctx["macros"] = [f'{m["name"].split("/")[-1][-40:]}({m["master"][-32:]})' for m in macs[:6]]
    on_mac = sum(p[2] for p in pts if any(_in(m["bbox"], p[0], p[1]) for m in g["macros"]))
    ctx["ov_on_macro"] = round(on_mac / tot, 3)
    edge = sum(p[2] for p in pts if any(_in(_grow(m["bbox"], 3.0), p[0], p[1]) and not _in(m["bbox"], p[0], p[1])
                                        for m in g["macros"]))
    ctx["ov_macro_edge3um"] = round(edge / tot, 3)
    # channel between two macros
    chan = None
    for i, a in enumerate(macs):
        for b in macs[i + 1:]:
            ox = min(a["bbox"][3], b["bbox"][3]) - max(a["bbox"][1], b["bbox"][1])
            oy = min(a["bbox"][2], b["bbox"][2]) - max(a["bbox"][0], b["bbox"][0])
            if ox > 0:   # side by side in x: vertical channel
                gap = max(a["bbox"][0], b["bbox"][0]) - min(a["bbox"][2], b["bbox"][2])
                if 0 <= gap < CHANNEL_UM and (chan is None or gap < chan[0]):
                    chan = (gap, "V", a["name"].split("/")[-1][-24:], b["name"].split("/")[-1][-24:])
            if oy > 0:
                gap = max(a["bbox"][1], b["bbox"][1]) - min(a["bbox"][3], b["bbox"][3])
                if 0 <= gap < CHANNEL_UM and (chan is None or gap < chan[0]):
                    chan = (gap, "H", a["name"].split("/")[-1][-24:], b["name"].split("/")[-1][-24:])
    ctx["channel"] = (f"{chan[0]:.1f}um {chan[2]}|{chan[3]}" if chan else None)
    inner = [cl for cl in g["_cells_near"](near)]
    std_area = sum(_area(cl[2]) for cl in inner)
    mac_area = sum(_ov(m["bbox"], near) for m in g["macros"])
    free = max(1.0, _area(near) - mac_area)
    ctx["density"] = round(std_area / free, 3)
    ctx["die_density"] = g["_die_density"]
    ctx["stations"] = sum(1 for cl in inner if STATION_RE.search(cl[3]))
    ctx["clock_cells"] = sum(1 for cl in inner if cl[0] == "K" or CLOCK_MASTER_RE.match(cl[1]) or CLOCK_NAME_RE.search(cl[3]))
    ctx["cells"] = len(inner)
    pins = [p for p in g["pins"] if p["sig"] not in ("POWER", "GROUND") and _in(_grow(bb, 15.0), p["x"], p["y"])]
    ctx["pins_near"] = len(pins)
    ctx["edge_dist_um"] = round(min(bb[0] - die[0], die[2] - bb[2], bb[1] - die[1], die[3] - bb[3]), 1)
    ctx["die_aspect"] = round(max(W, H) / max(1e-6, min(W, H)), 2)
    # cell-free non-macro area inside the cluster = blockage / reserved sites (geom_dump has no blockage rows)
    empty = 0
    for p in pts:
        if any(_in(m["bbox"], p[0], p[1]) for m in g["macros"]):
            continue
        if not g["_occupied"](p[0], p[1]):
            empty += p[2]
    ctx["ov_cellfree"] = round(empty / tot, 3)
    return ctx


def cluster_cause(c, ctx):
    """-> (cause, also[]) from the visual_brief classes."""
    s = {}
    if not ctx:
        return ("UNKNOWN-NOGEOM", [])
    s["OVER-MACRO"] = 2.0 * ctx["ov_on_macro"]
    if ctx.get("channel"):
        s["MACRO-CHANNEL"] = 1.2 + ctx["ov_macro_edge3um"]
    s["MACRO-PIN-FACE"] = 1.5 * ctx["ov_macro_edge3um"]
    s["BLOCKAGE-RESERVED"] = 1.8 * ctx["ov_cellfree"]
    if ctx["edge_dist_um"] < 20 and ctx["pins_near"] >= 20:
        s["PIN-ROW"] = 1.0 + min(1.0, ctx["pins_near"] / 200.0)
    if ctx["cells"]:
        s["STATION-CLUSTER"] = min(1.5, 8.0 * ctx["stations"] / ctx["cells"]) if ctx["stations"] >= 20 else 0
        s["CLOCK-TAP"] = min(1.5, 10.0 * ctx["clock_cells"] / ctx["cells"]) if ctx["clock_cells"] >= 10 else 0
    dd = max(0.02, ctx.get("die_density") or 0.02)
    s["LOCAL-DENSITY"] = min(1.6, (ctx["density"] / dd) / 3.0) if ctx["density"] > 0.45 else 0.3 * ctx["density"]
    if ctx["die_aspect"] > 4:
        s["THIN-ASPECT"] = 0.8
    s["GLOBAL-DEMAND"] = 0.5
    r = sorted(s.items(), key=lambda kv: -kv[1])
    return r[0][0], [k for k, v in r[1:4] if v >= 0.6]


# ----------------------------------------------------------------------------------------------- timing
NUM = r"(-?\d+(?:\.\d+)?)"


def _norm_grp(name):
    if not name:
        return "?"
    n = name.replace("\\", "")
    if "/" not in n and "." not in n:      # port
        return "port:" + re.sub(r"\d+", "N", re.sub(r"\[\d+\]$", "", n))
    h = hier(n, 2)
    if h in ("(top)", "u_bound"):       # flattened name: keep the first 4 '_' tokens of the leaf
        leaf = re.sub(r"(\[A-Z0-9_]+_?|\[\d+\])", "", re.split(r"[./]", n)[-1])
        h = "_".join(leaf.split("_")[:5])
    return re.sub(r"\d+", "N", h)


def parse_sta(path, top=50):
    """report_checks text -> list of path dicts."""
    with open(path, errors="replace") as f:
        txt = f.read()
    paths = []
    for blk in re.split(r"\n(?=Startpoint: )", "\n" + txt)[1:]:
        sp = re.match(r"Startpoint: (\S+)(.*)", blk)
        ep = re.search(r"\nEndpoint: (\S+)(.*)\n\s*\((.*)\)|\nEndpoint: (\S+)(.*)", blk)
        sl = re.search(NUM + r"\s+slack", blk)
        if not (sp and sl):
            continue
        epn = ep.group(1) or ep.group(4) if ep else "?"
        pg = re.search(r"Path Group: (\S+)", blk)
        pt = re.search(r"Path Type: (\S+)", blk)
        sclk = re.search(r"clocked by (\S+?)\)", sp.group(0) + blk[:400])
        body = blk.split("data arrival time")
        lat_l = _latency(body[0], sp.group(1))
        lat_c = _latency(body[1], epn) if len(body) > 1 else None
        data = body[0]
        cells = re.findall(r"\(([A-Za-z0-9_]+)\)\s*$", data, re.M)
        nbuf = sum(1 for c in cells if re.match(r"(BUF|INV|HB)", c))
        paths.append(dict(start=sp.group(1), end=epn, group=pg.group(1) if pg else "?",
                          type=(pt.group(1) if pt else "?"), slack=float(sl.group(1)),
                          sclk=sclk.group(1) if sclk else None, lat_launch=lat_l, lat_capture=lat_c,
                          stages=len(cells), bufs=nbuf,
                          start_port="(input port" in sp.group(0) or ("/" not in sp.group(1) and "." not in sp.group(1)),
                          end_port="output port" in (ep.group(0) if ep else "") or ("/" not in epn and "." not in epn)))
    return paths


def _latency(sec, inst):
    """clock latency at the reg clock pin of a launch / capture section (None for a port)."""
    edge = re.search(NUM + r"\s+" + NUM + r"\s+clock \S+ \((?:rise|fall) edge\)", sec)
    if not edge:
        return None
    t0 = float(edge.group(2))
    net = re.findall(NUM + r"\s+" + NUM + r"\s+clock network delay", sec)
    if net:
        return round(float(net[0][1]) - t0, 2)
    base = inst.rsplit("/", 1)[0] if "/" in inst and not inst.endswith("_") else inst
    for ln in sec.splitlines():
        if base and base in ln and re.search(r"\s[\^v]\s", ln):
            nums = re.findall(NUM, ln.split(base)[0])
            if nums:
                return round(float(nums[-1]) - t0, 2)
    return None


def timing_classes(paths, top=50, bound_ps=None):
    out = []
    for kind, typ in (("setup", "max"), ("hold", "min")):
        ps = sorted([p for p in paths if p["type"] == typ], key=lambda p: p["slack"])
        uniq, seen = [], set()
        for p in ps:
            k = (p["start"], p["end"])
            if k not in seen:
                seen.add(k); uniq.append(p)
        ps = uniq[:top]
        grp = collections.OrderedDict()
        for p in ps:
            k = (_norm_grp(p["start"]), _norm_grp(p["end"]), p["group"])
            grp.setdefault(k, []).append(p)
        for (sg, eg, pg), L in grp.items():
            ll = [p["lat_launch"] for p in L if p["lat_launch"] is not None]
            lc = [p["lat_capture"] for p in L if p["lat_capture"] is not None]
            mean = lambda v: round(sum(v) / len(v), 1) if v else None
            ml, mc = mean(ll), mean(lc)
            skew = round(mc - ml, 1) if (ml is not None and mc is not None) else None
            worst = min(p["slack"] for p in L)
            c = dict(kind=kind, start_grp=sg, end_grp=eg, path_group=pg, count=len(L), worst=round(worst, 2),
                     lat_launch=ml, lat_capture=mc, skew=skew, bound_ps=bound_ps,
                     bufs=sum(p["bufs"] for p in L), stages=sum(p["stages"] for p in L), example=(L[0]["start"], L[0]["end"]))
            c["insertion_share"] = _ins_share(kind, worst, skew)
            c["cause"] = timing_cause(c, L)
            out.append(c)
    return out


def _ins_share(kind, worst, skew):
    """share of the worst violation the skew explains (setup: launch late / capture early; hold: capture late)."""
    if worst >= 0 or skew is None:
        return 0.0
    harm = -skew if kind == "setup" else skew
    return round(max(0.0, min(1.0, harm / -worst)), 2) if harm > 0 else 0.0


def timing_cause(c, L):
    if c["path_group"].lower().startswith("async") or re.search(r"rst|reset", c["example"][0], re.I) and c["kind"] == "hold":
        return "RESET-ASYNC"
    if any(p["start_port"] or p["end_port"] for p in L):
        return "IO-BOUNDARY"
    if c["insertion_share"] >= 0.5:
        return "HOLD-SKEW" if c["kind"] == "hold" else "CLOCK-SKEW"
    if c["kind"] == "hold":
        return "HOLD-SKEW" if (c["skew"] or 0) > 0 else "HOLD-SHORT-PATH"
    if c["stages"] and c["bufs"] / c["stages"] >= 0.5:
        return "REACH"
    return "LOGIC-DEPTH"


# ----------------------------------------------------------------------------------------------- report
def _geom_index(g, bin_um=10.0):
    die = g["die"] or (0, 0, 1, 1)
    grid = collections.defaultdict(list)
    for cl in g["cells"]:
        b = cl[2]
        grid[(int((b[0] - die[0]) // bin_um), int((b[1] - die[1]) // bin_um))].append(cl)

    def near(box):
        out = []
        for ix in range(int((box[0] - die[0]) // bin_um) - 1, int((box[2] - die[0]) // bin_um) + 1):
            for iy in range(int((box[1] - die[1]) // bin_um) - 1, int((box[3] - die[1]) // bin_um) + 1):
                for cl in grid.get((ix, iy), ()):
                    if _ov(cl[2], box) > 0 or _in(box, cl[2][0], cl[2][1]):
                        out.append(cl)
        return out
    occ = set()
    fine = 2.0
    for cl in g["cells"]:
        b = cl[2]
        occ.add((int((b[0] + b[2]) / 2 // fine), int((b[1] + b[3]) / 2 // fine)))

    def occupied(x, y):
        ix, iy = int(x // fine), int(y // fine)
        return any((ix + a, iy + b) in occ for a in (-1, 0, 1) for b in (-1, 0, 1))
    g["_cells_near"] = near
    g["_occupied"] = occupied
    W, H = die[2] - die[0], die[3] - die[1]
    mac = sum(_area(m["bbox"]) for m in g["macros"])
    g["_die_density"] = round(sum(_area(cl[2]) for cl in g["cells"]) / max(1.0, W * H - mac), 4)


def analyze(a):
    os.makedirs(a.out, exist_ok=True)
    g = load_geom(a.geom) if a.geom and os.path.isfile(a.geom) else None
    if g:
        _geom_index(g)
    markers, rpt = [], []
    for p in a.cong or []:
        if os.path.isfile(p):
            rpt += parse_cong(p)
    capped = len(rpt) >= 20000
    gsrc = None
    if getattr(a, "gcells", None) and os.path.isfile(a.gcells):
        markers, gsrc = load_gcells(a.gcells)
        capped = False
    else:
        markers = rpt
    cl, totals = clusters(markers, a.min_ov, a.min_frac, a.gap)
    if gsrc is not None:
        for d in totals:
            totals[d]["hot90_gcells"] = gsrc.get("hot90", {}).get(d)
        for c in cl:              # net names come from the report markers inside the cluster
            nets = collections.Counter()
            b = c["bbox"]
            for m in rpt:
                if m["d"] == c["d"] and _in(b, (m["x0"] + m["x1"]) / 2, (m["y0"] + m["y1"]) / 2):
                    nets.update(m["nets"])
            c["top_hier"] = hier_counts(nets).most_common(4)
    for c in cl:
        c["ctx"] = context(c, g)
        c["cause"], c["also"] = cluster_cause(c, c["ctx"])
    paths = []
    for p in a.sta or []:
        if os.path.isfile(p):
            paths += parse_sta(p)
    tc = timing_classes(paths, a.top, a.bound_ps)
    res = dict(name=a.name, cong=a.cong, sta=a.sta, geom=a.geom, gcells=getattr(a, "gcells", None), totals=totals,
               markers=len(markers), capped=capped,
               die=(g["die"] if g else None), die_density=(g["_die_density"] if g else None),
               clusters=[{k: v for k, v in c.items() if k != "pts"} for c in cl], timing=tc,
               src=getattr(a, "src", None))
    with open(os.path.join(a.out, "census.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    with open(os.path.join(a.out, "census.tsv"), "w") as f:
        f.write("name\titem\tkind\tsize\tbbox_or_group\tcause\talso\tdetail\n")
        for c in cl:
            x = c["ctx"]
            det = (f'layers={c["layers"]} hier={c["top_hier"][:2]} macros={x.get("macros", [])[:3]} chan={x.get("channel")} '
                   f'dens={x.get("density")} stn={x.get("stations")} clk={x.get("clock_cells")} pins={x.get("pins_near")} '
                   f'on_mac={x.get("ov_on_macro")} cellfree={x.get("ov_cellfree")}')
            f.write(f'{a.name}\tC{c["id"]}\tGRT-{c["d"]}\t{c["ov"]} ovfl ({100*c["frac"]:.1f}%)\t'
                    f'x{c["bbox"][0]:.0f}-{c["bbox"][2]:.0f} y{c["bbox"][1]:.0f}-{c["bbox"][3]:.0f}\t{c["cause"]}\t'
                    f'{",".join(c["also"])}\t{det}\n')
        for i, t in enumerate(tc, 1):
            if t["worst"] >= 0:
                continue
            f.write(f'{a.name}\tP{i}\t{t["kind"]}\t{t["count"]} paths worst {t["worst"]}\t'
                    f'{t["start_grp"]}->{t["end_grp"]} [{t["path_group"]}]\t{t["cause"]}\t\t'
                    f'lat L/C {t["lat_launch"]}/{t["lat_capture"]} skew {t["skew"]} ins_share {t["insertion_share"]} '
                    f'bufs {t["bufs"]}/{t["stages"]}\n')
    try:
        render(a, g, cl, totals, tc, markers)
    except Exception as e:  # noqa: BLE001 - the PNG is advisory; the TSV/JSON stand alone
        print("HOTSPOT_CENSUS_PNG_FAIL", e, file=sys.stderr)
    nviol = sum(1 for t in tc if t["worst"] < 0)
    print(f"HOTSPOT_CENSUS {a.name} clusters {len(cl)} (H {totals.get('H', {}).get('overflow', 0)} "
          f"V {totals.get('V', {}).get('overflow', 0)}{' CAPPED' if capped else ''}) "
          f"path_classes {nviol} causes {dict(collections.Counter(c['cause'] for c in cl))} out {a.out}")
    return res


def render(a, g, cl, totals, tc, markers):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    die = (g["die"] if g else None) or (min(m["x0"] for m in markers), min(m["y0"] for m in markers),
                                         max(m["x1"] for m in markers), max(m["y1"] for m in markers)) if (g or markers) else (0, 0, 1, 1)
    W, H = die[2] - die[0], die[3] - die[1]
    fig, axs = plt.subplots(1, 3, figsize=(24, 8 * max(0.5, min(2.0, H / max(1, W)))+1.5), dpi=100,
                            gridspec_kw=dict(width_ratios=[1, 1, 0.8]))
    for ax, d in zip(axs[:2], ("H", "V")):
        if g:
            xs = [(c[2][0] + c[2][2]) / 2 for c in g["cells"][::max(1, len(g["cells"]) // 60000)]]
            ys = [(c[2][1] + c[2][3]) / 2 for c in g["cells"][::max(1, len(g["cells"]) // 60000)]]
            ax.scatter(xs, ys, s=0.2, c="0.75", lw=0)
            for m in g["macros"]:
                b = m["bbox"]
                ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc="0.85", ec="0.3", lw=0.5, alpha=0.6))
            ck = [c for c in g["cells"] if c[0] == "K"]
            if ck:
                ax.scatter([(c[2][0] + c[2][2]) / 2 for c in ck], [(c[2][1] + c[2][3]) / 2 for c in ck], s=0.6, c="green", lw=0)
            pp = [p for p in g["pins"] if p["sig"] not in ("POWER", "GROUND")]
            ax.scatter([p["x"] for p in pp], [p["y"] for p in pp], s=1.5, c="purple", marker="s", lw=0)
        mm = [m for m in markers if m["d"] == d]
        if mm:
            ax.scatter([(m["x0"] + m["x1"]) / 2 for m in mm], [(m["y0"] + m["y1"]) / 2 for m in mm], s=1.2,
                       c=[min(m["ov"], 8) for m in mm], cmap="Reds" if d == "H" else "Blues", vmin=0, vmax=8, lw=0)
        for c in cl:
            if c["d"] != d:
                continue
            b = c["bbox"]
            ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False, ec="k", lw=1.0))
            ax.annotate(f'{c["id"]}', (b[2], b[3]), fontsize=8, color="k", weight="bold")
        ax.add_patch(Rectangle((die[0], die[1]), W, H, fill=False, ec="k", lw=1))
        ax.set_xlim(die[0] - 0.01 * W, die[2] + 0.01 * W); ax.set_ylim(die[1] - 0.01 * H, die[3] + 0.01 * H)
        ax.set_aspect("equal")
        ax.set_title(f'{a.name} GRT {d}: overflow {totals.get(d, {}).get("overflow", 0)} in '
                     f'{totals.get(d, {}).get("gcells", 0)} gcells; {sum(1 for c in cl if c["d"] == d)} clusters', fontsize=9)
        ax.tick_params(labelsize=6)
    ax = axs[2]
    ax.axis("off")
    lines = [f"clusters (>= {a.min_ov} ovfl or >= {100*a.min_frac:.0f}% of dir total)"]
    for c in cl[:28]:
        b = c["bbox"]
        lines.append(f'{c["id"]:>2} {c["d"]} {c["ov"]:>6} {100*c["frac"]:4.1f}% x{b[0]:.0f}-{b[2]:.0f} y{b[1]:.0f}-{b[3]:.0f} {c["cause"]}')
    lines.append("")
    lines.append("failing path classes (top setup/hold, start->end group)")
    for t in [t for t in tc if t["worst"] < 0][:22]:
        lines.append(f'{t["kind"][0].upper()} {t["worst"]:>8.1f} n{t["count"]:<3} {t["start_grp"][:24]}->{t["end_grp"][:24]} '
                     f'skew {t["skew"]} {t["cause"]}')
    ax.text(0, 1, "\n".join(lines), va="top", ha="left", family="monospace", fontsize=6.5, transform=ax.transAxes)
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "census.png"))
    plt.close(fig)


# ----------------------------------------------------------------------------------------------- odb gcell map (v2)
def extract_gcells(odb_path, out):
    """Run under `openroad -python`: full GRT gcell map from the odb dbGCellGrid (no 20000-marker cap).
    Writes OUT json: {die, gcell_um, totals{H,V}, hot90{H,V}, markers:[[d,x0,y0,x1,y1,cap,use,ov,{layer:over}]...]}."""
    import array
    import odb  # noqa: F401 - only inside OpenROAD
    db = odb.dbDatabase.create()
    odb.read_db(db, odb_path)
    blk = db.getChip().getBlock()
    g = blk.getGCellGrid()
    res = dict(odb=odb_path, markers=[], totals={}, hot90={})
    if g is None:
        res["error"] = "no gcell grid in odb"
        json.dump(res, open(out, "w"))
        return res
    u = float(blk.getDbUnitsPerMicron())
    die = blk.getDieArea()
    xs = list(g.getGridX()) + [die.xMax()]
    ys = list(g.getGridY()) + [die.yMax()]
    nx, ny = len(xs) - 1, len(ys) - 1
    res["die"] = (die.xMin() / u, die.yMin() / u, die.xMax() / u, die.yMax() / u)
    res["grid"] = (nx, ny)
    acc = {d: (array.array("d", bytes(8 * nx * ny)), array.array("d", bytes(8 * nx * ny))) for d in "HV"}
    lover = collections.defaultdict(dict)
    for l in db.getTech().getLayers():
        if l.getType() != "ROUTING" or l.getRoutingLevel() < 2:
            continue
        d = "H" if l.getDirection() == "HORIZONTAL" else "V"
        cap_a, use_a = acc[d]
        cf, uf, ln = g.getCapacity, g.getUsage, l.getName()
        for ix in range(nx):
            base = ix * ny
            for iy in range(ny):
                c = cf(l, ix, iy)
                v = uf(l, ix, iy)
                if c == 0 and v == 0:
                    continue
                cap_a[base + iy] += c
                use_a[base + iy] += v
                if v > c:
                    lover[(d, ix, iy)][ln] = round(v - c, 2)
    for d in "HV":
        cap_a, use_a = acc[d]
        tot = h90 = 0
        for ix in range(nx):
            base = ix * ny
            for iy in range(ny):
                c, v = cap_a[base + iy], use_a[base + iy]
                if c > 0 and v >= 0.9 * c:
                    h90 += 1
                if v > c:
                    tot += v - c
                    res["markers"].append([d, xs[ix] / u, ys[iy] / u, xs[ix + 1] / u, ys[iy + 1] / u, round(c, 2),
                                           round(v, 2), round(v - c, 2),
                                           lover.get((d, ix, iy), {})])
        res["totals"][d] = round(tot, 1)
        res["hot90"][d] = h90
    json.dump(res, open(out, "w"))
    print(f"HOTSPOT_GCELLS {out} grid {nx}x{ny} H {res['totals']['H']} V {res['totals']['V']} markers {len(res['markers'])}")
    return res


def load_gcells(path):
    j = json.load(open(path))
    ms = [dict(d=m[0], x0=m[1], y0=m[2], x1=m[3], y1=m[4], cap=m[5], use=m[6], ov=m[7], layer=None, layers=m[8], nets=[])
          for m in j.get("markers", [])]
    return ms, j


# ----------------------------------------------------------------------------------------------- gaps + PROBE-PASS check
# cause -> keywords a covering structural row (VIS-COVERAGE cause_class + structural_row text) must name
COVER = {
    "MACRO-CHANNEL": r"CHAN|CHANNEL|JUNCTION|LANECH|GAP|XGA|ARRAY|MACRO|FLOOR|GROW|OUTLINE|SHAPE|SPREAD|CORRIDOR|STRIP|WALL|SLIT",
    "OVER-MACRO": r"CHAN|JUNCTION|LANECH|MACRO|OBS|OVER-?CORE|FLOOR|GROW|OUTLINE|SHAPE|XGA|ARRAY|CORRIDOR|WALL|SLIT|M[6-9]",
    "MACRO-PIN-FACE": r"PIN-?FACE|PINFACE|CHAN|MACRO|JUNCTION|LANECH|XGA|ARRAY|SLIT",
    "BLOCKAGE-RESERVED": r"RESERV|BLOCKAGE|KEEPOUT|SITE|CLOCK-?SITE|STRIP|BAND|TAP",
    "PIN-ROW": r"PIN|EDGE|STRIP|WINDOW|LANDING|FACE",
    "STATION-CLUSTER": r"STATION|STN|SITE|RELAY|BANK|HST|SPREAD|PAD",
    "CLOCK-TAP": r"TAP|CLOCK|CTS|SPINE|TRUNK|GRID",
    "LOCAL-DENSITY": r"DENS|SPREAD|GROW|OUTLINE|SHAPE|JUNCTION|LANECH|CHAN|BLOB|STACK|FLOOR",
    "THIN-ASPECT": r"ASPECT|SHAPE|GROW|OUTLINE",
    "GLOBAL-DEMAND": r"GROW|OUTLINE|SHAPE|DENS|LAYER|SPLIT",
    "CLOCK-SKEW": r"TAP|CLOCK|CTS|SKEW|SPINE|TRUNK|LATENCY|BALANCE",
    "HOLD-SKEW": r"TAP|CLOCK|CTS|SKEW|HOLD|LOCKUP|SHARED|BALANCE",
    "HOLD-SHORT-PATH": r"HOLD|LOCKUP|ECO|PAD",
    "RESET-ASYNC": r"RESET|RST|RELAY",
    "IO-BOUNDARY": r"PIN|IO|BOUNDARY|LAND|VCLK|PAD|FIFO|FACE",
    "MACRO-IO": r"MACRO|VIEW|ETM|LATENCY|PIN",
    "REACH": r"STATION|STN|REACH|RELAY|HOP|STAGE|PIPE|CYCLE",
    "LOGIC-DEPTH": r"STAGE|PIPE|CYCLE|DEPTH|FOLD|RTL|RETIME",
}


def base_type(t):
    t = t[3:] if t.startswith("ot_") else t
    return re.sub(r"(__(cl|pv)[0-9a-f]{6,})+$", "", t)


def census_items(res, setup_tns=-42.0):
    """census.json -> items needing a row: every cluster; setup classes < -42; hold classes < 0 (COORD fe8a2a5 (1)-(3))."""
    items = []
    for c in res.get("clusters", []):
        b = c["bbox"]
        items.append(dict(item=f'C{c["id"]}-{c["d"]} x{b[0]:.0f}-{b[2]:.0f} y{b[1]:.0f}-{b[3]:.0f}',
                          size=f'{c["ov"]} ovfl {100*c["frac"]:.1f}%', cause=c["cause"], also=c.get("also", [])))
    for t in res.get("timing", []):
        if (t["kind"] == "setup" and t["worst"] < setup_tns) or (t["kind"] == "hold" and t["worst"] < 0):
            items.append(dict(item=f'{t["kind"]} {t["start_grp"]}->{t["end_grp"]} [{t["path_group"]}]',
                              size=f'{t["count"]}p worst {t["worst"]} skew {t["skew"]}', cause=t["cause"], also=[]))
    return items


def load_coverage(path):
    rows = {}
    with open(path, errors="replace") as f:
        for ln in f:
            t = ln.rstrip("\n").split("\t")
            if ln.startswith("#") or len(t) < 9 or t[0] == "die":
                continue
            rows[base_type(t[1])] = dict(die=t[0], type=t[1], family=t[2], vis_lane=t[3], cause_class=t[6],
                                         row=t[7], status=t[8])
    return rows


def covering(item, cov):
    if not cov or cov["row"] in ("", "-", "PENDING", "NONE") or cov["row"].startswith("NONE-NEEDED"):
        return "NONE"
    txt = (cov["cause_class"] + " " + cov["row"]).upper()
    for cause in [item["cause"]] + list(item.get("also") or []):
        if re.search(COVER.get(cause, r"$^"), txt):
            return cov["row"].split()[0][:60]
    return "NONE"


def gaps(a):
    cov = load_coverage(a.coverage)
    owners = {}
    if a.owners and os.path.isfile(a.owners):
        for ln in open(a.owners, errors="replace"):
            t = ln.rstrip("\n").split("\t")
            if len(t) > 3 and t[0] in ("S81", "HEAD", "QC", "KV"):
                owners[base_type(t[1])] = t[3].split()[0]
    out = ["die\ttype\tfamily\titem\tsize\tcause\tcovering_row\towner_lane\tcensus"]
    n = collections.Counter()
    for cj in sorted(a.census):
        try:
            res = json.load(open(cj))
        except (OSError, ValueError):
            continue
        die, _, typ = (res.get("name") or "").partition("__")
        bt = base_type(typ)
        cv = cov.get(bt)
        fam = cv["family"] if cv else "?"
        owner = (cv["vis_lane"] if cv else None) or owners.get(bt, "UNOWNED")
        for it in census_items(res):
            cr = covering(it, cv)
            n["NONE" if cr == "NONE" else "covered"] += 1
            out.append("\t".join([die, typ, fam, it["item"], it["size"], it["cause"], cr, owner, cj]))
    with open(a.out, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"HOTSPOT_GAPS {a.out} items {sum(n.values())} covered {n['covered']} NONE {n['NONE']}")
    return out


def check(a):
    """PROBE-PASS census gate: exit 0 only when a census for TYPE exists and every item has a covering row."""
    rows = [ln.rstrip("\n").split("\t") for ln in open(a.gaps, errors="replace")][1:]
    mine = [r for r in rows if len(r) > 7 and base_type(r[1]) == base_type(a.type)]
    if not mine and not a.allow_clean:
        print(f"HOTSPOT_CHECK {a.type} NO-CENSUS (no HOTSPOT-GAPS rows; a clean census writes none: pass --allow-clean "
              f"with its census.json)")
        return 2
    none = [r for r in mine if r[6] == "NONE"]
    for r in none:
        print(f"HOTSPOT_CHECK {a.type} UNCOVERED {r[3]} {r[4]} {r[5]}")
    print(f"HOTSPOT_CHECK {a.type} {'PASS' if not none else 'FAIL'} items {len(mine)} uncovered {len(none)}")
    return 0 if not none else 1


# ----------------------------------------------------------------------------------------------- kit discovery + run
STAGE_ODBS = ("6_final.odb", "5_3_fillcell.odb", "5_2_route.odb", "5_1_grt.odb", "5_1_grt-failed.odb", "5_1_grt.prerepair.odb",
              "4_cts.odb", "4_1_cts.odb", "3_place.odb", "3_5_place_dp.odb", "3_4_place_resized.odb", "3_3_place_gp.odb",
              "3_5_place_dp-failed.odb", "3_3_place_gp-failed.odb")
STA_RPTS = ("6_finish.rpt", "5_route.rpt", "5_global_route_post.rpt", "4_cts_post_hook.rpt", "4_cts_final.rpt",
            "3_detailed_place.rpt", "3_resizer.rpt")


def kit_sources(kit):
    """kit dir (or its run dir) -> dict(odb, cong[], sta[], bound_ps, stage)."""
    run = kit if os.path.isdir(os.path.join(kit, "results")) else os.path.join(kit, "run")
    base = (glob.glob(os.path.join(run, "results", "*", "*", "base")) or [None])[0]
    rep = (glob.glob(os.path.join(run, "reports", "*", "*", "base")) or [None])[0]
    src = dict(odb=None, cong=[], sta=[], bound_ps=None, stage=None)
    if base:
        for o in STAGE_ODBS:
            p = os.path.join(base, o)
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                src["odb"], src["stage"] = p, o
                break
    if rep:
        cs = [p for p in glob.glob(os.path.join(rep, "congestion*.rpt")) if os.path.getsize(p) > 0]
        if cs:
            src["cong"] = [max(cs, key=os.path.getmtime)]
        for r in STA_RPTS:
            p = os.path.join(rep, r)
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                src["sta"] = [p]
                break
    for cj in (os.path.join(kit, "core_latency.json"), os.path.join(os.path.dirname(run), "core_latency.json")):
        try:
            src["bound_ps"] = json.load(open(cj)).get("target_ps")
            break
        except (OSError, ValueError, AttributeError):
            pass
    return src


def _docker(a, odb_dir, inner, extra=()):
    dk = ["docker"] if subprocess.call(["docker", "ps"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0 \
        else ["sudo", "docker"]
    cmd = dk + ["run", "--rm", "--cpus", "2", "--memory", f"{a.mem}g", "--memory-swap", f"{a.mem}g",
                "-v", f"{odb_dir}:/odb:ro", "-v", f"{os.path.abspath(a.out)}:/out", *extra,
                "-e", "OT_GEOM_OUT=/out/geom.tsv", "-e", f"HUID={os.getuid()}", "-e", f"HGID={os.getgid()}",
                "-w", "/out", a.docker_image, "bash", "-lc",
                f"source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; {inner}; rc=$?; chown -R $HUID:$HGID /out; exit $rc"]
    return subprocess.call(cmd)


def run_kit(a):
    src = kit_sources(a.kit)
    os.makedirs(a.out, exist_ok=True)
    geom = a.geom
    odb_dir = os.path.dirname(src["odb"]) if src["odb"] else None
    if not geom and src["odb"]:
        geom = os.path.join(a.out, "geom.tsv")
        if not os.path.isfile(geom) or os.path.getsize(geom) == 0:
            dump = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "autopilot", "geom_dump.tcl")
            dump = os.path.abspath(a.geom_dump or dump)
            import shutil
            shutil.copy(dump, os.path.join(a.out, "geom_dump.tcl"))
            with open(os.path.join(a.out, "dump.tcl"), "w") as f:
                f.write(f"read_db /odb/{os.path.basename(src['odb'])}\nsource /out/geom_dump.tcl\n")
            rc = _docker(a, odb_dir, "openroad -exit /out/dump.tcl > /out/dump.log 2>&1")
            if rc != 0:
                print(f"HOTSPOT_CENSUS geom dump failed rc {rc} ({src['odb']}); continuing without geometry", file=sys.stderr)
                geom = None
    gc = a.gcells
    if not gc and not a.no_gcells and src["odb"] and re.match(r"(5_|6_)", src["stage"] or ""):
        gc = os.path.join(a.out, "gcells.json")
        if not os.path.isfile(gc) or os.path.getsize(gc) == 0:
            tool = os.path.abspath(__file__)
            rc = _docker(a, odb_dir, f"openroad -python -exit /tool/{os.path.basename(tool)} extract-gcells "
                                     f"--odb /odb/{os.path.basename(src['odb'])} --out /out/gcells.json > /out/gcells.log 2>&1",
                         extra=("-v", f"{os.path.dirname(tool)}:/tool:ro"))
            if rc != 0 or not os.path.isfile(gc):
                print(f"HOTSPOT_CENSUS gcell map failed rc {rc}; falling back to the congestion report", file=sys.stderr)
                gc = None
    a.geom, a.cong, a.sta, a.gcells = geom, (a.cong or src["cong"]), (a.sta or src["sta"]), gc
    a.bound_ps = a.bound_ps or src["bound_ps"]
    a.src = src
    return analyze(a)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("analyze", "run"):
        s = sub.add_parser(n)
        s.add_argument("--out", required=True)
        s.add_argument("--name", default="type")
        s.add_argument("--geom")
        s.add_argument("--cong", nargs="*")
        s.add_argument("--sta", nargs="*")
        s.add_argument("--bound-ps", type=float)
        s.add_argument("--min-ov", type=int, default=MIN_OV)
        s.add_argument("--min-frac", type=float, default=MIN_FRAC)
        s.add_argument("--gap", type=int, default=GAP)
        s.add_argument("--top", type=int, default=50)
        s.add_argument("--gcells", help="extract-gcells json (full map; replaces the capped congestion report)")
        if n == "run":
            s.add_argument("--no-gcells", action="store_true", help="skip the odb gcell map (report markers only)")
            s.add_argument("--kit", required=True)
            s.add_argument("--geom-dump")
            s.add_argument("--mem", type=int, default=24)
            s.add_argument("--docker-image", default="openroad/orfs:asap7lock")
    s = sub.add_parser("extract-gcells", help="inside `openroad -python`: full gcell map of a GRT odb")
    s.add_argument("--odb", required=True); s.add_argument("--out", required=True)
    s = sub.add_parser("gaps", help="census.json files + VIS-COVERAGE.tsv -> HOTSPOT-GAPS.tsv")
    s.add_argument("--coverage", required=True); s.add_argument("--owners"); s.add_argument("--out", required=True)
    s.add_argument("census", nargs="+")
    s = sub.add_parser("check", help="PROBE-PASS census gate for one type (exit 0 = every item covered)")
    s.add_argument("--gaps", required=True); s.add_argument("--type", required=True)
    s.add_argument("--allow-clean", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "extract-gcells":
        return extract_gcells(a.odb, a.out)
    if a.cmd == "gaps":
        return gaps(a)
    if a.cmd == "check":
        return check(a)
    return run_kit(a) if a.cmd == "run" else analyze(a)


if __name__ == "__main__":
    r = main()
    if isinstance(r, int) and not isinstance(r, bool):
        sys.exit(r)
