#!/usr/bin/env python3
"""DIE-KV-99 vN2 hand-floorplan drawings (re-runnable).
usage (from a tools tree root, e.g. /dev/shm/dkv99/main):
  python3 -I draw_vN2.py PLAN OUTDIR [--fill fill_vN2.tsv] [--trunk trunk_vN2.json] [--label vN2c]
Writes OUTDIR/kv_vn2_floor.png, kv_vn2_taps.png, kv_vn2_cuts.png and draw_data.json (all numbers behind the figures).
Cut model 'main' = tools/die_plan check_cuts capacity (die_trial.die_core_rects: a core blocks every layer up to the
highest layer its LEF names); 'M7-free' = the same, but a core blocks M6/M7 only where its LEF OBS covers > 50% of the
core area on that layer (the core_obs coverage class COORD approved 11-12), else that layer is free minus nothing."""
import sys, os, re, json, math, warnings, collections, argparse
from pathlib import Path
sys.path.insert(0, "tools/die_plan"); sys.path.insert(0, "tools")
warnings.filterwarnings("ignore")
import schema as S
import check as C
import plan_geom as PG
import die_trial as DT
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib import cm, colors

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--fill", default="/srv/opentallas-scratch2/claude/dkv99/draw/fill_vN2.tsv")
ap.add_argument("--trunk", default="/srv/opentallas-scratch2/claude/dkv99/draw/trunk_vN2.json")
ap.add_argument("--label", default=None)
ap.add_argument("--cap", type=float, default=1200.0)
A = ap.parse_args()
plan = Path(A.plan); out = Path(A.out); out.mkdir(parents=True, exist_ok=True)
label = A.label or plan.parent.name
P = S.Plan(S.load(str(plan)), plan.parent / "die_plan.json")
W, H = P.W, P.H
MM = 1e-3
DATA = dict(plan=str(plan), label=label)


def short(tn):
    return tn.replace("kv3_", "")


def die_rect(n, r):
    a = P.to_die(n, r[:2]); b = P.to_die(n, r[2:])
    return min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])


def core_rects_type(t):
    out_ = []
    for h in t.get("hard_cores") or []:
        if "origin_um" not in h or "outline_um" not in h:
            continue
        x0, y0 = h["origin_um"]; w, hh = h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out_.append((x0, y0, x0 + w, y0 + hh, h))
    return out_


# ------------------------------------------------------------------ fill
fill = {}
if os.path.exists(A.fill):
    for ln in open(A.fill).read().splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 6:
            try:
                fill[f[0]] = float(f[5])
            except ValueError:
                fill[f[0]] = None
DATA["fill"] = fill

# ------------------------------------------------------------------ taps (plan inventory, pre REACH-FIX)
taps = {}
for tn in sorted({p["type"] for p in P.parts.values()}):
    t = P.types[tn]
    if t.get("hard"):
        continue
    try:
        m = PG.type_metrics(P, tn)
        G = PG.type_sites(P, tn)
        tot = sum(s[2] for s in G["sinks"])
        grid = [e for e in G["entries"] if PG.GR.GRID_TAP_RE.match(e[0])]
        taps[tn] = dict(n=sum(1 for p in P.parts.values() if p["type"] == tn), sinks=round(tot), grid_taps=len(grid),
                        tap_max=m.get("grid_tap_sinks_max"), need=math.ceil(tot / A.cap))
    except Exception as e:  # noqa: BLE001
        taps[tn] = dict(err=f"{type(e).__name__}: {str(e)[:80]}")
DATA["taps"] = taps

# ------------------------------------------------------------------ cut loads, two models
_cov = {}


def lef_cov(path):
    """{layer: OBS area fraction of SIZE} (rect-area sum, clamped to 1)"""
    if not path:
        return None
    p = (DT.ROOT / path) if not Path(path).is_absolute() else Path(path)
    if not p.is_file():
        return None
    if str(p) not in _cov:
        txt = p.read_text(errors="replace")
        m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt)
        area = float(m.group(1)) * float(m.group(2)) if m else 0
        acc = collections.Counter(); L = None
        i = txt.find("\n  OBS")
        for ln in (txt[i:] if i >= 0 else "").splitlines():
            s = ln.split()
            if not s:
                continue
            if s[0] == "LAYER":
                L = s[1]
            elif s[0] == "RECT" and L and len(s) >= 5:
                x0, y0, x1, y1 = map(float, s[1:5]); acc[L] += (x1 - x0) * (y1 - y0)
            elif s[0] == "END" and len(s) == 1:
                break
        _cov[str(p)] = {k: min(1.0, v / area) for k, v in acc.items()} if area else {}
    return _cov[str(p)]


