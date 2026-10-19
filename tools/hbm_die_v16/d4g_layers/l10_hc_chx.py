#!/usr/bin/env python3
"""DIE-HBM-LEAD 10-19: GEN2c contract post-layer L10 -- HC chain pin registers (HH-9) on the U-form HC quarters.

    l10_hc_chx.py IN_contract.json[.gz] OUT_contract.json --report R.json

Coordinator HC layout decision (lanes/H-D4G.md, DIE-HBM-LEAD 10-19): ONE electrical HC contract for GEN2c and the ring
floorplan revision (GEN2d):  root ot_hbm_hc_root_static QDRLY 2 + QCHX 11, hubs ot_hbm_hc_qhub_static DRLY 2 + CHX 11,
banks b0 CPO 1 (ot_hbm_hc_bankq0_static), b1/b3/b4/b5/b7 CPI = CPO = 1 (ot_hbm_hc_bankq_static), b2/b6 (edge banks,
ot_hbm_hc_bankq_ft_static) unchanged.  Latency ledger hc_tree 41 = RAW0 165 + 2 (DRLY 2 exit path) + 11 (CHX) + XRD + XRU.
GEN2c keeps the U form: banks at generic centroids, the b7 -> b0 exit crosses the hcx_<q>_* die relay (1 edge, the
second DRLY edge).  GEN2d (closed ring, b7 abuts b0) drops the die relay and moves that edge into bank 0 (bankq0 DRLY 2)
so hub DRLY / root QDRLY stay 2 and hc_tree stays 41 (one calendar, one hub/root kit).
Ports do not change (parameters only); exit != 0 if an expected instance or base parameter is missing.
"""
import argparse, gzip, json, sys

CHX = 11
Q4 = ('SW', 'SE', 'NW', 'NE')


def load(p):
    return json.load(gzip.open(p, 'rt') if p.endswith('.gz') else open(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = load(a.inp); I = c['instances']; prob = []; done = []

    def setp(n, master, need, add):
        x = I.get(n)
        if x is None or x['master'] != master:
            prob.append(f'{n}: expected {master}, got {None if x is None else x["master"]}'); return
        p = x.setdefault('params', {})
        for k, v in need.items():
            if p.get(k) != v:
                prob.append(f'{n}: expected {k}={v}, got {p.get(k)}')
        p.update(add); done.append([n, master, dict(p)])
        x['note'] = (x.get('note') or '') + f' | L10 HH-9 chain pin registers {add} (DIE-HBM-LEAD 10-19)'

    setp('hc_eng', 'ot_hbm_hc_root_static', {'QDRLY': 2}, {'QCHX': CHX})
    for q in Q4:
        setp(f'hc_{q}', 'ot_hbm_hc_qhub_static', {'DRLY': 2}, {'CHX': CHX})
        setp(f'hcb_{q}0', 'ot_hbm_hc_bankq0_static', {'DRLY': 1}, {'CPO': 1})
        for k in (1, 3, 4, 5, 7):
            setp(f'hcb_{q}{k}', 'ot_hbm_hc_bankq_static', {}, {'CPI': 1, 'CPO': 1})
        for k in (2, 6):
            x = I.get(f'hcb_{q}{k}')
            if x is None or x['master'] != 'ot_hbm_hc_bankq_ft_static' or x.get('params'):
                prob.append(f'hcb_{q}{k}: expected unparameterised ot_hbm_hc_bankq_ft_static')
        if not any(n.startswith(f'hcx_{q}_') for n in I):
            prob.append(f'hcx_{q}_*: U-form b7->b0 die relay missing (hub DRLY 2 needs it in GEN2c)')
    c.setdefault('notes', [])
    if isinstance(c['notes'], list):
        c['notes'].append('L10 (DIE-HBM-LEAD 10-19): HC chain pin registers bound -- root QCHX 11, hubs CHX 11, '
                          'b0 CPO 1, b1/3/4/5/7 CPI=CPO 1; U form + hcx die relay (DRLY 2); ledger hc_tree 41')
    rep = dict(layer='l10_hc_chx', chx=CHX, instances=done, problems=prob, hc_tree=41,
               form='U + hcx b7->b0 die relay (GEN2c); GEN2d closed ring = bankq0 DRLY 2, no die relay, same hub/root params')
    json.dump(rep, open(a.report, 'w'), indent=1)
    if prob:
        print('L10_FAIL', len(prob)); print('\n'.join(prob[:20])); sys.exit(2)
    json.dump(c, open(a.out, 'w'))
    print(f'L10_OK instances={len(done)} (root QCHX {CHX}, 4 hubs CHX {CHX}, 4 b0 CPO, 20 banks CPI/CPO)')


if __name__ == '__main__':
    main()
