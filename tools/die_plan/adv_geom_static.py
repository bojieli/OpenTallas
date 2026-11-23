"""Static placement-geometry advisories (COORD flow review 11-22 item 2; estimators, WARN only, never a gate).

Five checks over a composed plan, no kit, no RTL, seconds per plan.  Each has its own plan_advisory CHECKS entry (thin
module adv_<name>.py -> one function here):

  ADV-STATION-DENSITY  exact flop sites (internal_stations / ft_slots bit_sites_um + face_bit_sites_um, soft_reg_banks) per
                       BIN_UM x BIN_UM bin: fill = sites x cell area / free bin area (hard cores cut out).  WARN > FILL_WARN.
                       Known positive: S81 BKSEL packed 3,670 sites into 26 um (place could not legalise them).
  ADV-SITE-ON-ROW      an exact site inside CORE_AREA whose x is not on the 0.054 site grid or whose y is not a 0.27 row origin
                       (both from the CORE_AREA corner): place refuses it ("exact ... site is not on row/site", kit_istations).
                       Sites outside CORE_AREA are ADV-BANK-OFFAREA's.
  ADV-PLACE-REGION     place_regions[] that cannot hold movable cells: inst_re does not compile; box_um / centre_um outside
                       CORE_AREA or box_um with no free area (inside hard cores); every alternation term of inst_re a literal
                       name of a FIRM plan-placed instance (relay_sites keys / reset_pin_relay / reach_homes): the region has 0
                       movable cells and RePlAce diverges (GPL-0304).  Known positive: HEAD LEP-RINGCTL-1 hd_lep0N_w
                       ringctl_coll_i0/i1/i2 (each matched only its 2 FIRM control registers).
  ADV-BAND-BLOCKAGE    clock.landing_contract.bands[].rect_um overlapping a hard core (+ HALO_UM) on >= 25 % of its rect: the
                       landing flops of the band cannot sit there.  Known positive: QC slw_st_a CLAND band over a core halo.
  ADV-BAND-GAP         a band whose free area (rect minus hard cores + halo and the exact sites inside it) cannot hold its
                       padded_data_storage_flops (else live) at 100 % fill (area_reserve_um2 is a budget, not the rect).  Known positive:
                       KV kv3_hgi_v8 band free-gap.

findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-<NAME> ..."]; an exception is one "not checked" line.
"""
import math
import re
import sys
from pathlib import Path

CELL = (1.404, 0.27)          # async-reset DFF footprint (bit_site_cell_um default)
SITE_W, ROW_H = 0.054, 0.27
BIN_UM = 10.0
FILL_WARN = 0.7            # band reserve sizing (padded flops x cell / FILL_WARN)
DENSITY_WARN = 1.0         # exact-site fill of a bin's free area: > 1.0 cannot legalise (BKSEL 3,670 sites in 26 um = 2.1)
BLOCK_FRAC_WARN = 0.25     # a band blocked on >= 25 % of its rect (hard cores + halo; clock.keepouts_um are TAP keep-outs, not placement)
HALO_UM = 2.16
EPS = 1e-6
MAX_EX = 3
ROT = ("R90", "R270", "MXR90", "MYR90")


def _w(check, *parts):
    return " ".join(["WARN", check] + [str(p) for p in parts])


def core_area(t):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from kit_fit import kit_core_area
        return kit_core_area(t)
    except Exception:  # noqa: BLE001 -- fixture / older tree: the default inset
        w, h = t["outline_um"]
        return [4.32, 4.32, w - 4.32, h - 4.32]


def _cell(row):
    c = row.get("bit_site_cell_um") or row.get("cell_um") or CELL
    try:
        return float(c[0]), float(c[1])
    except (TypeError, ValueError, IndexError):
        return CELL


def _pt(xy):
    return isinstance(xy, (list, tuple)) and len(xy) >= 2 and all(isinstance(v, (int, float)) for v in xy[:2])