def core_rects_model(model, L):
    if model == "main":
        return DT.die_core_rects(P, L)
    li = int(L[1:]); top = int(P.layer_budget["partition_signal_max"][1:])
    res = []
    for n, p in P.parts.items():
        t = P.types[p["type"]]; w, h = t["outline_um"]; ox, oy = p["origin_um"]; o = p.get("orient", "R0")
        for (x0, y0, x1, y1, tl, _m, _v), hc in zip(DT.core_obs(t), [hc for hc in (t.get("hard_cores") or [])
                                                                   if "origin_um" in hc and "outline_um" in hc]):
            if li < 4 or li > min(int(tl[1:]), top):
                continue
            if li >= 6 and not (hc.get("obs_max") and int(hc["obs_max"][1:]) >= li):
                cv = lef_cov(hc.get("lef"))
                if cv is not None and cv.get(L, 0.0) <= 0.5:
                    continue
            if o in ("MY", "R180"):
                x0, x1 = w - x1, w - x0
            if o in ("MX", "R180"):
                y0, y1 = h - y1, h - y0
            res.append((ox + x0, oy + y0, ox + x1, oy + y1))
    return res


geo = {lid: C.lane_geometry(P, lid) for lid in P.lanes}
owned = C.cut_owned_segments(P, geo)
bands = DT.ft_band_rects(P)
step = P.budgets["cut_step_um"]
width = {lid: P.ports[P.lanes[lid]["ports"][0]]["width"] for lid in P.lanes}
# segments: crossing lists per orientation
vsegs, hsegs = [], []      # vertical wire segments (cross horizontal cuts), horizontal wire segments
for lid, (pts, _, _) in geo.items():
    tags = owned.get(lid) or {}
    for i, (p, q) in enumerate(zip(pts, pts[1:])):
        own = list((tags.get(i) or {}).values())
        if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) > 1e-6:
            vsegs.append((p[0], min(p[1], q[1]), max(p[1], q[1]), width[lid], own))
        elif abs(p[1] - q[1]) < 1e-6 and abs(p[0] - q[0]) > 1e-6:
            hsegs.append((p[1], min(p[0], q[0]), max(p[0], q[0]), width[lid], own))
EPS = C.EPS


