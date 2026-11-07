#!/usr/bin/env python3
"""KW-FIX-25/AUTORENDER 11-06: advisory physical smells of one stage ODB, from the dump layout_render.tcl writes.

    layout_smells.py DUMP.tsv --out smells.json [--congestion CSV] [--marks marks.tsv] [--one line.txt] [--odb PATH]

Six checks (OWNER 11-06 22:0x smell list), each {value, threshold, flag, computable, method, offenders[{.. x, y}]}:
  opposite_face_pins  pin to its partner logic / pin, measured across the block (ratio of the block size on that axis)
  pin_track_use       pins per sliding 20-um window of a face / tracks of the pin layer in 20 um
  channel_tracks      macro-macro and macro-edge channels: nets through the channel / tracks of the channel
  clock               entry to sink centroid, unshared clock path of related flop pairs, clock guides over foreign macros
  fanout_spread       one logical driver (traced through buffers) whose sinks spread over > 100 um
  local_density       standard-cell area / free area in 10-um bins

Stdlib only, Python >= 3.6 (ORFS container).  ADVISORY: thresholds flag, nothing here gates a build.  Where the ODB cannot give
an answer, a check says computable: false with the reason, and never guesses.  A pin / macro-free block: value null, no flag.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict

SCHEMA = "opentallas.layout_smells.v1"
TH = {"opposite_face_ratio": 0.6, "pin_track_use": 0.5, "pin_window_um": 20.0, "channel_use": 1.0, "channel_max_gap_um": 60.0,
      "clock_entry_ratio": 0.4, "clock_unshared_um": 200.0, "clock_over_macro_um": 50.0, "fanout_spread_um": 100.0,
      "local_density": 0.7, "density_bin_um": 10.0, "density_min_free": 0.25}
TOP = 20
MAX_CHANNELS = 200
MAX_FLIGHT_CHANNELS = 40       # place stage: no guides, nets x channels in pure Python
RELATED_FANIN_CAP = 32         # cells walked per launch flop when looking for related capture flops
REPEATER_RE = re.compile(r"^(BUF|INV|HB\d|CKINV)", re.I)
SEQ_RE = re.compile(r"^(DFF|DHL|DLL|SDF|ASYNC_DFF|ICG)", re.I)
ICG_RE = re.compile(r"^ICG", re.I)
SKIP_DENS_RE = re.compile(r"^(FILLER|DECAP)", re.I)
CLK_PIN_RE = re.compile(r"^(clk|clock|ck|clka|clkb|.*_clk|clk_.*|gclk)$", re.I)
TIE_RE = re.compile(r"^TIE", re.I)


def rnd(v, n=3):
    return None if v is None else round(v, n)


class Design:
    """the parsed dump"""

    def __init__(self, path):
        self.stage, self.top, self.ninst, self.big = "", "", 0, False
        self.die = self.core = None
        self.layers, self.level_layer = {}, {}
        self.insts, self.pins, self.nets, self.blockages = {}, [], {}, []
        self.guides = defaultdict(list)
        self.macros = []
        with open(path, errors="replace") as f:
            for ln in f:
                p = ln.rstrip("\n").split("\t")
                k = p[0]
                if k == "I":
                    iid, name, master, isb, top = p[1], p[2], p[3], p[4] == "1", int(p[5])
                    box = tuple(float(v) for v in p[6:10])
                    self.insts[iid] = dict(id=iid, name=name, master=master, block=isb, top=top, box=box,
                                           x=(box[0] + box[2]) / 2, y=(box[1] + box[3]) / 2, out=[])
                    if isb:
                        self.macros.append(self.insts[iid])
                elif k == "N":
                    terms = []
                    for t in (p[3].split(" ") if len(p) > 3 and p[3] else ()):
                        iid, mt, io, sg, xy = t.split(":", 4)
                        terms.append((iid, mt, io, sg, xy))
                    self.nets[p[1]] = dict(name=p[1], sig=p[2], terms=terms, pins=[])
                elif k == "G":
                    self.guides[p[1]].append((int(p[2]), float(p[3]), float(p[4]), float(p[5]), float(p[6])))
                elif k == "P":
                    box = tuple(float(v) for v in p[6:10])
                    self.pins.append(dict(name=p[1], net=p[2], sig=p[3], io=p[4], layer=p[5],
                                          x=(box[0] + box[2]) / 2, y=(box[1] + box[3]) / 2))
                elif k == "L":
                    self.layers[p[1]] = dict(name=p[1], level=int(p[2]), dir=p[3], pitch=float(p[4]))
                    self.level_layer[int(p[2])] = self.layers[p[1]]
                elif k == "B":
                    self.blockages.append(tuple(float(v) for v in p[1:5]))
                elif k == "D":
                    self.die = tuple(float(v) for v in p[1:5])
                elif k == "C":
                    self.core = tuple(float(v) for v in p[1:5])
                elif k == "H":
                    self.stage, self.ninst, self.big, self.top = p[1], int(p[2]), p[3] == "1", p[4] if len(p) > 4 else ""
        self.w = self.die[2] - self.die[0]
        self.h = self.die[3] - self.die[1]
        self.has_conn = bool(self.nets)
        for n in self.nets.values():
            n["drv"], n["loads"] = None, []
            for t in n["terms"]:
                if t[2] == "OUTPUT":
                    n["drv"] = t
                    if t[0] in self.insts:
                        self.insts[t[0]]["out"].append(n["name"])
                else:
                    n["loads"].append(t)
        for p in self.pins:
            n = self.nets.get(p["net"])
            if n is not None:
                n["pins"].append(p)

    def term_xy(self, t):
        if t[4]:
            x, y = t[4].split(",")
            return float(x), float(y)
        i = self.insts.get(t[0])
        return (i["x"], i["y"]) if i else (None, None)


def is_rep(inst):
    return bool(REPEATER_RE.match(inst["master"])) and not inst["block"]


def is_clock_term(d, t):
    return t[3] == "CLOCK" or bool(CLK_PIN_RE.match(t[1]))


def face_of(d, x, y):
    e = ((x - d.die[0], "W"), (d.die[2] - x, "E"), (y - d.die[1], "S"), (d.die[3] - y, "N"))
    return min(e)[1]


def result(value, threshold, flag, method, unit="", computable=True, offenders=(), **kw):
    r = dict(value=value, threshold=threshold, flag=bool(flag), unit=unit, computable=computable, method=method,
             offenders=list(offenders)[:TOP])
    r.update(kw)
    return r


def not_computable(reason, threshold=None, **kw):
    return result(None, threshold, False, reason, computable=False, **kw)


# ----- connectivity helpers

def forward_leaves(d, net_name, clock=None):
    """non-repeater loads and out pins reached from a net through buffers / inverters: [(kind, name, x, y)]"""
    out, stack, seen = [], [net_name], set()
    while stack:
        nn = stack.pop()
        if nn in seen:
            continue
        seen.add(nn)
        n = d.nets.get(nn)
        if n is None:
            continue
        for p in n["pins"]:
            if p["io"] == "OUTPUT":
                out.append(("pin", p["name"], p["x"], p["y"]))
        for t in n["loads"]:
            i = d.insts.get(t[0])
            if i is None:
                continue
            if is_rep(i) and i["out"]:
                stack.extend(i["out"])
            else:
                x, y = d.term_xy(t)
                out.append(("cell", i["name"], x, y))
    return out, seen


def backward_root(d, net_name):
    """the first non-repeater driver of a net: (kind, name, x, y), through buffers / inverters"""
    seen = set()
    nn = net_name
    while nn not in seen:
        seen.add(nn)
        n = d.nets.get(nn)
        if n is None:
            return None
        ins = [p for p in n["pins"] if p["io"] == "INPUT"]
        if ins:
            return ("pin", ins[0]["name"], ins[0]["x"], ins[0]["y"])
        t = n["drv"]
        if t is None:
            return None
        i = d.insts.get(t[0])
        if i is None:
            return None
        if is_rep(i):
            inp = [m for m in d.nets_of_inst.get(t[0], ()) if m != nn]
            if not inp:
                return None
            nn = inp[0]
            continue
        x, y = d.term_xy(t)
        return ("cell", i["name"], x, y)
    return None


def index_inputs(d):
    """inst id -> nets on its input pins (repeaters have one)"""
    d.nets_of_inst = defaultdict(list)
    for n in d.nets.values():
        for t in n["loads"]:
            d.nets_of_inst[t[0]].append(n["name"])


def clock_network(d):
    """Walk the clock from its entry pins.  Entry = a block input pin of sigtype CLOCK, or one whose net reaches a clock pin
    (LEF USE CLOCK or a CLK-like name) through buffers only.  Returns roots: [{pin, sinks, parent, plen, depth}]"""
    roots = []
    for p in d.pins:
        if p["io"] != "INPUT":
            continue
        is_clk = p["sig"] == "CLOCK"
        if not is_clk:
            n0, seen = [p["net"]], set()
            while n0 and not is_clk:
                nn = n0.pop()
                if nn in seen:
                    continue
                seen.add(nn)
                n = d.nets.get(nn)
                if n is None:
                    continue
                for t in n["loads"]:
                    i = d.insts.get(t[0])
                    if i is None:
                        continue
                    if is_rep(i):
                        n0.extend(i["out"])
                    elif (SEQ_RE.match(i["master"]) or i["block"]) and is_clock_term(d, t):
                        is_clk = True
                        break
        if not is_clk:
            continue
        # tree walk: node = instance id; parent, wire+cell path length (Manhattan pin to pin) and depth from the entry
        parent, plen, depth, sinks, cell_nets = {}, {}, {}, [], set()
        stack = [(p["net"], None, p["x"], p["y"], 0.0, 0)]
        guard = 0
        while stack and guard < 4000000:
            guard += 1
            nn, par, xd, yd, l0, dp = stack.pop()
            if nn in cell_nets:
                continue
            cell_nets.add(nn)
            n = d.nets.get(nn)
            if n is None:
                continue
            for t in n["loads"]:
                i = d.insts.get(t[0])
                if i is None or t[0] in parent:
                    continue
                x, y = d.term_xy(t)
                l1 = l0 + abs(x - xd) + abs(y - yd)
                seq = bool(SEQ_RE.match(i["master"])) and not ICG_RE.match(i["master"])
                if (seq or i["block"]):
                    if is_clock_term(d, t):
                        parent[t[0]], plen[t[0]], depth[t[0]] = par, l1, dp + 1
                        sinks.append(t[0])
                    continue
                if ICG_RE.match(i["master"]) and not is_clock_term(d, t):
                    continue     # enable pin
                parent[t[0]], plen[t[0]], depth[t[0]] = par, l1, dp + 1
                for o in i["out"]:
                    stack.append((o, t[0], i["x"], i["y"], l1, dp + 1))
        if sinks:
            roots.append(dict(pin=p, sinks=sinks, parent=parent, plen=plen, depth=depth, nets=cell_nets))
    return roots


# ----- the six checks

def check_opposite(d, clk_nets):
    th = TH["opposite_face_ratio"]
    if not d.pins:
        return result(None, th, False, "no signal pins", unit="pins")
    if not d.has_conn:
        return not_computable("no connectivity in the dump (big DB)", th)
    rows, n_seen = [], 0
    for p in d.pins:
        if p["net"] in clk_nets:
            continue
        if p["io"] == "INPUT":
            leaves, _ = forward_leaves(d, p["net"])
            leaves = [l for l in leaves if l[2] is not None and not (l[0] == "pin" and l[1] == p["name"])]
        else:
            r = backward_root(d, p["net"])
            leaves = [r] if r and r[2] is not None else []
        if not leaves:
            continue
        n_seen += 1
        cx = sum(l[2] for l in leaves) / len(leaves)
        cy = sum(l[3] for l in leaves) / len(leaves)
        f = face_of(d, p["x"], p["y"])
        ratio = abs(cx - p["x"]) / d.w if f in "WE" else abs(cy - p["y"]) / d.h
        if ratio > th:
            rows.append(dict(pin=p["name"], face=f, x=rnd(p["x"]), y=rnd(p["y"]), partner_x=rnd(cx), partner_y=rnd(cy),
                             partner=leaves[0][1], ratio=rnd(ratio), io=p["io"]))
    rows.sort(key=lambda r: -r["ratio"])
    groups = defaultdict(int)
    for r in rows:
        groups[re.sub(r"\[\d+\]|_\d+_?$", "", r["pin"])] += 1
    return result(len(rows), th, bool(rows), "pin centre vs centroid of first non-buffer sinks (input) / first non-buffer driver "
                  "(output), across the pin's face axis; ratio > threshold counted", unit="pins",
                  worst_ratio=rows[0]["ratio"] if rows else 0.0, pins_checked=n_seen, offenders=rows,
                  bus_groups=sorted(([k, v] for k, v in groups.items()), key=lambda kv: -kv[1])[:10])


def check_pin_tracks(d):
    th = TH["pin_track_use"]
    win = TH["pin_window_um"]
    if not d.pins:
        return result(None, th, False, "no signal pins", unit="fraction of tracks")
    by = defaultdict(list)
    for p in d.pins:
        f = face_of(d, p["x"], p["y"])
        by[(f, p["layer"])].append(p["y"] if f in "WE" else p["x"])
    rows, unknown = [], set()
    for (f, ly), cs in by.items():
        L = d.layers.get(ly)
        if not L or L["pitch"] <= 0:
            unknown.add(ly)
            continue
        cs.sort()
        tracks = win / L["pitch"]
        j, best = 0, []
        for i, c in enumerate(cs):
            while c - cs[j] > win:
                j += 1
            best.append((i - j + 1, cs[j], c))
        # worst windows on this face, not overlapping
        best.sort(key=lambda b: -b[0])
        taken = []
        for cnt, a, b in best:
            if any(a < t[1] and b > t[0] for t in taken):
                continue
            taken.append((a, b))
            mid = (a + b) / 2
            x, y = {"W": (d.die[0], mid), "E": (d.die[2], mid), "S": (mid, d.die[1]), "N": (mid, d.die[3])}[f]
            rows.append(dict(face=f, layer=ly, x=rnd(x), y=rnd(y), pins=cnt, tracks=rnd(tracks, 1), use=rnd(cnt / tracks), from_um=rnd(a), to_um=rnd(b)))
            if len(taken) >= 5:
                break
    rows.sort(key=lambda r: -r["use"])
    val = rows[0]["use"] if rows else None
    return result(val, th, val is not None and val > th, "pins of one face + layer in the worst sliding 20-um window / (20 um / layer pitch); "
                  "layer pitch from LEF, track-pattern offset and blocked tracks ignored", unit="fraction of tracks", offenders=rows,
                  **({"unknown_layers": sorted(unknown)} if unknown else {}))


def find_channels(d):
    """gaps between facing macros, and between a macro and the die edge, with no other macro in between.
    One channel = rectangle (x0,y0,x1,y1), 'along' = 'V' when wires run vertically through it (gap measured in x)."""
    if not d.macros:
        return []
    ms = d.macros
    mg = TH["channel_max_gap_um"]
    out, seen = [], set()

    def add(a, b, x0, y0, x1, y1, along):
        k = (rnd(x0, 2), rnd(y0, 2), rnd(x1, 2), rnd(y1, 2), along)
        if k in seen:
            return
        seen.add(k)
        top = max(a["top"], b["top"]) if b else a["top"]
        out.append(dict(a=a["name"], b=b["name"] if b else "die edge", x0=x0, y0=y0, x1=x1, y1=y1, along=along, top=top))

    for a in ms:
        ax0, ay0, ax1, ay1 = a["box"]
        # east gap (vertical channel): nearest macro to the east overlapping in y, else the die edge
        best = None
        for b in ms:
            if b is a:
                continue
            bx0, by0, bx1, by1 = b["box"]
            if bx0 >= ax1 and min(ay1, by1) > max(ay0, by0) and (best is None or bx0 < best["box"][0]):
                best = b
        if best is not None:
            g = best["box"][0] - ax1
            if 0 < g <= mg:
                add(a, best, ax1, max(ay0, best["box"][1]), best["box"][0], min(ay1, best["box"][3]), "V")
        else:
            g = d.die[2] - ax1
            if 0 < g <= mg:
                add(a, None, ax1, ay0, d.die[2], ay1, "V")
        # also the west edge
        if not any(b is not a and b["box"][2] <= ax0 and min(ay1, b["box"][3]) > max(ay0, b["box"][1]) for b in ms):
            g = ax0 - d.die[0]
            if 0 < g <= mg:
                add(a, None, d.die[0], ay0, ax0, ay1, "V")
        best = None
        for b in ms:
            if b is a:
                continue
            bx0, by0, bx1, by1 = b["box"]
            if by0 >= ay1 and min(ax1, bx1) > max(ax0, bx0) and (best is None or by0 < best["box"][1]):
                best = b
        if best is not None:
            g = best["box"][1] - ay1
            if 0 < g <= mg:
                add(a, best, max(ax0, best["box"][0]), ay1, min(ax1, best["box"][2]), best["box"][1], "H")
        else:
            g = d.die[3] - ay1
            if 0 < g <= mg:
                add(a, None, ax0, ay1, ax1, d.die[3], "H")
        if not any(b is not a and b["box"][3] <= ay0 and min(ax1, b["box"][2]) > max(ax0, b["box"][0]) for b in ms):
            g = ay0 - d.die[1]
            if 0 < g <= mg:
                add(a, None, ax0, d.die[1], ax1, ay0, "H")
    out.sort(key=lambda c: (c["x1"] - c["x0"]) if c["along"] == "V" else (c["y1"] - c["y0"]))
    return out[:MAX_CHANNELS]


def channel_capacity(d, c):
    """tracks through the channel on layers the macro blocks (obstruction top level), running along the channel; M1 excluded"""
    want = "VERTICAL" if c["along"] == "V" else "HORIZONTAL"
    g = (c["x1"] - c["x0"]) if c["along"] == "V" else (c["y1"] - c["y0"])
    cap, levels = 0.0, []
    for lv, L in d.level_layer.items():
        if 2 <= lv <= (c["top"] or 0) and L["dir"] == want and L["pitch"] > 0:
            cap += g / L["pitch"]
            levels.append(lv)
    return cap, set(levels), g


def net_bboxes(d, skip):
    out = []
    for n in d.nets.values():
        if n["name"] in skip:
            continue
        xs, ys = [p["x"] for p in n["pins"]], [p["y"] for p in n["pins"]]
        for t in n["terms"]:
            x, y = d.term_xy(t)
            if x is not None:
                xs.append(x)
                ys.append(y)
        if len(xs) >= 2:
            out.append((min(xs), min(ys), max(xs), max(ys), n["name"]))
    return out


def check_channels(d, clk_nets):
    th = TH["channel_use"]
    if not d.macros:
        return result(None, th, False, "no macros, no channels", unit="nets per track")
    if not d.has_conn:
        return not_computable("no connectivity in the dump (big DB)", th)
    chans = find_channels(d)
    if not chans:
        return result(None, th, False, "no macro gap of 0 < gap <= %g um" % TH["channel_max_gap_um"], unit="nets per track")
    if max(c["top"] for c in chans) < 2:
        return not_computable("macro LEF has no routing-layer obstructions: wires may pass over it, channel capacity undefined", th)
    use_guides = any(d.guides.values())
    rows = []
    if use_guides:
        method = "GRT guides crossing the channel mid-line, distinct nets on the blocked layers running along the channel"
        tile = 20.0
        idx = defaultdict(list)
        for nn, gs in d.guides.items():
            for g in gs:
                for ix in range(int(g[1] // tile), int(g[3] // tile) + 1):
                    for iy in range(int(g[2] // tile), int(g[4] // tile) + 1):
                        idx[(ix, iy)].append((nn, g))
        for c in chans:
            cap, lv, gap = channel_capacity(d, c)
            if c["along"] == "V":
                ym = (c["y0"] + c["y1"]) / 2
                r = (c["x0"], ym, c["x1"], ym)
            else:
                xm = (c["x0"] + c["x1"]) / 2
                r = (xm, c["y0"], xm, c["y1"])
            nets = set()
            for ix in range(int(r[0] // tile), int(r[2] // tile) + 1):
                for iy in range(int(r[1] // tile), int(r[3] // tile) + 1):
                    for nn, g in idx.get((ix, iy), ()):
                        if g[0] not in lv:
                            continue
                        if c["along"] == "V":
                            if g[2] <= r[1] <= g[4] and g[3] > r[0] and g[1] < r[2]:
                                nets.add((nn, g[0]))
                        elif g[1] <= r[0] <= g[3] and g[4] > r[1] and g[2] < r[3]:
                            nets.add((nn, g[0]))
            rows.append((c, cap, gap, float(len(nets))))
    else:
        method = ("no guides at this stage: ESTIMATE, each net's pin bounding box crossing the channel mid-line counts by the share of "
                  "its box the channel covers; the %d narrowest channels only" % MAX_FLIGHT_CHANNELS)
        bbs = net_bboxes(d, clk_nets)
        for c in chans[:MAX_FLIGHT_CHANNELS]:
            cap, lv, gap = channel_capacity(d, c)
            dem = 0.0
            if c["along"] == "V":
                ym = (c["y0"] + c["y1"]) / 2
                for b in bbs:
                    if b[1] < ym < b[3] and b[2] > c["x0"] and b[0] < c["x1"]:
                        dem += (min(b[2], c["x1"]) - max(b[0], c["x0"])) / max(b[2] - b[0], gap)
            else:
                xm = (c["x0"] + c["x1"]) / 2
                for b in bbs:
                    if b[0] < xm < b[2] and b[3] > c["y0"] and b[1] < c["y1"]:
                        dem += (min(b[3], c["y1"]) - max(b[1], c["y0"])) / max(b[3] - b[1], gap)
            rows.append((c, cap, gap, dem))
    off = []
    for c, cap, gap, dem in rows:
        use = dem / cap if cap > 0 else (float("inf") if dem else 0.0)
        off.append(dict(a=c["a"], b=c["b"], x=rnd((c["x0"] + c["x1"]) / 2), y=rnd((c["y0"] + c["y1"]) / 2), along=c["along"], gap_um=rnd(gap),
                        length_um=rnd((c["y1"] - c["y0"]) if c["along"] == "V" else (c["x1"] - c["x0"])), tracks=rnd(cap, 1), nets=rnd(dem, 1),
                        use=None if use == float("inf") else rnd(use), no_tracks=cap <= 0))
    off.sort(key=lambda o: -(o["use"] if o["use"] is not None else 1e9))
    worst = off[0]["use"] if off else None
    flag = any((o["use"] is None or o["use"] > th) for o in off)
    return result(worst, th, flag, method + "; capacity = gap / pitch on blocked layers >= M2, per-layer GRT adjustment ignored", unit="nets per track",
                  channels=len(off), offenders=off, source="grt_guides" if use_guides else "flight_bbox_estimate")


def check_clock(d, roots):
    th_e = TH["clock_entry_ratio"]
    out = dict(entry=None, divergence=None, over_macro=None)
    if not d.has_conn:
        return not_computable("no connectivity in the dump (big DB)", dict(entry_ratio=th_e), **out)
    if not roots:
        return not_computable("no clock entry pin found: no input pin of sigtype CLOCK or with a net reaching a CLK pin through buffers", dict(entry_ratio=th_e), **out)
    # 4a entry to sink centroid, biggest clock first
    entries, flags = [], []
    for r in sorted(roots, key=lambda z: -len(z["sinks"])):
        xs = [d.insts[s]["x"] for s in r["sinks"]]
        ys = [d.insts[s]["y"] for s in r["sinks"]]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        dist = abs(cx - r["pin"]["x"]) + abs(cy - r["pin"]["y"])
        entries.append(dict(pin=r["pin"]["name"], x=rnd(r["pin"]["x"]), y=rnd(r["pin"]["y"]), centroid_x=rnd(cx), centroid_y=rnd(cy), distance_um=rnd(dist), sinks=len(xs),
                            max_depth=max(r["depth"][s] for s in r["sinks"])))
    lim = th_e * (d.w + d.h)
    e0 = entries[0]
    out["entry"] = dict(value=e0["distance_um"], threshold=rnd(lim), flag=e0["distance_um"] > lim, unit="um Manhattan", offenders=entries[:TOP],
                        method="threshold = %g x (W + H): a mid-face entry passes, a corner entry flags" % th_e)
    flags.append(out["entry"]["flag"])
    # 4b divergence of related flop pairs (launch -> combinational -> capture, walk capped)
    tree = max(roots, key=lambda z: len(z["sinks"]))
    if d.stage == "place" and max(tree["depth"].values()) <= 1:
        out["divergence"] = dict(value=None, computable=False, method="no clock tree yet at place", threshold=TH["clock_unshared_um"], flag=False)
    else:
        rows = related_divergence(d, tree)
        th = TH["clock_unshared_um"]
        out["divergence"] = dict(value=rows[0]["unshared_um"] if rows else 0.0, threshold=th, flag=bool(rows) and rows[0]["unshared_um"] > th, unit="um Manhattan pin to pin",
                                 method="flop pairs one combinational cone apart (first %d cells per launch), tree parents walked to the last common cell; pin-to-pin Manhattan, not routed length; no CPPR/delay" % RELATED_FANIN_CAP,
                                 max_unshared_levels=max((r["levels"] for r in rows), default=0), offenders=rows[:TOP])
        flags.append(out["divergence"]["flag"])
    # 4c clock guides over foreign macros
    if not d.macros:
        out["over_macro"] = dict(value=0.0, threshold=TH["clock_over_macro_um"], flag=False, method="no macros", offenders=[])
    elif not any(d.guides.get(nn) for r in roots for nn in r["nets"]):
        out["over_macro"] = dict(value=None, computable=False, flag=False, threshold=TH["clock_over_macro_um"], method="no clock guides in this ODB (no GRT yet), wire over macro unknown", offenders=[])
    else:
        rows = []
        for r in roots:
            for nn in r["nets"]:
                gs = d.guides.get(nn)
                if not gs:
                    continue
                own = {t[0] for t in d.nets[nn]["terms"]}
                for m in d.macros:
                    if m["id"] in own:
                        continue
                    b = m["box"]
                    ln = 0.0
                    for g in gs:
                        w, h = min(g[3], b[2]) - max(g[1], b[0]), min(g[4], b[3]) - max(g[2], b[1])
                        if w > 0 and h > 0:
                            ln += max(w, h)
                    if ln > 0:
                        rows.append(dict(net=nn, macro=m["name"], x=rnd(m["x"]), y=rnd(m["y"]), length_um=rnd(ln, 1)))
        rows.sort(key=lambda r: -r["length_um"])
        th = TH["clock_over_macro_um"]
        v = rows[0]["length_um"] if rows else 0.0
        out["over_macro"] = dict(value=v, threshold=th, flag=v > th, unit="um of guide per net + macro", offenders=rows[:TOP],
                                 method="clock net GRT guides clipped to macros that net has no pin on; guides, not the routed wire, also at route stage")
        flags.append(out["over_macro"]["flag"])
    val = out["entry"]["value"]
    return result(val, out["entry"]["threshold"], any(flags), "see entry, divergence, over_macro", unit="um", offenders=entries, **out)


def related_divergence(d, tree):
    """unshared clock path of launch/capture pairs; the budget caps the walk, the worst pairs first"""
    par, plen, depth = tree["parent"], tree["plen"], tree["depth"]
    sinks = set(tree["sinks"])
    best = {}
    for s in tree["sinks"]:
        i = d.insts[s]
        visited, stack, caps = set(), list(i["out"]), set()
        while stack and len(visited) < RELATED_FANIN_CAP:
            nn = stack.pop()
            if nn in visited:
                continue
            visited.add(nn)
            n = d.nets.get(nn)
            if n is None:
                continue
            for t in n["loads"]:
                c = t[0]
                if c in sinks:
                    if not is_clock_term(d, t) and c != s:
                        caps.add(c)
                    continue
                ci = d.insts.get(c)
                if ci is not None and not ci["block"]:
                    stack.extend(ci["out"])
        if not caps:
            continue
        anc = {}
        a = s
        while a is not None:
            anc[a] = True
            a = par.get(a)
        for c in caps:
            b = c
            while b is not None and b not in anc:
                b = par.get(b)
            lca_len = plen.get(b, 0.0) if b is not None else 0.0
            lca_d = depth.get(b, 0) if b is not None else 0
            un = max(plen[s] - lca_len, plen[c] - lca_len)
            key = (min(s, c), max(s, c))
            if key not in best or best[key]["unshared_um"] < un:
                best[key] = dict(launch=i["name"], capture=d.insts[c]["name"], x=rnd(i["x"]), y=rnd(i["y"]), capture_x=rnd(d.insts[c]["x"]), capture_y=rnd(d.insts[c]["y"]),
                                 unshared_um=rnd(un, 1), levels=max(depth[s], depth[c]) - lca_d, last_common=d.insts[b]["name"] if b is not None else "entry pin")
    return sorted(best.values(), key=lambda r: -r["unshared_um"])[:TOP * 3]


def check_fanout(d, clk_nets):
    th = TH["fanout_spread_um"]
    if not d.has_conn:
        return not_computable("no connectivity in the dump (big DB)", th)
    rows = []
    for n in d.nets.values():
        nn = n["name"]
        if nn in clk_nets:
            continue
        t = n["drv"]
        ins = [p for p in n["pins"] if p["io"] == "INPUT"]
        if t is not None:
            i = d.insts.get(t[0])
            if i is None or is_rep(i) or TIE_RE.match(i["master"]):
                continue     # a repeater is part of its root's tree; ties are not routed long
            xd, yd, drv = (*d.term_xy(t), i["name"])
        elif ins:
            xd, yd, drv = ins[0]["x"], ins[0]["y"], ins[0]["name"]
        else:
            continue
        leaves, _ = forward_leaves(d, nn)
        leaves = [l for l in leaves if l[2] is not None]
        if len(leaves) < 2:
            continue
        xs, ys = [l[2] for l in leaves], [l[3] for l in leaves]
        span = max(xs) - min(xs) + max(ys) - min(ys)
        if span > th:
            rows.append(dict(driver=drv, net=nn, x=rnd(xd), y=rnd(yd), fanout=len(leaves), spread_um=rnd(span, 1), bbox=[rnd(min(xs)), rnd(min(ys)), rnd(max(xs)), rnd(max(ys))]))
    rows.sort(key=lambda r: -r["spread_um"])
    return result(rows[0]["spread_um"] if rows else 0.0, th, bool(rows), "first non-buffer driver -> non-buffer sinks through buffers/inverters; spread = width + height of the sinks' box; clock excluded",
                  unit="um", count=len(rows), offenders=rows)


def check_density(d):
    th = TH["local_density"]
    bin_um = TH["density_bin_um"]
    c = d.core or d.die
    if c[2] <= c[0] or c[3] <= c[1]:
        return not_computable("empty core area", th)
    nx, ny = max(1, int(math.ceil((c[2] - c[0]) / bin_um))), max(1, int(math.ceil((c[3] - c[1]) / bin_um)))
    used = defaultdict(float)
    for i in d.insts.values():
        if i["block"] or SKIP_DENS_RE.match(i["master"]):
            continue
        b = i["box"]
        ix, iy = int((i["x"] - c[0]) // bin_um), int((i["y"] - c[1]) // bin_um)
        if 0 <= ix < nx and 0 <= iy < ny:
            used[(ix, iy)] += (b[2] - b[0]) * (b[3] - b[1])
    rows = []
    blocked = [m["box"] for m in d.macros] + d.blockages
    for (ix, iy), a in used.items():
        x0, y0 = c[0] + ix * bin_um, c[1] + iy * bin_um
        x1, y1 = min(c[2], x0 + bin_um), min(c[3], y0 + bin_um)
        area = (x1 - x0) * (y1 - y0)
        fr = area
        for b in blocked:
            w, h = min(x1, b[2]) - max(x0, b[0]), min(y1, b[3]) - max(y0, b[1])
            if w > 0 and h > 0:
                fr -= w * h
        if fr < TH["density_min_free"] * area:
            continue
        rows.append(dict(x=rnd((x0 + x1) / 2, 1), y=rnd((y0 + y1) / 2, 1), density=rnd(a / fr)))
    rows.sort(key=lambda r: -r["density"])
    v = rows[0]["density"] if rows else 0.0
    over = sum(1 for r in rows if r["density"] > th)
    return result(v, th, v > th, "cell area by cell centre / free core area (macros + hard blockages off) in %g-um bins; fillers and decaps excluded; bins under %d%% free skipped" % (bin_um, int(TH["density_min_free"] * 100)),
                  unit="fraction", bins_over=over, bins=len(rows), offenders=rows)


def congestion_summary(path, macros=(), source="routing"):
    """gui::dump_heatmap Routing CSV: x0,y0,x1,y1,value (%).  Persisted GRT data at grt AND route stage (not recomputed from the routed wires).
    Gcells under a macro read 100% (its obstructions take the capacity), so they are left out; the map itself clamps at 100%."""
    if not path or not os.path.exists(path):
        return None
    rows = []
    boxes = [m["box"] for m in macros]
    with open(path) as f:
        next(f, None)
        for ln in f:
            p = ln.split(",")
            if len(p) >= 5:
                try:
                    r = (float(p[4]), float(p[0]), float(p[1]), float(p[2]), float(p[3]))
                except ValueError:
                    continue
                cx, cy = (r[1] + r[3]) / 2, (r[2] + r[4]) / 2
                if not any(b[0] <= cx <= b[2] and b[1] <= cy <= b[3] for b in boxes):
                    rows.append(r)
    if not rows:
        return None
    rows.sort(key=lambda r: -r[0])
    top = []     # hotspots at least 20 um apart
    for r in rows:
        x, y = (r[1] + r[3]) / 2, (r[2] + r[4]) / 2
        if all(abs(x - t["x"]) + abs(y - t["y"]) >= 20 for t in top):
            top.append(dict(x=rnd(x, 2), y=rnd(y, 2), pct=rnd(r[0], 1)))
            if len(top) >= 10:
                break
    how = ("OpenROAD Routing Congestion heat map (usage/capacity clamped at 100%, GRT data stored in the ODB; same data at route stage, not the routed wires); gcells under macros left out"
           if source == "routing" else "ESTIMATE: this ODB stores no GRT usage, so OpenROAD's RUDY map (net boxes, not router usage); gcells under macros left out")
    return dict(source=source, max_pct=rnd(rows[0][0], 1), gcells_outside_macros=len(rows), over_90pct=sum(1 for r in rows if r[0] > 90), at_100pct=sum(1 for r in rows if r[0] >= 100),
                top=top, method=how)


def compute(dump_path, congestion=None, odb=None, congestion_source="routing"):
    d = Design(dump_path)
    index_inputs(d)
    roots = clock_network(d) if d.has_conn else []
    clk_nets = set()
    for r in roots:
        clk_nets |= r["nets"]
    checks = {}
    for name, fn in (("opposite_face_pins", lambda: check_opposite(d, clk_nets)), ("pin_track_use", lambda: check_pin_tracks(d)),
                     ("channel_tracks", lambda: check_channels(d, clk_nets)), ("clock", lambda: check_clock(d, roots)),
                     ("fanout_spread", lambda: check_fanout(d, clk_nets)), ("local_density", lambda: check_density(d))):
        try:
            checks[name] = fn()
        except Exception as e:     # advisory: one bad check never loses the others
            checks[name] = not_computable("check raised %s: %s" % (type(e).__name__, e))
    doc = dict(schema=SCHEMA, stage=d.stage, block=d.top, odb=odb, instances=d.ninst, macros=len(d.macros), pins=len(d.pins),
               die_um=[rnd(v) for v in d.die], big_db=d.big, advisory=True, thresholds=TH, checks=checks)
    c = congestion_summary(congestion, d.macros, congestion_source) if congestion_source != "none" else None
    if c:
        doc["grt_congestion"] = c
    doc["summary"] = one_line(doc)
    return doc


def one_line(doc):
    fl = []
    for k, c in doc["checks"].items():
        if c.get("flag"):
            v = c.get("value")
            fl.append("%s=%s" % (k, v if v is not None else "?"))
    un = [k for k, c in doc["checks"].items() if not c.get("computable", True)]
    s = "%s %d/6 flagged%s" % (doc["stage"], len(fl), ": " + " ".join(fl) if fl else "")
    if un:
        s += " | not computable: " + ",".join(un)
    if doc.get("grt_congestion"):
        g = doc["grt_congestion"]
        s += " | %s max %.0f%%, %d gcells >90%%" % ("GRT" if g["source"] == "routing" else "RUDY", g["max_pct"], g["over_90pct"])
    return s


MARK_COLOR = dict(opposite_face_pins="magenta", pin_track_use="cyan", channel_tracks="white", clock="red", fanout_spread="orange", local_density="green")
MARK_TAG = dict(opposite_face_pins="OPP", pin_track_use="PIN", channel_tracks="CH", clock="CK", fanout_spread="FO", local_density="D")


def marks(doc, per_check=5):
    """x y text colour: flagged offenders drawn on the PNGs"""
    out = []
    for k, c in doc["checks"].items():
        if not c.get("flag"):
            continue
        rows = list(c.get("offenders") or [])
        if k == "clock":
            rows = []
            for s in ("entry", "divergence", "over_macro"):
                sc = c.get(s) or {}
                if sc.get("flag"):
                    rows += [dict(r, _s=s) for r in (sc.get("offenders") or [])[:2]]
        for r in rows[:per_check]:
            if r.get("x") is None or r.get("y") is None:
                continue
            out.append("%s\t%s\t%s\t%s" % (r["x"], r["y"], MARK_TAG[k], MARK_COLOR[k]))
    for t in (doc.get("grt_congestion") or {}).get("top", [])[:3]:
        if t["pct"] >= 90:
            out.append("%s\t%s\tHOT\twhite" % (t["x"], t["y"]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--out", required=True)
    ap.add_argument("--congestion")
    ap.add_argument("--congestion-source", default="routing", choices=("routing", "rudy", "none"))
    ap.add_argument("--odb")
    ap.add_argument("--marks")
    ap.add_argument("--one")
    a = ap.parse_args(argv)
    doc = compute(a.dump, a.congestion, a.odb, a.congestion_source)
    tmp = a.out + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, a.out)
    if a.marks:
        with open(a.marks, "w") as f:
            f.write("\n".join(marks(doc)) + "\n")
    if a.one:
        with open(a.one, "w") as f:
            f.write(doc["summary"] + "\n")
    print(doc["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
