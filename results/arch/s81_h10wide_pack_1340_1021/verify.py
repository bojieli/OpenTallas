"""Independent exact body/capacity/reticle/corridor certificate, no route claim."""
import json,hashlib,argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('baseline');ap.add_argument('candidate');ap.add_argument('--out',required=True);a=ap.parse_args()
p=json.load(open(a.baseline));q=json.load(open(a.candidate));bs=p['blocks']+p.get('blockages',[]);cs=q['blocks']+q.get('blockages',[])
assert len(bs)==len(cs)==163
assert len({b['name']for b in cs})==163
orig={b['name']:b for b in bs};errors=[]
for c in cs:
 b=orig[c['name']];assert c['master']==b['master']if'master'in b else c.get('master')is None
 assert c['kind']==b['kind'];assert abs(c['h']-b['h'])<.0001
 assert abs(c['w']-(1782.432 if b.get('master')=='col_h10'else b['w']))<.0001
 if b['kind']in('phy','ctrl'):assert c['x']==b['x']and c['y']==b['y']
 if c['x']<100 or c['y']<100 or c['x']+c['w']>32900.0001 or c['y']+c['h']>25900.0001:errors.append({'type':'outside','instance':c['name']})
minimum=float('inf')
for i,b in enumerate(cs):
 for c in cs[:i]:
  dx=max(c['x']-b['x']-b['w'],b['x']-c['x']-c['w']);dy=max(c['y']-b['y']-b['h'],b['y']-c['y']-c['h']);gap=max(dx,dy);minimum=min(minimum,gap)
  if gap<86.1499:errors.append({'type':'corridor_or_overlap','instances':[b['name'],c['name']],'gap_um':gap})
r={'status':'PASS'if not errors else'FAIL','errors':errors,'body_count':len(cs),'frame_count':sum(b['kind']=='frame'for b in cs),'h10_count':sum(b.get('master')=='col_h10'for b in cs),'serdes_count':sum(b['kind']=='link'for b in cs),'reserve_count':len(q.get('blockages',[])),'minimum_body_separation_um':minimum,'body_area_mm2':sum(b['w']*b['h']for b in cs)/1e6,'candidate_sha256':hashlib.sha256(Path(a.candidate).read_bytes()).hexdigest(),'scope':'GEOMETRY_MODEL_ONLY; no qualified source/view/route or timing claim'}
Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='errors'}));assert not errors
