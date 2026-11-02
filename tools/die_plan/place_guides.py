#!/usr/bin/env python3
"""DIE-S81-47 / DIE-HBM-57: die-agnostic GPL register guides (soft INCLUSIVE regions, released before DPL).

One method for every die (the DIE-HBM-57 PSlice place-prep form, generalised): registers are grouped by the hard
macros / fixed boundary registers they talk to through combinational logic, and each group gets ONE soft region in
the free space beside its anchors.  The regions are applied by the existing kit GPL hook (PRE_GLOBAL_PLACE =
face_flops.tcl sources macro_reg_guide.tcl) and removed before DPL (face_flops_release.tcl sources
macro_reg_guide_release.tcl): the same Tcl, spec format and fail-closed checks as gen_core_kit_hbm.py
--reg-guide-boxes (physical/die_plan/hbm_arch_cores), so HBM register_guides.json files apply unchanged.

    place_guides.py affinity --geom GEOM.tsv [--fixed-ff FACE.txt] --out ff_affinity.json
    place_guides.py build    --geom GEOM.tsv --affinity ff_affinity.json --mode macro|anchor --out guides.json
                             [--macro-group NAME=REGEX ...] [--png proposal.png]
    place_guides.py apply    --kit KIT --guides guides.json      (guides.json: {"boxes": [...]} or a bare HBM list)

GEOM.tsv is the tools/autopilot/geom_dump.tcl dump of a checkpoint (netlist + macro / pin / fixed positions).
Affinity: for every register, the data-cone endpoints (registers, macros, signal ports) of its D and Q, through
combinational cells only, stopping at every register / macro / port; clock pins, --skip-pins nets and nets with more
than --max-fanout sinks are not followed (no broadcast affinity).
Modes:
  macro   (HBM form) a movable register whose macro endpoints all lie in ONE --macro-group joins that group's guide;
          the guide sits at the free point that minimises the longest L1 distance to those macros.
  anchor  macro form + every movable register with a FIXED endpoint (macro, boundary port, face register in
          --fixed-ff, FIRM/LOCKED cell) is sited at the min-max point over ALL its fixed endpoints (a pin-side guide
          when only ports / face registers anchor it, a relay site between a macro and a far face otherwise);
          --ref-anchors adds its movable register endpoints at their --geom (reference placement) position.
Boxes: free = core minus (macros + --halo) minus a --face-band strip on faces that carry fixed registers; registers
with the same snapped target (--snap um) share one box, grown over free grid cells around the target (aspect <= 4 while
possible) until its register area fill <= --ff-fill; boxes stay pairwise disjoint; member sets are written as name prefixes that cover
exactly the members (no other core instance shares a prefix).  Unguided registers stay free.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
HBM = REPO / "physical" / "die_plan" / "hbm_arch_cores"
GEOM_RULES = REPO / "tools" / "autopilot" / "geom_rules.py"
SKIP_PINS = r"^(ck|clk|rst|rst_n|reset|reset_n)(\[\d+\])?$"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def plain(n):
    return n.replace("\\", "")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ affinity
def endpoints(D, skip_pins=SKIP_PINS, max_fanout=64, cap=256):
    """{register cid: (fanin endpoint refs, fanout endpoint refs)}; refs: ('S'|'M', cid) or ('p', k)."""
    sk = re.compile(skip_pins)
    seq = {c for c, v in D.cells.items() if v[0] == "S"}
    mac = {c for c, v in D.cells.items() if v[0] == "M"}
    comb = {c for c, v in D.cells.items() if v[0] in "BLK"}

    def ok_net(n):
        sig, drv, sinks = D.nets[n]
        if sig in ("CLOCK", "POWER", "GROUND") or len(sinks) > max_fanout:
            return False
        if drv and drv[0] == "p" and sk.search(D.pin_by_k[drv[1]]["name"]):
            return False
        return True

    def end_of(r):
        if r[0] == "p":
            return None if sk.search(D.pin_by_k[r[1]]["name"]) else ("p", r[1])
        if r[1] in seq:
            return ("S", r[1])
        if r[1] in mac:
            return ("M", r[1])
        return None

    succ, pred = defaultdict(list), defaultdict(list)
    for c in comb:
        for n in D.drives.get(c, []):
            if not ok_net(n):
                continue
            for s in D.nets[n][2]:
                if s[0] == "i" and not s[2] and s[1] in comb:
                    succ[c].append(s[1])
                    pred[s[1]].append(c)
    # Kahn order over the combinational DAG (cells on a loop are left out and counted)
    indeg = Counter({c: len(pred[c]) for c in comb})
    order, dq = [], deque(c for c in comb if indeg[c] == 0)
    while dq:
        c = dq.popleft()
        order.append(c)
        for t in succ[c]:
            indeg[t] -= 1
            if indeg[t] == 0:
                dq.append(t)
    WIDE = None
    fo, fi = {}, {}

    def add(acc, s):
        if acc is WIDE or s is WIDE:
            return WIDE
        acc |= s
        return WIDE if len(acc) > cap else acc

    for c in reversed(order):                      # fanout endpoints
        acc = set()
        for n in D.drives.get(c, []):
            if not ok_net(n):
                continue
            for s in D.nets[n][2]:
                if s[0] == "i" and s[2]:
                    continue
                if s[0] == "i" and s[1] in comb:
                    acc = add(acc, fo.get(s[1], set()))
                else:
                    e = end_of(s)
                    if e:
                        acc = add(acc, {e})
                if acc is WIDE:
                    break
            if acc is WIDE:
                break
        fo[c] = acc

    def drivers_in(c):
        for n, clk in D.cell_in.get(c, []):
            if clk or not ok_net(n):
                continue
            yield n

    for c in order:                                # fanin endpoints
        acc = set()
        for n in drivers_in(c):
            d = D.nets[n][1]
            if d is None:
                continue
            if d[0] == "i" and d[1] in comb:
                acc = add(acc, fi.get(d[1], set()))
            else:
                e = end_of(d)
                if e:
                    acc = add(acc, {e})
            if acc is WIDE:
                break
        fi[c] = acc
    out, wide = {}, Counter()
    for r in seq:
        ins, outs = set(), set()
        for n in drivers_in(r):
            d = D.nets[n][1]
            if d is None:
                continue
            if d[0] == "i" and d[1] in comb:
                s = fi.get(d[1], set())
                if s is WIDE:
                    wide["fanin"] += 1
                else:
                    ins |= s
            else:
                e = end_of(d)
                if e:
                    ins.add(e)
        for n in D.drives.get(r, []):
            if not ok_net(n):
                continue
            for s in D.nets[n][2]:
                if s[0] == "i" and s[2]:
                    continue
                if s[0] == "i" and s[1] in comb:
                    t = fo.get(s[1], set())
                    if t is WIDE:
                        wide["fanout"] += 1
                    else:
                        outs |= t
                else:
                    e = end_of(s)
                    if e:
                        outs.add(e)
        ins.discard(("S", r))
        outs.discard(("S", r))
        out[r] = (ins, outs)
    return out, dict(comb_loop_cells=len(comb) - len(order), wide_cones=dict(wide))


def fixed_set(D, fixed_ff_file=None):
    """registers that do not move in GPL: FIRM/LOCKED status in the dump + the face-register list (name first column)."""
    names = set()
    if fixed_ff_file:
        for ln in Path(fixed_ff_file).read_text().splitlines():
            if ln.strip():
                names.add(plain(ln.split("\t")[0]))
    st = D.extra.get("status", {})
    return {c for c, v in D.cells.items() if v[0] == "S" and (plain(v[6]) in names or st.get(c) in ("FIRM", "LOCKED"))}


def affinity(D, fixed_ff_file=None, nbr_cap=64, **kw):
    ep, info = endpoints(D, **kw)
    fixed = fixed_set(D, fixed_ff_file)
    rows = []
    for r, (ins, outs) in ep.items():
        c = D.cells[r]
        both = ins | outs
        rows.append(dict(ff=plain(c[6]), cid=r, area=round((c[4] - c[2]) * (c[5] - c[3]), 5), fixed=r in fixed,
                         xy=[round((c[2] + c[4]) / 2, 3), round((c[3] + c[5]) / 2, 3)],
                         macros=sorted(plain(D.cells[e[1]][6]) for e in both if e[0] == "M"),
                         pins=sorted(D.pin_by_k[e[1]]["name"] for e in both if e[0] == "p"),
                         fixed_ffs=sorted(plain(D.cells[e[1]][6]) for e in both if e[0] == "S" and e[1] in fixed),
                         ffs=sum(1 for e in both if e[0] == "S"),
                         ff_nbrs=sorted(plain(D.cells[e[1]][6]) for e in both
                                        if e[0] == "S" and e[1] not in fixed)[:nbr_cap]))
    rows.sort(key=lambda x: x["ff"])
    return dict(schema="opentallas.place_guides.affinity.v1", registers=len(rows), fixed=len(fixed), **info,
                rows=rows)


# ------------------------------------------------------------------------------------------------ geometry
class Grid:
    def __init__(self, core, pitch):
        self.x0, self.y0, self.x1, self.y1 = core
        self.p = pitch
        self.nx = int((self.x1 - self.x0) // pitch)
        self.ny = int((self.y1 - self.y0) // pitch)
        self.free = [[True] * self.ny for _ in range(self.nx)]

    def box(self, i0, j0, i1, j1):          # inclusive cell range -> um box
        return [round(self.x0 + i0 * self.p, 3), round(self.y0 + j0 * self.p, 3),
                round(self.x0 + (i1 + 1) * self.p, 3), round(self.y0 + (j1 + 1) * self.p, 3)]

    def block(self, b):
        """mark every grid cell that touches box b (um) as taken."""
        i0 = max(0, int((b[0] - self.x0) // self.p))
        j0 = max(0, int((b[1] - self.y0) // self.p))
        i1 = min(self.nx - 1, int((b[2] - self.x0 - 1e-9) // self.p))
        j1 = min(self.ny - 1, int((b[3] - self.y0 - 1e-9) // self.p))
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                self.free[i][j] = False

    def centre(self, i, j):
        return self.x0 + (i + 0.5) * self.p, self.y0 + (j + 0.5) * self.p


def l1_to_box(x, y, b):
    return max(b[0] - x, 0.0, x - b[2]) + max(b[1] - y, 0.0, y - b[3])


class Anchors:
    """max L1 distance to a set of boxes (exact) and points (exact through the 4 extremes of x+y and x-y)."""

    def __init__(self, boxes=(), pts=()):
        self.boxes = sorted(set(boxes))
        u = [x + y for x, y in pts]
        v = [x - y for x, y in pts]
        self.ext = (min(u), max(u), min(v), max(v)) if pts else None

    @classmethod
    def merge(cls, items):
        m = cls()
        m.boxes = sorted({b for a in items for b in a.boxes})
        ex = [a.ext for a in items if a.ext]
        m.ext = (min(e[0] for e in ex), max(e[1] for e in ex), min(e[2] for e in ex), max(e[3] for e in ex)) if ex else None
        return m

    def cost(self, x, y):
        c = max((l1_to_box(x, y, b) for b in self.boxes), default=0.0)
        if self.ext:
            u, v = x + y, x - y
            c = max(c, u - self.ext[0], self.ext[1] - u, v - self.ext[2], self.ext[3] - v)
        return c

    def minimax(self, n=16):
        xs = [b[0] for b in self.boxes] + [b[2] for b in self.boxes]
        ys = [b[1] for b in self.boxes] + [b[3] for b in self.boxes]
        if self.ext:                                     # bounding corners of the point set
            u0, u1, v0, v1 = self.ext
            xs += [(u0 + v0) / 2, (u1 + v1) / 2]
            ys += [(u0 - v1) / 2, (u1 - v0) / 2]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        best = None
        for t in range(n + 1):
            for w in range(n + 1):
                x, y = x0 + (x1 - x0) * t / n, y0 + (y1 - y0) * w / n
                c = self.cost(x, y)
                if best is None or c < best[0]:
                    best = (c, x, y)
        return best


def grow(G, cost, need_cells, stride=2, max_aspect=4.0):
    """seed = free cell of least cost; grow a free rectangle, each step taking the side whose new cells have the
    least worst cost, until it holds need_cells cells or cannot grow.  -> (i0, j0, i1, j1, worst cost) or None."""
    best = None
    for i in range(0, G.nx, stride):
        for j in range(0, G.ny, stride):
            if G.free[i][j]:
                c = cost(*G.centre(i, j))
                if best is None or c < best[0]:
                    best = (c, i, j)
    if best is None:
        return None
    _, i, j = best
    for a in range(max(0, i - stride), min(G.nx, i + stride + 1)):      # refine around the coarse seed
        for b in range(max(0, j - stride), min(G.ny, j + stride + 1)):
            if G.free[a][b]:
                c = cost(*G.centre(a, b))
                if c < best[0]:
                    best = (c, a, b)
    _, i, j = best
    i0 = i1 = i
    j0 = j1 = j
    worst = best[0]
    while (i1 - i0 + 1) * (j1 - j0 + 1) < need_cells:
        opts = []
        for side in ("l", "r", "d", "u"):
            if side == "l" and i0 > 0:
                cells = [(i0 - 1, jj) for jj in range(j0, j1 + 1)]
            elif side == "r" and i1 < G.nx - 1:
                cells = [(i1 + 1, jj) for jj in range(j0, j1 + 1)]
            elif side == "d" and j0 > 0:
                cells = [(ii, j0 - 1) for ii in range(i0, i1 + 1)]
            elif side == "u" and j1 < G.ny - 1:
                cells = [(ii, j1 + 1) for ii in range(i0, i1 + 1)]
            else:
                continue
            if all(G.free[a][b] for a, b in cells):
                w = i1 - i0 + 1 + (side in "lr")
                h = j1 - j0 + 1 + (side in "du")
                opts.append((max(w, h) / min(w, h) > max_aspect, max(cost(*G.centre(a, b)) for a, b in cells), side))
        if not opts:
            break
        _, c, side = min(opts)          # compact first (aspect <= max_aspect), then the least worst anchor distance
        worst = max(worst, c)
        if side == "l":
            i0 -= 1
        elif side == "r":
            i1 += 1
        elif side == "d":
            j0 -= 1
        else:
            j1 += 1
    return i0, j0, i1, j1, worst


def pure_prefixes(members, all_names):
    """shortest name prefixes (cut at '.', '[' or ']' boundaries) that cover exactly `members` among `all_names`."""
    members = set(members)
    cuts = re.compile(r"[.\[\]]")

    def heads(n):
        out = [n[:m.end()] for m in cuts.finditer(n)]
        return out + [n]
    tot, mem = Counter(), Counter()
    for n in all_names:
        for h in set(heads(n)):
            tot[h] += 1
    for n in members:
        for h in set(heads(n)):
            mem[h] += 1
    chosen = set()
    for n in sorted(members):
        for h in heads(n):
            if tot[h] == mem[h]:
                chosen.add(h)
                break
    # drop prefixes nested under a shorter chosen prefix
    return sorted(p for p in chosen if not any(q != p and p.startswith(q) for q in chosen))


def build(D, aff, mode="macro", macro_groups=(), halo=4.32, pitch=2.16, snap=43.2, ff_fill=0.20, min_ff=16,
          face_band=None, max_boxes=48, ref_anchors=False):
    core = D.extra["core"]
    cells = D.cells
    by_name = {plain(v[6]): c for c, v in cells.items()}
    macros = {plain(v[6]): [v[2], v[3], v[4], v[5]] for v in cells.values() if v[0] == "M"}
    pins = {p["name"]: (p["x"], p["y"]) for p in D.pins}
    groups = [(n, re.compile(rx)) for n, rx in macro_groups]

    def mgroup(m):
        for n, rx in groups:
            if rx.search(m):
                return n
        return m.split("[", 1)[0] if groups == [] else None

    G = Grid(core, pitch)
    for b in macros.values():
        G.block([b[0] - halo, b[1] - halo, b[2] + halo, b[3] + halo])
    fixed_rows = [r for r in aff["rows"] if r["fixed"]]
    if face_band is None:
        face_band = 2 * halo
    for r in fixed_rows:                           # keep the face registers' strip free (0 overlap with them)
        x, y = r["xy"]
        G.block([x - face_band, y - face_band, x + face_band, y + face_band])
    ref_xy = {r["ff"]: tuple(r["xy"]) for r in aff["rows"]}
    tgt, why = {}, Counter()
    for r in aff["rows"]:
        if r["fixed"]:
            continue
        ms = r["macros"]
        gs = {mgroup(m) for m in ms}
        anchors = []
        if mode == "macro":
            if not ms:
                why["no_macro"] += 1
                continue
            if len(gs) != 1 or None in gs:
                why["multi_or_ungrouped_macro"] += 1
                continue
            anchors = [("M", m) for m in ms]
            key = next(iter(gs))
        else:
            anchors = [("M", m) for m in ms] + [("P", p) for p in r["pins"]] + [("F", f) for f in r["fixed_ffs"]]
            if not anchors:
                why["no_fixed_endpoint"] += 1
                continue
            if ms and (len(gs) != 1 or None in gs) and not (r["pins"] or r["fixed_ffs"]):
                why["multi_or_ungrouped_macro"] += 1
                continue
            key = (next(iter(gs)) if len(gs) == 1 and None not in gs else "mixed") if ms else "face"
            if ref_anchors:                         # movable register neighbours at their reference (dump) position
                anchors += [("F", f) for f in r.get("ff_nbrs", [])]
        boxes, pts = [], []
        for k, a in anchors:
            if k == "M":
                boxes.append(tuple(macros[a]))
            elif k == "P":
                pts.append(pins[a])
            else:
                pts.append(ref_xy[a])
        an = Anchors(boxes, pts)
        best = an.minimax()
        tgt[r["ff"]] = dict(key=key, xy=(best[1], best[2]), minimax=best[0], anchors=an, area=r["area"])
    # cluster: same group key + same snapped target tile
    clus = defaultdict(list)
    for n, t in tgt.items():
        clus[(t["key"], int(t["xy"][0] // snap), int(t["xy"][1] // snap))].append(n)
    small = [k for k, v in clus.items() if len(v) < min_ff]
    for k in small:                                 # fold small clusters into the nearest big one of the same key
        big = [b for b, v in clus.items() if b[0] == k[0] and len(v) >= min_ff and b != k]
        if big:
            b = min(big, key=lambda q: abs(q[1] - k[1]) + abs(q[2] - k[2]))
            clus[b] += clus.pop(k)
        else:
            why["small_cluster"] += len(clus.pop(k))
    order = sorted(clus, key=lambda k: -len(clus[k]))
    for k in order[max_boxes:]:
        why["over_max_boxes"] += len(clus.pop(k))
    all_names = [plain(v[6]) for v in cells.values() if v[0] not in ("M",)]
    out, skipped = [], []
    for k in sorted(clus, key=lambda k: -len(clus[k])):
        mem = clus[k]
        area = sum(tgt[n]["area"] for n in mem)
        cost = Anchors.merge([tgt[n]["anchors"] for n in mem]).cost
        need = int(area / ff_fill / (pitch * pitch)) + 1
        g = grow(G, cost, need)
        if g is None:
            skipped.append(dict(key=list(k), ffs=len(mem), reason="no free cell"))
            why["no_free_cell"] += len(mem)
            continue
        i0, j0, i1, j1, worst = g
        box = G.box(i0, j0, i1, j1)
        barea = (box[2] - box[0]) * (box[3] - box[1])
        if area / barea >= 0.5:
            skipped.append(dict(key=list(k), ffs=len(mem), reason=f"box {box} fill {area / barea:.2f} >= 0.5"))
            why["box_too_small"] += len(mem)
            continue
        for i in range(max(0, i0 - 1), min(G.nx, i1 + 2)):      # one grid cell gap keeps boxes disjoint
            for j in range(max(0, j0 - 1), min(G.ny, j1 + 2)):
                G.free[i][j] = False
        name = re.sub(r"[^A-Za-z0-9_]", "_", f"g{len(out)}_{k[0]}")[:48]
        mm = max(tgt[n]["minimax"] for n in mem)
        out.append(dict(name=name, key=k[0], prefixes=pure_prefixes(mem, all_names), box_um=box,
                        ffs=len(mem), ff_area_um2=round(area, 2), box_area_um2=round(barea, 2),
                        ff_fill=round(area / barea, 4), anchor_minimax_um=round(mm, 1),
                        box_worst_anchor_um=round(worst, 1), members=sorted(mem)))
    return dict(schema="opentallas.place_guides.v1", mode=mode, ref_anchors=ref_anchors, halo_um=halo, pitch_um=pitch, snap_um=snap,
                ff_fill=ff_fill, face_band_um=face_band, core_um=list(core),
                registers=aff["registers"], fixed=aff["fixed"], guided=sum(b["ffs"] for b in out),
                unguided=dict(why), skipped=skipped, boxes=out)


def check_overlap(gd, D, fixed_names=()):
    """0 overlap of every box with macros+halo and with fixed (face) registers; boxes pairwise disjoint."""
    halo = gd.get("halo_um", 0)
    errs = []
    bx = [b["box_um"] for b in gd["boxes"]]
    for i, a in enumerate(bx):
        for b in bx[i + 1:]:
            if a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6:
                errs.append(f"boxes overlap {a} {b}")
    for c, v in D.cells.items():
        m = v[0] == "M"
        if not m and plain(v[6]) not in fixed_names:
            continue
        h = halo if m else 0.0
        for g in gd["boxes"]:
            a = g["box_um"]
            e = 1e-6
            if a[0] < v[4] + h - e and v[2] - h + e < a[2] and a[1] < v[5] + h - e and v[3] - h + e < a[3]:
                errs.append(f"{g['name']} overlaps {'macro+halo' if m else 'fixed register'} {plain(v[6])}")
    return errs


def render(D, gd, png, title=""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(11, 11))
    cols = plt.cm.tab20.colors
    for v in D.cells.values():
        if v[0] == "M":
            ax.add_patch(Rectangle((v[2], v[3]), v[4] - v[2], v[5] - v[3], facecolor="0.8", edgecolor="k", lw=.5))
            ax.text((v[2] + v[4]) / 2, (v[3] + v[5]) / 2, "/".join(plain(v[6]).split(".")[-3:-1])[:24], fontsize=5,
                    ha="center")
    for p in D.pins:
        ax.plot(p["x"], p["y"], ",", color="r")
    keys = sorted({b["key"] for b in gd["boxes"]})
    for b in gd["boxes"]:
        x0, y0, x1, y1 = b["box_um"]
        c = cols[keys.index(b["key"]) % len(cols)]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=c, alpha=.35, edgecolor=c, lw=1.2))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{b['name'].split('_')[0]}\n{b['ffs']}", fontsize=5, ha="center",
                va="center")
    X0, Y0, X1, Y1 = D.die
    ax.set(xlim=(X0, X1), ylim=(Y0, Y1), aspect="equal", xlabel="um", ylabel="um",
           title=title or f"{gd['mode']} guides: {len(gd['boxes'])} boxes, {gd['guided']} registers guided")
    handles = [Rectangle((0, 0), 1, 1, color=cols[i % len(cols)], alpha=.5) for i in range(len(keys))]
    ax.legend(handles, keys, fontsize=6, loc="upper right")
    fig.tight_layout()
    fig.savefig(png, dpi=140)


# ------------------------------------------------------------------------------------------------ apply
def spec_rows(boxes, core):
    """the gen_core_kit_hbm --reg-guide-boxes validation + Tcl spec text (one implementation for every die)."""
    H = _load(HBM / "gen_core_kit_hbm.py", "gen_core_kit_hbm")
    rgb = H.reg_guide_boxes_spec(boxes, core)
    spec = " ".join(f"{{{g['name']} {{{' '.join('{' + q + '}' for q in g['prefixes'])}}} "
                    f"{' '.join(H._um(v) for v in g['box_um'])}}}" for g in rgb)
    return rgb, spec


def kit_core(kit):
    cfg = (Path(kit) / "config.mk").read_text()
    m = re.search(r"^export CORE_AREA\s*=\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", cfg, re.M)
    if not m:
        raise SystemExit(f"{kit}/config.mk: no CORE_AREA")
    for hook in ("PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl", "PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl"):
        if hook not in cfg:
            raise SystemExit(f"{kit}/config.mk: GPL hook '{hook}' missing (guides need the face_flops GPL stage)")
    return tuple(float(v) for v in m.groups())


def apply(kit, guides_file, tag="place_guides"):
    kd = Path(kit)
    g = json.loads(Path(guides_file).read_text())
    boxes = g["boxes"] if isinstance(g, dict) else g
    boxes = [dict(name=b["name"], prefixes=b["prefixes"], box_um=b["box_um"]) for b in boxes]
    core = kit_core(kd)
    if (kd / "macro_reg_guide.tcl").exists():
        raise SystemExit(f"{kd}/macro_reg_guide.tcl exists (kit already guided); use a fresh kit copy")
    rgb, spec = spec_rows(boxes, core)
    (kd / "macro_reg_guide.tcl").write_text(
        f"# GENERATED by tools/die_plan/place_guides.py apply ({tag}). Do not edit.\n"
        f"set ::ot_mrg_spec [concat {spec}]\n" + (HBM / "macro_reg_guide.tcl").read_text())
    (kd / "macro_reg_guide_release.tcl").write_text((HBM / "macro_reg_guide_release.tcl").read_text())
    for f_, s_ in (("face_flops.tcl", "macro_reg_guide.tcl"), ("face_flops_release.tcl", "macro_reg_guide_release.tcl")):
        with open(kd / f_, "a") as fh:
            fh.write(f"# {tag}: tools/die_plan/place_guides.py GPL register guides\nsource /work/{s_}\n")
    rec = dict(source="tools/die_plan/place_guides.py apply", tag=tag, boxes=rgb,
               src=dict(file=str(guides_file), sha256=sha(guides_file)))
    (kd / "macro_reg_guide.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rgb


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("affinity")
    a.add_argument("--geom", required=True)
    a.add_argument("--fixed-ff")
    a.add_argument("--skip-pins", default=SKIP_PINS)
    a.add_argument("--max-fanout", type=int, default=64)
    a.add_argument("--out", required=True)
    b = sp.add_parser("build")
    b.add_argument("--geom", required=True)
    b.add_argument("--affinity", required=True)
    b.add_argument("--mode", choices=("macro", "anchor"), default="macro")
    b.add_argument("--macro-group", action="append", default=[], metavar="NAME=REGEX")
    b.add_argument("--halo", type=float, default=4.32)
    b.add_argument("--pitch", type=float, default=2.16)
    b.add_argument("--snap", type=float, default=43.2)
    b.add_argument("--ff-fill", type=float, default=0.20)
    b.add_argument("--min-ff", type=int, default=16)
    b.add_argument("--max-boxes", type=int, default=48)
    b.add_argument("--face-band", type=float)
    b.add_argument("--ref-anchors", action="store_true",
                   help="anchor mode: movable register neighbours also anchor, at their position in --geom")
    b.add_argument("--out", required=True)
    b.add_argument("--png")
    b.add_argument("--title", default="")
    c = sp.add_parser("apply")
    c.add_argument("--kit", required=True)
    c.add_argument("--guides", required=True)
    c.add_argument("--tag", default="place_guides")
    a_ = ap.parse_args(argv)
    if a_.cmd == "apply":
        rgb = apply(a_.kit, a_.guides, a_.tag)
        print(f"PLACE_GUIDES applied {len(rgb)} boxes to {a_.kit}")
        return 0
    GR = _load(GEOM_RULES, "geom_rules")
    D = GR.Design(a_.geom)
    if a_.cmd == "affinity":
        res = affinity(D, a_.fixed_ff, skip_pins=a_.skip_pins, max_fanout=a_.max_fanout)
        res["geom"] = dict(file=a_.geom, sha256=sha(a_.geom))
        Path(a_.out).write_text(json.dumps(res) + "\n")
        n = res["rows"]
        print(f"PLACE_GUIDES affinity {len(n)} registers ({res['fixed']} fixed): "
              f"{sum(1 for r in n if r['macros'])} reach a macro, {sum(1 for r in n if r['pins'])} a port, "
              f"{sum(1 for r in n if r['fixed_ffs'])} a fixed register; loops {res['comb_loop_cells']} wide {res['wide_cones']}")
        return 0
    aff = json.loads(Path(a_.affinity).read_text())
    mg = [tuple(x.split("=", 1)) for x in a_.macro_group]
    gd = build(D, aff, a_.mode, mg, a_.halo, a_.pitch, a_.snap, a_.ff_fill, a_.min_ff, a_.face_band, a_.max_boxes, a_.ref_anchors)
    fixed_names = {r["ff"] for r in aff["rows"] if r["fixed"]}
    gd["overlap_errors"] = check_overlap(gd, D, fixed_names)
    gd["affinity"] = dict(file=a_.affinity, sha256=sha(a_.affinity))
    Path(a_.out).write_text(json.dumps(gd, indent=1) + "\n")
    if a_.png:
        render(D, gd, a_.png, a_.title)
    print(f"PLACE_GUIDES build {a_.mode}: {len(gd['boxes'])} boxes, {gd['guided']} registers guided, "
          f"unguided {gd['unguided']}, max ff_fill {max([b['ff_fill'] for b in gd['boxes']] or [0])}, "
          f"overlap errors {len(gd['overlap_errors'])}")
    return 1 if gd["overlap_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
