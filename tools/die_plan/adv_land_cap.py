"""ADV-LAND-CAP (PRECHECK-R2, COORD 11-23; an estimator, never a gate).

Capacity of every soft clock-landing ring band (partition_types[].clock.landing_contract.bands[].rect_um / rects_um) against
the u_cland_* cells the kit pins FIRM in it, per type, before the kit:

  fill = demand / free
  free   = band rect (clipped to the kit core area) minus every hard core box + ROW_CUT_UM (rows stop ~2 um beside a macro;
           landing_place._row_free_fraction) or + its halo_um, the band's own hard ring child excluded
  demand = ring flops x per-flop reserve + the single FIRM landing sites the plan pins inside the band (START / status /
           local-reset / collector / relay / station points: adv_site_collide.type_items, 0.729 um2 each) + exact station
           bit sites inside it (adv_geom_static.exact_sites, cell body)

  ring flops  = ceil(FLOP_LIVE_K x live_data_storage_flops (5 per bit + epoch)) + FLOP_CTL.  Calibrated on the kit logs: S81
                ot_dp_clk_landing_cas DEPTH 4 + WREG = 5.75 per bit + 64..68 control registers (t9 leafup_i3 W 669 -> 3913,
                ft1_i / xtier_i0 W 277 -> 1661, ret_i0 W 71 -> 475; this formula 3915 / 1661 / 476); QC x_st_b_i W 9 -> 147 (120).
  per-flop reserve (landing_placement.tcl cland_place_ff):
     ring_place ff, pins on the N/S face (FLOW-12 pinslot column form, OT_CLAND_PINSLOT=1): rows x 0.27 x CELL_W, with the
       LAND-RING-2 row law of OT_CLAND_STRIP_DENS (wave env 1; plan budgets.cland_strip_density): C = floor(band length /
       CELL_W) columns, d1 = (ceil(1.15 n / C) + 1) x 0.27, rows = max(1, min(ceil(n / (C CELL_W d1) / target), floor(depth / d1)))
       - the kit counts the depth on the WHOLE rect, so a band under a macro keeps rows 3 on the rows that are left
     ring_place ff, pins on the E/W face (y-column pinslot): w/0.4 x 0.27 = FF_RESERVE_UM2
     any other ring (all cells FIRM): FF_RESERVE_UM2 x ALLCELL_K (kit cland_band_need over all ring cells / flops = 1.43-1.44)
  BLOCKED: a band crossed by the HALO-1 ring of a hard core with halo_um > 0 (gen_phys ot_macro_halo: hard placement
           blockages, macro_halo_carve only re-cuts them round fixed cells): the kit stops before placing anything
           ("OT_CLAND band ... overlaps hard placement blockage").

Real positives (fill >= FILL_WARN):
  S81 J8 v9 dsdv_slice_c1x_C__t9 (epyc7 fam-s81-slice-r6/trees/s81_j8v9 plan_h2_2249.json, kit 1122185657 3_3_place_gp.log
      "OT_CLAND BAND FAIL u_cland_leafup_i3 ... u_cland_xring_i1 ... u_cland_xtier_i0 ... no legal nonoverlapping row/site in
      reserved band"): the c1x core moves put u_c.u_xr / u_c.u_cap over 46 / 56 / 79 % of the three bands; leafup_i3 1.37,
      xring_i1 2.26, xtier_i0 3.36.  The same type's clean bands (ft1_i/ft2_i/leafup_i4/ret_i*, placed in that kit) 0.59-0.67.
  QC V3 st_a (slw_st_a_v2__clf4365a62, sle_st_a_v1__cl67389ecd, slw_st_a_v1__clb036e152, clfc5867a6__pvdf8e5ca4 ...:
      "OT_CLAND band u_cland_x_st_b_i ... overlaps hard placement blockage" = the 4.32-um halo ring of btab g_btb[1|3].u_m):
      BLOCKED; the placed twin slw_st_a_v2__cl9f076a5c (same band, no btab under it) 0.29.

Fix: move the band (or the core) so the band rows are free, or grow the band by the blocked share / split it.

    findings(raw, plan_path, tree=None, warn=FILL_WARN, list_all=False) -> ["WARN ADV-LAND-CAP ..."]
    band_fills(raw) -> [(type, band, fill, info dict)]  (fill = inf when BLOCKED or no free rows)
"""
import math
import os
import sys
import time

