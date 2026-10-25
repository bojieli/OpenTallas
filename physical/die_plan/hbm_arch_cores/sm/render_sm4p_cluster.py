#!/usr/bin/env python3
"""PATH-HBM-SM 10-25: render + geometry audit of the hnx-sm4p cluster halves (children from the half spec @4d6f5439dc,
child outlines = as-built LEF SIZE, child pins = the kit pin tables snapped to the plan lattice)."""
import json, re, sys, collections
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

D = Path(sys.argv[1]); OUT = Path(sys.argv[2])
VIEW2TOP = {"hnx_xs3": "hnx_xs3", "ot_hbm_accel_smh_bdc": "ot_hbm_accel_smh_bdc", "ot_hbm_accel_smh_tct": "ot_hbm_accel_smh_tct",
            "ot_hbm_accel_smh_tcl": "ot_hbm_accel_smh_tcl", "ot_smh_tr_group_beat_e": "ot_smh_tr_group_beat_e",
            "ot_smh_tr_group_land": "ot_smh_tr_group_land", "ot_smh_tr_group_row_w": "ot_smh_tr_group_row_w",
            "ot_smh_tr_group_row_e": "ot_smh_tr_group_row_e"}
COL = {"hnx_xs3": "#7fa7d9", "ot_hbm_accel_smh_bdc": "#e3a35b", "ot_hbm_accel_smh_tct": "#b58fd1", "ot_hbm_accel_smh_tcl": "#8cc68c",
       "ot_smh_tr_group_beat_e": "#d98080", "ot_smh_tr_group_land": "#d9c46a", "ot_smh_tr_group_row_w": "#6ac4c4",
       "ot_smh_tr_group_row_e": "#c48a6a"}
SHORT = {"hnx_xs3": "xs3n", "ot_hbm_accel_smh_bdc": "bdc", "ot_hbm_accel_smh_tct": "tct", "ot_hbm_accel_smh_tcl": "tcl",
         "ot_smh_tr_group_beat_e": "beat_e", "ot_smh_tr_group_land": "land", "ot_smh_tr_group_row_w": "row_w",
         "ot_smh_tr_group_row_e": "row_e"}
views = {}
for f in D.glob("views_*.json"):
    v = json.load(open(f))["view_list"][0]
    pins = json.load(open(D / Path(v["pins_file"]).name))
    views[v["module"]] = dict(w=v["outline_um"][0], h=v["outline_um"][1], pins=pins)


