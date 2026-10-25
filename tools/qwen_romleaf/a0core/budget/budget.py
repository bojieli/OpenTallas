#!/usr/bin/env python3
"""QC a0v8 10-24: per-cut track budget of an A0 core floorplan from the synthesized netlist (no placement run).

  budget.py --netlist 1_2_yosys.v --top qfd_tile_nk_a0c --macro-pins macro_pins.json --place place.tcl \
            --regions regions.tcl --pins pins.tcl --v7pos nk.inst.tsv --label v8 --out out_prefix [--taps taps.json]

Demand: every startpoint (flop output, hard-child output pin, input port) is one logical net whose bbox is the
startpoint plus every endpoint it reaches through combinational logic (flop / hard-child input pins, output ports;
clock pins excluded).  A cut line is crossed once by every net whose bbox spans it.
Positions: sequential cells of a BOXED region group (regions tcl, first matching regex as parent_regions.tcl) at a
deterministic uniform point in the group's boxes; FREE / unclaimed sequential cells at their v7 4_cts placed site
(probe nk.inst.tsv; the A0 v7 run); hard-child pins from place.tcl origin + orientation + LEF pin offset; ports at
the pins tcl location.
Capacity (GRT-derated tracks per um, from the v7 congestion report cap histogram, as the v7 review): free H 24/0.57,
free V 27/0.57; over an LSL head H 0 (OBS M1-M6; M8 0) and V 0.68/0.064 (M7); over ROM leaf / node H and V 0.68/0.064.
"""
import argparse
import collections
import hashlib
import json
import math
import pickle
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import netgraph as NG  # noqa: E402
import regions_parse as RP  # noqa: E402

CH, CV = 24 / 0.57, 27 / 0.57
OVM = 0.68 / 0.064
TOP_Y = 653.04  # ROM leaves' top edge = start of the LSL zone


def parse_place(path):
    out = {}
    cur = None
    for l in open(path):
        m = re.search(r"ot_ref_pick \$ot_ref_by (\S+) \{(.*?)\}\]", l)
        if m:
            cur = (m.group(1), m.group(2))
            continue
        m = re.search(r"setOrient (\S+); \$i setLocation \[expr \{round\(([\d.]+) \* \$dbu\)\}\] \[expr \{round\(([\d.]+) \* \$dbu\)\}\]", l)
        if m and cur:
            out[cur[1]] = dict(master=cur[0], orient=m.group(1), x=float(m.group(2)), y=float(m.group(3)))
            cur = None
    return out


def parse_pins(path):
    out = {}
    for l in open(path):
        m = re.match(r"place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{([\d.]+) ([\d.]+)\}", l)
        if m:
            out[m.group(1)] = (float(m.group(3)), float(m.group(4)))
    return out


