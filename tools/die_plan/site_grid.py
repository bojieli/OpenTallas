#!/usr/bin/env python3
"""site_grid: SITEGRID-1123 (ADV-SITEGRID-1123, FLOW-OPS-R3, COORD 16:1x) -- plan_gate_pre class SITEGRID.

KV D29 HGFORM (all 8 kv3_hg* types): 70,200 exact internal bank seats (internal_stations bit_sites_um of
o_ectl_Q_N_tN, e.g. (965, 1240)) were off the native site / row lattice.  ADV-OFF-GRID only warned; plan_gate_pre,
G0 and the bind passed, and the probe kit died in global_place: kit_istations is_exact_bank "exact internal bank site
is not on row/site".  This class decides the same predicate the kit evaluates, before any bind or kit:

    cx = round(x * dbu); cy = round(y * dbu)            (Tcl round: half away from zero)
    on grid  <=>  (cx - core_x0) % site_w == 0  and  (cy - core_y0) % row_h == 0     (dict exists ff_orient $cy)

in exact integer DBU arithmetic (the JSON number is read as its decimal literal, never float modulo), on the text the
generator prints for the kit (kit_istations "%0.9g", soft_cs_placement "%.9g", place_macro ".4f").  The S81 J9 B1 leaf t31
4903 soft CS sites were on grid in the plan and left it only through soft_cs_placement's old "%g" print (fixed here).  core_x0 / y0 =
the kit CORE_AREA corner (kit_fit.kit_core_area: outline inset, default 4.32 um = 80 sites / 16 rows, or the type's
kit_core_margins_um).  DBU / site / row from the tech + stdcell LEF the kits read ($OT_TECH_LEF / $OT_SC_LEF, else
the ORFS platform path when present), else the values of the locked ORFS image (opentallas/orfs asap7_tech_1x_201209.lef
DATABASE MICRONS 1000, MANUFACTURINGGRID 0.001; asap7sc7p5t SITE 0.054 BY 0.270).

  EXACT  (FAIL SITEGRID <type>)  sites the kit places exactly and refuses off grid at global_place:
         internal_stations[].bit_sites_um (is_exact_bank / is_packed_exact_banks), internal_stations[].face_bit_sites_um,
         clock.soft_reg_banks[].bit_sites_um (soft_cs_placement "soft CS bank off row/site"; also a type-level
         soft_reg_banks key if present).  Per type: count, rows, examples with the nearest legal origin, and the
         residual offsets (dx, dy in DBU) when the whole set is shifted by one vector.
  MACRO  hard_cores (origin + track_offset, as gen_phys.type_macros places them), lef contents, contents physical_parts.
         An origin off the site column / row is counted in the summary only: place_macro -exact / setLocation accepts
         any DBU origin, the track offsets deliberately put macros on routing tracks, and the kits of the adopted plans
         place with them (11-23: KV D29 649, QC V4 C4 685, HEAD 239 placed origins).  WARN SITEGRID-MACRO <type> per type
         for an origin off the manufacturing grid (setLocation rounds it, the kit macro is not where the plan put it;
         0 on the 4 live plans); $OT_SITEGRID_MACROS=1 lists the site / row offenders in those lines too.
  CELL   (counted in the WARN SITEGRID-SUMMARY line)  plan cell hints the kit legalises (relay_sites, reg_leaf_split copies,
         count_straps, clock.reserved_sites_um / sink_sites_um, reset.consumer_sites_um): counted only.
Sites outside CORE_AREA are ADV-BANK-OFFAREA's; ft_slots bit_sites_um are snapped by gen (ft_bit_sites.snap_slots).

    findings(raw) -> ["FAIL SITEGRID ...", "WARN SITEGRID-MACRO ...", "WARN SITEGRID-SUMMARY ..."]
    python3 -I tools/die_plan/site_grid.py PLAN.json [--all]          (stand-alone, read-only)
"""
import os
import re
import sys
import time
from decimal import Decimal, ROUND_HALF_UP

DBU_DEFAULT, SITE_DEFAULT, ROW_DEFAULT, MFG_DEFAULT = 1000, "0.054", "0.270", "0.001"
CORE_MARGIN = "4.32"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7/lef"
MAX_EX = 3
# the print format of each generator that hands exact sites to the kit Tcl (the kit judges the printed text)
SOFT_CS_SPEC = "%.9g"      # soft_cs_placement.emit (was %g until SITEGRID-1123: S81 leaf t31 1000.296 -> 1000.3, 4903 sites)


def _lef_text(env, default):
    p = os.environ.get(env) or default
    try:
        with open(p, errors="replace") as f:
            return f.read()
    except OSError:
        return None


