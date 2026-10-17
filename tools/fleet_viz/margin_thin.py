#!/usr/bin/env python3
"""DIE-BINDABLE / margin-thin list (coordinator, owner safe margins, 2026-10-16).

A CLOSED view is die-bindable only with native PASS AND TT >= +25 ps AND FF >= +10 ps.  Native PASS = the
tools/hier_contract/native_pin_audit.py per-view result passes (TT launch O-R <= 220 ps, capture S+R <= 190 ps, no
combinational pin arc) AND its boundary clock spread <= 80 ps AND the view carries insertion.json (R = the routed
boundary mean; without it the reference is unproven).  Closure is never revoked: the fleet-viz element table lists the
rest as 'closed, margin-thin' (tools/fleet_viz/elements.py apply_die_bindable reads the 'views' list of this file).

    native_pin_audit.py --root <checkout of main> --out AUDIT
    margin_thin.py --audit AUDIT --elements elements.json [--source SHA] --out results/arch/margin_thin_1016.json
(elements.json = fleet-viz /api/elements, for the per-design list of CLOSED registry rows with their best TT/FF.)
"""
import argparse, collections, datetime, json, pathlib

TT_PS, FF_PS, SPREAD_PS = 25.0, 10.0, 80.0


def native_of(v):
    why = []
    if not v.get('insertion', False): why.append('no insertion.json (R unproven)')
    if v.get('error'): why.append('audit error: %s' % v['error'])
    if v.get('pass') is False and v.get('fail_why'): why.append(v['fail_why'])
    elif v.get('pass') is not True and not v.get('error'): why.append('audit did not pass')
    if (v.get('spread_ps') or 0) > SPREAD_PS: why.append('spread %s > %g' % (v['spread_ps'], SPREAD_PS))
    return ('FAIL' if why else 'PASS'), '; '.join(why)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--audit', required=True); ap.add_argument('--elements', required=True)
    ap.add_argument('--source', default=''); ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    views = []
    for f in sorted(pathlib.Path(a.audit).glob('*.json')):
        doc = json.loads(f.read_text())
        if not isinstance(doc, dict) or 'views' not in doc: continue
        for v in doc['views']:
            nat, why = native_of(v)
            views.append(dict(cell=v.get('cell'), view=v.get('view'), job=v.get('job'), audit_design=doc.get('design'),
                              native=nat, native_why=why, launch_ps=v.get('launch_ps'), capture_ps=v.get('capture_ps'),
                              spread_ps=v.get('spread_ps'), R_ps=v.get('R_ps'), used_in_die=v.get('used')))
    by = {}
    for v in views:
        for k in filter(None, (v['job'], v['cell'])): by.setdefault(k, v)
    E = json.loads(pathlib.Path(a.elements).read_text())
    per, counts = collections.defaultdict(list), collections.defaultdict(collections.Counter)
    for r in E['independent_rows']:
        cat = r.get('closed_category') or r['category']
        if not cat.startswith('closed') or r['category'] == 'superseded': continue
        b = r.get('best') or {}; tt, ff = b.get('tt'), b.get('ff')
        v = by.get(b.get('job')) or next((by[k] for k in [r['element']] + r.get('variants', []) if k in by), None)
        native = (v or {}).get('native'); why = []
        if native != 'PASS': why.append('native ' + ((v or {}).get('native_why') or 'FAIL') if native == 'FAIL' else 'native unaudited (no view on main)')
        if tt is None or tt < TT_PS: why.append('TT %s < +%g' % (tt, TT_PS))
        if ff is None or ff < FF_PS: why.append('FF %s < +%g' % (ff, FF_PS))
        t = r['target']; counts[t]['closed'] += 1
        if not why: counts[t]['die_bindable'] += 1; continue
        counts[t]['margin_thin'] += 1
        counts[t]['thin_native_fail'] += native == 'FAIL'; counts[t]['thin_native_unaudited'] += native is None
        counts[t]['thin_tt'] += tt is None or tt < TT_PS; counts[t]['thin_ff'] += ff is None or ff < FF_PS
        per[t].append(dict(element=r['element'], category=cat, job=b.get('job'), tt=tt, ff=ff, native=native,
                           view=(v or {}).get('view'), why='; '.join(why), die_contract=bool(r.get('dies'))))
    for t in per: per[t].sort(key=lambda x: (not x['die_contract'], x['element']))
    out = dict(schema='opentallas.margin_thin.v1', generated=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               source_main=a.source, rule=dict(native='launch<=220, capture<=190 ps TT, no comb pin, spread<=%g ps, insertion.json present' % SPREAD_PS,
                                               tt_ps=TT_PS, ff_ps=FF_PS, note='closure is NOT revoked; margin-thin rows stay closed'),
               counts={t: dict(c) for t, c in counts.items()}, margin_thin=dict(per), views=views)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['counts'], indent=1))


if __name__ == '__main__':
    main()
