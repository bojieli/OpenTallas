import sys,inspect,json
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import geom_rules as G
s=inspect.getsource(G.r2r_metrics).replace('def r2r_metrics(D):','def r2r_all(D):').replace('best, arg, n_gt = 0.0, None, 0','best, arg, n_gt = 0.0, None, 0\n    rows=[]').replace('n_gt += 1','n_gt += 1\n            rows.append(dict(um=round(mx,3),launch=D.cells[src][6],capture=D.cells[cap][6],launch_xy=G.ctr(D.cells[src]),capture_xy=G.ctr(D.cells[cap])))').replace('return dict(r2r_memory_instances=', 'return dict(rows=sorted(rows,key=lambda r:-r["um"]),r2r_memory_instances=')
ns=G.__dict__.copy();ns['G']=G;exec(s,ns);r=ns['r2r_all'](G.Design(sys.argv[2]));Path(sys.argv[3]).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r)[:8000])
