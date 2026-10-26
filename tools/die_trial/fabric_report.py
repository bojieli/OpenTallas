#!/usr/bin/env python3
"""Report of a die fabric run (tools/die_trial/fabric.py): GRT per layer, worst windows, measured cut crossings vs
the plan's cut models, STA summaries.

    fabric_report.py RUN_DIR PLAN.json [--bin 1000] [--out RUN_DIR/report.json]

Inputs in RUN_DIR: fabric.log (GRT tables, OT_T timings), fabric.guide (route guides), grt_congestion.rpt,
nets.tsv, sta_*.{wns,end}, drv_*.rpt.
Windows: per bin (default 1 mm) and per layer, demand = guide length along the layer direction / bin length
(= average tracks used across the bin), capacity = layer tracks across the bin; usage = demand / capacity (raw
tracks, before blockages / PG / region adjustment: the GRT 'Derated resources' column gives the derated totals).
Overflow windows: from grt_congestion.rpt (one record per congested gcell edge).
Cuts: every partition face line of the plan (the G0 cut_lines positions) and the worst G0 sweep lines: bits whose
guides cross the line, per layer, vs tracks of that layer along the line.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import g2  # noqa: E402
import schema as S  # noqa: E402

GC = 9.6     # gcell (fabric.py GC_PITCH x 15): a one-gcell box is a via stack / pin access, not a run on that layer
DIRS = {"M4": "H", "M5": "V", "M6": "H", "M7": "V", "M8": "H", "M9": "V"}


def read_guides(path):
    """yield (net, [(x0, y0, x1, y1, layer)]) in um (DBU 1000)"""
    net, boxes = None, []
    with open(path) as f:
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            if s == "(":
                boxes = []
            elif s == ")":
                yield net, boxes
            else:
                p = s.split()
                if len(p) == 1:
                    net = p[0]
                elif len(p) >= 5:
                    boxes.append((int(p[0]) / 1000, int(p[1]) / 1000, int(p[2]) / 1000, int(p[3]) / 1000, p[4]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("plan")
    ap.add_argument("--bin", type=float, default=1000.0)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    run = Path(a.run)
    P = S.Plan(S.load(a.plan))
    rep = dict(run=str(run), plan=a.plan)
    log = "".join((run / x).read_text(errors="replace") for x in ("fabric.log", "repair.log") if (run / x).exists())
    rep["grt"] = g2.parse_grt(log)
    rep["timing_s"] = {k: int(v) for k, v in re.findall(r"OT_T (\S+) (\d+) s", log)}
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", log)
    rep["peak_rss_gb"] = round(int(m.group(1)) / 1e6, 1) if m else None
    # derated resources table
    der = {}
    for L, o, d in re.findall(r"^(M\d)\s+\w+\s+(\d+)\s+(\d+)\s+[\d.]+%", log, re.M):
        der[L] = dict(original=int(o), derated=int(d))
    rep["resources"] = der
    W, H, B = P.W, P.H, a.bin
    nx, ny = int(W // B) + 1, int(H // B) + 1
    pitch = {L: P.layers[L]["pitch_um"] for L in DIRS}
    demand = defaultdict(float)          # (L, i, j) -> track-um along the layer direction
    cuts_h = sorted({round(y, 2) for n in P.parts for y in (P.rect(n)[1], P.rect(n)[3]) if 0 < y < H})
    cuts_v = sorted({round(x, 2) for n in P.parts for x in (P.rect(n)[0], P.rect(n)[2]) if 0 < x < W})
    cross = {("h", c): defaultdict(int) for c in cuts_h}
    cross.update({("v", c): defaultdict(int) for c in cuts_v})
    nets = 0
    gfile = run / "fabric.guide"
    if gfile.exists():
        for net, boxes in read_guides(gfile):
            nets += 1
            seen = set()
            for x0, y0, x1, y1, L in boxes:
                if L not in DIRS:
                    continue
                if DIRS[L] == "H":
                    yc = (y0 + y1) / 2
                    j = min(int(yc // B), ny - 1)
                    x = x0
                    while x < x1 - 1e-6:
                        i = min(int(x // B), nx - 1)
                        e = min(x1, (i + 1) * B)
                        demand[(L, i, j)] += e - x
                        x = e
                    for c in cuts_v:
                        if x0 < c < x1:
                            if ("v", c) not in seen:
                                cross[("v", c)]["_nets"] += 1
                                seen.add(("v", c))
                            if x1 - x0 > GC + 1e-3 and (("v", c), L) not in seen:
                                cross[("v", c)][L] += 1
                                seen.add((("v", c), L))
                else:
                    xc = (x0 + x1) / 2
                    i = min(int(xc // B), nx - 1)
                    y = y0
                    while y < y1 - 1e-6:
                        j = min(int(y // B), ny - 1)
                        e = min(y1, (j + 1) * B)
                        demand[(L, i, j)] += e - y
                        y = e
                    for c in cuts_h:
                        if y0 < c < y1:
                            if ("h", c) not in seen:
                                cross[("h", c)]["_nets"] += 1
                                seen.add(("h", c))
                            if y1 - y0 > GC + 1e-3 and (("h", c), L) not in seen:
                                cross[("h", c)][L] += 1
                                seen.add((("h", c), L))
    rep["guide_nets"] = nets
    # guides are gcell-wide boxes: a box covers one gcell row/column, so demand per box = 1 track
    win = []
    for (L, i, j), d in demand.items():
        cap = B / pitch[L]
        win.append(dict(layer=L, x_mm=i * B / 1000, y_mm=j * B / 1000, tracks_used=round(d / B, 1),
                        tracks=int(cap), usage=round(d / B / cap, 4)))
    win.sort(key=lambda w: -w["usage"])
    rep["worst_windows_raw"] = win[:40]
    per_layer = defaultdict(list)
    for w in win:
        per_layer[w["layer"]].append(w["usage"])
    rep["window_usage_by_layer"] = {L: dict(max=max(v), p99=sorted(v)[int(0.99 * (len(v) - 1))], n=len(v))
                                    for L, v in sorted(per_layer.items())}
    # overflow windows from the congestion report: count records per bin
    ov = defaultdict(int)
    ovl = defaultdict(int)
    crpt = run / "grt_congestion.rpt"
    if crpt.exists():
        cur_layer = None
        for ln in open(crpt, errors="replace"):
            m = re.search(r"layer\s*:\s*(M\d)", ln) or re.search(r"\bon layer (M\d)", ln)
            if m:
                cur_layer = m.group(1)
            m = re.search(r"bbox\s*=\s*\(\s*([\d.]+),\s*([\d.]+)\s*\)\s*-\s*\(\s*([\d.]+),\s*([\d.]+)", ln)
            if m:
                x0, y0, x1, y1 = map(float, m.groups())
                k = (int(((x0 + x1) / 2) // B), int(((y0 + y1) / 2) // B))
                ov[k] += 1
                ovl[cur_layer] += 1
    tot = sum(ov.values())
    rep["overflow_gcells"] = dict(total=tot, by_layer=dict(ovl),
                                  worst_bins=[dict(x_mm=k[0] * B / 1000, y_mm=k[1] * B / 1000, gcells=v,
                                                   share=round(v / tot, 4))
                                              for k, v in sorted(ov.items(), key=lambda kv: -kv[1])[:15]] if tot else [])
    # cuts: crossings vs tracks
    cl = []
    for (o, c), d in cross.items():
        span = W if o == "h" else H
        lay = ["M5", "M7", "M9"] if o == "h" else ["M4", "M6", "M8"]
        tracks = {L: int(span / pitch[L]) for L in lay}
        bits = d.get("_nets", 0)
        cl.append(dict(line=("y=" if o == "h" else "x=") + f"{c:g}", bits=bits,
                       per_layer={L: dict(bits=d.get(L, 0), tracks=tracks[L], ratio=round(d.get(L, 0) / tracks[L], 4))
                                  for L in lay},
                       ratio_all=round(bits / sum(tracks.values()), 4),
                       note="bits = nets crossing (any layer); per-layer = runs longer than one gcell across the line",
                       ratio_m89=round(d.get(lay[-1], 0) / tracks[lay[-1]], 4)))
    cl.sort(key=lambda r: -r["ratio_all"])
    rep["cuts_measured"] = cl[:20]
    # STA (OpenSTA scenes: sta_<tag>_<corner>_<max|min>.wns = slack_only, .end = worst 200k endpoints)
    sta = {}
    for f in sorted(run.glob("sta_*.wns")):
        m = re.search(r"^clk\s+(-?[\d.]+)", f.read_text(), re.M)
        ent = dict(worst_ps=float(m.group(1)) if m else None)
        e = f.with_suffix(".end")
        if e.exists():
            t = e.read_text()
            sl = [float(x) for x in re.findall(r"(-?[\d.]+) \(VIOLATED\)", t)]
            ent["violating_listed"] = len(sl)
            ent["listed"] = len(re.findall(r"\((?:VIOLATED|MET)\)", t))
            if sl:
                ent["tns_listed_ps"] = round(sum(sl), 1)
                for thr in (-50, -100, -200, -400):
                    ent[f"viol_below_{-thr}ps"] = sum(1 for x in sl if x < thr)
        sta[f.stem] = ent
    for f in sorted(run.glob("tns_*.rpt")):
        sta[f.stem] = {k: float(v) for k, v in re.findall(r"tns (max|min) (-?[\d.]+)", f.read_text())}
    rep["viol_counts"] = {k: dict(max=int(a_), min=int(b_)) for k, a_, b_ in re.findall(r"OT_VIOL (\S+) max (\d+) min (\d+)", log)}
    rep["sta"] = sta
    for f in sorted(run.glob("drv_*.rpt")):
        t = f.read_text()
        rep.setdefault("drv", {})[f.stem] = dict(slew=len(re.findall(r"\(VIOLATED\)", t)))
    out = Path(a.out) if a.out else run / "report.json"
    out.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("grt", "timing_s", "peak_rss_gb", "overflow_gcells", "sta", "viol_counts")}, indent=1)[:6000])
    print("worst cut", json.dumps(cl[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
