#!/usr/bin/env python3
"""DIE-S81-32/MACRO site generator (scratch tool; its output delta_macro_sites_1029.json is committed with the delta).
Static macro sites inside each type's EXISTING outline: 8.64-um lattice + per-master track offset, macro columns that
never x-overlap with >= 10.8-um channels (kit_contract MIN_CHANNEL_UM), every stack gap >= 10.8 um, clear of ft
corridors (+10.8), landing bands (+10.8), existing contents/cores (+10.8), clock tap / landing pins / reset relays
(+21.6) and a 43.2-um edge band (face flops, pins)."""
import json
import math
import re
import sys
from pathlib import Path

WT = Path("/srv/opentallas-scratch2/claude/die-s81-34/kvt2site/wt")
import os
HIER = Path("/srv/opentallas-scratch2/claude/die-s81-34/kvt2/hier")
KITRTL = Path("/srv/opentallas-scratch2/claude/s81-kits-a/rtl")
sys.path.insert(0, str(WT / "tools/die_plan"))
import kit_contract as KC  # noqa: E402

G = 8.64
CH = 10.8
EDGE = 43.2
PT_HALO = 21.6
HALO = 10.8
COL_XC = None
# plan make_tracks (gen.py: M4-M9 offset = pitch/2) + platform M2/M3
TRK = {"M4": ("H", 0.048, 0.024, (0.024,)), "M5": ("V", 0.048, 0.024, (0.024,)), "M6": ("H", 0.064, 0.032, (0.032,)),
       "M7": ("V", 0.064, 0.032, (0.032,)), "M3": ("V", 0.036, 0.018, (0.009,)),
       "M2": ("H", 0.270, 0.018, (0.045, 0.081, 0.117, 0.153, 0.189, 0.225, 0.270))}


def lef_info(lef):
    t = (WT / lef).read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    pins = []
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", t, re.M | re.S):
        if re.search(r"\bUSE\s+(POWER|GROUND)\b", pm.group(2)):
            continue
        layer = None
        for tok in re.finditer(r"LAYER\s+(\S+)\s*;|RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", pm.group(2)):
            if tok.group(1):
                layer = tok.group(1)
            elif layer in TRK:
                pins.append((layer, *map(float, tok.groups()[1:])))
    return (float(m.group(1)), float(m.group(2))), pins


def on_grid(pins, ox, oy):
    for layer, x0, y0, x1, y1 in pins:
        d, p, w, offs = TRK[layer]
        lo, hi = (oy + y0, oy + y1) if d == "H" else (ox + x0, ox + x1)
        ok = False
        for of in offs:
            c = (lo + hi) / 2
            t = of + round((c - of) / p) * p
            if any(lo + w / 2 - 5e-4 <= tt <= hi - w / 2 + 5e-4 for tt in (t - p, t, t + p)):
                ok = True
        if not ok:
            return False
    return True


def track_offset(pins):
    """smallest (dx, dy): dx on the 0.108 (2-site) grid, dy on 0.012, every signal pin on a plan track (R0)."""
    for k in range(0, 40):
        for dx in (0.0, 0.108, 0.216, 0.324, 0.432):
            dy = round(0.012 * k, 3)
            if on_grid(pins, dx, dy):
                return (dx, dy)
    raise SystemExit("no on-grid offset")


def masters_of(tn):
    hm = json.loads((KITRTL / tn / "kit_rtl.json").read_text())["hard_macros"]
    cut = "/srv/opentallas-scratch2/claude/wt/s81-kits-a/"
    return {k: (v["lef"].split(cut)[1], [x.split(cut)[1] for x in v["libs"] if x.endswith("_tt.lib")][0])
            for k, v in hm.items()}


def instances(tn):
    out, m = [], None
    for ln in (HIER / f"{tn}.list2").read_text().split("\n"):
        if ln.startswith("=="):
            m = ln[2:]
        elif ln.strip():
            out.append((ln.split("/", 1)[1], m))
    return out


