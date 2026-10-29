import json,hashlib,subprocess
from pathlib import Path
import lec as E
w=Path('.')
r=json.loads((w/'rebuild.json').read_text())
assert r['equal'] and (w/'rebuilt.aig').read_bytes()==(w/'miter.aig').read_bytes(), 'unmatched frozen miter'
n=json.loads((w/'names.json').read_text());old=json.loads((w/'lec.json').read_text())
points=[x['point'] for x in old['failing']]
point=next(x for x in points if x.endswith('.abc[0]'))
idx=n['onames'].index(point)
script=f'&r {w / "miter.aig"}; &cone -a -O {idx}; &w {w / "coupon.aig"}; &put; sat -C 100000; write_cex -c {w / "coupon.cex"}'
p=subprocess.run([E.abc_bin(),'-c',script],text=True,capture_output=True)
(w/'coupon.abc.log').write_text(p.stdout+p.stderr)
print(p.stdout+p.stderr,flush=True)
a=E.read_aig(w/'coupon.aig');m=E.read_aig(w/'miter.aig')
assert a['I']==m['I']==len(n['inames'])
s=(w/'coupon.cex').read_text();bits=''.join(s.split())
assert len(bits)==m['I'] and set(bits)<={'0','1'},repr(s[:100])
values=[0]+list(map(int,bits))
for a,b in zip(m['ands'][::2],m['ands'][1::2]):
 values.append((values[a>>1]^(a&1)) & (values[b>>1]^(b&1)))
lit=m['outputs'][idx]
assert values[lit>>1]^(lit&1)==1,'CEX does not activate original named output'
# Identify the exact original structural support, without truncating it.
support=set();pending=[lit>>1];first=m['I']+1
while pending:
 v=pending.pop()
 if not v or v in support:continue
 support.add(v)
 if v>=first:
  off=2*(v-first);pending.extend([m['ands'][off]>>1,m['ands'][off+1]>>1])
inputs=sorted(v for v in support if v<=m['I'])
report={'point':point,'output_index':idx,'miter_sha256':hashlib.sha256((w/'miter.aig').read_bytes()).hexdigest(),'original_output_replay':1,'support_count':len(inputs),'support':[{ 'index':v-1,'name':n['inames'][v-1],'value':values[v]} for v in inputs]}
(w/'coupon.json').write_text(json.dumps(report,indent=2)+'\n')
print('EXACT_FROZEN_COUPON',point,idx,len(inputs),flush=True)