def tech():
    """-> dict(dbu, site_w, row_h, mfg) in integer DBU, from the LEFs when readable, else the locked-image values."""
    dbu, site, row, mfg, src = DBU_DEFAULT, SITE_DEFAULT, ROW_DEFAULT, MFG_DEFAULT, "default"
    t = _lef_text("OT_TECH_LEF", f"{PLAT}/asap7_tech_1x_201209.lef")
    if t:
        m = re.search(r"DATABASE\s+MICRONS\s+(\d+)", t)
        g = re.search(r"MANUFACTURINGGRID\s+([\d.]+)", t)
        dbu = int(m.group(1)) if m else dbu
        mfg = g.group(1) if g else mfg
        src = "lef"
    s = _lef_text("OT_SC_LEF", f"{PLAT}/asap7sc7p5t_28_R_1x_220121a.lef")
    if s:
        m = re.search(r"SITE\s+asap7sc7p5t\b.*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", s, re.S)
        if m:
            site, row = m.group(1), m.group(2)
    D = Decimal(dbu)
    return dict(dbu=dbu, site_w=int(Decimal(site) * D), row_h=int(Decimal(row) * D),
                mfg=max(1, int(Decimal(mfg) * D)), src=src)


def _dec(v):
    """exact decimal of a plan number (its JSON literal); Decimal passes through"""
    if isinstance(v, Decimal):
        return v
    return Decimal(v) if isinstance(v, int) else Decimal(repr(float(v)))


def to_dbu(v, dbu):
    """the kit's round(v * dbu) on the exact decimal literal of v (Tcl round = half away from zero)."""
    return int((_dec(v) * dbu).to_integral_value(rounding=ROUND_HALF_UP))


def exact_dbu(v, dbu):
    """True when v * dbu is an integer (v on the DBU grid before any rounding)."""
    d = _dec(v) * dbu
    return d == d.to_integral_value()


def kitv(v, spec):
    """the number the kit Tcl reads: the generator prints the plan value with SPEC (kit_istations is_exact_bank
    "%0.9g", soft_cs_placement "%g", gen_phys place_macro / setLocation ".4f"), so the check judges that text."""
    return Decimal(spec % float(v)) if spec.startswith("%") else Decimal(format(float(v), spec))


def _site(cls, lab, p, spec):
    x, y = kitv(p[0], spec), kitv(p[1], spec)
    if spec.startswith("%") and (x != _dec(p[0]) or y != _dec(p[1])) and (abs(x - _dec(p[0])) > Decimal("1e-6")
                                                                        or abs(y - _dec(p[1])) > Decimal("1e-6")):
        lab += f" [plan ({_lit(p[0])}, {_lit(p[1])}) printed {spec}]"
    return (cls, lab, x, y)


def _pt(p):
    if isinstance(p, (list, tuple)) and len(p) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p[:2]):
        return p[0], p[1]
    return None