def keepouts(t):
    W, H = t["outline_um"]
    rects, pts = [], []

    def band(face, win, other=None):
        lo, hi = win[0] - HALO, win[1] + HALO
        if face in "NS":
            if other is None:
                return [lo, 0, hi, H]
            return [lo, other[0] - HALO, hi, H] if face == "N" else [lo, 0, hi, other[1] + HALO]
        if other is None:
            return [0, lo, W, hi]
        return [0, lo, other[1] + HALO, hi] if face == "W" else [other[0] - HALO, lo, W, hi]

    for s in t.get("ft_slots", []):
        fi, fo, wi, wo = s["in_face"], s["out_face"], s["in_window_um"], s["out_window_um"]
        if {fi, fo} in ({"N", "S"}, {"E", "W"}):
            rects += [band(fi, wi), band(fo, wo)]
        else:                       # L corridor: each leg reaches across the other leg's window
            rects += [band(fi, wi, wo), band(fo, wo, wi)]
    ck = t.get("clock", {})
    pts.append(tuple(ck["tap_um"]))

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "rect_um" and isinstance(v, list) and len(v) == 4:
                    rects.append([v[0] - HALO, v[1] - HALO, v[2] + HALO, v[3] + HALO])
                elif k in ("xy", "xy_um", "tap_um", "root") and isinstance(v, list) and len(v) == 2 \
                        and all(isinstance(a, (int, float)) for a in v):
                    pts.append(tuple(v))
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(ck)
    walk(t.get("reset", {}))
    walk(t.get("internal_stations", []))
    for c in t.get("contents", []) + t.get("hard_cores", []):
        if "origin_um" in c and "outline_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            rects.append([x - HALO, y - HALO, x + w + HALO, y + h + HALO])
    return rects, pts


def hit(b, rects, pts):
    for r in rects:
        if b[0] < r[2] and r[0] < b[2] and b[1] < r[3] and r[1] < b[3]:
            return True
    for (x, y) in pts:
        if b[0] - PT_HALO < x < b[2] + PT_HALO and b[1] - PT_HALO < y < b[3] + PT_HALO:
            return True
    return False


def snap_up(v):
    return round(math.ceil(v / G - 1e-9) * G, 4)


def place(tn, t, groups):
    """groups: [(gname, [(inst, master, (w, h))], pref_rect or None)] -> (sites, rects, pts, unplaced).  Column
    packer: a column holds one master width; an item first stacks onto an existing column of its width (inside its
    preferred rect when it has one), else opens a new column left->right; columns never x-overlap and keep >= CH
    channels; stack gaps >= CH."""
    W, H = t["outline_um"]
    rects, pts = keepouts(t)
    cols = []                       # dict(x, w, top, boxes)
    out, left = [], []
    full = [EDGE, EDGE, W - EDGE, H - EDGE]

    def stack(c, it, area):
        w, h = it[2]
        y = snap_up(max(area[1], c["top"] + CH if c["boxes"] else area[1]))
        while y + h <= area[3] + 1e-6 and hit((c["x"], y, c["x"] + w, y + h), rects, pts):
            y = round(y + G, 4)
        return y if y + h <= area[3] + 1e-6 else None

    for gname, items, pref in groups:
        items = sorted(items, key=lambda it: (-it[2][0], -it[2][1], it[0]))
        for it in items:
            w, h = it[2]
            done = False
            for area in ([pref] if pref else []) + [full]:
                for c in cols:
                    if abs(c["w"] - w) > 1e-6 or c["x"] < area[0] - 1e-6 or c["x"] + w > area[2] + 1e-6:
                        continue
                    y = stack(c, it, area)
                    if y is not None:
                        c["boxes"].append((it, y)); c["top"] = y + h; done = True
                        out.append(dict(inst=it[0], module=it[1], xy=(c["x"], y), wh=it[2], group=gname))
                        break
                if done:
                    break
                xs = []
                x = snap_up(area[0])
                while x + w <= area[2] + 1e-6:
                    xs.append(x); x = round(x + G, 4)
                if COL_XC is not None:          # KVT2-SITE: open new columns nearest the bus centre first
                    xs.sort(key=lambda v: (abs(v + w / 2 - COL_XC), v))
                for x in xs:
                    if any(x < c["x"] + c["w"] + CH - 1e-6 and c["x"] - CH + 1e-6 < x + w for c in cols):
                        continue
                    c = dict(x=x, w=w, top=0.0, boxes=[])
                    y = stack(c, it, area)
                    if y is not None:
                        c["boxes"].append((it, y)); c["top"] = y + h; cols.append(c); done = True
                        out.append(dict(inst=it[0], module=it[1], xy=(x, y), wh=it[2], group=gname))
                        break
                if done:
                    break
            if not done:
                left.append(it)
    return out, rects, pts, left


