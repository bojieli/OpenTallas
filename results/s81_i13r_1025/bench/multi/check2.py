import json,re,sys
from pathlib import Path
r=Path(__file__).parent;cases=json.loads((r/'cases.json').read_text());out={};bad=[]
for c,e in cases.items():
 s=(r/(c+'.log')).read_text();a=[int(m[1],16) for m in re.findall(r'^LO (\d+) ([0-9a-f]+)',s,re.M)];b=[int(x,16) for x in e['expected_beats']]
 mism=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b));st=int(re.search(r'I13_RESULT.*st=([0-9a-f]+)',s)[1],16)
 acc=[int(x) for x in re.findall(r'^JOB_ACCEPT (\d+)',s,re.M)];dn=[int(x) for x in re.findall(r'^JOB_DONE (\d+)',s,re.M)]
 out[c]=dict(beats=len(a),expected=len(b),mismatches=mism,status=f'{st:04x}',fault=bool(st&1),accepts=acc,dones=dn)
 if e['expected_fault']:
  if not st&1: bad.append(c+':negative escaped')
 elif mism or st&1 or len(dn)<2: bad.append(c+':positive failed')
res=dict(cases=out,bad=bad,verdict='PASS' if not bad else 'FAIL');print(json.dumps(res,indent=1));(r/'summary.json').write_text(json.dumps(res,indent=1)+'\n');sys.exit(bool(bad))
