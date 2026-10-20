"""Read-only census of exact gate mapped netlists; clocks/constants excluded only."""
import sys,json,hashlib,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
import textbook_lint as T
for d in sorted(Path(__file__).parent.iterdir()):
 if not d.is_dir() or not ((d/'mapped.v').exists() or (d/'mapped.v.gz').exists()):continue
 p=d/'mapped.v';data=p.read_bytes() if p.exists() else gzip.decompress((d/'mapped.v.gz').read_bytes());g,top=T.flatten(T.parse_verilog(data.decode()),None);a=T.build(g,None);clk,_=T.clock_nets(g,a)
 rows=[]
 for x,(ci,pin) in a['driver'].items():
  if x in clk or x<=3 or (ci>=0 and a['kind'][ci] in ('buf','tie')):continue
  n,ff,ex=T.bufinv_fanout(g,a,x,clk)
  if n>32:rows.append({'driver':T.net_label(g,a,x),'loads':n,'flop_loads':ff,'flop_driver':ci>=0 and a['kind'][ci]=='ff'})
 rows.sort(key=lambda x:x['loads'],reverse=True)
 out={'top':top,'mapped_sha256':hashlib.sha256(data).hexdigest(),'all_nonclock_drivers_over32':len(rows),'flop_drivers_over32':sum(x['flop_driver'] for x in rows),'max_loads':rows[0]['loads'] if rows else 0,'violations':rows,'verdict':'FAIL' if rows else 'PASS'}
 (d/'census.json').write_text(json.dumps(out,indent=2)+'\n');print(d.name,{k:v for k,v in out.items() if k!='violations'})
 with gzip.open(d/'mapped.v.gz','wb') as f:f.write(data)
 if p.exists():p.unlink()
