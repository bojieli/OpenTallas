import json
from pathlib import Path
from core_infra_search import Model,add_entry_chain
p=Path('.');data=json.loads((p/'input.json').read_text());base=json.loads((p/'out/w4_c1.3_s78_slice.json').read_text());best=None;trials=[]
for n in range(7):
 for cell in data['libraries']['TT']:
  if n==0 and cell!=next(iter(data['libraries']['TT'])):continue
  s=add_entry_chain(base,n,cell);m=Model(s,data['libraries'],data['points'],data['caps'],data['wire_r_kohm_um']/4,data['wire_c_ff_um']*1.3);r=m.evaluate([q['master'] for q in s['core_tree']['nodes']]);pen=0
  for c,v in r.items():
   lo,hi={'TT':(230,270),'FF':(182.5,222.5)}[c];pen+=max(0,lo-v['leaf_min'])+max(0,v['leaf_max']-hi)+max(0,v['leaf_window']-20)+max(0,v['slew_max']-80)
  t=dict(count=n,cell=cell,result=r,violation_ps=pen);trials.append(t);key=(pen,n,max(q['leaf_window'] for q in r.values()),cell)
  if best is None or key<best[0]:best=(key,s,t)
_,s,t=best;(p/'chosen_slice.json').write_text(json.dumps(s,indent=1));(p/'entry_result.json').write_text(json.dumps(dict(chosen=t,trials=trials),indent=1));print(json.dumps(t),flush=True)
