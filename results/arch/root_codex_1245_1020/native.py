import pathlib,sys,json
root=pathlib.Path('cand');sys.path.insert(0,str(root/'tools/s81_dv'))
from forward_clock_guard import validate_native_forwarding
rows=[]
for p in root.glob('physical/ref_tile/*/views/*/forwarded_clock.json'):
 m=p.parent.name
 for c in ('tt','ff','ss'):
  lib=(p.parent/f'{m}_{c}.lib').read_text()
  rows.append(validate_native_forwarding(m,c,lib,lambda name: (p.parent/name).read_text() if (p.parent/name).exists() else None))
assert len(rows)==45,len(rows)
pathlib.Path('native45.json').write_text(json.dumps(rows,indent=2));print('NATIVE45 PASS')

import copy
p=next(root.glob('physical/ref_tile/s81dv_rlyh_*/views/*/forwarded_clock.json')).parent
m=p.name;lib=(p/f'{m}_tt.lib').read_text();files={x.name:x.read_text() for x in p.iterdir() if x.is_file() and x.suffix not in ('.png',)}
def reject(label,mutate):
 f=copy.deepcopy(files);l=mutate(f,lib)
 try: validate_native_forwarding(m,'tt',l,f.get)
 except (ValueError,KeyError,TypeError): print('EXPECTED_REJECT',label);return
 raise AssertionError(label)
reject('missing receipt',lambda f,l:(f.pop('forwarded_clock.json'),l)[1])
reject('changed raw',lambda f,l:(f.__setitem__('forwarded_tt.lib.raw',f['forwarded_tt.lib.raw']+' '),l)[1])
reject('master identity',lambda f,l:l.replace('cell ("'+m+'")','cell ("wrong")').replace('cell("'+m+'")','cell("wrong")'))
reject('phase relabel',lambda f,l:l.replace('negative_unate','positive_unate'))
def nan(f,l):
 r=json.loads(f['forwarded_clock.json']);r['corners']['tt']['output_absolute_ps']['arrival_max_rise']=float('nan');f['forwarded_clock.json']=json.dumps(r)
 a=json.loads(f['abstract.json']);a['forwarded_clock']=r['corners'];f['abstract.json']=json.dumps(a);return l
reject('nonfinite mirrored receipts',nan)
