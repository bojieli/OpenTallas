# Derive a candidate homes file from a parent by whole-block translations (multiples of 8.64 um, orientation kept).
import json,sys,copy
sys.path.insert(0,'/home/ubuntu/artifacts/globalfp/qwen/recovery-1325/recovered-source');import gfp_candidates as G
parent,name=sys.argv[1],sys.argv[2];moves=[(a.split(':')[0],float(a.split(':')[1]),float(a.split(':')[2])) for a in sys.argv[3:]]
d=json.load(open(parent));d=copy.deepcopy(d);h=d['homes'];rec=[]
for n,dx,dy in moves:
 assert abs(dx/8.64-round(dx/8.64))<1e-6 and abs(dy/8.64-round(dy/8.64))<1e-6,(n,dx,dy)
 h[n]['x']=round(h[n]['x']+dx,3);h[n]['y']=round(h[n]['y']+dy,3);rec.append({'instance':n,'dx_um':dx,'dy_um':dy})
d['candidate']=name;d['parent']=d.get('candidate_parent',parent);d.setdefault('fpq_moves',[]).extend(rec)
ov=G.overlaps(h);hits=[]
for key,r in d.get('reserve',{}).items():
 for n,i in h.items():
  if min(i['x']+i['w'],r['x']+r['w'])>max(i['x'],r['x'])+.001 and min(i['y']+i['h'],r['y']+r['h'])>max(i['y'],r['y'])+.001:hits.append([key,n])
print(name,'overlaps',ov,'reserve hits',hits)
assert not ov and not hits
json.dump(d,open(name+'-homes.json','w'),indent=1)
