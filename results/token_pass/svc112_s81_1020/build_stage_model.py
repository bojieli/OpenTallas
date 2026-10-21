"""Build a pinned split112 stage map from its actual all-frame allocator probes.

This is a bounded capacity model; the generated specs must still receive exact
full-stage compiler receipts before the map or a MU calendar can be admitted.
"""
import functools
import hashlib
import json
from pathlib import Path
import sys

D = Path(__file__).resolve().parent
sys.path.insert(0,str(D/'root/tools/s81_dv/layer_prog'))
import xs_stage_map as SM

def main():
    probe = json.loads((D/'out/probes/summary.json').read_text())
    s = {x['id']:x for x in probe['specs']}
    assert all(x['pass'] and x['frames']==112 and x['faults']==0 for x in s.values())
    slope = max(s[f'exp_n{n}']['q_max_fill']/n for n in (1,2,3))
    assert len({s[f'exp_n{n}']['q_max_fill']/n for n in (1,2,3)})==1
    costs = dict(slope=slope,
                 phases_per_expert=max(s[f'exp_n{n}']['cfg7_phases']/n for n in (1,2,3)),
                 dense={c:dict(q=s[f'dense_L{l}_n0']['q_max_fill'],
                               bf=s[f'dense_L{l}_n0']['bf_max_fill'],
                               phases=s[f'dense_L{l}_n0']['cfg7_phases'])
                        for c,l in [('L0',0),('L1',1),('L2',2),('L14',14),('L20',20),('L24',24)]},
                 source='actual split112 all-frame pinned N1/N2/N3 and dense N0 probes')
    SM.census = functools.lru_cache(None)(SM.census)
    for n in range(120,513):
        m=SM.build(n,costs,'split112 inventory, pinned pairs; bounded actual-allocator model')
        if m['stages_count']<=n and all(x['model_load']<8192 and x['n_experts']<=SM.nmax(
                costs,SM.cls_of(x['dense_layer']) if x['dense_layer'] is not None else None)
                for x in m['stages']):
            break
    else:
        raise RuntimeError('No feasible stage model through512')
    for count in (n,n+8):
        m=SM.build(count,costs,f'split112 candidate {count} stages; exact receipts owed')
        (D/f'stage_map_{count}_MODELONLY.json').write_text(json.dumps(m,indent=1)+'\n')
        (D/f'specs_{count}.json').write_text(json.dumps(SM.specs_of(m),indent=1)+'\n')
    copies=sum(len(x['dies']) for x in m['stages'] if x['copy_b'])
    rec=dict(scope='SPLIT112_BOUNDED_CAPACITY_MODEL_NOT_PHYSICAL_OR_MU_ADMISSION',
             inventory_sha256=hashlib.sha256((D/'inventory.json').read_bytes()).hexdigest(),
             costs=costs,required_stages_model=n,layer_dies_model=4*n,copy_b_dies_model=copies,
             fixed_other_dies_model=52,total_dies_model=4*n+copies+52,
             exact_full_stage_capacity='OWED',calendar='OWED',rates='NOT_QUALIFIED')
    (D/'stage_model.json').write_text(json.dumps(rec,indent=1)+'\n')
    print('SPLIT112_STAGE_MODEL',json.dumps(rec),flush=True)

if __name__=='__main__':
    main()