CHECK = "ADV-LAND-CAP"
FILL_WARN = 0.90
ROW_H = 0.27
CELL_W = 1.188              # widest DFFHQN drive-family width (cland_family_w; t9 kit: 220.32 um -> 185 columns, 38.88 -> 32, 12.96 -> 10)
FF_RESERVE_UM2 = 0.729      # DFFHQNx1 1.08 um / 0.4 -> 50 sites x 0.27 (clock_landing_plan FF_RESERVE40_UM2)
ALLCELL_K = 1.44            # all-cell ring reserve per ring flop (t9 BAND FAIL: 5612.2 / 3913, 9204.1 / 6420, 2391.5 / 1661)
FLOP_LIVE_K = 1.15          # kit ring flops per plan live storage flop (S81 DEPTH 4 + WREG)
FLOP_CTL = 68               # ring control / status registers (ctlkey 64-68; QC x_st_b_i 102)
ROW_CUT_UM = 2.16           # rows cut beside every macro (landing_place._row_free_fraction 2.17)
CORE_INSET_UM = 4.32
STRIP_DENS_DEFAULT = 1.0    # OT_CLAND_STRIP_DENS in the wave env of every die (config.mk)
SITE_RESERVE_UM2 = FF_RESERVE_UM2
MAX_LINES = 20
EPS = 1e-6
ROT = ("R90", "R270", "MXR90", "MYR90")
_HERE = os.path.dirname(os.path.abspath(__file__))


def _f(v):
    return "inf" if v == math.inf else f"{v:.2f}"


def _rect(r):
    try:
        r = [float(v) for v in r]
    except (TypeError, ValueError):
        return None
    return tuple(r) if len(r) == 4 and r[2] > r[0] and r[3] > r[1] else None


def _ov(a, b):
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _union_area(clip, rects):
    rs = [r for r in rects if _ov(clip, r) > EPS]
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


