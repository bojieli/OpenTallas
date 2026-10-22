import json,re
from pathlib import Path
from collections import Counter
p=Path('/srv/opentallas-scratch/claude/ref_gate/codex_s5_1020')
for q in p.glob('*.cold_pre.json'):
 top=q.name.removesuffix('.cold_pre.json');d=json.loads(q.read_text())['modules']['proof'];types=Counter(c['type'] for c in d['cells'].values());seq=[(n,c['type']) for n,c in d['cells'].items() if 'dff' in c['type'].lower() or c['type']=='$ff'];init={n:v['attributes']['init'] for n,v in d['netnames'].items() if 'init' in v.get('attributes',{})};assert not init
 text=(p/(top+'.cold.sv')).read_text();pairs=re.findall(r'\(n(\d+)_c0 == n\d+_c(\d+)\)',text);separate=[]
 for root,j in pairs:
  a=d['netnames']['u.n'+root+'_c0']['bits'];b=d['netnames']['u.n'+root+'_c'+j]['bits'];assert a!=b;separate.append(dict(root=root,copy=j,state_output_bits=[a,b]))
 allowed={'$scopeinfo','$_AND_','$_NOT_','$_OR_','$_DFF_P_','$_DFFSR_PNN_','$_ANDNOT_','$eq','$and'};assert not set(types)-allowed,set(types)-allowed
 r=dict(sequential_instances=len(seq),state_init_attributes=init,no_opt_merge=True,no_unknown_cells_allowed=True,copy_equalities=len(pairs),all_copy_outputs_distinct=True,cell_type_inventory=dict(types),sequential_cell_names=seq,distinct_copy_outputs=separate)
 (p/(top+'.checked_inventory.json')).write_text(json.dumps(r,indent=1)+'\n');print(top,len(seq),len(pairs),'no init attrs, distinct copy bits, no unknown cells')
