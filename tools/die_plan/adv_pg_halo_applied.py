"""ADV-PG-HALO-APPLIED (FP-CONVERGE-QC 11-25; an estimator, report only, never a gate).

Class: a hard_cores[].pg_halo_um that never reaches the PDN.  PG-EDGE-HALO-1 (gen_phys.core_pg_halos / core_pg_grids) emits a
`define_pdn_grid -macro ... -halo h` only for a core whose type has core_pg_connect on and whose halo is > 0; ADV-PG-EDGE-PIN skips every
core with pg_halo_um > 0 and so trusts the halo blindly.  QC st_a (DRC 72 = M5 Short/Spacing at u_r1/r2/r3 faces) was a halo that
was missing from the plan; the same silent loss can come from these plan states, each a WARN per type:
  HALO-INERT    pg_halo_um > 0 on a core of a type with core_pg_connect explicitly false: core_pg_grids returns [] and no halo grid exists
  HALO-SMALL    0 < halo < MIN_HALO_UM (0.3 um): under half a VDD+VSS M5 pair plus one spacing (0.228 um) with margin, straps still touch the edge
  HALO-LARGE    halo > MAX_HALO_UM (8.64 um, 2 M5 pairs x 1 pitch of the M7 stripe): the tile PG is cut back far enough to starve the macro supply
  HALO-BAD      pg_halo_um present but not a finite number >= 0
  HALO-CLASH    two cores of one type with the same physical_inst / inst but different halos (core_pg_halos keeps the last)
  HALO-DROPPED  a core whose module carries pg_halo_um > 0 on a sibling core elsewhere in the plan, with none or 0 on this one
                (a row that rewrote hard_cores, or a type added after the halo row; the halo row keys are per core)
findings(raw, plan_path, tree=None, **kw) -> WARN lines (+ a LIST summary).  Fix: set hard_cores[].pg_halo_um (1.296 for st_a) and
core_pg_connect true/unset on the type.
"""
import math
import os

CHECK = "ADV-PG-HALO-APPLIED"
MIN_HALO_UM = float(os.environ.get("OT_ADV_PG_HALO_MIN_UM", "0.3"))
MAX_HALO_UM = float(os.environ.get("OT_ADV_PG_HALO_MAX_UM", "8.64"))
MAX_EX = 4


def _w(*parts):
    return " ".join(["WARN", CHECK] + [str(p) for p in parts])


def _num(v):
    if v is None:
        return 0.0
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        raise ValueError(v)
    return float(v)


def _cores(raw):
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if isinstance(t, dict):
            for hc in t.get("hard_cores") or []:
                if isinstance(hc, dict):
                    yield tn, t, hc


def findings(raw, plan_path=None, tree=None, **_kw):
    haloed = {}                                   # module -> a (type, inst) with halo > 0
    for tn, t, hc in _cores(raw):
        try:
            if _num(hc.get("pg_halo_um")) > 0:
                haloed.setdefault(hc.get("module"), (tn, hc.get("inst")))
        except ValueError:
            pass
    by = {}                                       # (class, type) -> [text]
    for tn, t, hc in _cores(raw):
        inst, mod = hc.get("inst", "?"), hc.get("module", "?")
        try:
            h = _num(hc.get("pg_halo_um"))
        except ValueError:
            by.setdefault(("HALO-BAD", tn), []).append(f"{inst} pg_halo_um={hc.get('pg_halo_um')!r}")
            continue
        if h > 0:
            if t.get("core_pg_connect") is False:
                by.setdefault(("HALO-INERT", tn), []).append(f"{inst} halo {h:g}")
            if h < MIN_HALO_UM:
                by.setdefault(("HALO-SMALL", tn), []).append(f"{inst} halo {h:g} < {MIN_HALO_UM:g}")
            if h > MAX_HALO_UM:
                by.setdefault(("HALO-LARGE", tn), []).append(f"{inst} halo {h:g} > {MAX_HALO_UM:g}")
        elif mod in haloed and haloed[mod][0] != tn:
            by.setdefault(("HALO-DROPPED", tn), []).append(f"{inst} ({mod}; halo on {haloed[mod][0]}/{haloed[mod][1]})")
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        seen = {}
        for hc in (t.get("hard_cores") or []) if isinstance(t, dict) else []:
            k = hc.get("physical_inst") or hc.get("inst")
            try:
                h = _num(hc.get("pg_halo_um"))
            except ValueError:
                continue
            if k in seen and seen[k] != h:
                by.setdefault(("HALO-CLASH", tn), []).append(f"{k} halo {seen[k]:g} vs {h:g}")
            seen[k] = h
    out, counts = [], {}
    for (cls, tn), ex in sorted(by.items()):
        counts[cls] = counts.get(cls, 0) + len(ex)
        out.append(_w(cls, f"{tn}: {len(ex)} core(s): " + "; ".join(ex[:MAX_EX]) + (" ..." if len(ex) > MAX_EX else "")))
    if out:
        out.append(f"LIST {CHECK} " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + " core(s) (fix: hard_cores[].pg_halo_um, core_pg_connect)")
    return out
