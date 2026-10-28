"""G0C STREET RULE (METHODOLOGY 12.10c, OWNER 2026-10-27 ~18:4x; lane HBM-STREETS-1).

Hard cores sit on a channel ("street") grid:
  street_reach   every point of every hard core is <= reach_um (default 400, the ~405-um reach rule) from the street
                 network, measured along a row or column (a repeated wire leaves the street straight into the core);
  street_width   a street is free die area (no hard core, no PHY macro) at least width_um wide in both axes, where
                 width_um >= (clock repeater + hold buffer + FT repeater widths) / fill (12.7e 60 % fill); the street
                 network is the largest 4-connected street component (pockets enclosed by cores are not streets:
                 a leg into them would cross a core);
  street_clock_leg  no clock leg crosses a hard core: every die-clock H-tree leg (die_clock_mesh mesh.json htree
                 a->b, x first then y) and every mesh-driver / tree cell of a clock build lies outside the keep-outs;
                 a build that failed with unplaced legs / drivers (plan_errors.json) is an ERROR per row;
  street_die_leg every die-level lane register / station (lane geometry regs) lies outside the hard cores.

Inputs are plain rectangles so the rule is testable without a plan: analyze(W, H, keepouts, cfg, legs, points).
check.check_streets() feeds it from a plan (die_clock.keepouts) + optional clock builds.
Plan configuration (all optional): die.streets = {reach_um, width_um, raster_um, clock_um, hold_um, ft_um, fill}.
"""
import json
import math
from pathlib import Path

import numpy as np

DEFAULTS = dict(
    reach_um=400.0,      # 12.10c "<= ~400 um from a channel" (405-um reach rule)
    raster_um=8.64,      # die grid
    clock_um=4.32,       # one BUFx24 clock repeater pair site + shield/PG clearance across the street
    hold_um=4.32,        # data hold-buffer column (12.4a a1)
    ft_um=8.64,          # FT repeater columns (bits crossing at <= 60 % fill, plan default; per die override)
    fill=0.6,            # 12.7e margin: bays / streets <= 60 % full
    leg_max_um=480.0,    # die clock: max unrepeated leg (die_clock_mesh hop_max)
)


def required_width(cfg):
    """street width the repeater / hold / FT budget needs at the fill margin, snapped up to the raster."""
    w = (cfg["clock_um"] + cfg["hold_um"] + cfg["ft_um"]) / cfg["fill"]
    g = cfg["raster_um"]
    return math.ceil(w / g - 1e-9) * g


def config(decl=None):
    cfg = dict(DEFAULTS)
    cfg.update({k: float(v) for k, v in (decl or {}).items() if k in DEFAULTS or k == "width_um"})
    cfg["required_width_um"] = required_width(cfg)
    cfg.setdefault("width_um", cfg["required_width_um"])
    return cfg


def raster(W, H, rects, g):
    nx, ny = int(math.ceil(W / g)), int(math.ceil(H / g))
    occ = np.zeros((ny, nx), dtype=bool)
    for r in rects:
        # a cell is blocked when its centre is inside the rect (closed)
        i0 = max(0, int(math.ceil(r[0] / g - 0.5 - 1e-9)))
        i1 = min(nx - 1, int(math.floor(r[2] / g - 0.5 + 1e-9)))
        j0 = max(0, int(math.ceil(r[1] / g - 0.5 - 1e-9)))
        j1 = min(ny - 1, int(math.floor(r[3] / g - 0.5 + 1e-9)))
        if i1 >= i0 and j1 >= j0:
            occ[j0:j1 + 1, i0:i1 + 1] = True
    return occ


def _runs(free, axis):
    """length (cells) of the free run along `axis` that contains each cell (0 on blocked cells)."""
    a = np.moveaxis(free, axis, -1)
    n = a.shape[-1]
    idx = np.arange(n)
    left = np.maximum.accumulate(np.where(~a, idx, -1), axis=-1)
    right = np.flip(np.minimum.accumulate(np.flip(np.where(~a, idx, n), axis=-1), axis=-1), axis=-1)
    run = np.where(a, right - left - 1, 0)
    return np.moveaxis(run, -1, axis)