def check(tn, t, sites):
    W, H = t["outline_um"]
    rects, pts = keepouts(t)
    bx = [(s["xy"][0], s["xy"][1], s["xy"][0] + s["wh"][0], s["xy"][1] + s["wh"][1]) for s in sites]
    bad = []
    for i, b in enumerate(bx):
        if b[0] < EDGE - 1e-6 or b[1] < EDGE - 1e-6 or b[2] > W - EDGE + 1e-6 or b[3] > H - EDGE + 1e-6:
            bad.append(("edge", sites[i]["inst"]))
        if hit(b, rects, pts):
            bad.append(("keepout", sites[i]["inst"]))
        for j in range(i):
            c = bx[j]
            if b[0] < c[2] + CH - 1e-6 and c[0] < b[2] + CH - 1e-6 and b[1] < c[3] + CH - 1e-6 and c[1] < b[3] + CH - 1e-6:
                bad.append(("spacing", sites[i]["inst"], sites[j]["inst"]))
    boxes = [(s["inst"], *b) for s, b in zip(sites, bx)]
    cl = KC._clusters(boxes, 1, 3)
    edges = [4.32] + [v for c in cl for v in (min(b[1] for b in c), max(b[3] for b in c))] + [W - 4.32]
    for i, c in enumerate(cl):
        lo, hi = min(b[1] for b in c), max(b[3] for b in c)
        if lo - edges[2 * i] < CH - 1e-6 or edges[2 * i + 3] - hi < CH - 1e-6:
            bad.append(("column_channel", i))
        st = sorted(c, key=lambda b: b[2])
        if len(st) > 1 and max(st[k + 1][2] - st[k][4] for k in range(len(st) - 1)) < CH - 1e-6:
            bad.append(("stack", i))
    return bad, len(cl)


def render(tn, t, sites, rects, pts, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    W, H = t["outline_um"]
    fig, ax = plt.subplots(figsize=(11, 9.5))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5, ec="k"))
    ax.add_patch(Rectangle((EDGE, EDGE), W - 2 * EDGE, H - 2 * EDGE, fill=False, lw=0.6, ec="0.6", ls="--"))
    for r in rects:
        x0, y0, x1, y1 = max(r[0], 0), max(r[1], 0), min(r[2], W), min(r[3], H)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#f4c27a", ec="#c88a2a", alpha=0.35, lw=0.4))
    for b in t.get("buses", []):
        lo, hi = b["window_um"]
        d = 12
        rr = {"N": (lo, H - d, hi - lo, d), "S": (lo, 0, hi - lo, d), "W": (0, lo, d, hi - lo),
              "E": (W - d, lo, d, hi - lo)}[b["face"]]
        ax.add_patch(Rectangle(rr[:2], rr[2], rr[3], fc="#3a7bd5" if b["dir"] == "in" else "#2ca25f", ec="none"))
        ax.text(rr[0] + rr[2] / 2, rr[1] + rr[3] / 2, b["name"], fontsize=5, ha="center", va="center")
    for x, y in pts:
        ax.plot(x, y, "x", color="#b2182b", ms=4, mew=0.8)
    ax.plot(*t["clock"]["tap_um"], "*", color="#b2182b", ms=12)
    pal = ["#6a51a3", "#e6550d", "#31a354", "#3182bd", "#de2d26", "#756bb1", "#636363", "#fd8d3c", "#74c476",
           "#9e9ac8", "#8c6d31", "#17becf"]
    cm = {}
    for s in sites:
        c = cm.setdefault(s["group"], pal[len(cm) % len(pal)])
        ax.add_patch(Rectangle(s["xy"], s["wh"][0], s["wh"][1], fc=c, ec="k", lw=0.3, alpha=0.85))
    for g, c in cm.items():
        ax.plot([], [], "s", color=c, label=g)
    ax.plot([], [], "s", color="#f4c27a", label="keepout: ft corridor / landing band (+10.8)")
    ax.plot([], [], "x", color="#b2182b", label="clock tap (*) / landing pins / reset relays")
    ax.legend(fontsize=6, loc="upper right", framealpha=0.9)
    ax.set_xlim(-20, W + 20)
    ax.set_ylim(-20, H + 20)
    ax.set_aspect("equal")
    ax.set_title(f"{tn}: {len(sites)} new macro sites, outline {W} x {H} unchanged", fontsize=9)
    fig.savefig(png, dpi=130, bbox_inches="tight")
    plt.close(fig)


def group_key(tn, inst):
    """locality groups: logical owner of each macro (bound sub-block)."""
    p = inst.split(".")
    p[1] = p[1][4:] if p[1].startswith("u_u_") else p[1]
    if "LP" in tn:
        if p[1].startswith("ln"):
            return p[1]                          # ln0..3: the 4 MU lanes (S81-LP-2 lane-macro boundary)
        if p[1] == "lep":
            return "lep." + p[3]                 # lep g_tx[i] / g_rx[i]
        return p[1]
    return p[1]


