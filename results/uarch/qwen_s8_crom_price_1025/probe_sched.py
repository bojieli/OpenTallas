import json,os,sys
from pathlib import Path
R=Path(__file__).resolve().parent
os.environ['DV2_S8DIE']='1'
sys.path.insert(0,str(R/'tree/tools/qwen_layerbench'))
import dv_lower_vec as V
A=json.loads((R/'vec_ages.json').read_text())
orig=V.Sched.keys
records={}
for mode in ('resid','silu'):
 for hop in (2,4):
  def keys(self,s,entry,kind,offs):
   if kind=='x':return [(('x',m,entry+self.arr[s]+o+hop*abs(m-s)),j) for j,o in enumerate(offs) for m in range(V.N)]
   return orig(self,s,entry,kind,offs)
  V.Sched.keys=keys
  lw=V.lower_vec(mode,ages=A,ar_order='row')
  records[f'{mode}_occupancy{hop}']={'stream_commands':[{k:c[k] for k in ('edge','label')} for c in lw['commands'] if c['label'].startswith(('XS ','SILU '))], 'last_x_e5':max(x['edge_e5'] for x in lw['expected']['x']), 'collisions':lw['collisions']}
V.Sched.keys=orig
(R/'occupancy_schedules.json').write_text(json.dumps(records,indent=1))
print(json.dumps(records))
