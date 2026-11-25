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
  ADV-RECT-OUTLINE     (COORD 11-24) a clock-band rect (landing_contract.bands / band_fixed_um rect_um or rects_um), a
                       tap_windows_um / band_tap_windows_um window, a tap_reserved_um entry or any other landing-contract rect
                       that is not inside its type's outline [0, 0, w, h].  Known positive: R9 svc_ytrade_row.py shrank the S81
                       svc_lo N edges by 34.56 um but moved only two-number points; the band and tap windows stayed outside
                       (t7 attn_i0).
  ADV-BITSITE-AREA     (COORD 11-24 flow review) every explicit bit site -- ft_slots[].bit_sites_um, internal_stations
                       bit_sites_um / face_bit_sites_um and the landing CS banks (clock.soft_reg_banks / soft_reg_banks
                       bit_sites_um) -- whose cell footprint (bit_site_cell_um) is not inside CORE_AREA (off-core) or not
                       inside the outline (off-outline), and footprints that overlap on the core site/row grid (collide).
                       Known positive: S81 c8, 47 types (42 leaf, 5 svc) with bit sites off the core or colliding.

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


# ---------------------------------------------------------------- ADV-RECT-OUTLINE
def _as_rect(v):
    """[x0, y0, x1, y1] or a corner pair [[x0, y0], [x1, y1]] -> normalised (x0, y0, x1, y1); else None"""
    if isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
        x0, y0, x1, y1 = (float(x) for x in v)
    elif isinstance(v, (list, tuple)) and len(v) == 2 and all(_pt(p) and len(p) == 2 for p in v):
        (x0, y0), (x1, y1) = ((float(a), float(b)) for a, b in v)
    else:
        return None
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _rect_list(v):
    """a rect, or a list of rects / corner pairs"""
    r = _as_rect(v)
    if r is not None:
        return [r]
    return [x for x in (_as_rect(e) for e in v) if x] if isinstance(v, (list, tuple)) else []


_LC_RECT_KEY = re.compile(r"(rect|window|reserved|keepout|box|region)", re.I)


def clock_rects(t):
    """-> [(where, rect)] every clock-band / tap-window / tap-reserved / landing-contract rect of a type"""
    ck = t.get("clock") or {}
    out = []

    def band(prefix, b):
        if not isinstance(b, dict):
            return
        for k in ("rect_um", "rects_um", "tap_windows_um"):
            for i, r in enumerate(_rect_list(b.get(k))):
                out.append((f"{prefix}.{k}" + (f"[{i}]" if k != "rect_um" else ""), r))
    lc = ck.get("landing_contract") or {}
    for bn, b in sorted((lc.get("bands") or {}).items() if isinstance(lc.get("bands"), dict) else []):
        band(f"landing_contract.bands.{bn}", b)
    for bn, b in sorted((ck.get("band_fixed_um") or {}).items() if isinstance(ck.get("band_fixed_um"), dict) else []):
        band(f"band_fixed_um.{bn}", b)
    for k in ("band_tap_windows_um", "tap_windows_um", "tap_reserved_um"):
        for i, r in enumerate(_rect_list(ck.get(k))):
            out.append((f"clock.{k}[{i}]", r))

    def walk(x, path):       # other landing-contract rects (bands handled above)
        if isinstance(x, dict):
            for k, v in x.items():
                if path == "landing_contract" and k == "bands":
                    continue
                rl = _rect_list(v) if _LC_RECT_KEY.search(k) and k.endswith("_um") else []
                if rl:
                    for i, r in enumerate(rl):
                        out.append((f"{path}.{k}" + (f"[{i}]" if _as_rect(v) is None else ""), r))
                    continue
                walk(v, f"{path}.{k}")
        elif isinstance(x, list):
            for i, v in enumerate(x):
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}[{i}]")
    walk(lc, "landing_contract")
    return out


