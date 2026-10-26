"""Same-outline SU10 placement, weighted by actual non-clock port-bit traffic."""
import argparse,json,re,itertools,sys,hashlib
from pathlib import Path
import numpy as np
W=Path(__file__).resolve().parents[3];sys.path[:0]=[str(W),str(W/'tools/die_plan')]
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);args=ap.parse_args()
import schema as S
from gen_phys import type_pins
base=args.plan.parent;raw=json.load(open(args.plan));t=raw['partition_types']['q_su10'];cores=t['hard_cores'];names=[c['inst'] for c in cores];idx={s:i for i,s in enumerate(names)};P=S.Plan(raw)
pins={};bus={}
for b,i,_,x,y,_ in type_pins(P,'q_su10'):bus.setdefault(b,[]).append((x,y))
bus={b:np.mean(v,axis=0) for b,v in bus.items()}
conns=json.load(open(base/'core_conns.json'))['q_su10'];weights=np.zeros((len(cores),len(cores)));terms=[]
for i,c in enumerate(cores):
 groups={}
 for p in json.load(open(base/c['pins_file'])):
  name=re.sub(r'\[\d+\]$','',p['name']);groups.setdefault(name,[]).append((p['x'],p['y']))
 for port,targets in conns.get(c['inst'],{}).items():
  if re.search(r'clk|clock|^ck|rst|reset|strap_',port):continue
  pts=groups.get(port)
  if not pts:continue
  pt=np.mean(pts,axis=0);cw,ch=c['outline_um'];o=c.get('orient','R0')
  if o in('MY','R180'):pt[0]=cw-pt[0]
  if o in('MX','R180'):pt[1]=ch-pt[1]
  for target in targets:
   kind,_,partner=target.partition(':')
   if kind=='core' and partner in idx:weights[i,idx[partner]]+=len(pts)
   if kind=='bus' and partner in bus:terms.append((i,pt,bus[partner],len(pts)))
size=np.array([c['outline_um'] for c in cores]);old=np.array([c['origin_um'] for c in cores]);tall=np.array([i for i,c in enumerate(cores) if c['outline_um'][1]>300]);short=np.array([i for i,c in enumerate(cores) if c['outline_um'][1]<300]);assert len(tall)==4 and len(short)==8
perms=np.array(list(itertools.permutations(range(8))),dtype=np.int16);xs=[34.56,518.4,1002.24,1486.08];tall_slots=np.array([(x,34.56) for x in xs]);best=None

def cost(origins):
 centres=origins+size/2;out=float((weights*np.abs(centres[:,None]-centres[None,:]).sum(axis=2)).sum())
 for i,p,b,w in terms:out+=w*float(np.abs(origins[i]+p-b).sum())
 return out

for y0,y1 in ((527.04,777.6),(527.04,1036.8),(673.92,924.48),(673.92,1175.04)):
 slots=np.array([(x,y) for y in(y0,y1) for x in xs]);origins=slots[perms];centres=origins+size[short][None,:,:]/2
 fixed=np.zeros(len(perms))
 for i,ci in enumerate(short):
  for j,cj in enumerate(short):
   if weights[ci,cj]:fixed+=weights[ci,cj]*np.abs(centres[:,i]-centres[:,j]).sum(axis=1)
  for k,p,b,w in terms:
   if k==ci:fixed+=w*np.abs(origins[:,i]+p-b).sum(axis=1)
 for tp in itertools.permutations(range(4)):
  pos=old.copy();pos[tall]=tall_slots[list(tp)];tc=pos[tall]+size[tall]/2;score=fixed.copy()
  for i,ci in enumerate(short):
   for j,cj in enumerate(tall):
    score+=(weights[ci,cj]+weights[cj,ci])*np.abs(centres[:,i]-tc[j]).sum(axis=1)
  constant=0.
  for i,ci in enumerate(tall):
   for j,cj in enumerate(tall):constant+=weights[ci,cj]*np.abs(tc[i]-tc[j]).sum()
   for k,p,b,w in terms:
    if k==ci:constant+=w*np.abs(pos[ci]+p-b).sum()
  pick=int(np.argmin(score));value=float(score[pick]+constant)
  if best is None or value<best[0]:pos[short]=origins[pick];best=value,pos.copy(),(y0,y1)
value,pos,ys=best
assert abs(value-cost(pos))<max(1e-3,abs(value)*1e-9)
report=dict(type='q_su10',scope='same-outline cell-corridor placement proposal, no route receipt',outline_um=t['outline_um'],source='plan_r2/core_conns + actual M5 pin bit counts',clock_reset_excluded=True,weighted_bit_um_before=cost(old),weighted_bit_um_after=value,ratio=value/cost(old),short_rows_um=ys,placements={c['inst']:pos[i].tolist() for i,c in enumerate(cores)})
report['plan_sha256']=hashlib.sha256(args.plan.read_bytes()).hexdigest()
out=args.out
if out.exists():raise FileExistsError(out)
out.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
