import json,sys
from pathlib import Path
rows=json.loads(Path(sys.argv[1]).read_text());out=[]
for row in rows:
 m=row['meta'];d=Path(m['remote']);cell=row['cell'];r={'cell':cell,'remote':str(d),'files':{}}
 for suffix in ['.netlist.v','.ys','.files.json','.stat']:
  p=d/(cell+suffix);r['files'][suffix]={'exists':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None}
 r['native_candidates']=[str(p) for p in d.glob('*native*.json')]
 r['etm_tt_exists']=(d/'etm_tt.tcl').is_file();out.append(r)
print(json.dumps(out,indent=2))
