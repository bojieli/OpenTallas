# Reproduce from repo root: python3 tools/qwen_kv_die/evidence/lane_reservation_search_fa7fe4ff9.py /home/ubuntu/scratch/kv-lanemirror
from pathlib import Path
exec(Path(__file__).with_name('lane_incident_vehicle_fa7fe4ff9.py').read_text())
import numpy as np, math
# Reserve one complete clock/epoch/data station per failing instance pair.
pairrows=collections.defaultdict(list)
for r in rows:
 if r['transport']:pairrows[r['src'][0],r['dst'][0]].append(r)
bad={k:v for k,v in pairrows.items() if any(r['after']>r['reach'] for r in v)}
step=100000; bins=collections.defaultdict(list)
def putbox(box):
 x,y,w,h,name=box
 for a in range(int(x//step),int((x+w)//step)+1):
  for b in range(int(y//step),int((y+h)//step)+1):bins[a,b].append(box)
def collides(x,y,w,h):
 seen=set()
 for a in range(int(x//step),int((x+w)//step)+1):
  for b in range(int(y//step),int((y+h)//step)+1):
   for ox,oy,ow,oh,name in bins[a,b]:
    if name in seen:continue
    seen.add(name)
    if x<ox+ow and ox<x+w and y<oy+oh and oy<y+h:return True
 return False
for n,(x,y,o) in placements[1].items():
 m=macros.get(insts.get(n,('',{}))[0])
 if m:putbox((x,y,m['W'],m['H'],n))
results=[]
for (src,dst),rr in sorted(bad.items()):
 widths=[int(insts[e][0].rsplit('_',1)[1]) for e in (src,dst) if insts[e][0].startswith(('qkd_rlysh','qkd_landsh'))];S=max(widths);master=f'qkd_rlysh_{S}';m=macros[master];W,H=m['W'],m['H'];rel=L.origin_rules(m,'R0');widthreach=min(r['reach'] for r in rr);routes=[]
 for r in rr:
  if r['src'][1]=='ck_o' and r['dst'][1]=='ckf':ip,op='ckf','ck_o'
  elif r['src'][1]=='eb' and r['dst'][1]=='ea':ip,op='ea','eb'
  else:
   bit=r['dst'][2] if r['dst'][1]=='a' else r['src'][2];ip,op=f'a[{bit}]',f'b[{bit}]'
  def loc(pin):
   q=m['pd'].get(pin)
   if q is None:return None
   x1,y1,x2,y2=q['rects'][0][1];return ((x1+x2)/2,(y1+y2)/2)
  aa,bb=loc(ip),loc(op)
  if aa is None or bb is None:continue
  routes.append((points(r['src'],1)[0],aa,bb,points(r['dst'],1)[0]))
 arr=np.array(routes);base=(arr[:,0,:].mean(axis=0)+arr[:,3,:].mean(axis=0))/2-np.array([W,H])/2
 def snap(v,axis):
  rule=rel[axis];P=rule['joint_period_nm'];return min((r+round((v-r)/P)*P for r in rule['legal_origins_mod_joint_nm']),key=lambda x:abs(x-v))
 found=None
 offsets=sorted(((dx,dy) for dx in range(-108000,108001,5400) for dy in range(-108000,108001,5400)),key=lambda z:z[0]*z[0]+z[1]*z[1])
 for dx,dy in offsets:
  x,y=snap(base[0]+dx,'x'),snap(base[1]+dy,'y')
  if min(x,y)<0 or x+W>13260672 or y+H>28475280 or collides(x,y,W,H):continue
  xy=np.array([x,y]);left=np.abs(arr[:,0,:]-(arr[:,1,:]+xy)).sum(axis=1).max()/1000;right=np.abs(arr[:,3,:]-(arr[:,2,:]+xy)).sum(axis=1).max()/1000
  if max(left,right)<=widthreach:
   found=dict(x_um=x/1000,y_um=y/1000,w_um=W/1000,h_um=H/1000,orient='R0',left_max_um=float(left),right_max_um=float(right));putbox((x,y,W,H,f'reserve_{src}_{dst}'));break
 results.append(dict(src=src,dst=dst,master=master,reach_um=widthreach,reserved=found,status='CANDIDATE_SLOT' if found else 'NO_LOCAL_SLOT'))
print('reserved',sum(bool(r['reserved']) for r in results),'of',len(results));(p/'reservation_candidates.json').write_text(json.dumps(dict(note='Proposed station reservations only; no netlist, schedule or landing E/K changes applied. Pin-centre spans and nonoverlap checked against failed source/adapted placements and earlier proposed slots. Full route/clock/STA still owed.',rows=results),indent=1)+'\n')
