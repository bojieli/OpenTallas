"""adv_tapkey_site.py -- PRECHECK ADV-TAPKEY-SITE (TAPKEY-SITE 11-24; report only).

Every name-keyed tap table of a type (die clock.tap_offset / tap_window .per_port_ps[T], type clock.tap_pin_heights_um,
type clock.tap_group.fixed_taps) is compared, through the type's site stamp clock.tap_sites_um (tap_site.py), with the plan's
CURRENT tap at that site.  A stamped port whose current tap at its site has another name (renumbered) or no tap within 9 um
(unsited) is reported with the tables that reference it; gen_phys re-keys the stamped tables the same way (tap_site.rekey_plan).
Types with name-keyed tables but no stamp are counted as NO-STAMP (ADV-TAPOFF-SITE judges those against a baseline plan).
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import os
import sys
from pathlib import Path

MAX_LINES = 20


def _w(*a):
    return "WARN ADV-TAPKEY-SITE " + " ".join(str(x) for x in a)


def _findings(raw, plan_path, tree=None, **kw):
    here = (Path(tree) / "tools" / "die_plan") if tree and (Path(tree) / "tools" / "die_plan" / "schema.py").is_file() else Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    fb = Path(__file__).resolve().parent
    if (fb / "tap_site.py").is_file() and str(fb) not in sys.path:
        sys.path.append(str(fb))
    import tap_site as TS
    try:
        import taps as _T
        _T.PLAN_DIR = os.environ.get("OT_ADV_PLANDIR") or str(Path(plan_path).resolve().parent)
    except Exception:  # noqa: BLE001
        pass
    import schema as S
    P = S.Plan(raw, Path(plan_path))
    out, nst, nbad, nost, unev, totm = [], 0, 0, 0, 0, 0
    for tn in sorted(raw.get("partition_types") or {}):
        tabs = TS.type_tables(raw, tn)
        if TS._stamped(raw, tn) is None:
            nost += bool(tabs)
            continue
        try:
            sites = TS.current_sites(P, raw, tn)
        except Exception:  # noqa: BLE001
            unev += 1
            continue
        moved, n = TS.check_type(raw, tn, sites)
        nst += 1
        refs = {}
        for label, box, key, form in tabs:
            for q in (box[key].keys() if form == "keys" else box[key].values()):
                refs.setdefault(q, set()).add(label)
        hit = [(p, q, d) for p, q, d in moved if p in refs]
        if hit:
            nbad += 1
            totm += len(hit)
            out.append((len(hit), _w(f"{tn}: {len(hit)} of {n} stamped tap names referenced by name-keyed tables now name another site: "
                                     + " ".join(f"{p}->{q or 'UNSITED'}({','.join(sorted(refs[p]))})" for p, q, _d in hit[:8])
                                     + "; gen_phys re-keys them by site (tap_site.rekey_plan); re-stamp the source plan with tap_site.py rekey")))
    out.sort(key=lambda x: -x[0])
    lines = [m for _, m in out[:MAX_LINES]]
    lines.append(_w("summary", f"{nbad} of {nst} stamped types have referenced tap names on another site ({totm} names); "
                               f"{nost} types with name-keyed tap tables carry no site stamp (tap_site.py stamp; ADV-TAPOFF-SITE needs a baseline for them); "
                               f"{unev} stamped types not evaluable"))
    return lines


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]
