"""LEAD9-S81: specs for the 122-frame (idx3 repack keeping 122 frames) map, N stages, slope 72 costs."""
import sys,json
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'root/tools/s81_dv/layer_prog'))
import xs_stage_map as SM
n=int(sys.argv[1]); mod=json.loads((D/'inventory_slot_model.json').read_text())['122']
c=dict(json.loads((D/'required_stage_model.json').read_text())['costs']); c['slope']=mod['worst_expert_words_per_pair_representatives']
c['phases_per_expert']=max(r['phases']/r['n'] for r in mod['exact_small_rows'])
m=SM.build(n,c,f'{n}-stage pinned (PAIR_ROTATE=0), 122-frame inventory 9cce72c0 (idx3 repack keeping 122 frames), LEAD9-S81')
assert m['stages_count']<=n,m['stages_count']
(D/f'stage_map_f122_{n}.json').write_text(json.dumps(m,indent=1)+'\n')
sp=SM.specs_of(m);(D/f'specs_f122_{n}.json').write_text(json.dumps(sp,indent=1)+'\n')
print('SPECS122',n,m['stages_count'],len(sp),max(s['model_load'] for s in m['stages']),max(s['n_experts'] for s in m['stages']))
