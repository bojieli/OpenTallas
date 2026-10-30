import argparse,hashlib,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--source',required=True);p.add_argument('--routed',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools)
import odb
from infra_replay import physical_snapshot

def digest(path):
 d=odb.dbDatabase.create();odb.read_db(d,path);b=d.getChip().getBlock();h=hashlib.sha256();count=0
 for n in sorted(b.getNets(),key=lambda v:v.getName()):
  if str(n.getSigType())!='CLOCK':continue
  count+=1;h.update(json.dumps([n.getName(),physical_snapshot(n)],sort_keys=True,separators=(',',':')).encode())
 return dict(clock_nets=count,sha256=h.hexdigest())
x=digest(a.source);y=digest(a.routed);ok=x==y;Path(a.out).write_text(json.dumps(dict(source=x,routed=y,verdict='CLOCK_ROUTES_UNCHANGED' if ok else 'FAIL_CLOCK_CHANGED',scope='Preservation only; PG IR and real-view die STA still required'),indent=2)+'\n');print(x,y,ok,flush=True)
if not ok:raise ValueError('GRT changed actual fixed clock')