def seg_loads(model):
    cores = {L: core_rects_model(model, L) for L in ("M4", "M5", "M6", "M7")}
    worst = {}
    for orient in ("horizontal", "vertical"):
        wire_dir = "V" if orient == "horizontal" else "H"
        lim = (H if orient == "horizontal" else W)
        cuts = [step * k for k in range(1, int(lim // step) + 1)]
        segs = vsegs if orient == "horizontal" else hsegs
        for c in cuts:
            hits = []
            for a, lo, hi, w, own in segs:
                if lo < c - EPS and hi > c + EPS:
                    if orient == "horizontal" and any(b[0] + EPS < a < b[2] - EPS and b[1] + EPS < c < b[3] - EPS for b in own):
                        continue
                    if orient == "vertical" and any(b[1] + EPS < a < b[3] - EPS and b[0] + EPS < c < b[2] - EPS for b in own):
                        continue
                    hits.append((a, w))
            if not hits:
                continue
            for pn in P.parts:
                r = P.rect(pn)
                lo, hi, a0, a1 = (r[0], r[2], r[1], r[3]) if orient == "horizontal" else (r[1], r[3], r[0], r[2])
                if not (a0 < c - EPS and a1 > c + EPS):
                    continue
                sb = sum(w for a, w in hits if lo - EPS <= a <= hi + EPS)
                if not sb:
                    continue
                t = P.ptype(pn); frac = t.get("ft_track_frac", C.FT_TRACK_FRAC); cap = 0.0
                for L in C.PART_FT_LAYERS[wire_dir]:
                    if L not in P.layers:
                        continue
                    if orient == "horizontal":
                        obs = [(cr[0], cr[2]) for cr in cores[L] if cr[1] + EPS < c < cr[3] - EPS]
                        res = [(br[1], br[3], br[5]) for br in bands if br[0] == L and br[2] + EPS < c < br[4] - EPS]
                    else:
                        obs = [(cr[1], cr[3]) for cr in cores[L] if cr[0] + EPS < c < cr[2] - EPS]
                        res = [(br[2], br[4], br[5]) for br in bands if br[0] == L and br[1] + EPS < c < br[3] - EPS]
                    cap += C.cut_interval_tracks(lo, hi, P.layers[L]["pitch_um"], frac, obs, res)
                ratio = sb / cap if cap else math.inf
                if ratio > worst.get(pn, (0,))[0]:
                    worst[pn] = (round(ratio, 4), orient, c, sb, round(cap))
    return worst


loads = {m: seg_loads(m) for m in ("main", "M7free")}
DATA["seg_worst"] = {m: {k: list(v) for k, v in d.items()} for m, d in loads.items()}

# ------------------------------------------------------------------ trunk
trunk = json.load(open(A.trunk)) if os.path.exists(A.trunk) else None


# ------------------------------------------------------------------ common die axes
def die_axes(ax, title):
    ax.set_xlim(0, W * MM); ax.set_ylim(0, H * MM); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)"); ax.set_title(title, fontsize=11)
    ax.set_xticks([k for k in range(0, int(W * MM) + 1)]); ax.set_yticks([k for k in range(0, int(H * MM) + 1)])


def part_label(n, tn, extra=""):
    x0, y0, x1, y1 = P.rect(n)
    w, h = x1 - x0, y1 - y0
    rot = 90 if h > 1.6 * w and w < 1100 else 0
    fs = 5.2 if w > 1500 else 4.4
    return dict(x=(x0 + x1) / 2 * MM, y=(y0 + y1) / 2 * MM, s=f"{n}\n{short(tn)}{extra}", rotation=rot, fontsize=fs)


def lbl_box(ax, d):
    ax.text(d["x"], d["y"], d["s"], rotation=d["rotation"], fontsize=d["fontsize"], ha="center", va="center", zorder=9,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))


# ------------------------------------------------------------------ (1) floor
cmap = plt.get_cmap("YlGn")
norm = colors.Normalize(vmin=0.0, vmax=0.15)
fig, ax = plt.subplots(figsize=(16, 16 * H / W * 0.92 + 1.5), dpi=150)
for n, p in P.parts.items():
    x0, y0, x1, y1 = P.rect(n); tn = p["type"]; f = fill.get(tn)
    if f is None:
        ax.add_patch(Rectangle((x0 * MM, y0 * MM), (x1 - x0) * MM, (y1 - y0) * MM, fc="#eeeeee", ec="black", lw=0.6, hatch="////"))
    else:
        ax.add_patch(Rectangle((x0 * MM, y0 * MM), (x1 - x0) * MM, (y1 - y0) * MM, fc=cmap(norm(f)), ec="black", lw=0.6))
    for cx0, cy0, cx1, cy1, _h in core_rects_type(P.types[tn]):
        a, b, c_, d = die_rect(n, [cx0, cy0, cx1, cy1])
        ax.add_patch(Rectangle((a * MM, b * MM), (c_ - a) * MM, (d - b) * MM, fc="#8d99ae", ec="#2b2d42", lw=0.25, alpha=0.85))
    extra = "" if f is None else f"\nfill {f:.3f}"
    if tn == "kv3_hroot":
        extra += "\nASPECT EXC 2.27"
    if tn == "kv3_sys_c":
        extra += "\nASPECT EXC 2.08"
    lbl_box(ax, part_label(n, tn, extra))
for ch in P.die.get("channels") or []:
    try:
        r = P.channel_rect(ch)
        ax.add_patch(Rectangle((r[0] * MM, r[1] * MM), (r[2] - r[0]) * MM, (r[3] - r[1]) * MM, fc="#ffd166", ec="#e76f51",
                               lw=1.0, alpha=0.6, zorder=4))
    except Exception:  # noqa: BLE001
        pass
for w_ in P.die.get("io") or []:
    x0, y0, x1, y1 = w_["rect_um"]
    ax.add_patch(Rectangle((x0 * MM, y0 * MM), (x1 - x0) * MM, (y1 - y0) * MM, fc="none", ec="magenta", lw=0.8, ls="--", zorder=5))
if trunk:
    segs = [((s["x0"] * MM, s["y0"] * MM), (s["x1"] * MM, s["y1"] * MM)) for s in trunk["segments"] if s.get("kind") == "trunk"]
    ax.add_collection(LineCollection(segs, colors="#d62828", linewidths=1.6, zorder=7))
    rr = trunk["region_roots"]
    ax.scatter([r["xy"][0] * MM for r in rr], [r["xy"][1] * MM for r in rr], s=10, c="#003049", zorder=8, marker="s")
    ax.scatter([trunk["root"]["xy"][0] * MM], [trunk["root"]["xy"][1] * MM], s=60, c="#d62828", marker="*", zorder=8)
sm = cm.ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01); cb.set_label("slot fill = kit std-cell area / (outline - hard cores); hatched = no kit data")
die_axes(ax, f"KV {label} hand floorplan (DIE-KV-99 draft 2): grey = hard cores (W streets visible in hg/hgi), "
             f"red = die clock trunk + squares = 128 region roots, star = root hub_C\n"
             f"(trunk from DIE-PROTO-3 vFk tree: vF outline, sys_SE region shifts in vN2), magenta dashed = die io windows")
