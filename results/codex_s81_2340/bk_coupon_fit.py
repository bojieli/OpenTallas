"""Fit actual frozen physical legs; retains unconstrained residuals and stage data."""
import collections,json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
b=Path(sys.argv[1]);t=json.load(open(b/'clock/tree_frozen.json'));nodes={int(k):v for k,v in t['nodes'].items()};nb={int(k):v for k,v in t['node_buf'].items()};sites=t['sites'];tapcount=collections.Counter(x['node'] for x in t['taps']);out={'routing':'M8/M9 actual 2W2S .08/.08; frozen body homes; real PG obstructions','fit':{}}
for corner in ('TT','FF'):
 arr={}
 for l in (b/f'out_{corner}'/f'arr_{corner}.txt').read_text().splitlines():
  a=l.split()
  if a and a[0]=='N':arr[a[1]]=list(map(float,a[2:4]))
 rows=[]
 for i,n in nodes.items():
  p=n.get('parent')
  if p is None:continue
  chain=n['physical_leg']['chain'];lengths=[abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(chain,chain[1:])]
  # Use actual endpoint cells, not obsolete pre-body topology coordinates.
  v=nb[i];parent=nb[p];segs=[];seen=set()
  while v!=parent:
   if v in seen:raise ValueError('cycle')
   seen.add(v);q=t['parent_of'][v];a,z=sites[v],sites[q];segs.append(abs(a[0]-z[0])+abs(a[1]-z[1]));v=q
  if len(segs)!=len(lengths):raise ValueError('chain stage mismatch')
  fo=len(n.get('kids',[]))+tapcount.get(i,0)
  rows.append({'node':i,'features':[len(segs),sum(segs),sum(x*x for x in segs),fo-1],'early_ps':arr[nb[i]][1]-arr[nb[p]][1],'late_ps':arr[nb[i]][0]-arr[nb[p]][0]})
 X=np.array([r['features'] for r in rows]);o={'rows':rows}
 for edge in ('early','late'):
  y=np.array([r[edge+'_ps'] for r in rows]);coef=np.linalg.lstsq(X,y,rcond=None)[0];nc=nnls(X,y)[0]
  def stats(c):
   r=y-X@c;return {'coef':list(c),'rms_ps':float(np.sqrt(np.mean(r*r))),'max_abs_ps':float(max(abs(r))),'p90_abs_ps':float(np.percentile(abs(r),90))}
  o[edge]={'least_squares':stats(coef),'nonnegative':stats(nc)}
 out['fit'][corner]=o
 print(corner,json.dumps({k:v for k,v in o.items() if k!='rows'}))
Path(sys.argv[2]).write_text(json.dumps(out,indent=2)+'\n')
