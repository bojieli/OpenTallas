"""Assign equal-master legal FF sites from source-net harmonic targets; no CAD."""
from pathlib import Path
O=Path(__file__).resolve().parent
src=(O/'model_channels.py').read_text().split('for it in range(')[0];exec(compile(src,str(O/'model_channels.py'),'exec'))
from scipy.spatial import cKDTree
internal=set(json.load(open(O/'internal_names.json')));groups=collections.defaultdict(list)
for p in poses:
 if p['name'] in internal:groups[p['master']].append(p)
mov0=move.copy();move=np.array(list(mov)+[ids[n] for n in internal]);initial=xy.copy()
for it in range(160):
 for dim in range(2):
  s=np.bincount(a,weights=w*xy[b,dim],minlength=len(xy))+np.bincount(b,weights=w*xy[a,dim],minlength=len(xy));target=(s[move]+.012*initial[move,dim])/(den[move]+.012);xy[move,dim]=.7*target+.3*xy[move,dim]
 project()
for group in groups.values():
 sites=np.array([[(p['ll_dbu'][0]+p['size_dbu'][0]/2)/1000,(p['ll_dbu'][1]+p['size_dbu'][1]/2)/1000] for p in group]);tree=cKDTree(sites);targets=np.array([xy[ids[p['name']]] for p in group]);dist,nearest=tree.query(targets,k=min(32,len(group)));available=set(range(len(group)));mapping={}
 if len(group)==1:dist=np.array([[dist[0]]]);nearest=np.array([[nearest[0]]])
 # Recursive balanced spatial transport preserves cone neighborhood while using every exact site.
 def partition(ns,ss):
  if len(ns)==1:mapping[int(ns[0])]=int(ss[0]);return
  axis=int(np.argmax(np.ptp(sites[ss],axis=0)));ns=ns[np.argsort(targets[ns,axis],kind='stable')];ss=ss[np.argsort(sites[ss,axis],kind='stable')];mid=len(ns)//2;partition(ns[:mid],ss[:mid]);partition(ns[mid:],ss[mid:])
 partition(np.arange(len(group)),np.arange(len(group)))
 saved=[(p['ll_dbu'][:],p['orient']) for p in group]
 for ni,p in enumerate(group):p['ll_dbu'],p['orient']=saved[mapping[ni]]
(O/'FF_sites.json.gz').write_bytes(gzip.compress(json.dumps(poses,separators=(',',':')).encode(),mtime=0));print('CONE_ASSIGNED',len(internal))