def h01(s):
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def in_boxes(boxes, name):
    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
    t = h01(name + "#b") * sum(areas)
    for b, a in zip(boxes, areas):
        if t <= a:
            break
        t -= a
    return (b[0] + h01(name + "#x") * (b[2] - b[0]), b[1] + h01(name + "#y") * (b[3] - b[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist"); ap.add_argument("--top"); ap.add_argument("--macro-pins")
    ap.add_argument("--place"); ap.add_argument("--regions"); ap.add_argument("--pins"); ap.add_argument("--v7pos")
    ap.add_argument("--label"); ap.add_argument("--out"); ap.add_argument("--cache")
    ap.add_argument("--point-boxes", action="store_true", help="every boxed group's cells at its box centre (cluster model)")
    ap.add_argument("--dump-ends", default="", help="regex of startpoint owners: write their endpoint centroids")
    ap.add_argument("--moves", default="", help="json: list of [regex, x, y] FREE-cell site overrides")
    a = ap.parse_args()
    mp = json.load(open(a.macro_pins))
    macro_dirs = {m: {p[0]: p[1] for p in v["pins"]} for m, v in mp.items()}
    if a.cache and Path(a.cache).exists():
        f_pins, drv, sinks, cell_out = pickle.load(open(a.cache, "rb"))
    else:
        f, drv, sinks, cell_out = NG.build(a.netlist, a.top, macro_dirs, [])
        f_pins = f.pins
        sinks = dict(sinks)
        cell_out = dict(cell_out)
        if a.cache:
            pickle.dump((f_pins, drv, sinks, cell_out), open(a.cache, "wb"))
    place = parse_place(a.place)
    pins = parse_pins(a.pins)
    groups = RP.parse(a.regions)
    v7 = {}
    for l in open(a.v7pos):
        n, m, b, x0, y0, x1, y1 = l.rstrip("\n").split("\t")
        if b == "1":
            continue
        v7[n.replace("\\", "")] = ((float(x0) + float(x1)) / 2, (float(y0) + float(y1)) / 2)
    fam = collections.defaultdict(list)
    for n, xy in v7.items():
        fam[re.sub(r"\$.*", "", re.sub(r"\[\d+\]", "[]", n))].append(xy)
    famc = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in fam.items()}
    moves = [(re.compile(r), x, y) for r, x, y in (json.loads(a.moves) if a.moves else [])]
    # hard children: rect + pin transform
    mrect = []
    minst = {}
    for pat, p in place.items():
        w, h = mp[p["master"]]["w"], mp[p["master"]]["h"]
        mrect.append((p["master"], p["x"], p["y"], p["x"] + w, p["y"] + h))
        minst[pat] = (p, w, h)

    def macro_pin_xy(owner, master, pin):
        key = owner.replace("\\", "")
        key = re.sub(r"^u_ot_pr_core\.", "", key)
        p, w, h = minst[key]
        pp = PINIDX[master].get(pin)
        if pp is None:
            return None
        px, py = pp
        if p["orient"] == "MY":
            px = w - px
        elif p["orient"] != "R0":
            raise SystemExit("orient " + p["orient"])
        return (p["x"] + px, p["y"] + py)

    PINIDX = {m: {q[0]: (q[3], q[4]) for q in v["pins"]} for m, v in mp.items()}
    gcount = collections.Counter()
    seqpos = {}
    missing = collections.Counter()

    def seq_xy(name):
        if name in seqpos:
            return seqpos[name]
        g = None
        for gg in groups:
            if gg["rc"].search(name):
                g = gg
                break
        gname = g["name"] if g else "-none-"
        gcount[gname] += 1
        if g and g["type"] != "FREE" and g["boxes"]:
            if a.point_boxes:
                b = max(g["boxes"], key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
                xy = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            else:
                xy = in_boxes(g["boxes"], name)
        else:
            xy = None
            for rc, x, y in moves:
                if rc.search(name):
                    xy = (x, y)
                    break
            if xy is None:
                xy = v7.get(name)
            if xy is None:
                xy = famc.get(re.sub(r"\$.*", "", re.sub(r"\[\d+\]", "[]", name)))
                if xy is not None:
                    missing["fam:" + gname] += 1
            if xy is None:
                missing[gname] += 1
        seqpos[name] = xy
        return xy

    def pos(idx):
        k, kind, owner, master, pin, d = f_pins[idx]
        if kind == "seq":
            return seq_xy(owner.replace("\\", ""))
        if kind == "macro":
            return macro_pin_xy(owner, master, pin)
        if kind == "port":
            return pins.get(owner) or pins.get(owner.split("[")[0])
        return None

    res = {}

    def run():
        res["bb"] = NG.endpoints_bbox(_F(f_pins), drv, sinks, cell_out, pos)

    threading.stack_size(1 << 29)
    sys.setrecursionlimit(2000000)
    t = threading.Thread(target=run)
    t.start(); t.join()
    nets = []
    for d, bb in res["bb"].items():
        if bb[4] == 0:
            continue
        p = pos(d)
        if p is None:
            continue
        k, kind, owner, master, pin, dd = f_pins[d]
        if kind == "port" and owner.startswith("ck"):
            continue
        x0, y0, x1, y1 = min(bb[0], p[0]), min(bb[1], p[1]), max(bb[2], p[0]), max(bb[3], p[1])
        far = max(bb[5] - (p[0] + p[1]), bb[6] - (p[0] - p[1]), bb[7] - (-p[0] + p[1]), bb[8] - (-p[0] - p[1]))
        nets.append((x0, y0, x1, y1, owner, round(far, 1), p))
    print(a.label, "startpoints with endpoints", len(nets), "groups", dict(gcount), "missing pos", dict(missing))

    def capH(c, ylo, yhi):
        tot = 0.0
        y = ylo
        while y < yhi:
            k = None
            for m, x0, y0, x1, y1 in mrect:
                if x0 <= c < x1 and y0 <= y < y1:
                    k = m
            tot += 0.5 * ((0.0 if "lsl" in k else OVM) if k else CH)
            y += 0.5
        return tot

    def capV(c, xlo, xhi):
        tot = 0.0
        x = xlo
        while x < xhi:
            k = None
            for m, x0, y0, x1, y1 in mrect:
                if x0 <= x < x1 and y0 <= c < y1:
                    k = m
            tot += 0.5 * (OVM if k else CV)
            x += 0.5
        return tot

    import numpy as np
    X0 = np.array([n[0] for n in nets]); Y0 = np.array([n[1] for n in nets])
    X1 = np.array([n[2] for n in nets]); Y1 = np.array([n[3] for n in nets])
    W, H = 457.92, 1157.76
    out = dict(label=a.label, nets=len(nets), groups=dict(gcount), vcuts=[], hcuts=[], hcuts_e=[], hcuts_w=[])
    top = Y0 >= TOP_Y - 5
    for c in np.arange(20, 450, 2.5):
        dem = int(((X0 < c) & (X1 > c) & top).sum())
        dl = int(((X0 < c) & (X1 > c) & (Y1 > TOP_Y)).sum())
        out["vcuts"].append([float(c), dem, dl, round(capH(c, TOP_Y, H - 2.16))])
    for c in np.arange(TOP_Y - 30, H - 10, 2.5):
        dem = int(((Y0 < c) & (Y1 > c)).sum())
        out["hcuts"].append([float(c), dem, round(capV(c, 2.16, W - 2.16))])
        de = int(((Y0 < c) & (Y1 > c) & (X0 >= 195)).sum())
        out["hcuts_e"].append([float(c), de, round(capV(c, 195.0, W - 2.16))])
        dw = int(((Y0 < c) & (Y1 > c) & (X1 <= 205)).sum())
        out["hcuts_w"].append([float(c), dw, round(capV(c, 2.16, 205.0))])
    # named column summaries
    cols = dict(W_col=(100.656, 200.448), M_col=(200.448, 300.24), gap=(300.24, 335.664), E_col=(335.664, 435.456),
                node_col=(22.464, 69.984), Wchan=(69.984, 100.656), Echan=(435.456, 455.0))
    summ = {}
    for nm, (lo, hi) in cols.items():
        rows = [r for r in out["vcuts"] if lo + 2 <= r[0] <= hi - 2]
        if rows:
            w = max(rows, key=lambda r: r[1] / max(r[3], 1))
            wl = max(rows, key=lambda r: r[2] / max(r[3], 1))
            summ[nm] = dict(x=w[0], demand=w[1], cap=w[3], ratio=round(w[1] / max(w[3], 1), 3),
                            x_loose=wl[0], demand_loose=wl[2], ratio_loose=round(wl[2] / max(wl[3], 1), 3))
    for nm, key in (("H_full", "hcuts"), ("H_east", "hcuts_e"), ("H_west", "hcuts_w")):
        for zn, (lo, hi) in dict(band=(TOP_Y - 5, 676), row01=(812, 836), row12=(972, 997),
                                 row0=(676, 812), row1=(836, 972), row2=(997, 1137)).items():
            rows = [r for r in out[key] if lo <= r[0] <= hi]
            if rows:
                w = max(rows, key=lambda r: r[1] / max(r[2], 1))
                summ[f"{nm}.{zn}"] = dict(y=w[0], demand=w[1], cap=w[2], ratio=round(w[1] / max(w[2], 1), 3))
    # register -> register hop length (start -> farthest endpoint, Manhattan) per startpoint class in the LSL zone
    hop = collections.defaultdict(list)
    for x0, y0, x1, y1, o, far, p in nets:
        if y1 < TOP_Y:
            continue
        hop[HCLS(o)].append(far)
    hs = {}
    for k, v in hop.items():
        v.sort()
        hs[k] = dict(n=len(v), p50=v[len(v) // 2], p99=v[int(len(v) * 0.99)], max=v[-1], over405=sum(1 for d in v if d > 405))
    out["hops"] = hs
    for k in sorted(hs, key=lambda k: -hs[k]["max"])[:14]:
        print("  hop", k, hs[k])
    out["summary"] = summ
    for k, v in summ.items():
        print(f"  {k:14s} {v}")
    json.dump(out, open(a.out + ".json", "w"), indent=1)
    pickle.dump(nets, open(a.out + ".nets.pkl", "wb"))
    # clock sinks: every sequential cell (its site) + every hard child's clock pin
    ck = [(n, xy) for n, xy in seqpos.items() if xy is not None]
    for pat, (p, w, h) in minst.items():
        xy = macro_pin_xy("u_ot_pr_core." + pat, p["master"], "clk")
        ck.append((pat + "/clk", xy))
    pickle.dump(ck, open(a.out + ".sinks.pkl", "wb"))
    if a.dump_ends:
        rx = re.compile(a.dump_ends)
        net_of = {d: r for r, d in drv.items()}
        dump = {}
        for d in res["bb"]:
            k, kind, owner, master, pin, dd = f_pins[d]
            if kind == "comb" or not rx.search(owner.replace("\\", "")):
                continue
            stack = [net_of[d]]; seen = set(stack); pts = []
            while stack:
                r = stack.pop()
                for s_ in sinks.get(r, ()):
                    kk, kd, ow, ms, pn, di = f_pins[s_]
                    if kd == "comb":
                        for o in cell_out[ow]:
                            if o not in seen:
                                seen.add(o); stack.append(o)
                    elif pn not in NG.CLK_PINS:
                        q = pos(s_)
                        if q:
                            pts.append(q)
            if pts:
                dump[owner.replace("\\", "")] = [sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts), len(pts),
                                                  pos(d)]
        json.dump(dump, open(a.out + ".ends.json", "w"), indent=0)


def HCLS(n):
    n = n.replace("\\", "")
    n = re.sub(r"^u_ot_pr_core\.u_g\.u_tile\.u_tile\.u_logic\.", "", n)
    m = re.search(r"g_sl\[(\d)\]\.g_hd\.(g_tx9\.(u_qlw2[we]|u_qlr2[cwe]|tc|g_r\[\d\]\.u_tx)|g_out9\.(u_qlw3|u_qlr3)|g_lrr|u_lh)", n)
    if m:
        return "head%s.%s" % (m.group(1), (m.group(3) or m.group(4) or m.group(2)).split(".")[0].replace("g_r[1]", "rung1"))
    if "g_l2c.u_qlw2c" in n:
        return "l2c"
    if re.match(r"_\d+_$", n):
        return "anon"
    n = re.sub(r"\[\d+\]", "[]", n)
    n = re.sub(r"\$.*", "", n)
    return ".".join(n.split(".")[:3])


class _F:
    def __init__(self, pins):
        self.pins = pins


if __name__ == "__main__":
    main()
