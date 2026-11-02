from pathlib import Path
from collections import defaultdict
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');old={i:g.ctr(c)for i,c in D.cells.items()};byname={c[6]:i for i,c in D.cells.items()};moved=set()
def move(i,x,y):
 c=list(D.cells[i]);a,b=g.ctr(c);dx,dy=x-a,y-b;c[2]+=dx;c[4]+=dx;c[3]+=dy;c[5]+=dy;D.cells[i]=tuple(c)
 if abs(dx)+abs(dy)>1e-6:moved.add(i)
for i,c in list(D.cells.items()):
 x,y=g.ctr(c)
 if 'u_cland_i_seq__g_fan_N__u_fan_kc/'in c[6]:move(i,x,y-146.88)
 elif 'u_cland_i_fch_pc_Q_N_q/'in c[6]or'u_cland_i_kvpc_Q_N_pc__fo/'in c[6]:move(i,x+172.8,y)
for z in json.load(open(P/'current_graph_lp_margin391.json'))[0]['targets']:move(byname[z['name']],*z['new'])
rows=[]
for p in D.pins:
 if p['sig']in['POWER','GROUND','CLOCK']or g.CLOCK_PIN_RE.search(p['name']):continue
 n=D.pin_net.get(p['k']);caps=[]
 if n is None:continue
 if p['io']=='OUTPUT':
  cur=n;seen=set()
  while cur not in seen:
   seen.add(cur);dr=D.nets[cur][1]
   if not dr or dr[0]!='i':break
   i=dr[1];k=D.kind(i)
   if k=='S':caps=[i];break
   ins=[nn for nn,ck in D.cell_in.get(i,[])if not ck]
   if k!='B'or len(ins)!=1:break
   cur=ins[0]
 else:
  front=[n];seen={n}
  while front and not caps:
   nf=[]
   for nn in front:
    for s in D.nets[nn][2]:
     if s[0]!='i'or s[2]:continue
     i=s[1];k=D.kind(i)
     if k=='S':caps.append(i)
     elif k=='B':
      for on in D.drives.get(i,[]):
       if on not in seen:seen.add(on);nf.append(on)
   front=nf
 if not caps or not any(i in moved for i in caps):continue
 a=min(abs(old[i][0]-p['x'])+abs(old[i][1]-p['y'])for i in caps);b=min(abs(g.ctr(D.cells[i])[0]-p['x'])+abs(g.ctr(D.cells[i])[1]-p['y'])for i in caps)
 rows.append(dict(pin=p['name'],direction=p['io'],xy=[p['x'],p['y']],old_nearest_um=a,new_nearest_um=b,first_regs=[D.cells[i][6]for i in caps],new_regs=[list(g.ctr(D.cells[i]))for i in caps]))
groups=defaultdict(list)
for r in rows:groups[r['pin'].split('[')[0]].append(r)
res=dict(scope='STATIC current391 witness against UNCHANGED publicpin coordinates; B/INV-only first-direction register census, no land-ring substitute or contract adoption',moved_actual_existing_bodies=len(moved),affected_public_pins=len(rows),affected_groups={k:dict(pins=len(a),old_max=max(z['old_nearest_um']for z in a),new_max=max(z['new_nearest_um']for z in a),new_over150=sum(z['new_nearest_um']>150for z in a))for k,a in groups.items()},rows=rows)
(P/'endpoint_pin_cost.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k!='rows'})