def main():
    plan = json.loads((WT / "physical/die_plan/s81/plan_s13r2.json").read_text())
    types = sys.argv[1].split(",")
    outdir = Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    res = {}
    lefc = {}
    for tn in types:
        t = plan["partition_types"][tn]
        views = masters_of(tn)
        inst = instances(tn)
        items = []
        for i, m in inst:
            lef, lib = views[m]
            if lef not in lefc:
                wh, pins = lef_info(lef)
                lefc[lef] = (wh, track_offset(pins), len(pins))
            items.append((i, m, lefc[lef][0]))
        W, H = t["outline_um"]
        free = (W - 2 * EDGE) * (H - 2 * EDGE)
        marea = sum(w * h for _, _, (w, h) in items)
        harea = sum((w + CH) * (h + CH) for _, _, (w, h) in items)
        groups = {}
        for it in items:
            groups.setdefault(group_key(tn, it[0]), []).append(it)
        prefs = PREFS.get(tn.split("__")[0]) or bus_pref(t)
        gl = [(g, v, prefs.get(g, prefs.get(g.split(".")[0] + ".*", prefs.get("*")))) for g, v in sorted(groups.items(), key=lambda kv: ORDER(tn, kv[0]))]
        sites, rects, pts, left = place(tn, t, gl)
        for s in sites:
            lef, lib = views[s["module"]]
            (w, h), (dx, dy), npin = lefc[lef]
            s.update(lef=lef, lib=lib, origin_um=[round(s["xy"][0] + dx, 4), round(s["xy"][1] + dy, 4)],
                     outline_um=[w, h], track_offset_um=[dx, dy])
        bad, ncol = check(tn, t, sites)
        render(tn, t, sites, rects, pts, outdir / f"{tn}.png")
        res[tn] = dict(n=len(sites), masters={m: sum(1 for s in sites if s["module"] == m) for m in sorted({s["module"] for s in sites})},
                       macro_area_um2=round(marea, 1), with_channel_area_um2=round(harea, 1), free_area_um2=round(free, 1),
                       fill=round(harea / free, 4), columns=ncol, problems=bad, unplaced=[list(x[:2]) for x in left],
                       sites=[dict(inst=s["inst"], module=s["module"], lef=s["lef"], lib=s["lib"], origin_um=s["origin_um"],
                                   outline_um=s["outline_um"], group=s["group"]) for s in sites])
        print(tn, len(sites), "unplaced", len(left), "fill", res[tn]["fill"], "cols", ncol, "problems", len(bad), bad[:3])
    (outdir / "sites.json").write_text(json.dumps(res, indent=1))


def bus_pref(t):
    """{"*": rect}: 700 um wide, 560 um deep box at the type's bus-window centroid face (locality-first 12.13)."""
    W, H = t["outline_um"]
    pts = []
    for b in t["buses"]:
        c = (b["window_um"][0] + b["window_um"][1]) / 2
        pts.append({"N": (c, H), "S": (c, 0), "W": (0, c), "E": (W, c)}[b["face"]])
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    x0 = min(max(EDGE, cx - 350), W - EDGE - 700)
    y0 = min(max(EDGE, cy - 280), H - EDGE - 560)
    return {"*": [round(x0, 2), round(y0, 2), round(x0 + 700, 2), round(y0 + 560, 2)]}


def ORDER(tn, g):
    return (0 if g.startswith("ln") else 1 if g.startswith("lep") else 2, g)


# locality preferences (type frame): LP MU lanes ln0/ln1 by the W half (coll_i0/i1, coll_o0/o1 S windows x < 456),
# ln2/ln3 by the E half (coll_i2/i3, coll_o2/o3 x 663-1129); lep tx/rx next to the E-face lepk buses (y < 538);
# (nh: lanes W half, lep E); landing SRAMs anywhere; kv_leaf / seqhost: bus-centroid box (bus_pref).
PREFS = {
    "dsdv_slice_lepw_mus_LP": {"ln0": [43.2, 43.2, 450, 620], "ln1": [43.2, 620, 450, 1183.68],
                               "ln2": [660, 43.2, 1010, 620], "ln3": [660, 620, 1010, 1183.68],
                               "lep.*": [1010, 43.2, 1399.68, 1183.68]},
    "dsdv_slice_lepe_nh_mus_LP": {"ln0": [43.2, 43.2, 470, 620], "ln1": [43.2, 620, 470, 1183.68],
                                  "lep.*": [700, 43.2, 1399.68, 1183.68]},
}
PREFS["dsdv_slice_lepw_mu_LP"] = PREFS["dsdv_slice_lepw_mus_LP"]
PREFS["dsdv_slice_lepe_mu_LP"] = PREFS["dsdv_slice_lepw_mus_LP"]

if __name__ == "__main__":
    main()