def face(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def half_pins(tcl):
    out = []
    for m in re.finditer(r"place_pin -pin_name \{([^}]+)\} -layer (\w+) -location \{([-0-9.]+) ([-0-9.]+)\}", tcl):
        out.append((m.group(1), float(m.group(3)), float(m.group(4))))
    return out


def stations(tcl):
    return [(m.group(1), float(m.group(2)), float(m.group(3))) for m in
            re.finditer(r"^st_group (\S+) \{.*\} ([0-9.]+) ([0-9.]+) \d+", tcl, re.M)]


rep = {}
fig, axes = plt.subplots(1, 2, figsize=(15, 15), gridspec_kw=dict(width_ratios=[1, 1]))
for ax, h_ in zip(axes, "ns"):
    S = json.load(open(D / f"half_{h_}.json"))
    W, H = S["outline"]["w"], S["outline"]["h"]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec="k"))
    rects, issues = [], []
    for c in S["children"]:
        mod = Path(c["view"]).name
        v = views[mod]
        x, y = c["at"]; w, h = v["w"], v["h"]
        rects.append((c["inst"], mod, x, y, w, h, c["orient"]))
        for q, nm in ((x, "x"), (y, "y")):
            if abs(q / 43.2 - round(q / 43.2)) > 1e-6:
                issues.append(f"{c['inst']} {nm}={q} off 43.2 lattice")
        ax.add_patch(Rectangle((x, y), w, h, fc=COL[mod], ec="k", lw=0.8, alpha=0.85))
        ax.text(x + w / 2, y + h / 2, f"{SHORT[mod]}\n{c['inst'].split('.')[-2] if '.' in c['inst'] else c['inst']}{' MX' if c['orient'] == 'MX' else ''}",
                ha="center", va="center", fontsize=6.5)
        # child pins after orientation
        fc = collections.Counter()
        for p in v["pins"]:
            px, py = p["x"], p["y"]
            if c["orient"] == "MX":
                py = h - py
            fc[face(px, py, w, h)] += 1
            ax.plot([x + px], [y + py], ",", color="k")
        for f_, n in fc.items():
            lw = 1 + 3 * n / max(fc.values())
            seg = {"N": ([x, x + w], [y + h, y + h]), "S": ([x, x + w], [y, y]), "W": ([x, x], [y, y + h]), "E": ([x + w, x + w], [y, y + h])}[f_]
            ax.plot(*seg, color="#c00000", lw=lw, alpha=0.6)
    # halos / overlaps
    gaps = []
    for i, a in enumerate(rects):
        _, _, ax0, ay0, aw, ah, _ = a
        for edge, g in (("W", ax0), ("S", ay0), ("E", W - ax0 - aw), ("N", H - ay0 - ah)):
            gaps.append((g, f"{a[0]} to tile {edge}"))
        for b in rects[i + 1:]:
            _, _, bx0, by0, bw, bh, _ = b
            dx = max(bx0 - (ax0 + aw), ax0 - (bx0 + bw))
            dy = max(by0 - (ay0 + ah), ay0 - (by0 + bh))
            if dx < 0 and dy < 0:
                issues.append(f"OVERLAP {a[0]} / {b[0]}")
            gaps.append((max(dx, dy), f"{a[0]} / {b[0]}"))
    gmin = min(gaps)
    hard = sum(r[4] * r[5] for r in rects)
    # half pins per face + worst 10-um window
    hp = half_pins(open(D / f"half_{h_}_pins.tcl").read())
    byf = collections.defaultdict(list)
    for n, x, y in hp:
        byf[face(x, y, W, H)].append(x if face(x, y, W, H) in "NS" else y)
    dens = {}
    for f_, cs in byf.items():
        cs.sort(); best, j = 0, 0
        for i in range(len(cs)):
            while cs[i] - cs[j] > 10: j += 1
            best = max(best, i - j + 1)
        span = (W if f_ in "NS" else H)
        dens[f_] = dict(pins=len(cs), lo=round(cs[0], 1), hi=round(cs[-1], 1), cover=round((cs[-1] - cs[0]) / span, 2), peak_per_um=round(best / 10, 1))
        for c_ in cs[::max(1, len(cs) // 400)]:
            if f_ == "W": ax.plot([-6, 0], [c_, c_], color="b", lw=0.3)
            if f_ == "E": ax.plot([W, W + 6], [c_, c_], color="b", lw=0.3)
            if f_ == "N": ax.plot([c_, c_], [H, H + 6], color="b", lw=0.3)
            if f_ == "S": ax.plot([c_, c_], [-6, 0], color="b", lw=0.3)
    st = stations(open(D / f"half_{h_}_stations.tcl").read())
    for n, sx, sy in st:
        ax.plot([sx], [sy], "^", color="m", ms=4)
    # station hops along each gather lane (sorted by y) and from the N gin face
    hops = []
    lanes = collections.defaultdict(list)
    for n, sx, sy in st:
        lanes[sx].append(sy)
    for sx, ys in lanes.items():
        ys = sorted(ys + ([H] if h_ == "n" else [H]))
        hops += [round(b - a, 1) for a, b in zip(ys, ys[1:])]
    rep[f"hnx_rp3lp3h_{h_}"] = dict(outline=[W, H], aspect=round(H / W, 2), children=len(rects),
                                    by_type=dict(collections.Counter(SHORT[r[1]] for r in rects)),
                                    hard_um2=round(hard), hard_fill=round(hard / (W * H), 3), min_gap_um=round(gmin[0], 2),
                                    min_gap_where=gmin[1], lattice_or_overlap_issues=issues, face_pins=dens,
                                    stations=len(st), max_station_hop_um=max(hops) if hops else None)
    ax.set_xlim(-30, W + 30); ax.set_ylim(-30, H + 30); ax.set_aspect("equal")
    ax.set_title(f"hnx_rp3lp3h_{h_} {W}x{H} um, {len(rects)} hard children, hard fill {hard / (W * H):.2f}\n"
                 f"red = child pin faces (width ~ pin count), blue = half pins, magenta = FIRM stations", fontsize=9)
    for gx in range(0, int(W) + 1, 216):
        ax.axvline(gx, color="0.85", lw=0.3, zorder=0)
fig.suptitle("PATH-HBM-SM: hnx-sm4p cluster halves (spec @4d6f5439dc; child pins = kit tables on plan lattice)", fontsize=11)
fig.tight_layout()
fig.savefig(OUT / "sm4p_cluster_halves.png", dpi=110)
json.dump(rep, open(OUT / "sm4p_cluster_geom.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
