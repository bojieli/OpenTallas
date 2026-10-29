import json,pickle,hashlib
from pathlib import Path
w=Path('.')
with (w/'state_candidate.pkl').open('rb') as f:L=pickle.load(f)
m,kind=L.build();m.write(w/'diagnose.aig');assert (w/'diagnose.aig').read_bytes()==(w/'miter.aig').read_bytes()
bits=''.join((w/'coupon.cex').read_text().split());values=[0]+list(map(int,bits))
for a,b in zip(m.ands[::2],m.ands[1::2]):values.append((values[a>>1]^(a&1))&(values[b>>1]^(b&1)))
v=lambda l:values[l>>1]^(l&1)
point=json.loads((w/'coupon.json').read_text())['point'];prefix=point.rsplit('.',1)[0]+'.'
inputs=dict(zip(m.inames,map(int,bits)))
def state(sd,k,seen=()):
 if (sd,k) in seen:return 'cycle'
 h=L.hyp.get(('both',k),L.hyp.get((sd,k)))
 if h:
  if h[0]=='const':return h[1]
  if h[0]=='eq':
   a=state(h[1],h[2],seen+((sd,k),));return a^h[3] if isinstance(a,int) else a
 for key in [k,sd+':'+k]:
  if key in inputs:return inputs[key]
 return 'absent'
words={}
for stem,width in [('cws_c',24),('s1_c',24),('cmd_ws',6),('s1',6),('written',64)]:
 words[stem]={sd:[state(sd,prefix+stem+f'[{i}]') for i in range(width)] for sd in ['gold','gate']}
r={'point':point,'gold_D':v(L.dlit[('gold',point)]),'gate_D':v(L.dlit[('gate',point)]),'words_lsb_first':words}
(w/'diagnosis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
