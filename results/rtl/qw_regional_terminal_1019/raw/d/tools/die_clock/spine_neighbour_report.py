#!/usr/bin/env python3
"""GEN16 10-19: NEIGHBOUR verdict of a spine die clock build (item 3 measured check).
  spine_neighbour_report.py CHECK.json SPEC_V.json [--budget 80] [--out OUT.json]
Reads die_clock_check.json (neighbour_check classes; spine members = one family, so every communicating cross-region
pair is judged at TT and FF) and splits the judged classes into: intra-region, NEIGHBOUR (the unlanded direct
cross-region region pairs recorded in the spec: neighbour-matched boundary required <= budget at TT and FF), other
cross-region (landed / forwarded lane ends: informational, their crossing is landed).  Prints one line."""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('check'); ap.add_argument('spec')
    ap.add_argument('--budget', type=float, default=80.0)
    ap.add_argument('--out')
    a = ap.parse_args()
    nc = json.load(open(a.check)).get('neighbour_check') or {}
    sp = json.load(open(a.spec))
    nbp = {'|'.join(sorted(p)) for p in sp.get('neighbour_pairs', [])}
    res = dict(intra=dict(classes=0, over=0, pairs=0), neighbour=dict(classes=0, over=0, pairs=0, worst=[]),
               other_cross=dict(classes=0, over=0, pairs=0), budget_ps=a.budget, ff_measured=nc.get('ff_measured'))
    for k, c in (nc.get('classes') or {}).items():
        if not c.get('judged'):
            continue
        kind, _, rp = k.partition(':')
        g = 'intra' if kind == 'intra' else ('neighbour' if rp in nbp else 'other_cross')
        r = res[g]
        r['classes'] += 1; r['pairs'] += c['pairs']; r['over'] += 1 if c['over'] else 0
        if g == 'neighbour':
            r['worst'].append(dict(pair=rp, pairs=c['pairs'], over=c['over'], tt_max=(c.get('tt_ps') or {}).get('max'),
                                   ff_max=(c.get('ff_ps') or {}).get('max')))
    res['neighbour']['worst'].sort(key=lambda w: -max(w['tt_max'] or 0, w['ff_max'] or 0))
    res['neighbour']['pairs_spec'] = len(nbp)
    res['neighbour']['unjudged'] = len(nbp) - res['neighbour']['classes']
    ok = res['neighbour']['over'] == 0 and res['neighbour']['classes'] > 0 and res['ff_measured']
    res['verdict'] = 'PASS' if ok and res['neighbour']['unjudged'] == 0 else ('FAIL' if res['neighbour']['over'] else 'INCOMPLETE')
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    w = res['neighbour']['worst'][:5]
    print('QCLK_SPINE_NEIGHBOUR', res['verdict'], f"budget {a.budget}",
          'neighbour region pairs judged', res['neighbour']['classes'], 'of', len(nbp), 'over', res['neighbour']['over'],
          '| intra classes over', res['intra']['over'], 'of', res['intra']['classes'],
          '| other cross over', res['other_cross']['over'], 'of', res['other_cross']['classes'],
          '| worst', ' '.join(f"{x['pair']} TT {x['tt_max']} FF {x['ff_max']}" for x in w))


if __name__ == '__main__':
    main()