def _cores(t):
    """[(x0, y0, x1, y1, inst, halo)] hard cores / lef contents"""
    out = []
    for h in list(t.get("hard_cores") or []) + [c for c in (t.get("contents") or []) if isinstance(c, dict) and c.get("lef")]:
        try:
            (x0, y0), (w, hh) = h["origin_um"], h["outline_um"]
            x0, y0, w, hh = float(x0), float(y0), float(w), float(hh)
            halo = float(h.get("halo_um") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if h.get("orient", "R0") in ROT:
            w, hh = hh, w
        out.append((x0, y0, x0 + w, y0 + hh, str(h.get("inst") or h.get("name") or "core"), halo))
    return out


def _own(nm, b, inst):
    return inst in (f"cl_{nm}", str(b.get("instance") or "\0"), nm, str(b.get("hard_core") or "\0")) or \
        (inst.startswith("cl") and inst.endswith(f"_{nm}"))


def _core_area(t):
    try:
        if _HERE not in sys.path:
            sys.path.insert(0, _HERE)
        from kit_fit import kit_core_area
        return tuple(float(v) for v in kit_core_area(t))
    except Exception:  # noqa: BLE001 -- fixture / older tree
        w, h = t["outline_um"]
        return (CORE_INSET_UM, CORE_INSET_UM, float(w) - CORE_INSET_UM, float(h) - CORE_INSET_UM)


def _strip_target(raw, tn, kw):
    v = kw.get("strip_dens")
    if v is None:
        b = raw.get("budgets") or {}
        d = b.get("cland_strip_density")
        if isinstance(d, dict):
            d = d.get(tn, d.get("default"))
        v = d if isinstance(d, (int, float)) and not isinstance(d, bool) else None
    if v is None:
        try:
            v = float(os.environ.get("OT_CLAND_STRIP_DENS", STRIP_DENS_DEFAULT))
        except ValueError:
            v = STRIP_DENS_DEFAULT
    return float(v) if v and float(v) > 0 else None


def _face(t, nm, r):
    """face of the band's bus pins: the fclk_in_<bus> pin (landing_contract.pins), else the outline edge nearest the band"""
    w, h = (float(v) for v in t["outline_um"])
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    xy = None
    for p in lc.get("pins") or []:
        if isinstance(p, dict) and p.get("name") in (f"fclk_in_{nm}", f"cland_fstart_in_{nm}"):
            xy = p.get("xy_um")
            break
    if isinstance(xy, (list, tuple)) and len(xy) >= 2:
        x, y = float(xy[0]), float(xy[1])
        d = {"W": x, "E": w - x, "S": y, "N": h - y}
    else:
        d = {"W": r[0], "E": w - r[2], "S": r[1], "N": h - r[3]}
    return min(d, key=d.get)


def ring_flops(b):
    live = b.get("live_data_storage_flops")
    if not isinstance(live, (int, float)) or isinstance(live, bool) or live <= 0:
        wd = b.get("width")
        if not isinstance(wd, (int, float)) or isinstance(wd, bool):
            return None
        live = 5 * (int(wd) + 1)
    return int(math.ceil(FLOP_LIVE_K * live - 1e-9)) + FLOP_CTL


def per_flop(b, r, face, n, target):
    """(um2 per ring flop, form text) as landing_placement.tcl reserves it"""
    if b.get("ring_place") != "ff":
        return FF_RESERVE_UM2 * ALLCELL_K, "all cells FIRM"
    if face in ("E", "W"):
        return FF_RESERVE_UM2, f"{face} y-column w/0.4"
    length, depth = r[2] - r[0], r[3] - r[1]
    nc = max(1, int(math.floor(length / CELL_W + 1e-9)))
    d1 = (math.ceil(1.15 * n / nc - 1e-9) + 1) * ROW_H
    rows = 1
    if target:
        need = int(math.ceil(n / (nc * CELL_W * d1) / target - 1e-9))
        fit = max(1, int(math.floor(depth / d1 + 1e-9)))
        rows = max(1, min(need, fit))
    return rows * ROW_H * CELL_W, f"{face} strip {nc} cols rows {rows}"


def _point_sites(t):
    try:
        if _HERE not in sys.path:
            sys.path.insert(0, _HERE)
        from adv_site_collide import type_items
        return [(x, y) for _k, _n, x, y in type_items(t)]
    except Exception:  # noqa: BLE001
        return []


def _exact_sites(t):
    try:
        if _HERE not in sys.path:
            sys.path.insert(0, _HERE)
        from adv_geom_static import exact_sites
        return [(x, y, cw * ch) for _l, x, y, cw, ch in exact_sites(t)]
    except Exception:  # noqa: BLE001
        return []


def _used_types(raw):
    return {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}


def type_bands(raw, tn, t, **kw):
    """[(band, fill, info)] of one type's soft ring bands"""
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    bands = lc.get("bands") or {}
    if not isinstance(bands, dict) or not bands or not t.get("outline_um"):
        return []
    cores = _cores(t)
    ca = _core_area(t)
    target = _strip_target(raw, tn, kw)
    pts = exact = None
    out = []
    for nm, b in sorted(bands.items()):
        if not isinstance(b, dict):
            continue
        if any(c[4] == f"cl_{nm}" for c in cores):    # realised as its own hard ring child: a macro, not rows
            continue
        rects = [x for x in (_rect(v) for v in (b.get("rects_um") or [b.get("rect_um")])) if x]
        if not rects:
            continue
        n = ring_flops(b)
        if n is None:
            continue
        area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in rects)
        free, blocked, hits = 0.0, [], {}
        for r in rects:
            rc = (max(r[0], ca[0]), max(r[1], ca[1]), min(r[2], ca[2]), min(r[3], ca[3]))
            if rc[2] <= rc[0] or rc[3] <= rc[1]:
                continue
            obs = []
            for x0, y0, x1, y1, inst, halo in cores:
                if _own(nm, b, inst):
                    continue
                e = max(halo, ROW_CUT_UM)
                o = (x0 - e, y0 - e, x1 + e, y1 + e)
                ov = _ov(rc, o)
                if ov <= EPS:
                    continue
                obs.append(o)
                hits[inst] = hits.get(inst, 0.0) + _ov(rc, (x0, y0, x1, y1))
                # HALO-1 ring = hard placement blockage: any ring area inside the band stops the kit
                if halo > 0 and _ov(r, (x0 - halo, y0 - halo, x1 + halo, y1 + halo)) - _ov(r, (x0, y0, x1, y1)) > 1e-3:
                    blocked.append((inst, halo))
            free += (rc[2] - rc[0]) * (rc[3] - rc[1]) - _union_area(rc, obs)
        if pts is None:
            pts, exact = _point_sites(t), _exact_sites(t)
        nsite = sum(1 for x, y in pts if any(r[0] <= x <= r[2] and r[1] <= y <= r[3] for r in rects))
        ex = sum(a for x, y, a in exact if any(r[0] <= x < r[2] and r[1] <= y < r[3] for r in rects))
        face = _face(t, nm, rects[0])
        per, form = per_flop(b, rects[0], face, n, target)
        demand = n * per + nsite * SITE_RESERVE_UM2 + ex
        fill = math.inf if blocked or free <= EPS else demand / free
        out.append((nm, fill, dict(area=area, free=max(free, 0.0), demand=demand, flops=n, per=per, form=form, sites=nsite,
                                   exact_um2=ex, blocked=blocked, hits=hits, rect=list(rects[0]), width=b.get("width"),
                                   ring_place=b.get("ring_place") or "all")))
    return out