def _dist(mask, axis):
    """cells to the nearest True cell along `axis` (both directions), inf when the line has none."""
    a = np.moveaxis(mask, axis, -1)
    n = a.shape[-1]
    idx = np.arange(n, dtype=np.float64)
    big = 1e18
    last = np.maximum.accumulate(np.where(a, idx, -big), axis=-1)
    nxt = np.flip(np.minimum.accumulate(np.flip(np.where(a, idx, big), axis=-1), axis=-1), axis=-1)
    d = np.minimum(idx - last, nxt - idx)
    return np.moveaxis(d, -1, axis)


def components(mask):
    """4-connected components of a boolean raster via row runs + union-find: (labels raster, sizes dict)."""
    ny, nx = mask.shape
    parent = []

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    rows = []
    for j in range(ny):
        row = mask[j]
        if not row.any():
            rows.append([])
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        cur = []
        for s, e in zip(st.tolist(), en.tolist()):
            k = len(parent)
            parent.append(k)
            cur.append((s, e, k))
        prev = rows[-1] if rows else []
        p = 0
        for s, e, k in cur:                      # overlap with previous-row runs (both sorted)
            while p < len(prev) and prev[p][1] <= s:
                p += 1
            q = p
            while q < len(prev) and prev[q][0] < e:
                ra, rb = find(k), find(prev[q][2])
                if ra != rb:
                    parent[ra] = rb
                q += 1
        rows.append(cur)
    lab = np.full(mask.shape, -1, dtype=np.int64)
    sizes = {}
    for j, cur in enumerate(rows):
        for s, e, k in cur:
            r = find(k)
            lab[j, s:e] = r
            sizes[r] = sizes.get(r, 0) + (e - s)
    return lab, sizes


def _l_segments(a, b):
    """x first then y (die_clock_mesh leg convention); a straight leg is one segment."""
    if abs(a[0] - b[0]) < 1e-9 or abs(a[1] - b[1]) < 1e-9:
        return [(a, b)]
    m = (b[0], a[1])
    return [(a, m), (m, b)]


def seg_hits(a, b, r, eps=1e-6):
    """axis-aligned segment a-b runs through the open interior of rect r (running along an edge is legal)."""
    if abs(a[1] - b[1]) < 1e-9:                      # horizontal
        x0, x1 = sorted((a[0], b[0]))
        return r[1] + eps < a[1] < r[3] - eps and min(x1, r[2]) - max(x0, r[0]) > eps
    if abs(a[0] - b[0]) < 1e-9:                      # vertical
        y0, y1 = sorted((a[1], b[1]))
        return r[0] + eps < a[0] < r[2] - eps and min(y1, r[3]) - max(y0, r[1]) > eps
    return any(seg_hits(s, e, r, eps) for s, e in _l_segments(a, b))


def is_phy(name):
    """die PHY macro keep-outs (die.io rects, io-partition clock keep-outs): street obstacles, not reach-checked cores."""
    return str(name).startswith("io/") or "/clock_keepout_" in str(name)


def in_open(p, r, eps=1e-6):
    return r[0] + eps < p[0] < r[2] - eps and r[1] + eps < p[1] < r[3] - eps