def exact_sites(t, keys=("internal_stations", "ft_slots")):
    """-> [(row label, x, y, cw, ch)] of every exact flop site of a type (ft_slots sites as planned; gen snaps them to the grid)"""
    out = []
    for key in keys:
        for k, e in enumerate(t.get(key) or []):
            if not isinstance(e, dict):
                continue
            cw, ch = _cell(e)
            lab = f"{key}[{k}]" + (f" {e['name']}" if e.get("name") else "")
            for st in e.get("bit_sites_um") or []:
                for xy in st or []:
                    if _pt(xy):
                        out.append((lab, float(xy[0]), float(xy[1]), cw, ch))
            for xy in e.get("face_bit_sites_um") or []:
                if _pt(xy):
                    out.append((lab, float(xy[0]), float(xy[1]), cw, ch))
    for k, e in enumerate(t.get("soft_reg_banks") or []):
        if not isinstance(e, dict):
            continue
        cw, ch = _cell(e)
        for xy in e.get("bit_sites_um") or []:
            if _pt(xy):
                out.append((f"soft_reg_banks[{k}] {e.get('id', '')}".strip(), float(xy[0]), float(xy[1]), cw, ch))
    return out


def hard_rects(t, halo=0.0):
    """-> [(x0, y0, x1, y1, name)] hard cores / lef contents (+ halo)"""
    out = []
    for h in list(t.get("hard_cores") or []) + [c for c in (t.get("contents") or []) if isinstance(c, dict) and c.get("lef")]:
        try:
            (x0, y0), (w, hh) = h["origin_um"], h["outline_um"]
        except (KeyError, TypeError, ValueError):
            continue
        if h.get("orient", "R0") in ROT:
            w, hh = hh, w
        out.append((x0 - halo, y0 - halo, x0 + w + halo, y0 + hh + halo, h.get("inst") or h.get("name") or "core"))
    return out


def keepouts(t):
    return [tuple(r[:4]) + ("keepout",) for r in ((t.get("clock") or {}).get("keepouts_um") or []) if isinstance(r, (list, tuple)) and len(r) >= 4]


def _ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _union_area(clip, rects, step=0.54):
    """area of clip covered by the union of rects (grid sampling at `step`; exact enough for an estimator)"""
    rs = [r for r in rects if _ov(clip, r) > 0]
    if not rs:
        return 0.0
    if len(rs) == 1:
        return _ov(clip, rs[0])
    xs = sorted({clip[0], clip[2]} | {min(max(v, clip[0]), clip[2]) for r in rs for v in (r[0], r[2])})
    ys = sorted({clip[1], clip[3]} | {min(max(v, clip[1]), clip[3]) for r in rs for v in (r[1], r[3])})
    a = 0.0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in rs):
                a += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return a


def _types(raw):
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if isinstance(t, dict) and t.get("outline_um"):
            yield tn, t


def _safe(check, fn):
    def run(raw, plan_path, tree=None, **kw):
        try:
            return fn(raw, plan_path, tree, **kw)
        except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
            return [_w(check, "not checked", f"{type(e).__name__}: {str(e)[:200]}")]
    return run


