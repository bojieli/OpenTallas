#!/usr/bin/env python3
"""adv_density.py -- PRECHECK-R2 static advisory ADV-DENSITY (COORD 11-22; owner 11-19: an estimator, never a gate).

Std-cell density of every placed soft type of a composed plan, BEFORE its next kit:

  density = measured synth std cells / um2 of the piece outline not under a hard core (hard_cores[] union, clipped)

the same definition as cell_check.py (PLAN-GEN-RULES-1 rule C, flag 0.42 = route_supply GRT-pass limit), so a type
that is re-cut (strip/body split, outline shrink, cores moved in) is judged on its NEW soft area with its measured
cell count.  A piece is any plan partition type: a strip/body split piece is its own type (type_split), so it is
measured on its own outline.  WARN at >= DENS_WARN (0.6 cells/um2; the 0.42 rule-C limit is quoted in the fix).

Cell counts (no synthesis here): a cache of the kit-wave result.json counts (harvest_cells.py; cells = the kit's
native_cell_count stdcells / synth_stat 'Number of cells', top only, block macros excluded) keyed die -> type, the
exact type first, else the newest kit of the same base type (cohort suffixes __cl<hex>/__pv<hex> stripped: same
logic, other pins/landing), else plan type.cells on a type without hard cores.  A type with none is counted as
unmeasured (summary line).

Calibration (cache 11-22, 668 measured kits): QC hc types sign at 0.78-0.91 cells/um2 (SRAM-dense, cells small),
so a type whose own (or base) kit PLACED at a density >= today's is not re-warned (measured evidence beats the
estimate); the warning is for densities no kit of that logic has placed: S81 lepe_mu_C t1 strip_S 0.907 (place FAIL,
OT_CLAND band, FLOW-STRIPBODY-R2), svc_*_rs (>= 2.5, place FAIL).  The landing-band reserve (clock.landing_contract
.bands rect_um) is reported as the net density on the area left for logic.  place_regions[].util > 0.6 is also
warned (a plan-declared region target over the same limit).

    findings(raw, plan_path, tree=None, cells_cache=None|path|dict, warn=0.6) -> ["WARN ADV-DENSITY ..."]
"""
import json
import math
import os
import re
from pathlib import Path

CHECK = "DENSITY"
DENS_WARN = 0.6          # cells / soft um2 (COORD 11-22 request: ~0.6)
RULE_C = 0.42            # cell_check.DENS_FLAG (route_supply FLAG_AT["dens"])
REGION_UTIL_WARN = 0.6
CELL_AREA_UM2 = 0.14     # precheck.CELL_AREA_UM2 (mean ASAP7 std cell), for the quoted std-cell area fraction
MAX_LINES = 20
SUFFIX = re.compile(r"(?:__(?:cl|pv)[0-9a-f]{6,})+$")
CACHE_ENV = "OT_ADV_CELLS_CACHE"
CACHE_DEFAULTS = ("adv_cache/cells_cache.json",                     # next to this module (tools/die_plan/adv_cache)
                  "/srv/opentallas-scratch2/claude/precheck-cache/cells_cache.json")


def _w(obj, msg):
    return f"WARN ADV-{CHECK} {obj}: {msg}"


def base_type(tn):
    return SUFFIX.sub("", tn)


def union_area(rects):
    """area of a union of axis-aligned rects [(x0, y0, x1, y1)] (cell_check.union_area)."""
    rects = [r for r in rects if r[2] > r[0] and r[3] > r[1]]
    if not rects:
        return 0.0
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    a = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        iv = sorted((r[1], r[3]) for r in rects if r[0] <= x0 and r[2] >= x1)
        cov, cur = 0.0, None
        for lo, hi in iv:
            if cur is None or lo > cur[1]:
                if cur:
                    cov += cur[1] - cur[0]
                cur = [lo, hi]
            else:
                cur[1] = max(cur[1], hi)
        if cur:
            cov += cur[1] - cur[0]
        a += cov * (x1 - x0)
    return a


def core_rects(t):
    w, h = map(float, t["outline_um"])
    rr = []
    for hc in t.get("hard_cores") or []:
        try:
            ox, oy = map(float, hc["origin_um"])
            cw, ch = map(float, hc["outline_um"])
        except (KeyError, TypeError, ValueError):
            continue
        rr.append((max(0.0, ox), max(0.0, oy), min(w, ox + cw), min(h, oy + ch)))
    return rr


