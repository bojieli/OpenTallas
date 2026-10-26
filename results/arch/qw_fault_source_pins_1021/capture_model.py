import runpy,re,json
from pathlib import Path
from types import SimpleNamespace as I
D=runpy.run_path(str(Path(__file__).parent/'repro.py'))
B=D['B']; F=D['F'];V=D['V'];entries=D['entries']
C=Path('/srv/opentallas-scratch/claude/mu-die-qw/dv2f21g5r6b/out/case')
sizes={};cur=None
for line in (C/'elements.lef').open():
 q=re.match(r'MACRO (\S+)',line)
 if q:cur=q[1]
 q=re.match(r'\s*SIZE ([\d.]+) BY ([\d.]+)',line)
 if q:sizes[cur]=tuple(map(float,q.groups()))
masters={}
for line in (C/'die.v').open():
 q=re.match(r'\s*(\w+)\s+(\w+)\s*\(',line)
 if q and q[1] in sizes:masters[q[2]]=q[1]
inst=[]
for line in (C/'place.tcl').open():
 q=re.search(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)',line)
 if q:
  n,x,y,o=q.groups();w,h=sizes[masters[n]]
  if o in ('R90','R270','MXR90','MYR90'):w,h=h,w
  inst.append(I(name=n,x=float(x),y=float(y),w=w,h=h))
# Actual R6b die outline; derive bounds from its manifest rather than assume.
manifest=json.load(open(C/'manifest.json'));die=manifest['die']
m=dict(insts=inst,die=die);occ=F.Occ(m)
leaves=[];wire=[]
for k in range(0,len(entries),16):
 group=entries[k:k+16]
 q=F.make_master(V,len(group))
 rects=D['v'].pin_rects(q,1,{p:sp[1] for p,sp in q.ports.items()})
 native={nm.split('[')[0]:((r[0]+r[2])/2,(r[1]+r[3])/2) for nm,L,r in rects}
 input_xy=[native[f'f{j}'] for j in range(len(group))]
 cx=sum(e['xy'][0] for e in group)/len(group);cy=sum(e['xy'][1] for e in group)/len(group)
 def legal(r):
  return all(F._man(tuple(e['xy']),(r[0]+input_xy[j][0],r[1]+input_xy[j][1]))<=405 for j,e in enumerate(group))
 at=occ.site(V,cx+43.2,cy,rmax=180,step=4.32,ok=legal)
 assert at is not None,('no legal capture box',k)
 leaf=dict(name=f'model_capture{k//16}',xy=at,n=len(group),native_input_xy=input_xy,sources=[e['port'] for e in group])
 leaves.append(leaf)
 for j,e in enumerate(group):wire.append(dict(source=e['port'],source_xy=e['xy'],target=[at[0]+input_xy[j][0],at[1]+input_xy[j][1]],um=F._man(tuple(e['xy']),(at[0]+input_xy[j][0],at[1]+input_xy[j][1]))))
print('LEGAL_CAPTURE_MODEL_PASS',len(inst),'actual frames',len(entries),'actual sourcebits',len(leaves),'nonoverlapping21.6umcaptureboxes','maxwire',max(w['um'] for w in wire))
(B/'CAPTURE_MODEL.json').write_text(json.dumps(dict(scope='placement+exact perbit capture wires only; same owner/clock source plan; root/reset/clock/native/GEN qualification owed; actualR6bdata+reset occupancy conservative reference, R7AFfault roots notincluded',reference=str(C),die=die,actual_frames=len(inst),leaves=leaves,wires=wire,maxwire_um=max(w['um'] for w in wire)),indent=2))
