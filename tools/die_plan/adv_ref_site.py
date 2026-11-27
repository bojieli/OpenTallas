"""adv_ref_site.py -- PRECHECK ADV-REF-SITE (TAPKEY-SITE 11-24, FABLE flow review item 3; report only, r703).

One class for every NAME or INDEX reference to a clock tap or reset-tree node (ref_site.py): name-keyed tap tables and
rst_n_t<i> / rr_t<i> reset references are resolved to xy on the current tap grid.
  REACH  a local reset reference (collector_children / collector_local_sources / landing_local_resets) more than one relay hop
         (405 um) from the consumer it serves (QC sle_sc_v3 rst_n_t69, 1184 um, -241 ps; no baseline needed)
  MOVED  with baseline= (the last-bound plan): a reference whose resolved site moved > 9 um
  KIND   with baseline=: an index reference that crossed the tap count (seam output <-> clock tap relay)
  STAMP  stamped name-keyed tables (clock.tap_sites_um) now naming another site (adv_tapkey_site)
Bit sites are explicit xy: ADV-BITSITE-SEAT.  findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
$OT_ADV_REFSITE_TYPES=a,b (set by a scoped PRE, P-SCOPE-VIEW-KEYOUT 11-26): judge only those types, on the WHOLE plan raw (the reset
wavefront needs every partition and reset.keep_outs type; a scope view of the plan is NOT-EVALUABLE KeyError).
"""
import json
import os
import sys
from pathlib import Path

MAX_LINES = 20


def _w(*a):
    return "WARN ADV-REF-SITE " + " ".join(str(x) for x in a)


def _findings(raw, plan_path, tree=None, **kw):
    here = (Path(tree) / "tools" / "die_plan") if tree and (Path(tree) / "tools" / "die_plan" / "schema.py").is_file() else Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    fb = Path(__file__).resolve().parent
    if (fb / "ref_site.py").is_file() and str(fb) not in sys.path:
        sys.path.append(str(fb))
    import ref_site as RS
    import tap_site as TS
    os.environ.get("OT_ADV_PLANDIR") and TS.ROOTS.setdefault(str(plan_path), os.environ["OT_ADV_PLANDIR"])
    base = kw.get("baseline")
    braw, bpath = None, None
    if base:
        braw = base if isinstance(base, dict) else json.loads(Path(base).read_text())
        bpath = plan_path if isinstance(base, dict) else base
    only = set(filter(None, os.environ.get("OT_ADV_REFSITE_TYPES", "").split(","))) or None
    lines = []
    RS.run(raw, plan_path, braw, bpath, types=only, log=lines.append)
    out = [_w(ln.replace("\t", " ")) for ln in lines if not ln.startswith("SUMMARY")][:MAX_LINES]
    try:
        import adv_tapkey_site as AT
        sraw = raw if only is None else dict(raw, partition_types={k: t for k, t in (raw.get("partition_types") or {}).items() if k in only})
        out += [x.replace("ADV-TAPKEY-SITE", "ADV-REF-SITE STAMP") for x in AT.findings(sraw, plan_path, tree)]
    except Exception:  # noqa: BLE001
        pass
    out += [_w(ln.replace("\t", " ")) for ln in lines if ln.startswith("SUMMARY")]
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]
