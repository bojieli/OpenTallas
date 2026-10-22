import json,sys
from pathlib import Path
sys.path.insert(0,'src/tools/s81_dv/layer_prog')
import lower_bk as B
class Die:
 links={}
 def strap(self, inst, field):return {'uid':0x5b,'ik':4,'ek':5}[field]
op={'op':'attn.idx.topk_final','start':100,'end':278}
res={}
for on in (False,True):
 r=B.lower(Die(),op,dict(fixtures=Path('fx'),layer='L20',sched={'ops':[op]},bk_indexed13=on))
 p=json.loads(r['files']['prog/bk/attn.idx.topk_final.plan.json'])
 assert p['golden_ok'] and p['indexed13']==on
 assert p['ingress_beats']==(324 if on else 5983)
 assert p['span_edges']==(1033 if on else 6692)
 assert r['status']=='PARTIAL' and r['gap'], 'do not claim missing producer LOWERED'
 res[str(on)]=p
Path('compiler_check.json').write_text(json.dumps(res,indent=1)+'\n')
print('INDEXED13_COMPILER_FLAG PASS')
