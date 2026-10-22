import re,json
from pathlib import Path
rows=[]
for f in Path('out').glob('*.log'):
 s=f.read_text();m=re.search('OT_LAND (.*)',s);assert m,s
 d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',m[1])}
 if f.name.startswith('p_'):assert d['mism']==0 and d['fault']==0 and d['meas']==18,d
 else:assert d['mism']>0,d
 if f.name=='invalid_k.log':assert d['fault']==1,d
 rows.append(dict(file=f.name,result=d))
Path('out/receipt.json').write_text(json.dumps(dict(verdict='PASS',source_reset4=True,cases=rows),indent=1)+'\n');print('SOURCE4_PASS',len(rows))
