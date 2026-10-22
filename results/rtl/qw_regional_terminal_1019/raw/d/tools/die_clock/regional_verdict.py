#!/usr/bin/env python3
"""QW-DIECLK 10-19: verdict of a REGIONAL die clock build (landed-regions standard), one line + JSON.
  regional_verdict.py CHECK.json LANDED_PAIRS.json MANIFEST.json [--budget 80] [--period 833.333] [--out OUT.json]
PASS needs ALL of:
  intra    every region's judged pair class (die_clock_check --per-region) <= budget at TT and FF;
  landed   no cross-region data crossing left unlanded (landed_pairs NEIGHBOUR + GAP = 0; else the GEN owes landings);
  drift    every landed lane's clock lag drift |dck_FF - dck_TT| <= T/2 (the 4-slot ring window keeps one E per lane);
  spine    the forwarded spine carries no pads (balance false) -- a padded spine is the rejected global-balance shape.
NO_ROOT pairs are reported (GEN gap), never a clocking pass."""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('check'); ap.add_argument('pairs'); ap.add_argument('manifest')
    ap.add_argument('--budget', type=float, default=80.0)
    ap.add_argument('--period', type=float, default=833.333)
    ap.add_argument('--out')
    a = ap.parse_args()
    nc = (json.load(open(a.check)).get('neighbour_check') or {})
    intra = dict(classes=0, over=0, worst=[])
    for k, c in (nc.get('classes') or {}).items():
        if not c.get('judged') or not k.startswith('intra:'):
            continue
        intra['classes'] += 1
        if c.get('over'):
            intra['over'] += 1
            intra['worst'].append([k[6:], c['pairs'], (c.get('tt_ps') or {}).get('max'), (c.get('ff_ps') or {}).get('max')])
    intra['worst'].sort(key=lambda w: -max(w[2] or 0, w[3] or 0))
    lp = json.load(open(a.pairs))
    s = lp['summary']; pc = s.get('pairs', {})
    owed = dict(neighbour_bits=pc.get('NEIGHBOUR', 0), gap_bits=pc.get('GAP', 0), no_root=pc.get('NO_ROOT', 0),
                links=len(lp.get('land_owed', [])))
    meas = [r for r in lp.get('lanes', []) if 'drift' in r]
    drift = dict(lanes=len(lp.get('lanes', [])), measured=len(meas),
                 max_abs=max((abs(r['drift']) for r in meas), default=None),
                 over_half_T=sum(abs(r['drift']) > a.period / 2 for r in meas),
                 worst=sorted(([r['bid'], r.get('dck_tt'), r.get('dck_ff'), r['drift']] for r in meas),
                              key=lambda w: -abs(w[3]))[:8])
    m = json.load(open(a.manifest)); sp = m.get('spine') or {}
    spine = dict(present=bool(sp), balance=sp.get('balance'), cells=sp.get('cells'), levels=sp.get('levels'),
                 pads=(sp.get('model') or {}).get('pads'), model_insertion_ps=(sp.get('model') or {}).get('model_insertion_ps'))
    ok = dict(intra=intra['classes'] > 0 and intra['over'] == 0 and bool(nc.get('ff_measured')),
              landed=owed['neighbour_bits'] == 0 and owed['gap_bits'] == 0,
              drift=drift['measured'] > 0 and drift['over_half_T'] == 0,
              spine=(not spine['present']) or (spine['balance'] is False and not spine['pads']))
    v = 'PASS' if all(ok.values()) else 'FAIL'
    res = dict(schema='opentallas.qwen_compute.regional_clock_verdict.v1', verdict=v, ok=ok, intra=intra, owed=owed,
               drift=drift, spine=spine, budget_ps=a.budget, period_ps=a.period)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    print('QCLK_REGIONAL', v, ' '.join(f'{k}={"ok" if x else "FAIL"}' for k, x in ok.items()),
          f"| intra over {intra['over']}/{intra['classes']} worst", ' '.join(f'{w[0]} TT {w[2]} FF {w[3]}' for w in intra['worst'][:4]),
          f"| land owed links {owed['links']} bits N{owed['neighbour_bits']}+G{owed['gap_bits']} noroot {owed['no_root']}",
          f"| lane drift max {drift['max_abs']} >T/2 {drift['over_half_T']}/{drift['measured']}",
          f"| spine cells {spine['cells']} levels {spine['levels']} pads {spine['pads']} model {spine['model_insertion_ps']}")


if __name__ == '__main__':
    main()
