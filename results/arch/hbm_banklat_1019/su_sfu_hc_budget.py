#!/usr/bin/env python3
"""HBM-BANKLAT-SU 10-19: LG tap chain budget (SU pgslice_lg / SFU tap_leaf / HC tap_leaf_term) and the die pads it implies.
    python3 su_sfu_hc_budget.py CONTRACT.json OUT.json      (uses tools/hbm_die_v16/d4g_bank_latency.py check())
Budget = one scalar value per tap master on every quadrant (one hard view each): SU 18/15 (GEN2c max need 17/14, +1 for
GEN2d), SFU = SU + 4 + 2 lane edges (GEN2c max su<->sfu 1/1), HC = SFU + 4 + 4 lane edges (GEN2c max sfu<->hc 2/2).
The die pads each hop's SHORT direction (narrow side preferred: rq 17 b/bank for reads, w_done 1 b/bank for writes) so
every bank's round trip equals the budget; the LAT class then PASSes with the params set to the budget."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/hbm_die_v16'))
import d4g_bank_latency as L
BUDGET = {'ot_hbm_su_static_pgslice_lg': (18, 15), 'ot_hgi_sfu_lg_pair_tap_leaf': (24, 21),
          'ot_hgi_sfu_lg_pair_tap_leaf_term': (32, 29)}
REF = {m: {r[1]: (r[4], r[5]) for r in L.RULES[m]} for m in BUDGET}      # kind -> (ref value, ref rt)


def main(contract, out):
    c = L.load(contract); rows, _ = L.check(c)
    res = []
    for r in rows:
        if r['master'] not in BUDGET or r['kind'] not in ('rd', 'wr'):
            continue
        ref, ref_rt = REF[r['master']][r['kind']]
        bud = BUDGET[r['master']][0 if r['kind'] == 'rd' else 1]
        tgt = bud - ref + ref_rt                                           # round trip the budget implies (tool units)
        hop = []
        for p in r['paths']:
            own = p['rt'] - p.get('down_rt', 0) - (L.TAP_EDGES if 'via' in p else 0)   # this hop's share (bank or lanes)
            want_own = tgt - ((BUDGET_RT_DOWN[r['master']][r['kind']]) if 'via' in p else 0)
            hop.append(dict(bank=p['bank'], via=p.get('via'), lanes=[p['lane_rq'], p['lane_rr']], rt_now=p['rt'],
                            pad=want_own - own))
        res.append(dict(client=r['client'], master=r['master'], kind=r['kind'], param=r['param'], gen2c_have=r.get('have'),
                        gen2c_need=r.get('want'), budget=bud, pads=hop, ok=all(h['pad'] >= 0 for h in hop)))
    Path(out).write_text(json.dumps(dict(schema='opentallas.hbm_banklat_su.budget.v1', contract=str(contract),
                                         budget={m: dict(READ_RETURN=v[0], WRITE_RETURN=v[1]) for m, v in BUDGET.items()},
                                         note=__doc__, rows=res), indent=1))
    bad = [x['client'] + '.' + x['kind'] for x in res if not x['ok']]
    print(f'BUDGET rows={len(res)} over_budget={len(bad)} {bad[:8]}')
    print('max pad per hop:', max(h['pad'] for x in res for h in x['pads']))


# downstream round trip (tool units) under budget, for chained taps: SU budget rt = 18-10+6 = 14 / 15-7+3 = 11; SFU 24-14+10 = 20 / 21-11+7 = 17
BUDGET_RT_DOWN = {'ot_hgi_sfu_lg_pair_tap_leaf': {'rd': 14 + L.TAP_EDGES, 'wr': 11 + L.TAP_EDGES},
                  'ot_hgi_sfu_lg_pair_tap_leaf_term': {'rd': 20 + L.TAP_EDGES, 'wr': 17 + L.TAP_EDGES}}

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
