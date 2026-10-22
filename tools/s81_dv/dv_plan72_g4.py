#!/usr/bin/env python3
"""S81 selected72 G4 plan (S81-LINK5 L5-G4 10-21): dv_plan72.build on the G3 base plan augmented with the 5th lane pair.

The base plan gains two SerDes instances lk_WN2 / lk_WN3 (master ot_pdie_serdes, base geometry = lk_WN0 / lk_WN1, so
dv_plan72 maps them to the G4 floorplan slots link_0_4 / link_0_5) and four links copied from the s_0N <-> lk_WN0/1 links
(same class, bits, kind, names lt_/lr_lk_WN2/3): s_0N tx2 -> lk_WN2 tx, lk_WN2 rx -> s_0N rx2, s_0N tx3 -> lk_WN3 tx,
lk_WN3 rx -> s_0N rx3.  s_0N endpoint seeds continue the W-face pin pitch (160 um) above tx1/rx1; the SerDes seeds sit at
the same relative position as on lk_WN0/1.  Port names tx2/tx3/rx2/rx3 = the end-parent top ot_s81sl_slice_lepw_mab_mu_72
(L5-RTL).  s_0N keeps its plan master key dsdv_slice_lepw_mu (the bind overlay maps that key to the mab module).
"""
import argparse, copy, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dv_plan72 import build

NEW = (('lk_WN2', 'lk_WN0', 2), ('lk_WN3', 'lk_WN1', 3))
PITCH = 160.0


def augment(base):
    b = copy.deepcopy(base); names = [x['name'] for x in b['blocks']]; ix = {n: i for i, n in enumerate(names)}
    assert 'lk_WN2' not in ix and 'lk_WN3' not in ix
    by_i = {l['i']: l for l in b['links']}
    top_tx = max(by_i[f'lt_lk_WN{j}']['e'][0][3] for j in (0, 1)); top_rx = max(by_i[f'lr_lk_WN{j}']['e'][1][3] for j in (0, 1))
    for k, (new, src, port) in enumerate(NEW):
        nb = dict(copy.deepcopy(b['blocks'][ix[src]]), name=new); b['blocks'].append(nb); ni = len(b['blocks']) - 1
        for pre, top in (('lt', top_tx), ('lr', top_rx)):
            l = copy.deepcopy(by_i[f'{pre}_{src}']); l['i'] = f'{pre}_{new}'
            for key in ('sp', 'h', 's', 'L'):
                l.pop(key, None)
            sl, lk = (0, 1) if pre == 'lt' else (1, 0)          # e index of the s_0N end / the SerDes end
            assert b['blocks'][l['e'][sl][0]]['name'] == 's_0N' and l['e'][lk][0] == ix[src]
            l['e'][lk][0] = ni
            l['e'][sl][1] = ('tx' if pre == 'lt' else 'rx') + str(port)
            l['e'][sl][3] = round(top + (k + 1) * PITCH, 4)
            b['links'].append(l)
    return b


def main():
    a = argparse.ArgumentParser(); a.add_argument('--base', required=True); a.add_argument('--inventory', required=True)
    a.add_argument('--packing', required=True); a.add_argument('--out', required=True); v = a.parse_args()
    base, inv, pk = [json.load(open(x)) for x in (v.base, v.inventory, v.packing)]
    p = build(augment(base), inv, pk)
    p['facts']['physical72']['g4'] = dict(lane_pair5='s_0N pair B (lepw_mab_mu_72) <-> lk_WN2/lk_WN3 = link_0_4/link_0_5',
                                          new_links=[f'{x}_{n}' for n, _, _ in NEW for x in ('lt', 'lr')],
                                          reserves=[r['name'] for r in p['blockages']])
    Path(v.out).write_text(json.dumps(p, indent=1))
    print(json.dumps(dict(blocks=len(p['blocks']), links=len(p['links']), blockages=len(p['blockages']), die=p['facts']['die_um'])))


if __name__ == '__main__':
    main()