def core_dbu(t, dbu):
    """kit CORE_AREA [x0, y0, x1, y1] in DBU (kit_fit.kit_core_area; default inset 4.32 um)."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        from kit_fit import kit_core_area
        c = kit_core_area(t)
    except Exception:  # noqa: BLE001 -- fixture / older tree: the default inset
        w, h = t["outline_um"]
        m = float(CORE_MARGIN)
        c = [m, m, float(w) - m, float(h) - m]
    return [to_dbu(round(float(v), 6), dbu) for v in c]


def sites(t):
    """-> [(class, label, x, y)] of one type's plan-specified sites (type frame, um, as written in the plan)."""
    out = []
    for k, e in enumerate(t.get("internal_stations") or []):
        if not isinstance(e, dict):
            continue
        lab = f"internal_stations[{k}] {e.get('conn', '')}".strip()
        for j, stage in enumerate(e.get("bit_sites_um") or []):
            for b, p in enumerate(stage if isinstance(stage, list) else []):
                q = _pt(p)
                if q:
                    out.append(_site("EXACT", f"{lab} stage {j} bit {b}", q, "%0.9g"))
        for b, p in enumerate(e.get("face_bit_sites_um") or []):
            q = _pt(p)
            if q:
                out.append(_site("EXACT", f"{lab} face bit {b}", q, "%0.9g"))
    ck = t.get("clock") if isinstance(t.get("clock"), dict) else {}
    for where, banks in (("clock.soft_reg_banks", ck.get("soft_reg_banks")), ("soft_reg_banks", t.get("soft_reg_banks"))):
        for k, e in enumerate(banks if isinstance(banks, list) else []):
            if isinstance(e, dict):
                for b, p in enumerate(e.get("bit_sites_um") or []):
                    q = _pt(p)
                    if q:
                        out.append(_site("EXACT", f"{where}[{k}] {e.get('id', '')} bit {b}", q, SOFT_CS_SPEC))
    for c in t.get("hard_cores") or []:
        q = _pt(c.get("origin_um")) if isinstance(c, dict) else None
        if q and c.get("lef"):
            ox, oy = (c.get("track_offset_um") or [0, 0])[:2]
            out.append(_site("MACRO", f"hard_cores {c.get('physical_inst') or c.get('inst')}",
                             (float(q[0]) + float(ox), float(q[1]) + float(oy)), ".4f"))
    cores = {c.get("inst") for c in t.get("hard_cores") or [] if isinstance(c, dict)}
    for c in t.get("contents") or []:
        if not isinstance(c, dict):
            continue
        for q in c.get("physical_parts") or []:
            p = _pt(q.get("origin_um")) if isinstance(q, dict) else None
            if p:
                out.append(_site("MACRO", f"contents {q.get('physical_inst') or c.get('inst')}", p, ".4f"))
        if c.get("lef") and c.get("inst") not in cores:
            p = _pt(c.get("origin_um"))
            if p:
                out.append(_site("MACRO", f"contents {c.get('physical_inst') or c.get('inst')}", p, ".4f"))
    rs = t.get("relay_sites")
    if isinstance(rs, dict):
        for name, v in rs.items():
            p = _pt(v)
            if p:
                out.append(("CELL", f"relay_sites[{name}]", p[0], p[1]))
    for k, e in enumerate(t.get("reg_leaf_split") or []):
        for j, c in enumerate((e.get("copies") or []) if isinstance(e, dict) else []):
            p = _pt(c.get("site_um")) if isinstance(c, dict) else None
            if p:
                out.append(("CELL", f"reg_leaf_split[{k}].copies[{j}]", p[0], p[1]))
    for k, e in enumerate(t.get("count_straps") or []):
        if isinstance(e, dict):
            for p in e.get("sites_um") or []:
                q = _pt(p)
                if q:
                    out.append(("CELL", f"count_straps[{k}]", q[0], q[1]))
    for key in ("reserved_sites_um", "sink_sites_um"):
        for p in ck.get(key) or []:
            q = _pt(p)
            if q:
                out.append(("CELL", f"clock.{key}", q[0], q[1]))
    rst = t.get("reset") if isinstance(t.get("reset"), dict) else {}
    for p in rst.get("consumer_sites_um") or []:
        q = _pt(p)
        if q:
            out.append(("CELL", "reset.consumer_sites_um", q[0], q[1]))
    return out


def judge(x, y, core, T):
    """-> None (outside CORE_AREA: BANK-OFFAREA's) or (dx, dy, nx, ny, mfg_ok): residuals in DBU vs the core lattice
    and the nearest legal origin in DBU."""
    dbu, sw, rh = T["dbu"], T["site_w"], T["row_h"]
    cx, cy = to_dbu(x, dbu), to_dbu(y, dbu)
    x0, y0, x1, y1 = core
    if cx < x0 or cy < y0 or cx > x1 or cy > y1:
        return None
    dx, dy = (cx - x0) % sw, (cy - y0) % rh
    nx = cx - dx + (sw if 2 * dx >= sw else 0)
    ny = cy - dy + (rh if 2 * dy >= rh else 0)
    mfg_ok = exact_dbu(x, dbu) and exact_dbu(y, dbu) and cx % T["mfg"] == 0 and cy % T["mfg"] == 0
    return dx, dy, nx, ny, mfg_ok


