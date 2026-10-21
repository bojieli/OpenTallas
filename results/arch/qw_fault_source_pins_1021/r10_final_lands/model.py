from pathlib import Path
import re,json,hashlib,sys
C=Path(sys.argv[1]);B=Path(__file__).resolve().parent
names={'flt_root_d2d_rom_g3','flt_root_native59_g1','flt_root_sys_face_g0','rly_flt_t_d2d_rom_g3_0','rly_flt_t_native59_g1_0'}
masters={};pins={};macro=pin=None
for line in (C/'elements.lef').open():
 s=line.strip();q=re.fullmatch(r'MACRO (\S+)',s)
 if q:macro=q[1];pin=None;continue
 q=re.fullmatch(r'PIN (\S+)',s)
 if q and macro:pin=q[1];continue
 q=re.fullmatch(r'SIZE ([\d.]+) BY ([\d.]+) ;',s)
 if q:masters[macro]=tuple(map(float,q.groups()))
 q=re.fullmatch(r'RECT ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ;',s)
 if q and macro and pin:pins.setdefault((macro,pin),[]).append(tuple(map(float,q.groups())))
 if s=='END '+str(pin):pin=None
 elif s=='END '+str(macro):macro=pin=None
inst={};allmaster={}
for line in (C/'die.v').open():
 q=re.fullmatch(r'\s*(\w+)\s+(\w+)\s+\((.*)\);\s*',line)
 if q and q[1] in masters:
  allmaster[q[2]]=q[1]
  if q[2] in names:inst[q[2]]=dict(master=q[1],ports=dict(re.findall(r'\.(\w+)\(([^()]*)\)',q[3])))
frames={}
for line in (C/'place.tcl').open():
 q=re.search(r'findInst (\S+)\] ([-\d.]+) ([-\d.]+) (\S+)',line)
 if q:
  n,x,y,o=q.groups();w,h=masters[allmaster[n]]
  if o in ('R90','R270','MXR90','MYR90'):w,h=h,w
  frames[n]=tuple(map(float,(x,y)))+(w,h)
  if n in names:
   assert o=='R0',(n,o)
   inst[n].update(x=float(x),y=float(y),orient=o)
assert set(inst)==names
refs={}
def point(n,p):
 m=inst[n]['master'];rects=pins.get((m,p),[])+pins.get((m,p+'[0]'),[])
 assert rects,('missing actual LEF bit pin',m,p)
 points={((a+c)/2,(b+d)/2)for a,b,c,d in rects}
 assert len(points)==1,('ambiguous actual bit pin',m,p,points)
 x,y=points.pop();v=inst[n];pt=[round(v['x']+x,6),round(v['y']+y,6)]
 refs[n+'.'+p]=dict(master=m,rects=rects,xy=pt)
 return pt
def hop(a,b):
 assert inst[a[0]]['ports'][a[1]]==inst[b[0]]['ports'][b[1]],('broken actual net',a,b)
 pa,pb=point(*a),point(*b);d=round(sum(abs(x-y)for x,y in zip(pa,pb)),6);assert d<=405
 return dict(source=a,target=b,net=inst[a[0]]['ports'][a[1]],source_xy=pa,target_xy=pb,um=d)
chains=[]
for child,parent,land in [('flt_root_d2d_rom_g3','flt_root_native59_g1','rly_flt_t_d2d_rom_g3_0'),('flt_root_native59_g1','flt_root_sys_face_g0','rly_flt_t_native59_g1_0')]:
 hs=[hop((child,'o'),(land,'a')),hop((land,'b'),(parent,'f0'))]
 assert inst[land]['ports']['ck_s']==inst[child]['ports']['ck']
 assert inst[land]['ports']['ck']==inst[parent]['ports']['ck']
 x,y,w,h=frames[land];over=[]
 for n,(a,b,c,d)in frames.items():
  if n!=land and x<a+c-1e-6 and a<x+w-1e-6 and y<b+d-1e-6 and b<y+h-1e-6:over.append(n)
 assert not over,(land,over)
 chains.append(dict(child=child,parent=parent,landing=land,frame=frames[land],master=inst[land]['master'],hops=hs,max_um=max(z['um']for z in hs),source_clock=inst[land]['ports']['ck_s'],destination_clock=inst[land]['ports']['ck'],reset_ports={k:v for k,v in inst[land]['ports'].items()if k in ('rs','en')},overlaps=over))
record=dict(scope='read-only actual final r10bfp case LEF pin identity + emitted net connectedness + four-hop reach + landing occupied-frame proof only; strict bind/root sink/clock/reset timing remain owed',case=str(C),actual_frames=len(frames),chains=chains,pin_refs=refs,case_sha256={f:hashlib.sha256((C/f).read_bytes()).hexdigest()for f in ['elements.lef','die.v','place.tcl','manifest.json']})
(B/'FINAL_FAULT_LAND.json').write_text(json.dumps(record,indent=2));print('FINAL_FAULT_LAND_PASS',len(frames),'actual frames',len(chains),'actual landings',max(c['max_um']for c in chains),'um max');print(json.dumps(chains,indent=2))