class _Index:
    def __init__(self, rects, b=500.0):
        self.b, self.g = b, {}
        for r in rects:
            for i in range(int(r[0] // b), int(r[2] // b) + 1):
                for j in range(int(r[1] // b), int(r[3] // b) + 1):
                    self.g.setdefault((i, j), []).append(r)

    def near(self, x0, y0, x1, y1):
        seen = set()
        for i in range(int(min(x0, x1) // self.b), int(max(x0, x1) // self.b) + 1):
            for j in range(int(min(y0, y1) // self.b), int(max(y0, y1) // self.b) + 1):
                for r in self.g.get((i, j), ()):
                    if id(r) not in seen:
                        seen.add(id(r))
                        yield r


def analyze(W, H, keepouts, cfg=None, legs=(), points=(), unplaced=()):
    """keepouts: [(x0, y0, x1, y1, name)] die frame (hard cores + PHY macros).  legs: [(name, a, b)] clock legs.
    points: [(name, (x, y), kind)] cells / stations that must sit on streets.  unplaced: [(name, detail)] build rows.
    Returns dict(cfg, streets, cores[...], legs_over_core[...], points_in_core[...], unplaced[...], errors[...])."""
    cfg = cfg or config()
    g = cfg["raster_um"]
    occ = raster(W, H, keepouts, g)
    free = ~occ
    k = int(math.ceil(cfg["width_um"] / g - 1e-9))
    wide = free & (_runs(free, 1) >= k) & (_runs(free, 0) >= k)
    lab, sizes = components(wide)
    main = max(sizes, key=sizes.get) if sizes else None
    net = lab == main if main is not None else np.zeros_like(wide)
    dist = np.minimum(_dist(net, 0), _dist(net, 1)) * g
    errors = []
    cores = []
    ny, nx = occ.shape
    for r in keepouts:
        if is_phy(r[4]):
            continue                     # die PHY macros: obstacles for streets, own clock inside (not a hard core)
        i0 = max(0, int(math.floor(r[0] / g)))
        i1 = min(nx, max(i0 + 1, int(math.ceil(r[2] / g))))
        j0 = max(0, int(math.floor(r[1] / g)))
        j1 = min(ny, max(j0 + 1, int(math.ceil(r[3] / g))))
        d = float(dist[j0:j1, i0:i1].max())
        row = dict(name=r[4], rect_um=[round(v, 3) for v in r[:4]], street_dist_um=(round(d, 2) if d < 1e17 else None))
        cores.append(row)
        if not d <= cfg["reach_um"] + 1e-6:
            errors.append(("street_reach", r[4], f"core {r[4]}: farthest point {('no street' if d >= 1e17 else f'{d:.0f} um')} "
                           f"from the street network > {cfg['reach_um']:g} um (12.10c: open a street beside it / move it onto "
                           "the street grid)"))
    if cfg["width_um"] + 1e-6 < cfg["required_width_um"]:
        errors.append(("street_width", None, f"die.streets.width_um {cfg['width_um']:g} < required {cfg['required_width_um']:g} um "
                       f"((clock {cfg['clock_um']:g} + hold {cfg['hold_um']:g} + FT {cfg['ft_um']:g}) / fill {cfg['fill']:g})"))
    idx = _Index(list(keepouts))
    over = []
    for name, a, b in legs:
        for s, e in _l_segments(a, b):
            hit = next((r for r in idx.near(s[0], s[1], e[0], e[1]) if seg_hits(s, e, r)), None)
            if hit is not None:
                L = abs(a[0] - b[0]) + abs(a[1] - b[1])
                over.append(dict(leg=name, a=list(a), b=list(b), len_um=round(L, 2), core=hit[4]))
                errors.append(("street_clock_leg", hit[4], f"clock leg {name} {L:.0f} um crosses hard core {hit[4]} "
                               "(12.10c: run the leg along a street)"))
                break
    inside = []
    for name, p, kind in points:
        hit = next((r for r in idx.near(p[0], p[1], p[0], p[1]) if in_open(p, r)), None)
        if hit is not None:
            inside.append(dict(name=name, xy=list(p), kind=kind, core=hit[4]))
            errors.append(("street_clock_leg" if kind.startswith("clock") else "street_die_leg", hit[4],
                           f"{kind} {name} at ({p[0]:.1f}, {p[1]:.1f}) inside hard core {hit[4]} (12.10c: on a street)"))
    for name, detail in unplaced:
        errors.append(("street_clock_leg", None, f"clock build: {name} unplaced ({detail}) -- no legal street site"))
    st = dict(raster_um=g, width_um=cfg["width_um"], required_width_um=cfg["required_width_um"],
              street_area_mm2=round(float(net.sum()) * g * g / 1e6, 3),
              free_area_mm2=round(float(free.sum()) * g * g / 1e6, 3),
              pockets=len(sizes) - (1 if sizes else 0),
              pocket_area_mm2=round(float(sum(v for kk, v in sizes.items() if kk != main)) * g * g / 1e6, 3))
    worst = sorted((c for c in cores), key=lambda c: -(c["street_dist_um"] if c["street_dist_um"] is not None else 1e9))
    return dict(cfg=cfg, streets=st, cores=cores, worst_cores=worst[:10], legs_over_core=over, points_in_core=inside,
                errors=errors, net=net)


def clock_build_legs(build_dir):
    """(legs, points, unplaced) of a die_clock_mesh build dir: htree a->b legs, driver / tree cell sites, and the
    failed-build rows of plan_errors.json / mesh.json unplaced."""
    d = Path(build_dir)
    legs, pts, unpl = [], [], []
    pe = d / "plan_errors.json"
    mf = d / "mesh.json"
    if not mf.is_file() and (d / "mesh" / "mesh.json").is_file():
        mf, pe = d / "mesh" / "mesh.json", d / "mesh" / "plan_errors.json"
    if pe.is_file():
        for r in json.loads(pe.read_text()).get("rows", []):
            if r.get("kind") == "unplaced":
                unpl.append((r.get("name"), r.get("detail")))
    if mf.is_file():
        M = json.loads(mf.read_text())
        for h in M.get("htree", []):
            if h.get("a") and h.get("b"):
                legs.append((f"L{h.get('level')}:{h.get('tag')}", tuple(h["a"]), tuple(h["b"])))
        for key, dr in (M.get("drivers") or {}).items():
            if dr.get("site") and not dr.get("pushdown"):
                pts.append((f"ckm_d_{key}", tuple(dr["site"]), "clock_driver"))
        for u in M.get("unplaced", []) or []:
            unpl.append((str(u[:2]), str(u[2:])))
    return legs, pts, unpl


def render(A, keepouts, png, W, H, title=""):
    """street map: grey = hard cores / PHY, green = street network, yellow = pockets, red = cores over reach,
    magenta = clock legs over a core, blue x = stations / drivers inside a core."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    g = A["cfg"]["raster_um"]
    fig, ax = plt.subplots(figsize=(16, 16 * H / W + 0.8))
    net = A["net"]
    img = np.zeros(net.shape + (4,))
    img[net] = (0.55, 0.85, 0.55, 1.0)
    ax.imshow(img, origin="lower", extent=(0, net.shape[1] * g, 0, net.shape[0] * g), interpolation="nearest")
    bad = {c["name"] for c in A["cores"] if c["street_dist_um"] is None or c["street_dist_um"] > A["cfg"]["reach_um"] + 1e-6}
    for r in keepouts:
        c = "#d62728" if r[4] in bad else ("#9a9a9a" if not is_phy(r[4]) else "#6a6aa0")
        ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc=c, ec="k", lw=0.15, alpha=0.9))
    for o in A["legs_over_core"]:
        ax.plot([o["a"][0], o["b"][0], o["b"][0]], [o["a"][1], o["a"][1], o["b"][1]], "m-", lw=1.2)
    for p in A["points_in_core"]:
        ax.plot([p["xy"][0]], [p["xy"][1]], "bx", ms=5)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    st = A["streets"]
    ax.set_title(f"{title} street map (12.10c): green = streets >= {st['width_um']:g} um, red = {len(bad)} cores > "
                 f"{A['cfg']['reach_um']:g} um from a street, magenta = {len(A['legs_over_core'])} clock legs over a core, "
                 f"x = {len(A['points_in_core'])} stations in a core", fontsize=9)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)
