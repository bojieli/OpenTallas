import json,hashlib
from pathlib import Path
Q=Path('/srv/opentallas-scratch2/claude');R=Q/'codex-qc-import-0824';out=R/'reachfix';out.mkdir(exist_ok=True)
p=json.load(open(Q/'codex-provider-import-1029/proposal_qc_wave2_compact/placements.json'));moved=[]
for q in p['cells']:
 if any(('u_rst_'+s+'.') in q['inst'] for s in ['r1_1','r3_1']) and q['inst'].endswith('slice$491'):
  old=q['bbox_dbu'][:];q['xy_dbu'][1]-=79920;q['bbox_dbu'][1]-=79920;q['bbox_dbu'][3]-=79920;moved.append(dict(inst=q['inst'],old=old,new=q['bbox_dbu'],delta_dbu=[0,-79920]))
assert len(moved)==2
p['physical_fix']=dict(cause='actual native reset driver-to-first receive FF reach 483.618/469.233um',moved=moved,added_cells=0,added_cycles=0)
json.dump(p,open(out/'placements.json','w'),separators=(',',':'));json.dump(p['physical_fix'],open(out/'fix.json','w'),indent=2);print(json.dumps(p['physical_fix'],indent=2))
