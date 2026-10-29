"""DIE-HBM-13: OWNER 10-29 05:3x modeled M6/M7 SPB PHY/EP escape with canonical edge-depth pins.
Every inherited .032-square interior data island becomes an edge-depth stub on the first escape layer above
the preserved full M1-M5 OBS: N/S-face pins -> M7 (vertical) .032 across x .192 depth on an M7 track;
E/W-face pins -> M6 (horizontal) .032 across x .192 depth on an M6 track. Pin centre kept on its face line,
across-coordinate snapped to the nearest free track (no two pins share a track). Status M5 edge pins
(Codex canonical) unchanged. OBS, macro sizes, FF sites, nets, tracks unchanged. MODELED abstract until
vendor LEF arrives (owner: swap in later)."""
import json,re,sys,hashlib,shutil
from pathlib import Path
base,out=map(Path,sys.argv[1:3]); out.mkdir(parents=True,exist_ok=False)
for n in ['macros.lib','probe.v','make_tracks.tcl']: shutil.copy2(base/n,out/n)
s=(base/'macros.lef').read_text()
ORG={'PHY_SPB_PROBE':(103.68,0.0),'EP_SPB_PROBE':(181.44,1088.64)}
OFF,PITCH,W,DEP=0.032,0.064,0.032,0.192
changes=[]
for m,(gx,gy) in ORG.items():
  a=s.index('MACRO '+m); b=s.index('END '+m,a); body=s[a:b]
  W_,H_=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',body).groups())
  used={}
  def snap(v,g,key):
    k0=round((v+g-OFF)/PITCH)
    for d in [0,1,-1,2,-2,3,-3,4,-4]:
      k=k0+d
      if (key,k) not in used: used[(key,k)]=1; return OFF+k*PITCH-g
    raise ValueError('no free track')
  def rep(mt):
    name,txt=mt.group(1),mt.group(2)
    r=re.search(r'LAYER (\S+) ;\s*RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',txt)
    L=r.group(1); x0,y0,x1,y1=map(float,r.group(2,3,4,5))
    if not (x1-x0<0.033 and y1-y0<0.033): return mt.group(0)   # canonical status pin: keep
    cx,cy=(x0+x1)/2,(y0+y1)/2
    if m=='PHY_SPB_PROBE':   # digital north face line y=635.04 (600.48+34.56 published envelope)
      face='N'; top=635.04; X=snap(cx,gx,'N'); new=('M7',[X-W/2,top-DEP,X+W/2,top])
    elif cx<W_/2: face='W'; Y=snap(cy,gy,'W'); new=('M6',[0.0,Y-W/2,DEP,Y+W/2])
    else: face='E'; Y=snap(cy,gy,'E'); new=('M6',[W_-DEP,Y-W/2,W_,Y+W/2])
    changes.append(dict(master=m,pin=name,face=face,old=[L,[x0,y0,x1,y1]],new=[new[0],[round(v,6) for v in new[1]]]))
    t2=txt[:r.start()]+f'LAYER {new[0]} ;\n   RECT '+' '.join(f'{v:.6f}' for v in new[1])+' ;'+txt[r.end():]
    return f' PIN {name}\n{t2} END {name}\n'
  body=re.sub(r' PIN (\S+)\n(.*?) END \1\n',rep,body,flags=re.S)
  s=s[:a]+body+s[b:]
(out/'macros.lef').write_text(s)
t=(base/'probe.tcl').read_text(); mode=sys.argv[3] if len(sys.argv)>3 else 'access'
if 'pin_access\nwrite_db' in t: t=t[:t.index('write_db /work/pin_access_before.odb')]
if mode=='access': t+='pin_access\nputs SPB_M67_ACCESS_DONE\n'
(out/'probe.tcl').write_text(t)
import collections
json.dump(dict(status='MODELED_M6M7_ESCAPE_OWNER_1029_NO_VENDOR_ABSTRACT',authority='OWNER 10-29 05:3x via COORD: modeled M6/M7 escape + canonical edge-depth pin contract; swap vendor abstracts later',
  base=str(base),base_lef_sha256=hashlib.sha256((base/'macros.lef').read_bytes()).hexdigest(),
  new_lef_sha256=hashlib.sha256((out/'macros.lef').read_bytes()).hexdigest(),
  counts=collections.Counter(f"{c['master']}:{c['face']}:{c['new'][0]}" for c in changes),
  max_snap_um=max(abs(((c['old'][1][0]+c['old'][1][2])/2 if c['face']=='N' else (c['old'][1][1]+c['old'][1][3])/2)-((c['new'][1][0]+c['new'][1][2])/2 if c['face']=='N' else (c['new'][1][1]+c['new'][1][3])/2)) for c in changes),
  unchanged=['full M1-M5 OBS both macros','macro SIZE/placement','4104 FF sites','5130 nets','status M5 edge pins','track grid'],
  changes=changes),open(out/'pin_changes.json','w'),indent=1)
print(json.load(open(out/'pin_changes.json'))['counts'], json.load(open(out/'pin_changes.json'))['max_snap_um'])