def _lit(v):
    """the plan number as written (no 6-digit %g rounding: 509.7955 must not print as 509.796)"""
    t = format(_dec(v), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


def _um(v, dbu):
    s = format(Decimal(v) / Decimal(dbu), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def type_findings(tn, t, T):
    """-> (core, bad): bad[EXACT | MACRO | MFG | CELL] = [(label, x, y, dx, dy, nx, ny)]; MFG = macro origins off the
    manufacturing grid (also in MACRO when off the site column / row)."""
    core = core_dbu(t, T["dbu"])
    bad = {"EXACT": [], "MACRO": [], "MFG": [], "CELL": []}
    for cls, lab, x, y in sites(t):
        r = judge(x, y, core, T)
        if r is None:
            continue
        dx, dy, nx, ny, mfg_ok = r
        e = (lab, x, y, dx, dy, nx, ny)
        if cls == "MACRO" and not mfg_ok:
            bad["MFG"].append(e)
        if dx or dy:
            bad[cls].append(e)
    return core, bad


def _plan_xy(lab):
    """(x, y) Decimals of the '[plan (x, y) printed %g]' label suffix"""
    m = re.search(r"\[plan \(([-\d.]+), ([-\d.]+)\) printed", lab)
    return Decimal(m.group(1)), Decimal(m.group(2))


def _row(lab):
    return re.sub(r" (stage \d+ )?(face )?bit \d+( \[plan .*\])?$", "", lab)


def findings(raw, max_ex=MAX_EX, T=None, all_macros=None):
    """SITEGRID lines for a raw plan dict; never raises (an unreadable plan is one WARN)."""
    try:
        t0 = time.time()
        T = T or tech()
        if all_macros is None:
            all_macros = os.environ.get("OT_SITEGRID_MACROS") == "1"
        dbu = T["dbu"]
        types = raw.get("partition_types") if isinstance(raw, dict) else None
        if not types:
            return []
        fails, warns, ncell, ncell_t, ntypes, nfail, nmac, mac_t = [], [], 0, 0, 0, 0, 0, []
        for tn, t in sorted(types.items()):
            if not isinstance(t, dict) or not t.get("outline_um"):
                continue
            ntypes += 1
            core, bad = type_findings(tn, t, T)
            grid = (f"grid x0 {_um(core[0], dbu)} + k x {_um(T['site_w'], dbu)}, y0 {_um(core[1], dbu)} + k x "
                    f"{_um(T['row_h'], dbu)} um (DBU {dbu})")

            def ex(b):
                return "; ".join(f"{lab} ({_lit(x)}, {_lit(y)}) -> nearest ({_um(nx, dbu)}, {_um(ny, dbu)})"
                                 for lab, x, y, dx, dy, nx, ny in b[:max_ex])
            b = bad["EXACT"]
            if b:
                nfail += len(b)
                rows = sorted({_row(e[0]) for e in b})
                vec = sorted({(e[3], e[4]) for e in b})
                npr = sum(1 for e in b if " printed %" in e[0] and (judge(*_plan_xy(e[0]), core, T) or (1, 1))[:2] == (0, 0))
                shift = (f"; one residual (dx, dy) = ({vec[0][0]}, {vec[0][1]}) DBU on all" if len(vec) == 1
                         else f"; {len(vec)} distinct residuals")
                fails.append(f"FAIL SITEGRID {tn}: {len(b)} exact bank site(s) off the native site/row grid on {len(rows)} "
                             f"bank row(s) ({', '.join(rows[:3])}{' ...' if len(rows) > 3 else ''}); the kit refuses them at "
                             f"global_place (\"exact internal bank site is not on row/site\"); {grid}{shift}; e.g. {ex(b)}; "
                             + (f"; {npr} of them are ON grid in the plan and leave it only through the generator's print "
                                f"(too few significant digits): fix the print, not the plan" if npr else "")
                             + "; fix: snap each site to x0 + round((x - x0) / site) x site, y0 + round((y - y0) / row) x row "
                             f"in the row generator")
            if bad["MACRO"]:
                nmac += len(bad["MACRO"])
                mac_t.append((-len(bad["MACRO"]), tn))
            m = bad["MFG"] if not all_macros else bad["MFG"] + [e for e in bad["MACRO"] if e not in bad["MFG"]]
            if m:
                warns.append(f"WARN SITEGRID-MACRO {tn}: {len(bad['MFG'])} macro origin(s) off the {_um(T['mfg'], dbu)} um "
                             f"manufacturing grid (setLocation rounds them: the kit macro is not where the plan put it), "
                             f"{len(bad['MACRO'])} off the site column / row (place_macro -exact accepts those); {grid}; "
                             f"e.g. {ex(m)}")
            if bad["CELL"]:
                ncell += len(bad["CELL"])
                ncell_t += 1
        summ = (f"WARN SITEGRID-SUMMARY {nfail} exact bank site(s) off grid in {len(fails)} type(s) (FAIL), "
                f"{nmac} macro origin(s) off the site column / row in {len(mac_t)} type(s) (counted: track offsets put "
                f"macros on routing tracks; {', '.join(n for _, n in sorted(mac_t)[:3])}{' ...' if len(mac_t) > 3 else ''}; "
                f"OT_SITEGRID_MACROS=1 lists them), "
                f"{ncell} legalised cell hint site(s) in {ncell_t} type(s) (counted only); {ntypes} types, DBU {dbu} "
                f"({T['src']}), {time.time() - t0:.1f} s")
        return fails + warns + ([summ] if fails or warns or ncell or nmac else [])
    except Exception as e:  # noqa: BLE001
        return [f"WARN SITEGRID not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    ap = [a for a in sys.argv[1:] if not a.startswith("--")]
    raw = json.load(open(ap[0]))
    for ln in findings(raw, max_ex=100000 if "--all" in sys.argv else MAX_EX):
        print(ln)
