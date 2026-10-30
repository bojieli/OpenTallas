import sys,json
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
p=Path('/tmp/head_collect_review');D=G.Design(p/'hb4.tsv');land=G.land_ring_captures(D,json.load((p/'land_slots.json').open()),json.load((p/'face_guard.json').open()));moves={}
for pn,ids in land['caps'].items():
 pin=next(q for q in D.pins if q['name']==pn)
 if max(abs(G.ctr(D.cells[i])[0]-pin['x'])+abs(G.ctr(D.cells[i])[1]-pin['y']) for i in ids)<=150:continue
 for k,i in enumerate(sorted(ids)):
  c=D.cells[i];w,h=c[4]-c[2],c[5]-c[3];x=max(8,pin['x'])+(k%2)*1.2;y=14+(k//2)*1.2
  moves[c[6]]=[x,y]
  D.cells[i]=(c[0],c[1],x,y,x+w,y+h,c[6])
out=p/'hb4_pinfix';out.mkdir(exist_ok=True);json.dump(moves,(out/'moves.json').open('w'),indent=1)
with (out/'geom.tsv').open('w') as f:
 for ln in (p/'hb4.tsv').read_text().splitlines():
  r=ln.split('\t')
  if r[0]=='C':r[4:8]=[str(v) for v in D.cells[int(r[1])][2:6]];ln='\t'.join(r)
  f.write(ln+'\n')
print('moves',len(moves));print(G.r2r_metrics(D))
