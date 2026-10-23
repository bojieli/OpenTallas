#!/usr/bin/env python3
"""Replay physical reset placement from an immutable finalized real case."""
import argparse,collections,hashlib,importlib.util,json,re,sys,time
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('run');ap.add_argument('out');ap.add_argument('--bind-override');ap.add_argument('--inspect-only',action='store_true');a=ap.parse_args()
r=Path(a.run);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(r/'src/tools/s81_dv'));sys.path.insert(0,str(r/'src/tools'))
import dv_rvcase as D
from calendar_sites import reserve, frame_region_boxes, remove_rect
bind=Path(a.bind_override) if a.bind_override else r/'bind/bind'
hints=json.load(open(bind/'place_hints.json'));plan=json.load(open(r/'plan.json'));T=json.load(open(r/'table.json'));bc=json.load(open(bind/'bind_case.json'))
nets,tin,tout,insts=D.DPB.parse_die(bind/'die.v','dv_die');insts=[v for v in insts if v[0]!='__assign__']
ibits={};touch=collections.defaultdict(set)
for mst,nm,_,cm in insts:
 ibits[nm]={p:D.DPB.expr_bits(e,nets) for p,e in cm.items()}
 for bits in ibits[nm].values():
  for n,b in bits:
   if n not in ('CONST','Z','UNDECL'):touch[n].add(nm)
positions={m.group(1):(float(m.group(2)),float(m.group(3))) for m in re.finditer(r'place_inst -name (\S+) -location \{([\d.-]+) ([\d.-]+)\}',(r/'case/place.tcl').read_text())}
size={}
for p in (r/'case/views').glob('*.lef'):
 for line in open(p):
  m=re.match(r'\s*SIZE ([\d.]+) BY ([\d.]+)',line)
  if m:size[p.stem]=tuple(map(float,m.groups()));break
loc={}
for mst,nm,_,_ in insts:
 if nm not in positions:
  hp=next((p for p in hints['reset_place'] if p['inst']==nm),None)
  if hp:positions[nm]=(hp['xy'][0]-8.64,hp['xy'][1]-8.64)
  else:continue
 wh=size.get(mst) or size.get('rv_'+nm.removeprefix('u_')) or ((1.2,.6) if nm.startswith(('fwd_','rinv_')) else None)
 if nm.startswith('u_'):
  b=next(b for b in plan['blocks'] if b['name']==nm[2:]);wh=(b['w'],b['h'])
 if wh is None:raise RuntimeError((mst,nm))
 loc[nm]=(*positions[nm],*wh,'FIRM')
st={p['inst'] for p in hints['reset_place']}
connectivity_sha=hashlib.sha256(json.dumps(ibits,sort_keys=True).encode()).hexdigest()
clock_sha=hashlib.sha256(json.dumps({v:{p:b for p,b in ports.items() if p.lower() in ('ck','clk','ck_f','ck_o','clk_peer')} for v,ports in ibits.items()},sort_keys=True).encode()).hexdigest()
parent={};kids=collections.defaultdict(list);terms=collections.defaultdict(list)
skip=set();lanes=collections.defaultdict(dict)
for mst,nm,_,cm in insts:
 if mst.startswith('dsfd_dvrly') and 'ck' in cm:
  m=re.match(r'^n(\w+)_fck\[(\d+)\]$',cm['ck'])
  if m:lanes[m[1]][int(m[2])]=nm
for lane,ss in lanes.items():
 for k,nm in ss.items():
  if k>=2 and k-1 in ss:skip.add(nm)
blocks={b['name']:b for b in plan['blocks']}
planned={p['inst']:tuple(p['xy']) for p in hints['reset_place']}
cen=lambda v:(loc[v][0]+loc[v][2]/2,loc[v][1]+loc[v][3]/2)
for v in sorted(st):
 for net in {n for n,b in ibits[v].get('o',[])}:
  for u in sorted(touch[net]):
   if u==v:continue
   if u in st:
    if any(n==net for p in ('i','rs') for n,b in ibits[u].get(p,[])) and u not in parent:parent[u]=v;kids[v].append(u)
   elif u not in skip and u in loc:
    if u.startswith('u_') and u[2:] in hints.get('block_rst_pin',{}):terms[v].append(tuple(hints['block_rst_pin'][u[2:]]))
    elif u.startswith('u_') and u[2:] in blocks:
     b=blocks[u[2:]];x,y=planned[v];terms[v].append((min(max(x,b['x']),b['x']+b['w']),min(max(y,b['y']),b['y']+b['h'])))
    else:terms[v].append(cen(u))
