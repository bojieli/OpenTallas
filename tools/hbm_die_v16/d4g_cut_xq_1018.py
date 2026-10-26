#!/usr/bin/env python3
"""HBM-PRICE5 (10-18): d4g_phy cut + bit-mm for cross-quadrant COLL topologies (extends H-D4G3b d4g_cut_ring2.py):
rings 1..4 (+280 b per direction per added ring on every COLL_RING link) and a 2x2 full mesh (diagonal COLL links
coll_SW<->coll_NE, coll_SE<->coll_NW of W bits per direction) on top of ring A [+ ring B]."""
import copy, json, sys, math
from pathlib import Path
W = Path(sys.argv[2])
sys.path.insert(0, str(W / 'tools/hbm_die_v15')); sys.path.insert(0, str(W / 'tools/hbm_die_v16'))
import plan_study_1017 as S
import plan_d4g as D
out = Path(sys.argv[1])
PA = json.loads((S.A_DIR / 'compact.P.json').read_text()); GA = json.loads((S.A_DIR / 'compact.graph.json').read_text())
PB, HB = S.plan_b(PA, side='inner')
P = D.plan_d4g(PA, 400.0, 'phy')[0]
def ctr(n):
    r = P[n]; return (r['x'] + r['w'] / 2, r['y'] + r['h'] / 2)
geo = {n: ctr(n) for n in ('coll_SW', 'coll_SE', 'coll_NW', 'coll_NE') if n in P}
man = lambda a, b: abs(geo[a][0] - geo[b][0]) + abs(geo[a][1] - geo[b][1])
lens = dict(edge_SW_SE=man('coll_SW', 'coll_SE'), edge_SE_NE=man('coll_SE', 'coll_NE'), edge_NE_NW=man('coll_NE', 'coll_NW'),
            edge_NW_SW=man('coll_NW', 'coll_SW'), diag_SW_NE=man('coll_SW', 'coll_NE'), diag_SE_NW=man('coll_SE', 'coll_NW'))
VARS = {'one_ring': (0, 0), 'two_ring': (280, 0), 'three_ring': (560, 0), 'four_ring': (840, 0),
        'mesh_1w': (0, 280), 'mesh_2w': (280, 560), 'two_ring_plus_diag_1w': (280, 280)}
res = dict(geometry_um=geo, link_manhattan_um=lens)
for tag, (add, diag) in VARS.items():
    G = copy.deepcopy(S.graph_b(GA))
    tmpl = None
    for l in G['links']:
        if l['cls'] == 'COLL_RING':
            l['bits'] += add; tmpl = tmpl or dict(l)
    if diag:
        for s, d in (('coll_SW', 'coll_NE'), ('coll_NE', 'coll_SW'), ('coll_SE', 'coll_NW'), ('coll_NW', 'coll_SE')):
            l = dict(tmpl); l.update(src=s, dst=d, bits=diag, id=f'{s}>{d}:COLL_RING', provenance=f'HBM-PRICE5 mesh diagonal {diag} b/dir')
            G['links'].append(l)
    ev = S.write_plan(out / tag, P, G, HB, 'd4g_phy_' + tag)
    cut = ev['cut_phy_unmasked']
    res[tag] = dict(added_ring_bits_per_direction=add, diagonal_bits_per_direction=diag,
                    cut_v=cut['worst_v']['ratio'], cut_h=cut['worst_h']['ratio'], worst_v=cut['worst_v'], worst_h=cut['worst_h'],
                    graph_bit_mm=ev['sum_bits_mm'], coll_ring_stages=ev['per_class'].get('COLL_RING', {}).get('stages_bw'))
    print(tag, json.dumps({k: v for k, v in res[tag].items() if k not in ('worst_v', 'worst_h')}), flush=True)
(out / 'cut_xq_1018.json').write_text(json.dumps(res, indent=1, default=str))