def band_overlaps(raw):
    """OVERLAP (COORD 11-23, FAM-S81-SLICE-R6 monitor_0 on t8 / lepe_nh_mus 92 um2): every landing band rect (any band,
    flops or not) overlapping a hard core / lef macro, or its halo_um ring, of the same type by > 0 um2 (own cl_ core
    excluded) -> [(type, band, inst, core_um2, halo_um2, rect)]"""
    types = raw.get("partition_types") or {}
    used = _used_types(raw)
    res = []
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
            continue
        bands = ((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}
        if not isinstance(bands, dict) or not bands:
            continue
        cores = _cores(t)
        if not cores:
            continue
        for nm, b in sorted(bands.items()):
            if not isinstance(b, dict) or any(c[4] == f"cl_{nm}" for c in cores):
                continue
            rects = [x for x in (_rect(v) for v in (b.get("rects_um") or [b.get("rect_um")])) if x]
            for x0, y0, x1, y1, inst, halo in cores:
                if _own(nm, b, inst):
                    continue
                co = sum(_ov(r, (x0, y0, x1, y1)) for r in rects)
                ho = sum(_ov(r, (x0 - halo, y0 - halo, x1 + halo, y1 + halo)) for r in rects) - co if halo > 0 else 0.0
                if co > EPS or ho > EPS:
                    res.append((tn, nm, inst, co, ho, list(rects[0])))
    return res


def band_fills(raw, **kw):
    types = raw.get("partition_types") or {}
    used = _used_types(raw)
    res = []
    for tn, t in sorted(types.items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
            continue
        for nm, fill, info in type_bands(raw, tn, t, **kw):
            res.append((tn, nm, fill, info))
    return res


def findings(raw, plan_path, tree=None, warn=FILL_WARN, **kw):
    """WARN ADV-LAND-CAP lines (capped at MAX_LINES) + one summary line with the band fill distribution; never raises."""
    try:
        t0 = time.time()
        if not isinstance(raw, dict) or not raw.get("partition_types"):
            return [f"WARN {CHECK} not checked: plan has no partition_types"]
        res = band_fills(raw, **kw)
        ovl = band_overlaps(raw)
        olines = [f"WARN {CHECK} {tn}: OVERLAP band {nm} {[round(v, 2) for v in r]} overlaps hard core {inst} by "
                  f"{co:.0f} um2{f' + {ho:.0f} um2 of its halo' if ho > EPS else ''}; the kit legalises landing cells out of "
                  f"the core (or fails 'no legal site'); fix: move / trim the band clear of {inst} and its halo"
                  for tn, nm, inst, co, ho, r in sorted(ovl, key=lambda x: -(x[3] + x[4]))]
        if not res:
            return (olines[:MAX_LINES] + ([f"WARN {CHECK} {len(ovl)} band x core overlap(s)"] if ovl else [])) or \
                [f"WARN {CHECK} not checked: no soft clock.landing_contract.bands in the placed types"]
        bad = sorted([x for x in res if x[2] >= warn], key=lambda x: (-x[2], x[0], x[1]))
        lines = []
        for tn, nm, fill, i in bad:
            hit = ", ".join(f"{k} {v:.0f}" for k, v in sorted(i["hits"].items(), key=lambda kv: -kv[1])[:2])
            if i["blocked"]:
                inst, halo = i["blocked"][0]
                lines.append(f"WARN {CHECK} {tn}: band {nm} {[round(v, 2) for v in i['rect']]} is crossed by the HALO-1 ring of "
                             f"{inst} (halo_um {halo:g} = hard placement blockage): BLOCKED, the kit stops at place "
                             f"('OT_CLAND band u_cland_{nm} ... overlaps hard placement blockage'); free rows {i['free']:.0f} of "
                             f"{i['area']:.0f} um2 for {i['flops']} ring flops; fix: move the band (or {inst}) so no halo "
                             f"ring crosses it")
                continue
            lines.append(f"WARN {CHECK} {tn}: band {nm} fill {_f(fill)} >= {warn:g}: {i['flops']} ring flops x "
                         f"{i['per']:.3f} um2 ({i['form']}) + {i['sites']} FIRM sites + {i['exact_um2']:.0f} um2 station sites = "
                         f"{i['demand']:.0f} um2 vs {i['free']:.0f} um2 free of {i['area']:.0f} um2 rect "
                         f"{[round(v, 2) for v in i['rect']]}{' (under ' + hit + ' um2)' if hit else ''}; risk 'OT_CLAND no "
                         f"legal nonoverlapping row/site in reserved band'; fix: move the band clear of the cores or grow it "
                         f"to >= {i['demand'] / 0.75:.0f} um2 free")
        out = lines[:MAX_LINES] + olines[:max(5, MAX_LINES - len(lines))]
        fin = [x[2] for x in res]
        buck = [sum(1 for f in fin if f < 0.5), sum(1 for f in fin if 0.5 <= f < 0.7), sum(1 for f in fin if 0.7 <= f < warn),
                sum(1 for f in fin if f >= warn), sum(1 for x in res if x[3]["blocked"])]
        top = sorted(res, key=lambda x: -x[2])[:8]
        ntypes = len({x[0] for x in res})
        nbad_t = len({x[0] for x in bad})
        out.append(f"WARN {CHECK} {len(bad)} band(s) in {nbad_t} type(s) at fill >= {warn:g} ({buck[4]} BLOCKED by a halo ring)"
                   f"{' (first ' + str(len(lines[:MAX_LINES])) + ' listed)' if len(lines) > MAX_LINES else ''}; "
                   f"{len(ovl)} band x core OVERLAP(s) in {len({x[0] for x in ovl})} type(s); "
                   f"{len(res)} soft ring bands in {ntypes} types: fill <0.5 {buck[0]}, 0.5-0.7 {buck[1]}, 0.7-{warn:g} {buck[2]}, "
                   f">={warn:g} {buck[3]}; top: "
                   + ", ".join(f"{tn}/{nm} {'BLOCKED' if f == math.inf and i['blocked'] else _f(f)}" for tn, nm, f, i in top)
                   + f"; {time.time() - t0:.1f} s")
        if kw.get("list_all") or os.environ.get("OT_ADV_LANDCAP_ALL", "0") == "1":
            out += [f"INFO {CHECK} {tn}/{nm} fill {_f(f)} ({i['form']}, {i['flops']} flops, free {i['free']:.0f}/{i['area']:.0f})"
                    for tn, nm, f, i in res]
        return out
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    t0 = time.time()
    raw = json.load(open(sys.argv[1]))
    t1 = time.time()
    for ln in findings(raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
                       list_all=os.environ.get("OT_ADV_LANDCAP_ALL", "0") == "1"):
        print(ln)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")