def soft_area(t):
    """(soft um2, core um2): outline not under a hard core (cell_check.soft_area)."""
    w, h = map(float, t["outline_um"])
    c = union_area(core_rects(t))
    return w * h - c, c


def band_area(t):
    """um2 of the landing-band reserve rects (clock.landing_contract.bands[*].rect_um) outside the hard cores."""
    w, h = map(float, t["outline_um"])
    bands = (((t.get("clock") or {}).get("landing_contract") or {}).get("bands")) or {}
    rr = []
    for b in bands.values() if isinstance(bands, dict) else []:
        r = (b or {}).get("rect_um") if isinstance(b, dict) else None
        if isinstance(r, (list, tuple)) and len(r) == 4:
            rr.append((max(0.0, float(r[0])), max(0.0, float(r[1])), min(w, float(r[2])), min(h, float(r[3]))))
    if not rr:
        return 0.0
    cores = core_rects(t)
    return max(0.0, union_area(rr + cores) - union_area(cores))


def load_cache(src):
    if isinstance(src, dict):
        return src, "<dict>"
    cands = [src] if src else []
    if os.environ.get(CACHE_ENV):
        cands.insert(0, os.environ[CACHE_ENV])
    here = Path(__file__).resolve().parent
    cands += [str(here / CACHE_DEFAULTS[0]), CACHE_DEFAULTS[1]]
    for c in cands:
        if c and os.path.isfile(c):
            with open(c) as f:
                return json.load(f), c
    return None, None


def _rec(entry):
    """(newest record, newest placed record) of a cache entry (v2 {last, placed}; v1 flat record)."""
    if not isinstance(entry, dict):
        return None, None
    if "last" in entry or "placed" in entry:
        return entry.get("last"), entry.get("placed")
    return entry, (entry if entry.get("stage") in ("geom", "geom_run") else None)


def cells_for(tn, t, dc, by_base):
    """(cells, basis, newest rec, placed rec) for a type, or (None, why, None, None)."""
    if tn in dc:
        last, pl = _rec(dc[tn])
        if last and last.get("cells"):
            return int(last["cells"]), "kit", last, pl
    b = base_type(tn)
    cands = [n for n in by_base.get(b, []) if n != tn]
    if cands:
        best = max(cands, key=lambda n: (_rec(dc[n])[0] or {}).get("t0", 0))
        last, pl = _rec(dc[best])
        if last and last.get("cells"):
            # placed evidence of a sibling cohort counts only on the same outline (same soft area)
            return int(last["cells"]), f"base kit {best}", last, pl
    if t.get("cells") and not t.get("hard_cores"):
        return int(t["cells"]), "plan type.cells", None, None
    return None, "unmeasured", None, None


def _kit_word(rec):
    if not rec:
        return ""
    import time
    st = f"{rec.get('stage')} {rec.get('verdict')}"
    try:
        day = time.strftime("%m-%d", time.localtime(float(rec.get("t0"))))
    except (TypeError, ValueError):
        day = "?"
    return f"kit {day} {st}"


def _fmt(v):
    return f"{v:,.0f}"


def _fix(t, cells, soft, core, grid):
    w, h = map(float, t["outline_um"])
    need = cells / RULE_C
    grow = need / soft if soft > 0 else float("inf")
    k = max(2, math.ceil(cells / (RULE_C * soft))) if soft > 0 else 2
    s = f"grow the soft area x{grow:.2f} to {_fmt(need)} um2 (rule C {RULE_C})"
    # a full-width strip / thin piece: say the height (or width) at the same other side, on the die grid
    if min(w, h) <= 0.15 * max(w, h):
        if w >= h:
            hh = (need + core) / w
            if grid:
                hh = math.ceil(hh / grid - 1e-9) * grid
            s += f", i.e. height >= {hh:.2f} um at width {w:g}"
        else:
            ww = (need + core) / h
            if grid:
                ww = math.ceil(ww / grid - 1e-9) * grid
            s += f", i.e. width >= {ww:.2f} um at height {h:g}"
    return s + f", or split into {k} pieces / move cores out"


