#!/usr/bin/env python3
"""S81 selected72 G8 plan (S81-G8 10-21): the G7 plan constructor (dv_plan72_g4.augment + dv_plan72.build + dv_plan72_g7.g7,
unchanged blocks/links: 161 blocks, 819 links, 2 blockages) on the G8 floorplan (dv_floorplan72_g8.py: full reticle
33000 x 26000, 0.1 mm seal ring, wider slice-row / service streets, all four end parents 2851.2) + the qualified S81
release map bound into the plan facts (map72-bind 483869b91: the same asserts as dv_plan --stage-map there:
verdict all_pass, die_frames 72 / rom_slots 660 = this plan's inventory, layer_dies 964 = 241 x 4 = listed dies).
"""
import argparse, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dv_plan72 import build
from dv_plan72_g4 import augment
from dv_plan72_g7 import g7

STAGE_MAP = 'results/arch/s81_map72_1021/r2_241/stage_map_f72r224gpq_241.json'


def bind_stage_map(p, path):
    facts = p['facts']; raw = Path(path).read_bytes(); sm = json.loads(raw)
    assert sm.get('verdict', {}).get('all_pass'), ('stage map capacity verdict not all_pass', path)
    want = (sm['die_frames'], sm.get('rom_slots'))
    assert facts['n_frames'] == want[0] and (want[1] is None or facts.get('rom_slots') == want[1]), \
        ('stage map qualified on another die inventory', path, want, facts['n_frames'], facts.get('rom_slots'))
    assert sm['stages_count'] == len(sm['stages'])
    assert sm['layer_dies'] == sm['stages_count'] * sm['rank_dies_per_stage'] == sum(len(s['dies']) for s in sm['stages']), \
        ('stage map layer_dies mismatch', sm['layer_dies'], sm['stages_count'], sm['rank_dies_per_stage'])
    facts['stage_map'] = dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), stages=sm['stages_count'],
                              rank_dies_per_stage=sm['rank_dies_per_stage'], layer_dies=sm['layer_dies'], plan=sm.get('plan'),
                              die_frames=want[0], verdict=sm['verdict'], bound_by='map72-bind 483869b91 (qualified, unchanged)')


def main():
    a = argparse.ArgumentParser(); a.add_argument('--base', required=True); a.add_argument('--inventory', required=True)
    a.add_argument('--packing', required=True); a.add_argument('--out', required=True); a.add_argument('--stage-map', default=STAGE_MAP)
    v = a.parse_args()
    base, inv, pk = [json.load(open(x)) for x in (v.base, v.inventory, v.packing)]
    p = g7(build(augment(base), inv, pk), pk)
    geo = {b['name']: b for b in pk['best']['blocks']}
    for b in p['blocks']:                       # G8 end slots: plan width follows the floorplan slot (s_0S 2505.6 -> 2851.2)
        if b['name'] in ('s_0S', 's_0N', 's_7S', 's_7N'):
            slot = [g for g in geo.values() if abs(g['x'] - b['x']) < 1e-3 and abs(g['y'] - b['y']) < 1e-3]
            assert len(slot) == 1 and slot[0]['name'].startswith('end_parent_'), (b['name'], slot)
            b['w'] = slot[0]['w']
    p['facts']['physical72']['g4'] = dict(lane_pair5='s_0N pair B (lepw_mab_mu_72) <-> lk_WN2/lk_WN3 = link_0_4/link_0_5',
                                          new_links=['lt_lk_WN2', 'lr_lk_WN2', 'lt_lk_WN3', 'lr_lk_WN3'],
                                          reserves=[r['name'] for r in p['blockages']])
    p['facts']['physical72']['g8'] = dict(pk['g8_changes'], floorplan='dv_floorplan72_g8.py (G7 + full reticle, seal ring 100)')
    p['facts']['reticle_margin_um'] = dict(owner_10_21='full 33 x 26 mm reticle, 0.5 mm margin dropped, ~0.1 mm seal ring inside the outline',
                                           seal_ring_um=pk['g8_changes']['seal_ring_um'])
    bind_stage_map(p, v.stage_map)
    Path(v.out).write_text(json.dumps(p, indent=1))
    print(json.dumps(dict(blocks=len(p['blocks']), links=len(p['links']), blockages=len(p['blockages']), die=p['facts']['die_um'],
                          stage_map=p['facts']['stage_map']['stages'])))


if __name__ == '__main__':
    main()