fig.tight_layout(); fig.savefig(out / "kv_vn2_floor.png"); plt.close(fig)

# ------------------------------------------------------------------ (2) taps
rows = sorted(((tn, d) for tn, d in taps.items() if "tap_max" in d and d["tap_max"]), key=lambda kv: -kv[1]["tap_max"])
fig, ax = plt.subplots(figsize=(16, 7), dpi=150)
xs = range(len(rows))
vals = [d["tap_max"] for _, d in rows]
cols = ["#d62828" if v > 2 * A.cap else ("#f77f00" if v > A.cap else "#2a9d8f") for v in vals]
ax.bar(xs, vals, color=cols)
ax.axhline(A.cap, color="black", ls="--", lw=1); ax.text(len(rows) - 1, A.cap * 1.04, f"cap {A.cap:.0f}", ha="right")
for i, (tn, d) in enumerate(rows):
    ax.text(i, vals[i] * 1.02, f"{d['grid_taps']}/{d['need']}", ha="center", va="bottom", fontsize=5.5, rotation=90)
ax.set_xticks(list(xs)); ax.set_xticklabels([short(tn) for tn, _ in rows], rotation=90, fontsize=7)
ax.set_ylabel("worst grid tap sinks (plan inventory)")
n_over = sum(v > A.cap for v in vals)
ax.set_title(f"KV {label}: worst clock tap per type, PRE-REACH-FIX taps (plan sink inventory = lower bound); "
             f"{n_over}/{len(rows)} types over the {A.cap:.0f} cap; label = grid taps / taps needed at the cap", fontsize=10)
fig.tight_layout(); fig.savefig(out / "kv_vn2_taps.png"); plt.close(fig)

# ------------------------------------------------------------------ (3) cuts
fig, axs = plt.subplots(1, 2, figsize=(16, 8 * H / W + 1.0), dpi=150)
rn = colors.Normalize(vmin=0.0, vmax=1.0)
rmap = plt.get_cmap("RdYlGn_r")
hgi_parts = [n for n, p in P.parts.items() if P.parts[n]["type"].startswith("kv3_hgi")]
for ax, (m, title) in zip(axs, (("main", "main G0 model (core blocks up to its LEF top layer)"),
                                ("M7free", "M7-free model (M6/M7 blocked only where LEF OBS > 50%)"))):
    nover = 0
    for n in P.parts:
        x0, y0, x1, y1 = P.rect(n)
        v = loads[m].get(n)
        r = v[0] if v else 0.0
        nover += r > 0.6
        ax.add_patch(Rectangle((x0 * MM, y0 * MM), (x1 - x0) * MM, (y1 - y0) * MM, fc=rmap(rn(min(r, 1.0))), ec="black",
                               lw=(1.6 if n in hgi_parts else 0.4)))
        if v and r >= 0.3:
            ax.text((x0 + x1) / 2 * MM, (y0 + y1) / 2 * MM, f"{r:.2f}\n{'H' if v[1] == 'horizontal' else 'V'}@{v[2]:g}",
                    ha="center", va="center", fontsize=6.5, zorder=6)
    die_axes(ax, f"KV {label} cut-line segment loads (ft tracks M4-M7 x ft_track_frac, step {step:g} um)\n{title}\nworst partition segment per slot; {nover} slots > 0.6; thick outline = hgi column")
    ax.title.set_fontsize(9)
sm = cm.ScalarMappable(norm=rn, cmap=rmap); sm.set_array([])
fig.colorbar(sm, ax=axs, fraction=0.02, pad=0.01).set_label("segment bits / ft tracks (limit 0.6)")
fig.subplots_adjust(left=0.05, right=0.9, top=0.95, bottom=0.04, wspace=0.12)
fig.savefig(out / "kv_vn2_cuts.png", bbox_inches="tight"); plt.close(fig)

json.dump(DATA, open(out / "draw_data.json", "w"), indent=1)
over = {m: sorted(((k, v[0]) for k, v in d.items() if v[0] > 0.6), key=lambda kv: -kv[1]) for m, d in loads.items()}
print("taps over cap:", n_over, "of", len(rows))
for m in over:
    print(m, "slots > 0.6:", len(over[m]), over[m][:12])
