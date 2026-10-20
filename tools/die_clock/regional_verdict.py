#!/usr/bin/env python3
"""QW-DIECLK 10-19: verdict of a REGIONAL die clock build (landed-regions standard), one line + JSON.
  regional_verdict.py CHECK.json LANDED_PAIRS.json MANIFEST.json [--budget 80] [--period 833.333] [--out OUT.json]
PASS needs ALL of:
  intra    every region's judged pair class (die_clock_check --per-region) <= budget at TT and FF;
  landed   no cross-region data crossing left unlanded (landed_pairs NEIGHBOUR + GAP = 0; else the GEN owes landings);
  drift    every landed lane fits ONE E in its L5 window (lanes/LANDING-CONTRACT.md: (E-D)T + t_hold < dL < ET - t_cq -
           t_setup at TT and FF; window width D*T): pre-STA proxy |dck_FF - dck_TT| <= (D-1)*T - 2*margin (QW-DIECLK4
           10-20: the old T/2 proxy was 4x stricter than the contract window and is still reported as info); with
           --land-plan (tools/qwen_split/fwd_land_plan.py plan on the die STA, per-lane D) the STA window is binding:
           window_fail must be empty;
  spine    the forwarded spine carries no pads (balance false) -- a padded spine is the rejected global-balance shape.
NO_ROOT pairs are reported (GEN gap), never a clocking pass; BUMP pairs (off-die forwarded inputs, qfd_sigbump) are owed
a hop-0 on the feed clock + landing by the GEN and also fail 'landed'."""
import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('check'); ap.add_argument('pairs'); ap.add_argument('manifest')
    ap.add_argument('--budget', type=float, default=80.0)
    ap.add_argument('--period', type=float, default=833.333)
    ap.add_argument('--D', type=int, default=4, help='landing ring depth for the pre-STA drift proxy')
    ap.add_argument('--margin', type=float, default=100.0, help='ps per window side (t_cq + t_setup / t_hold + jitter)')
    ap.add_argument('--land-plan', help='fwd_land_plan.json of the die STA (binding L5 window per lane)')
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
                bump_bits=pc.get('BUMP', 0), links=len(lp.get('land_owed', [])))
    meas = [r for r in lp.get('lanes', []) if 'drift' in r]
    drift = dict(lanes=len(lp.get('lanes', [])), measured=len(meas),
                 max_abs=max((abs(r['drift']) for r in meas), default=None),
                 over_half_T_info=sum(abs(r['drift']) > a.period / 2 for r in meas),
                 window_proxy_ps=round((a.D - 1) * a.period - 2 * a.margin, 1),
                 over_window=sum(abs(r['drift']) > (a.D - 1) * a.period - 2 * a.margin for r in meas),
                 worst=sorted(([r['bid'], r.get('dck_tt'), r.get('dck_ff'), r['drift']] for r in meas),
                              key=lambda w: -abs(w[3]))[:8])
    if a.land_plan:
        pl = json.load(open(a.land_plan)); su = pl.get('summary', {})
        drift['land_plan'] = dict(path=a.land_plan, D=pl.get('D'), D_hist=su.get('D_hist'), links=su.get('links'),
                                  window_fail=su.get('window_fail', []), no_slack=su.get('no_slack', []))
    m = json.load(open(a.manifest)); sp = m.get('spine') or {}
    spine = dict(present=bool(sp), balance=sp.get('balance'), cells=sp.get('cells'), levels=sp.get('levels'),
                 pads=(sp.get('model') or {}).get('pads'), model_insertion_ps=(sp.get('model') or {}).get('model_insertion_ps'))
    ok = dict(intra=intra['classes'] > 0 and intra['over'] == 0 and bool(nc.get('ff_measured')),
              landed=owed['neighbour_bits'] == 0 and owed['gap_bits'] == 0 and owed['bump_bits'] == 0,
              drift=drift['measured'] > 0 and drift['over_window'] == 0 and
              (not a.land_plan or not drift['land_plan']['window_fail']),
              spine=(not spine['present']) or (spine['balance'] in (False, 'geometric') and not spine['pads']))
    v = 'PASS' if all(ok.values()) else 'FAIL'
    res = dict(schema='opentallas.qwen_compute.regional_clock_verdict.v1', verdict=v, ok=ok, intra=intra, owed=owed,
               drift=drift, spine=spine, budget_ps=a.budget, period_ps=a.period)
    if a.out:
        json.dump(res, open(a.out, 'w'), indent=1)
    print('QCLK_REGIONAL', v, ' '.join(f'{k}={"ok" if x else "FAIL"}' for k, x in ok.items()),
          f"| intra over {intra['over']}/{intra['classes']} worst", ' '.join(f'{w[0]} TT {w[2]} FF {w[3]}' for w in intra['worst'][:4]),
          f"| land owed links {owed['links']} bits N{owed['neighbour_bits']}+G{owed['gap_bits']} noroot {owed['no_root']} bump {owed['bump_bits']}",
          f"| lane drift max {drift['max_abs']} >window {drift['window_proxy_ps']} {drift['over_window']}/{drift['measured']} (info >T/2 {drift['over_half_T_info']})",
          (f"| STA L5 window_fail {len(drift['land_plan']['window_fail'])} D {drift['land_plan']['D_hist']}" if a.land_plan else '| STA L5 not given'),
          f"| spine cells {spine['cells']} levels {spine['levels']} pads {spine['pads']} model {spine['model_insertion_ps']}")


if __name__ == '__main__':
    main()
