#!/usr/bin/env python3
"""H-D4G3b fork C: re-check the d4g_phy plan cut with the two-ring collective (HBM-B-RTL3c ring B: +280 b per direction on
every quadrant-to-quadrant COLL_RING link = +560 b per link), plan_d4g.plan_d4g(PA, 400, 'phy') unchanged otherwise."""
import copy, json, sys
from pathlib import Path
W = Path('/home/ubuntu/wt/hd4g')
sys.path.insert(0, str(W / 'tools/hbm_die_v15')); sys.path.insert(0, str(W / 'tools/hbm_die_v16'))
import plan_study_1017 as S
import plan_d4g as D
out = Path(sys.argv[1])
PA = json.loads((S.A_DIR / 'compact.P.json').read_text()); GA = json.loads((S.A_DIR / 'compact.graph.json').read_text())
PB, HB = S.plan_b(PA, side='inner')
P = D.plan_d4g(PA, 400.0, 'phy')[0]
res = {}
for tag, add in (('one_ring', 0), ('two_ring', 280)):
    G = copy.deepcopy(S.graph_b(GA))
    n = 0
    for l in G['links']:
        if l['cls'] == 'COLL_RING':
            l['bits'] += add; n += 1
    ev = S.write_plan(out / tag, P, G, HB, 'd4g_phy_' + tag)
    cut = ev['cut_phy_unmasked']
    res[tag] = dict(coll_ring_links=n, added_bits_per_direction=add, cut_v=cut['worst_v']['ratio'], cut_h=cut['worst_h']['ratio'],
                    worst_v=cut['worst_v'], worst_h=cut['worst_h'], graph_bit_mm=ev['sum_bits_mm'],
                    coll_ring_stages=ev['per_class'].get('COLL_RING', {}).get('stages_bw'))
    print(tag, json.dumps({k: v for k, v in res[tag].items() if k not in ('worst_v', 'worst_h')}))
(out / 'cut_ring2.json').write_text(json.dumps(res, indent=1, default=str))