def _rect_outline(raw, plan_path, tree=None, **_kw):
    out, n_types, n_rects = [], 0, 0
    kinds = {}
    for tn, t in _types(raw):
        try:
            w, h = (float(v) for v in t["outline_um"][:2])
        except (TypeError, ValueError):
            continue
        bad = []
        for where, r in clock_rects(t):
            n_rects += 1
            over = max(-r[0], -r[1], r[2] - w, r[3] - h)
            if over > EPS:
                bad.append((where, r, over))
        if bad:
            n_types += 1
            for where, _r, _o in bad:
                k = re.sub(r"\[\d+\]", "", where.split(".")[0] if not where.startswith("landing_contract.bands") else "landing_contract.bands")
                kinds[k] = kinds.get(k, 0) + 1
            worst = max(b[2] for b in bad)
            ex = "; ".join(f"{wh} {[round(v, 3) for v in r]} ({o:.2f} um out)" for wh, r, o in bad[:MAX_EX])
            out.append(_w("ADV-RECT-OUTLINE", f"{tn}: {len(bad)} clock rect(s) outside the outline [0, 0, {w:g}, {h:g}] "
                          f"(worst {worst:.2f} um): {ex}{' ...' if len(bad) > MAX_EX else ''}"))
    if out:
        out.append(f"LIST ADV-RECT-OUTLINE {sum(kinds.values())} rect(s) on {n_types} type(s) outside their outline "
                   f"(of {n_rects} checked): " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
    return out


# ---------------------------------------------------------------- ADV-BITSITE-AREA
def bit_sites(t):
    """-> [(family, label, x, y, w, h)] every explicit bit-site cell footprint (lower-left) of a type"""
    out = []
    for fam, key in (("ft", "ft_slots"), ("ist", "internal_stations")):
        for k, e in enumerate(t.get(key) or []):
            if not isinstance(e, dict):
                continue
            w, h = _cell(e)
            nm = e.get("name") or e.get("conn") or k
            for j, st in enumerate(e.get("bit_sites_um") or []):
                for b, xy in enumerate(st or []):
                    if _pt(xy):
                        out.append((fam, f"{key}[{nm}],{j},{b}", float(xy[0]), float(xy[1]), w, h))
            for b, xy in enumerate(e.get("face_bit_sites_um") or []):
                if _pt(xy):
                    out.append((fam, f"{key}[{nm}].face,{b}", float(xy[0]), float(xy[1]), w, h))
    for src in (t.get("soft_reg_banks"), (t.get("clock") or {}).get("soft_reg_banks")):
        for k, e in enumerate(src or []):
            if not isinstance(e, dict):
                continue
            w, h = _cell(e)
            for b, xy in enumerate(e.get("bit_sites_um") or []):
                if _pt(xy):
                    out.append(("land", f"soft_reg_banks[{e.get('id', k)}],{b}", float(xy[0]), float(xy[1]), w, h))
    return out


def site_collisions(sites, origin, site_w=SITE_W, row_h=ROW_H):
    """footprints that overlap once snapped to the core grid (ft_bit_sites.footprint_conflicts semantics, sweep per
    row): -> [(earlier label, label)]; one pair per site that lands on an occupied site/row cell"""
    x0, y0 = origin
    rows = {}
    for i, (_f, lab, x, y, w, h) in enumerate(sites):
        c, r = round((x - x0) / site_w), round((y - y0) / row_h)
        cw, rh = max(1, math.ceil(w / site_w - 1e-6)), max(1, math.ceil(h / row_h - 1e-6))
        for rr in range(r, r + rh):
            rows.setdefault(rr, []).append((c, c + cw, i))
    hit = {}
    for lst in rows.values():
        lst.sort()
        end, owner = None, None
        for c0, c1, i in lst:
            if end is not None and c0 < end and i != owner:
                hit.setdefault(i, owner)
            if end is None or c1 > end:
                end, owner = c1, i
    return [(sites[o][1], sites[i][1]) for i, o in sorted(hit.items())]


def _bitsite_area(raw, plan_path, tree=None, **_kw):
    out, tot = [], dict(types=0, off_core=0, off_outline=0, collide=0, sites=0)
    fams = {}
    for tn, t in _types(raw):
        ss = bit_sites(t)
        if not ss:
            continue
        tot["sites"] += len(ss)
        x0, y0, x1, y1 = (float(v) for v in core_area(t)[:4])
        w, h = (float(v) for v in t["outline_um"][:2])
        off_c, off_o = [], []
        for f, lab, x, y, cw, ch in ss:
            d = max(x0 - x, y0 - y, x + cw - x1, y + ch - y1)
            if d > EPS:
                off_c.append((lab, x, y, d))
                fams[f] = fams.get(f, 0) + 1
                if max(-x, -y, x + cw - w, y + ch - h) > EPS:
                    off_o.append(lab)
        col = site_collisions(ss, (x0, y0))
        if off_c or col:
            tot["types"] += 1
            tot["off_core"] += len(off_c)
            tot["off_outline"] += len(off_o)
            tot["collide"] += len(col)
            parts = []
            if off_c:
                wst = max(off_c, key=lambda e: e[3])
                parts.append(f"{len(off_c)} off CORE_AREA [{x0:g}, {y0:g}, {x1:g}, {y1:g}] ({len(off_o)} off the outline; worst "
                             f"{wst[3]:.2f} um: {wst[0]} at ({wst[1]:g}, {wst[2]:g}))")
            if col:
                parts.append(f"{len(col)} colliding footprint(s) (e.g. {'; '.join(f'{a} x {b}' for a, b in col[:MAX_EX])})")
            out.append(_w("ADV-BITSITE-AREA", f"{tn}: {len(ss)} bit sites: " + "; ".join(parts)))
    if out:
        out.append(f"LIST ADV-BITSITE-AREA {tot['types']} type(s): {tot['off_core']} off-core ({tot['off_outline']} off-outline), "
                   f"{tot['collide']} colliding, of {tot['sites']} bit sites; off-core by family "
                   + (", ".join(f"{k} {v}" for k, v in sorted(fams.items())) or "none"))
    return out


density = _safe("ADV-STATION-DENSITY", _density)
on_row = _safe("ADV-SITE-ON-ROW", _on_row)
region = _safe("ADV-PLACE-REGION", _region)
band_blockage = _safe("ADV-BAND-BLOCKAGE", _band_block)
band_gap = _safe("ADV-BAND-GAP", _band_gap)
rect_outline = _safe("ADV-RECT-OUTLINE", _rect_outline)
bitsite_area = _safe("ADV-BITSITE-AREA", _bitsite_area)
ALL = (("STATION-DENSITY", density), ("SITE-ON-ROW", on_row), ("PLACE-REGION", region), ("BAND-BLOCKAGE", band_blockage), ("BAND-GAP", band_gap),
       ("RECT-OUTLINE", rect_outline), ("BITSITE-AREA", bitsite_area))

if __name__ == "__main__":
    import json
    p = sys.argv[1]
    raw = json.loads(Path(p).read_text())
    for _n, fn in ALL:
        for line in fn(raw, p):
            print(line)