hop=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
actual={v:cen(v) for v in st}
old=[('station',v,u,hop(actual[v],actual[u])) for v in sorted(st) for u in kids[v]]+ [('load',v,str(t),hop(actual[v],t)) for v in sorted(st) for t in terms[v]]
json.dump(old,open(out/'original_hops.json','w'))
print('ORIGINAL',len([x for x in old if x[3]>405.002]),max(x[3] for x in old),flush=True)
box={};cr=bc.get('clock_regions') or {}
if cr.get('mode')=='geometric':
 grid=D.GC.Grid.from_spec(cr['grid']);reg={b:('b_'+b if v['kind']=='own_root' else v['cell']) for b,v in cr['blocks'].items()};ext=D.GC.extents(grid,plan['blocks'],reg,[b for b,v in cr['blocks'].items() if v['kind']=='table_clock'])
 for v in st:
  ck=[n for n,b in ibits[v].get('ck',[]) if n in tin and n.startswith('ck_')]
  if ck and ck[0] not in T.get('clock_domains',{}) and ck[0][3:] in ext:
   e=ext[ck[0][3:]];box[v]=(e[0]-395,e[1]-395,e[2]+395,e[3]+395)
box=frame_region_boxes(st,ibits,blocks,405,box)
W,H=json.load(open(r/'case/case.json'))['die_um'];placer=D.Placer(W,H)
for v,l in loc.items():
 if v not in st:placer.add((l[0],l[1],l[0]+l[2],l[1]+l[3]))
for b in plan.get('blockages',[]):placer.add((b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
for v in st:
 x,y=planned[v];w,h=loc[v][2:4];loc[v]=(x-w/2,y-h/2,w,h,'FIRM')
if a.inspect_only:
 diag=[]
 for p in hints['reset_place']:
  if p.get('kind')!='frame_chain_reset_v2':continue
  v=p['inst'];c=planned[v];w,h=loc[v][2:4];rr=(c[0]-w/2,c[1]-h/2,c[0]+w/2,c[1]+h/2)
  coll=[(n,l) for n,l in loc.items() if n not in st and l[0]<rr[2]+.5 and rr[0]<l[0]+l[2]+.5 and l[1]<rr[3]+.5 and rr[1]<l[1]+l[3]+.5]
  diag.append(dict(inst=v,master=next(m for m,n,_,_ in insts if n==v),clock=ibits[v].get('ck'),xy=c,box=box.get(v),colliders=coll))
 json.dump(diag,open(out/'explicit_diagnostics.json','w'),indent=1)
 print(json.dumps(diag),flush=True);sys.exit()
import subprocess
patch_path=Path(__file__).with_name('calendar_sites_cap30.patch')
patched=out/'dv_rvcase_patched.py'
subprocess.run(['patch','--fuzz=0','-o',str(patched),str(Path(D.__file__)),str(patch_path)],check=True)
source=patched.read_text();lo=source.index('def _rs_repair(');hi=source.index('\ndef gen_safety_facts',lo)
exec(source[lo:hi],D.__dict__)
original_repair=D._rs_repair
def checkpoint_repair(*args,**kwargs):
 import pickle
 with open(out/'before_repair.pickle','wb') as f:pickle.dump((args,{k:v for k,v in kwargs.items() if k!='remove_rect'}),f)
 print('DP_COMPLETE_BEGIN_REPAIR',flush=True)
 return original_repair(*args,**kwargs)
D._rs_repair=checkpoint_repair
rep,over=D.rs_chain_place(sorted(st),insts,ibits,touch,loc,placer,hints,blocks,405,skip_loads=skip,box_of=box,repair=True,reserve_calendar=True,reserve_blockages=plan.get('blockages', []))
report=rep['calendar_reservation']
geometry=D.Placer(W,H)
for v,l in loc.items():
 if v not in st:geometry.add((l[0],l[1],l[0]+l[2],l[1]+l[3]))
for b in plan.get('blockages',[]):geometry.add((b['x'],b['y'],b['x']+b['w'],b['y']+b['h']))
collisions=[];outbox=[]
for v in sorted(st):
 x,y,w,h,_=loc[v];rect=(x,y,x+w,y+h)
 if geometry.hits(rect):collisions.append(v)
 geometry.add(rect)
 if v in box:
  c=cen(v);b=box[v]
  if not (b[0]<=c[0]<=b[2] and b[1]<=c[1]<=b[3]):outbox.append(v)
rep['final_collisions']=collisions;rep['final_out_of_region']=outbox
identity={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (bind/'die.v',r/'case/die.v',r/'plan.json',r/'table.json',r/'land.json')}
identity.update(connectivity_sha256=connectivity_sha,clock_connections_sha256=clock_sha,reset_stage_names_sha256=hashlib.sha256(json.dumps(sorted(st)).encode()).hexdigest(),reset_stage_count=len(st))
assert connectivity_sha==hashlib.sha256(json.dumps(ibits,sort_keys=True).encode()).hexdigest()
json.dump(dict(reservation=report,result=rep,original_over405=[x for x in old if x[3]>405],over=over,identity=identity,placement=loc),open(out/'result.json','w'),indent=1)
print('RESULT',json.dumps(rep),flush=True)
