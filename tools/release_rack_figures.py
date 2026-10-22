#!/usr/bin/env python3
"""Figures for docs/RELEASE_RACK.md: reads results/arch/release_rack_1021/rack.json (tools/release_rack_design.py)
and writes standalone SVGs to results/arch/release_rack_1021/figures/:

  tray_<sys>.svg       one tray board: quads (TP groups), mesh traces, stage traces, rear cable cages
  elevation_<sys>.svg  rack elevation, trays in folded serpentine pipeline order, power shelves, spare slots
  options.svg          OPTION D vs OPTION S: cables, switch chips, latency per crossing, wall power
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import release_rack_design as R  # noqa: E402

REC = R.OUT / "rack.json"
FIG = R.OUT / "figures"
INK, MUTED, RULE, SURF = "#0b0b0b", "#52514e", "#d6d4ce", "#fcfcfb"
LEGEND = {"S81": [("stage", "stage TP4 group"), ("copyB", "copy-B group"), ("head", "head group"), ("power", "power shelf")],
          "Qwen-ROM": [("compute", "one Qwen ROM system (2 OU)"), ("power", "power shelf")],
          "HBM-DS": [("hbm", "HBM die quad (4 dies, 8 stacks)"), ("power", "power shelf")],
          "HBM-Qwen": [("hbm", "one HBM Qwen system (1 OU)"), ("power", "power shelf")]}
KIND = {"stage": "#2a78d6", "copyB": "#eb6834", "head": "#6250d6", "compute": "#2a78d6", "kv": "#1baf7a",
        "hbm": "#1baf7a", "spare": "#ffffff", "power": "#eda100", "mgmt": "#a7a59d"}
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"


def T(x, y, s, size=11, fill=INK, anchor="start", weight=400):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(s))}</text>')


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">'
            f'<title>{html.escape(title)}</title><rect width="{w}" height="{h}" fill="{SURF}"/>' + "".join(body) + "</svg>\n")


def kind_of(uid):
    return {"H": "head", "B": "copyB", "S": "stage", "P": "compute", "K": "kv", "D": "hbm", "p": "hbm"}.get(uid[0], "stage")


def tray_fig(sysrec):
    t = sysrec["trays"]["rows"][1] if len(sysrec["trays"]["rows"]) > 1 else sysrec["trays"]["rows"][0]
    sc = 0.9
    W, H = 533 * sc + 220, 800 * sc + 80
    ox, oy = 20, 40
    b = [T(ox, 22, f"{sysrec['title']}: tray {t['tray']} board (1 OU, 533 x 800 mm, top view, front at bottom)", 13, weight=600)]
    b.append(f'<rect x="{ox}" y="{oy}" width="{533*sc}" height="{800*sc}" fill="none" stroke="{MUTED}" stroke-width="1.5"/>')
    Y = lambda y: oy + (800 - y) * sc
    X = lambda x: ox + x * sc
    b.append(f'<rect x="{X(40)}" y="{Y(800)}" width="{453*sc}" height="{25*sc}" fill="{RULE}"/>')
    b.append(T(X(266), Y(800) + 15, "rear OSFP cages (flyover twinax to 8-lane DAC / AEC)", 10, MUTED, "middle"))
    p = R.v("pkg_pitch_mm")
    for q, uid in t["quads"].items():
        q = int(q)
        qx, qy = R.QUAD_XY[q]
        col = KIND[kind_of(uid)]
        b.append(f'<rect x="{X(qx-p*1.15)}" y="{Y(qy+p*1.15)}" width="{2.3*p*sc}" height="{2.3*p*sc}" rx="6" fill="none" '
                 f'stroke="{col}" stroke-dasharray="4 3"/>')
        pts = [R.pkg_xy(q, r) for r in range(4)]
        for i in range(4):          # mesh traces
            for j in range(i + 1, 4):
                (ax, ay), (bx, by) = pts[i], pts[j]
                b.append(f'<path d="M{X(ax)},{Y(ay)} L{X(bx)},{Y(ay)} L{X(bx)},{Y(by)}" fill="none" stroke="{col}" '
                         f'stroke-width="1.2" opacity="0.6"/>')
        for r, (x, y) in enumerate(pts):
            b.append(f'<rect x="{X(x-27.5)}" y="{Y(y+27.5)}" width="{55*sc}" height="{55*sc}" rx="4" fill="{col}" '
                     f'opacity="0.18" stroke="{col}"/>')
            b.append(T(X(x), Y(y) + 4, f"r{r}", 10, INK, "middle"))
        b.append(T(X(qx), Y(qy + p * 1.15) - 4, f"quad {q}: {uid}", 11, INK, "middle", 600))
    lx = ox + 533 * sc + 16
    notes = [f"{t['dies']} dies, {t['hbm_stacks']} HBM3E stacks", f"{t['serdes_macros']} SerDes macros",
             f"IT {t['it_w']/1000:.2f} kW, DC in {t['dc_input_w']/1000:.2f} kW",
             "TP mesh: 6 board traces a quad", "(100-170 mm, KR 28 dB budget)",
             "stage hop in tray: trace", "stage hop off tray: flyover + cable",
             "liquid cold plate per package"]
    for i, s in enumerate(notes):
        b.append(T(lx, oy + 20 + 18 * i, s, 11, MUTED))
    return svg(W, H, b, f"{sysrec['title']} tray board plan")


def elevation_fig(sysrec):
    racks = sysrec["racks"]
    nr = racks["count"]
    slots = racks["slots"]
    ou_h, rw, gap = 13, 210, 40
    tou = sysrec["trays"].get("tray_ou", 1)
    shelves = 2 * R.v("shelves_per_side")
    total_ou = R.v("orv3_usable_ou")
    W = max(640, 40 + nr * (rw + gap))
    H = 70 + total_ou * ou_h + 40
    base = 50 + total_ou * ou_h
    b = [T(20, 24, f"{sysrec['title']}: rack elevation ({nr} racks, folded serpentine pipeline order)", 13, weight=600)]
    for r in range(nr):
        x0 = 20 + r * (rw + gap)
        b.append(f'<rect x="{x0}" y="{base - total_ou*ou_h}" width="{rw}" height="{total_ou*ou_h}" fill="none" stroke="{MUTED}"/>')
        b.append(T(x0 + rw / 2, base + 18, f"R{r+1}", 12, INK, "middle", 600))
        for k in range(shelves):
            y = base - (k + 1) * ou_h
            b.append(f'<rect x="{x0+2}" y="{y+1}" width="{rw-4}" height="{ou_h-2}" fill="{KIND["power"]}" opacity="0.55"/>')
            b.append(T(x0 + 6, y + ou_h - 3, f"power shelf {'AB'[k % 2]}{k//2+1} (33 kW)", 8.5))
        used = [s[1] for s in slots if s[0] == r]
        top = max(used) + tou if used else shelves
        for k in (top, top + 1):
            y = base - (k + 1) * ou_h
            lab, col = ("spare tray slot", KIND["spare"]) if k == top else ("mgmt switch", KIND["mgmt"])
            b.append(f'<rect x="{x0+2}" y="{y+1}" width="{rw-4}" height="{ou_h-2}" fill="{col}" stroke="{MUTED}" '
                     f'stroke-dasharray="3 2" opacity="0.8"/>')
            b.append(T(x0 + 6, y + ou_h - 3, lab, 8.5, MUTED))
    for t, (r, ou) in enumerate(slots):
        x0 = 20 + r * (rw + gap)
        y = base - (ou + tou) * ou_h
        rows_ = sysrec["trays"]["rows"]
        row = rows_[t] if t < len(rows_) else rows_[0]
        q = row["quads"]
        ks = [kind_of(u) for u in q.values()]
        main = max(set(ks), key=ks.count)
        w4 = (rw - 4) / 4
        for i in range(4):
            uid = q.get(str(i), q.get(i))
            col = KIND[kind_of(uid)] if uid else "#ffffff"
            b.append(f'<rect x="{x0+2+i*w4}" y="{y+1}" width="{w4-1}" height="{tou*ou_h-2}" fill="{col}" opacity="0.75"/>')
        first = [u for u in q.values()] if len(rows_) > 1 else ["system %d" % (t + 1)]
        b.append(T(x0 + rw / 2, y + tou * ou_h - 3, f"T{t}: " + " ".join(first), 7.5, "#ffffff", "middle"))
    ly = H - 12
    for i, (k, lab) in enumerate(LEGEND[sysrec["name"]]):
        b.append(f'<rect x="{20+i*190}" y="{ly-9}" width="10" height="10" fill="{KIND[k]}"/>')
        b.append(T(34 + i * 190, ly, lab, 10, MUTED))
    return svg(W, H, b, f"{sysrec['title']} rack elevation")


def options_fig(rec):
    syss = [s for s in rec["systems"] if s["name"] != "HBM-Qwen"]     # in-package: option S does not apply
    metrics = [("cables", "off-board cables", lambda c, s: c["cables"]),
               ("switch_chips", "switch chips", lambda c, s: c["switch_chips"]),
               ("latency", "ns per crossing (worst)", lambda c, s: c["latency_ns_range"][1] if "latency_ns_range" in c else c["latency_ns"]),
               ("wall", "wall kW", None)]
    cw, ch, pad = 190, 120, 26
    W = 150 + len(metrics) * (cw + pad)
    H = 60 + len(syss) * (ch + 30)
    b = [T(20, 24, "OPTION D (direct traces + cables) vs OPTION S (static circuits through the switch)", 13, weight=600)]
    for si, s in enumerate(syss):
        y0 = 50 + si * (ch + 30)
        b.append(T(20, y0 + ch / 2, s["name"], 12, INK, "start", 600))
        for mi, (key, lab, fn) in enumerate(metrics):
            x0 = 150 + mi * (cw + pad)
            if key == "wall":
                vals = [s["power"]["wall_kw_D"], s["power"]["wall_kw_S"]]
            else:
                vals = [fn(s["compare"]["D"], s), fn(s["compare"]["S"], s)]
            mx = max(vals) or 1
            if si == 0:
                b.append(T(x0, 44, lab, 10.5, MUTED))
            for k, (o, val) in enumerate(zip("DS", vals)):
                bw = (cw - 60) * val / mx
                yy = y0 + 18 + k * 40
                b.append(f'<rect x="{x0+18}" y="{yy}" width="{max(bw,1):.1f}" height="24" rx="4" fill="{"#2a78d6" if o == "D" else "#a7a59d"}"/>')
                b.append(T(x0, yy + 16, o, 11, INK))
                b.append(T(x0 + 22 + max(bw, 1), yy + 16, f"{val:,.0f}" if val >= 10 or val == 0 else f"{val:.1f}", 10.5, INK))
    return svg(W, H, b, "Option D vs option S")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    rec = json.loads(REC.read_text())
    for s in rec["systems"]:
        n = s["name"].lower()
        if s["name"] in ("S81", "HBM-DS"):
            (FIG / f"tray_{n}.svg").write_text(tray_fig(s))
        (FIG / f"elevation_{n}.svg").write_text(elevation_fig(s))
    (FIG / "options.svg").write_text(options_fig(rec))
    print("figures ->", FIG.relative_to(ROOT))


if __name__ == "__main__":
    main()
