#!/usr/bin/env python3
"""Verify every compressed binding against Yosys JSON; a strap-bit mutant must fail."""
import copy,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]; out=root/'results/arch/hbm_native_1013/sm'
m=json.load(open(out/'component.json')); d=json.load(open(out/'elaborated.json'))['modules'][m['logical_module']]
def verify(manifest):
 expected={}; got={}
 for name,c in d['cells'].items():
  for p,bits in c['connections'].items():
   for i,b in enumerate(bits): expected[(name,p,i)]=b
 for p,c in d['ports'].items():
  for i,b in enumerate(c['bits']): expected[('$boundary',p,i)]=b
 for n in manifest['connections']:
  for e in n['endpoints']:
   assert e['width']==len(n['elaboration_bits'])
   for k,b in enumerate(n['elaboration_bits']):
    key=(e['instance'],e['port'],e['lsb']+k); assert key not in got,key; got[key]=b
 for e in manifest['constant_binding']:
  for k in range(e['width']):
   key=(e['instance'],e['port'],e['lsb']+k); assert key not in got,key; got[key]=e['value']
 assert expected==got,{'missing':len(expected.keys()-got.keys()),'extra':len(got.keys()-expected.keys()),'unequal':sum(expected[k]!=got[k] for k in expected.keys()&got.keys())}
 return len(expected)
count=verify(m); mutant=copy.deepcopy(m); row=next(c for c in mutant['constant_binding'] if c['port']=='xs_a1'); original=row.copy(); row['width']=1; row['value']='1' if row['value']=='0' else '0'
if original['width']>1: original['lsb']+=1; original['width']-=1; mutant['constant_binding'].append(original)
try: verify(mutant)
except AssertionError as err: killed=True; failure=str(err)
else: killed=False; failure='mutant survived'
assert killed
report={'all_endpoint_bits_exact':True,'verified_endpoint_bits':count,'mutant':'flip exactly one constant xs_a1 bit','mutant_rejected':killed,'mutation_failure':failure,'scope':'Connectivity and constant-strap binding exactness only; hard-block arithmetic, seams, timing and throughput remain unqualified.'}
(out/'binding_verification.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report))