def _findings(raw, plan_path, tree=None, cells_cache=None, warn=DENS_WARN, **_kw):
    P = raw.get("partition_types") or {}
    if not P:
        return [_w("not checked", "plan has no partition_types")]
    cache, src = load_cache(cells_cache)
    die = (raw.get("die") or {}).get("name")
    out, region = [], []
    # plan-declared region targets need no cache
    for tn in sorted(P):
        for r in P[tn].get("place_regions") or []:
            try:
                u = float(r.get("util"))
            except (TypeError, ValueError):
                continue
            if u > REGION_UTIL_WARN:
                region.append(_w(tn, f"place_regions {r.get('name')} util {u:g} > {REGION_UTIL_WARN} (region target over the "
                                     f"density limit); lower util (region area = cells x {CELL_AREA_UM2} / util)"))
    if cache is None:
        return region + [_w("not checked", f"no cell-count cache (set {CACHE_ENV} or run harvest_cells.py)")]
    allc = cache.get("cells") or {}
    dc = dict(allc.get(die) or {}) if die in allc else {k: v for d in allc.values() for k, v in d.items()}
    by_base = {}
    for n in dc:
        by_base.setdefault(base_type(n), []).append(n)
    grid = None
    try:
        g = (raw.get("die") or {}).get("grid_um")
        grid = float(g[0] if isinstance(g, (list, tuple)) else g) if g else None
    except (TypeError, ValueError):
        grid = None
    placed = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
    hits, n_meas, n_base, n_un, n_ok = [], 0, 0, 0, 0
    for tn in sorted(P):
        t = P[tn]
        if placed and tn not in placed:
            continue
        if t.get("hard") or not t.get("outline_um"):
            continue
        try:
            soft, core = soft_area(t)
        except (TypeError, ValueError, KeyError):
            continue
        if soft <= 0:
            continue
        cells, basis, last, pl = cells_for(tn, t, dc, by_base)
        if cells is None:
            n_un += 1
            continue
        n_meas += basis == "kit"
        n_base += basis.startswith("base")
        dens = cells / soft
        if dens < warn:
            continue
        # measured evidence: a kit of this logic placed at >= this density on the same soft area
        if pl and pl.get("cells") and pl.get("soft_um2"):
            pd = float(pl["cells"]) / float(pl["soft_um2"])
            if pd >= dens * 0.98 and (basis == "kit" or abs(float(pl["soft_um2"]) - soft) <= 0.01 * soft):
                n_ok += 1
                continue
        band = band_area(t)
        net = cells / (soft - band) if soft - band > 0 else float("inf")
        w, h = map(float, t["outline_um"])
        msg = (f"{_fmt(cells)} synth cells ({basis}{', ' + _kit_word(last) if last else ''}) over {_fmt(soft)} um2 soft "
               f"area ({w:g}x{h:g} minus {_fmt(core)} um2 cores) = {dens:.3f} cells/um2 >= {warn:g} "
               f"(~{dens * CELL_AREA_UM2:.0%} std-cell area")
        if band > 0:
            msg += f"; landing bands reserve {_fmt(band)} um2 = {band / soft:.0%}, net {net:.2f} cells/um2"
        msg += f"); no kit of this logic placed at this density; {_fix(t, cells, soft, core, grid)}"
        hits.append((dens, _w(tn, msg)))
    hits.sort(key=lambda r: -r[0])
    out = region[:MAX_LINES] + [m for _, m in hits[:int(_kw.get('max_lines') or MAX_LINES)]]
    out.append(_w("summary", f"{len(hits)} types >= {warn:g} cells/um2 ({len(region)} region rows); measured {n_meas} exact + "
                             f"{n_base} base-type, {n_ok} dense but placed before at >= that density, {n_un} unmeasured; "
                             f"cache {Path(src).name if src else '-'} {cache.get('made', '')}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import sys
    import time
    t0 = time.time()
    with open(sys.argv[1]) as f:
        _raw = json.load(f)
    t1 = time.time()
    for ln in findings(_raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
                       cells_cache=sys.argv[3] if len(sys.argv) > 3 else None,
                       max_lines=int(os.environ.get("OT_ADV_MAX_LINES", MAX_LINES))):
        print(ln)
    print(f"# ADV-{CHECK} load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")