# ---------------------------------------------------------------- ADV-STATION-DENSITY
def _density(raw, plan_path, tree=None, bin_um=BIN_UM, fill_warn=DENSITY_WARN, **_kw):
    out = []
    for tn, t in _types(raw):
        bins = {}
        for lab, x, y, cw, ch in exact_sites(t):
            k = (int(x // bin_um), int(y // bin_um))
            b = bins.setdefault(k, [0, 0.0, set()])
            b[0] += 1
            b[1] += cw * ch
            b[2].add(lab)
        if not bins:
            continue
        hr = hard_rects(t)
        over = []
        for (bx, by), (n, a, labs) in bins.items():
            box = (bx * bin_um, by * bin_um, (bx + 1) * bin_um, (by + 1) * bin_um)
            free = bin_um * bin_um - _union_area(box, hr)
            fill = a / free if free > EPS else math.inf
            if fill > fill_warn:
                over.append((fill, n, box, sorted(labs)))
        if over:
            over.sort(key=lambda o: -o[0])
            f, n, box, labs = over[0]
            tot = sum(o[1] for o in over)
            out.append(_w("ADV-STATION-DENSITY", f"{tn}: {len(over)} {bin_um:g}-um bin(s) over {fill_warn:g} exact-site fill ({tot} sites); worst "
                          f"[{box[0]:g} {box[1]:g}] {n} sites fill {'inf' if f == math.inf else f'{f:.2f}'} from {', '.join(labs[:3])}"
                          f"{' ...' if len(labs) > 3 else ''}: place cannot legalise them; spread the bank sites"))
    return out


# ---------------------------------------------------------------- ADV-SITE-ON-ROW
def _on_row(raw, plan_path, tree=None, **_kw):
    out = []
    for tn, t in _types(raw):
        x0, y0, x1, y1 = core_area(t)
        bad = []
        for lab, x, y, cw, ch in exact_sites(t, keys=("internal_stations",)):   # ft_slots sites are snapped by gen (ft_bit_sites.snap_slots)
            if x < x0 - EPS or y < y0 - EPS or x + cw > x1 + EPS or y + ch > y1 + EPS:
                continue                               # ADV-BANK-OFFAREA
            dx = (x - x0) / SITE_W
            dy = (y - y0) / ROW_H
            if abs(dx - round(dx)) * SITE_W > 1e-3 or abs(dy - round(dy)) * ROW_H > 1e-3:
                bad.append((lab, x, y))
        if bad:
            rows = sorted({b[0] for b in bad})
            out.append(_w("ADV-SITE-ON-ROW", f"{tn}: {len(bad)} exact site(s) off the row/site grid (x0 {x0:g} + k x {SITE_W}, y0 {y0:g} + k x {ROW_H}) "
                          f"on {len(rows)} row(s) ({', '.join(rows[:4])}{' ...' if len(rows) > 4 else ''}); place refuses them: "
                          + "; ".join(f"{b[0]} ({b[1]:g},{b[2]:g})" for b in bad[:MAX_EX])))
    return out


# ---------------------------------------------------------------- ADV-PLACE-REGION
_META = re.compile(r"[.*+?\[\](){}|\\^$]")


def _terms(rx):
    """top-level alternation terms of a regex with ^ / $ anchors and \\. / \\[ escapes removed; None when a term has a wildcard"""
    s = rx.strip()
    if s.startswith("^(") and s.endswith(")$"):
        s = s[2:-2]
    elif s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    out = []
    for term in s.split("|"):
        lit = re.sub(r"\\([.\[\]/])", r"\1", term.strip("^$"))
        if _META.search(lit.replace(".", "").replace("[", "").replace("]", "")):
            return None
        out.append(lit)
    return out


def _region(raw, plan_path, tree=None, **_kw):
    out = []
    for tn, t in _types(raw):
        regs = t.get("place_regions") or []
        if not regs:
            continue
        x0, y0, x1, y1 = core_area(t)
        hr = hard_rects(t)
        firm = set((t.get("relay_sites") or {}).keys()) | set((t.get("reach_homes") or {}) if isinstance(t.get("reach_homes"), dict) else ())
        for e in t.get("reset_pin_relay") or []:
            if isinstance(e, dict):
                firm.update(str(v) for k, v in e.items() if k in ("inst", "name"))
        for r in regs:
            if not isinstance(r, dict):
                continue
            nm, rx = r.get("name", "?"), r.get("inst_re", "")
            why = []
            try:
                re.compile(rx)
            except re.error as e:
                why.append(f"inst_re does not compile ({e})")
            b = r.get("box_um")
            if isinstance(b, (list, tuple)) and len(b) == 4:
                if b[2] - b[0] <= EPS or b[3] - b[1] <= EPS:
                    why.append(f"box_um {b} is empty")
                elif b[0] < x0 - EPS or b[1] < y0 - EPS or b[2] > x1 + EPS or b[3] > y1 + EPS:
                    why.append(f"box_um {b} leaves CORE_AREA [{x0:g} {y0:g} {x1:g} {y1:g}]")
                elif _union_area(tuple(b), hr) >= (b[2] - b[0]) * (b[3] - b[1]) - EPS:
                    why.append(f"box_um {b} lies entirely under hard cores")
            c = r.get("centre_um")
            if isinstance(c, (list, tuple)) and len(c) == 2 and not (x0 <= c[0] <= x1 and y0 <= c[1] <= y1):
                why.append(f"centre_um {c} outside CORE_AREA")
            terms = _terms(rx) if not why else None
            if terms and firm:
                hit = [x for x in terms if any(x in f or f in x for f in firm)]
                if len(hit) == len(terms):
                    why.append(f"every inst_re term names a FIRM plan-placed instance ({', '.join(terms[:3])}): 0 movable cells "
                               f"(RePlAce GPL-0304 diverges; cone {r.get('cone', 'auto')})")
            if why:
                out.append(_w("ADV-PLACE-REGION", f"{tn}: place_regions {nm}: " + "; ".join(why)))
    return out


# ---------------------------------------------------------------- bands
def _bands(t):
    """soft landing bands only: a band realised as its own hard ring child core (cl_<band>, KV-HGSPLIT) is a macro, not rows"""
    for nm, b in sorted((((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).items()):
        r = b.get("rect_um") if isinstance(b, dict) else None
        if isinstance(r, (list, tuple)) and len(r) == 4 and r[2] > r[0] and r[3] > r[1]:
            yield nm, b, tuple(float(v) for v in r)


def _own(nm, b, o):
    """the band's own realisation (cl_<band> hard ring child / its declared instance) is not a blockage of the band"""
    n = str(o[4])
    return n in (f"cl_{nm}", str(b.get("instance") or "\0"), nm) or n.endswith(f"_{nm}") and n.startswith("cl")


def _hard_band(t, nm):
    return any(str(o[4]) == f"cl_{nm}" for o in hard_rects(t))


def _band_block(raw, plan_path, tree=None, halo=HALO_UM, **_kw):
    out = []
    for tn, t in _types(raw):
        blk = hard_rects(t, halo)
        for nm, b, r in _bands(t):
            if _hard_band(t, nm):
                continue
            own = [o for o in blk if _ov(r, o) > EPS and not _own(nm, b, o)]
            hits = [(o[4], _ov(r, o)) for o in own]
            area = (r[2] - r[0]) * (r[3] - r[1])
            cov = _union_area(r, own) if hits else 0.0
            if hits and cov >= BLOCK_FRAC_WARN * area:
                out.append(_w("ADV-BAND-BLOCKAGE", f"{tn}: landing band {nm} rect {list(r)} overlaps {len(hits)} blockage(s) "
                              f"({', '.join(h[0] for h in hits[:3])}; hard cores +{halo:g} um halo): {cov:.0f} of {area:.0f} um2 "
                              f"({cov / area:.0%}) blocked; move the band clear of the core halo"))
    return out


def _band_gap(raw, plan_path, tree=None, halo=HALO_UM, fill_warn=FILL_WARN, **_kw):
    out = []
    for tn, t in _types(raw):
        blk = hard_rects(t, halo)
        sites = exact_sites(t)
        for nm, b, r in _bands(t):
            if _hard_band(t, nm):
                continue
            area = (r[2] - r[0]) * (r[3] - r[1])
            free = area - _union_area(r, [o for o in blk if not _own(nm, b, o)])
            used = sum(cw * ch for _l, x, y, cw, ch in sites if r[0] <= x < r[2] and r[1] <= y < r[3])
            free -= used
            # demand = the flops the band must hold at 100 % fill (area_reserve_um2 is a budget that may exceed the rect by design)
            n = b.get("padded_data_storage_flops") or b.get("live_data_storage_flops")
            need = n * CELL[0] * CELL[1] if isinstance(n, (int, float)) and n > 0 else None
            if need is not None and free < need - EPS:
                out.append(_w("ADV-BAND-GAP", f"{tn}: landing band {nm} free area {max(free, 0):.0f} um2 < {n} flops x {CELL[0] * CELL[1]:.3f} = {need:.0f} um2 at 100 % fill "
                              f"(rect {area:.0f} um2 minus hard cores +{halo:g} halo and {used:.0f} um2 of exact sites): the band flops "
                              f"cannot all land; widen the band or move it into free rows"))
    return out


density = _safe("ADV-STATION-DENSITY", _density)
on_row = _safe("ADV-SITE-ON-ROW", _on_row)
region = _safe("ADV-PLACE-REGION", _region)
band_blockage = _safe("ADV-BAND-BLOCKAGE", _band_block)
band_gap = _safe("ADV-BAND-GAP", _band_gap)
ALL = (("STATION-DENSITY", density), ("SITE-ON-ROW", on_row), ("PLACE-REGION", region), ("BAND-BLOCKAGE", band_blockage), ("BAND-GAP", band_gap))

if __name__ == "__main__":
    import json
    p = sys.argv[1]
    raw = json.loads(Path(p).read_text())
    for _n, fn in ALL:
        for line in fn(raw, p):
            print(line)
