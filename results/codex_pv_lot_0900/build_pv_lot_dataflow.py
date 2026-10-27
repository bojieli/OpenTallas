"""One PV join pin/lot proposal; no RTL, pipeline, cycle or active-plan mutation.
Clock-island relocation is explicitly left to the KV die-clock owner.
"""
import copy,gzip,json,pathlib,sys,math,re,collections
HERE=pathlib.Path(__file__).parent;I=HERE/'input';O=HERE/'out_dataflow';D=O/'pd';D.mkdir(parents=True,exist_ok=True);(D/'cores').mkdir(exist_ok=True)
P=json.load(gzip.open(I/'hm_r26.json.gz','rt'));old=copy.deepcopy(P);W,H=259.2,172.8;MOD='ot_qwen_tp8_pv_join_t'
for f in (I/'cores').glob('*.json'):(D/'cores'/f.name).write_bytes(f.read_bytes())
def nat(n):
 m=re.fullmatch(r'(.*)\[(\d+)\]',n);return (m[1],int(m[2])) if m else (n,-1)
def face(q,w=172.8,h=172.8):
 if q['name'] in ('clk','rst_n'):return 'I'
 d={'W':q['x'],'E':w-q['x'],'S':q['y'],'N':h-q['y']};return min(d,key=d.get)
def newface(q):
 b,j=nat(q['name'])
 if b=='ts0':return 'S'
 if b=='ts2':return 'N'
 if b=='ts1':return 'S' if j<448 else 'W'
 if b=='ts3':return 'W' if j<96 else 'N' if j>=576 else 'E'
 return face(q)
base=json.load(open(I/'cores/pv_join_pins.json'));by=collections.defaultdict(list)
for q in base['pins']:
 if q['name'] not in ('clk','rst_n'):by[newface(q)].append(q['name'])
pos={}
for f,names in by.items():
 names=sorted(names,key=nat);span=H if f in 'WE' else W;start=2.376 if f in 'WE' else 2.328
 ntracks=round((span-2*start)/.048)
 for j,n in enumerate(names):
  t=round(start+.048*round(j*ntracks/(len(names)-1)),6)
  pos[n]=dict(layer='M4' if f in 'WE' else 'M5',x=.096 if f=='W' else W-.096 if f=='E' else t,y=.096 if f=='S' else H-.096 if f=='N' else t)
for q in base['pins']:
 if q['name'] in ('clk','rst_n'):pos[q['name']]=dict(layer='M5',x=round(q['x']+(W-172.8)/2,6),y=q['y'])
views={};pin_delta=[];dens={}
for suffix in ('','_fMX','_fR180'):
 fn='pv_join_pins'+suffix+'.json';v=json.load(open(I/'cores'/fn));out=copy.deepcopy(v)
 for q in out['pins']:
  orig=copy.deepcopy(q);q.update(pos[q['name']])
  if suffix=='_fMX':q['y']=round(H-q['y'],6)
  elif suffix=='_fR180' and q['name'] not in ('clk','rst_n'):q['x']=round(W-q['x'],6);q['y']=round(H-q['y'],6)
  if q!=orig:pin_delta.append(dict(view=fn,name=q['name'],old=orig,new=q))
 out['frame']='core R0, origin (0,0), outline 259.2 x 172.8'
 out['source']=v.get('source','')+' | CODEX PV lot proposal: W259.2 H172.8, numeric bus order, <=60 pins/10um window; clock/reset centre entry and RTL/cycles unchanged'
 ff=collections.defaultdict(list)
 for q in out['pins']:
  f=face(q,W,H)
  if f!='I':ff[f].append(q['y'] if f in 'WE' else q['x'])
 report={}
 for f,xs in ff.items():
  xs.sort();peak=0;i=0
  for j,x in enumerate(xs):
   while x-xs[i]>10.0+1e-9:i+=1
   peak=max(peak,j-i+1)
  assert peak<=60,(fn,f,peak)
  report[f]=dict(pins=len(xs),peak_10um=peak,pins_per_um=peak/10,min_spacing_um=round(min(b-a for a,b in zip(xs,xs[1:])),6))
  assert min(b-a for a,b in zip(xs,xs[1:]))>=.144-1e-6
 out['faces']={f:dict(pins=len(xs),layers=['M4' if f in 'WE' else 'M5']) for f,xs in ff.items()}
 views[fn]=out;dens[fn]=report;(D/'cores'/fn).write_text(json.dumps(out,indent=1)+'\n')
def hb(h):
 x,y=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);w,hg=h['outline_um'];return [min(x,x+dx),min(y,y+dy),max(x+w,x+dx+w),max(y+hg,y+dy+hg)]
def hits(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def inside(q,b):return b[0]<q[0]<b[2] and b[1]<q[1]<b[3]
def trans(pt,h):
 x,y=pt;w,ht=h['outline_um'];o=h.get('orient','R0');x,y={'R0':(x,y),'MX':(x,ht-y),'MY':(w-x,y),'R180':(w-x,ht-y)}[o];dx,dy=h.get('track_offset_um',[0,0]);return [round(h['origin_um'][0]+dx+x,6),round(h['origin_um'][1]+dy+y,6)]
cores=[];moves=[];clock=[];unsited=[];lot_fail=[]
for tn,t in P['partition_types'].items():
 hs=[h for h in t.get('hard_cores',[]) if h['module']==MOD]
 if not hs:continue
 for h in hs:
  before=copy.deepcopy(h);h['origin_um'][0]=round(h['origin_um'][0]-(W-172.8)/2,6);h['outline_um']=[W,H]
  fn=pathlib.Path(h['pins_file']).name;vv={q['name']:q for q in views[fn]['pins']};ov={q['name']:q for q in json.load(open(I/'cores'/fn))['pins']}
  for n in ('clk','rst_n'):assert trans((vv[n]['x'],vv[n]['y']),h)==trans((ov[n]['x'],ov[n]['y']),before),(tn,h['inst'],n)
  h['note']=h.get('note','')+' | PENDING CODEX PV lot/pin repair259.2x172.8; numeric face packing, 0cycles; parentclock islands MUST be re-sited before route'
  cores.append(dict(type=tn,inst=h['inst'],old=before,new=copy.deepcopy(h)))
  for q in t['hard_cores']:
   if q is not h and hits(hb(h),hb(q)):lot_fail.append((tn,h['inst'],q['inst']))
  for j,r in enumerate(t['clock'].get('die_islands_um',[])):
   if hits(hb(h),r):clock.append(dict(type=tn,core=h['inst'],index=j,rect_um=r,new_core_rect=hb(h)))
 for key in ('ft_slots','internal_stations'):
  for si,s in enumerate(t.get(key,[])):
   rr=s.get('regs_um',[])
   if key=='ft_slots' and not rr and not s.get('bit_sites_um'):unsited.append((tn,s['name']))
   for j,q in enumerate(list(rr)):
    body=next((hb(h) for h in hs if inside(q,hb(h))),None)
    if body is None:continue
    assert 0<j<len(rr)-1,(tn,key,si,j,'endpoint needs owner')
    clear=1.08 if s.get('width',1)==1 else 2.7
    cand=[[body[0]-clear,q[1]],[body[2]+clear,q[1]],[q[0],body[1]-clear],[q[0],body[3]+clear]]
    good=[]
    for p in cand:
     if any(inside(p,hb(h)) for h in t['hard_cores']):continue
     hops=[abs(p[0]-a[0])+abs(p[1]-a[1]) for a in (rr[j-1],rr[j+1])]
     if max(hops)>405+1e-7:continue
     good.append((abs(p[0]-q[0])+abs(p[1]-q[1]),p,hops))
    assert good,(tn,key,si,j,q,body)
    _,p,ho=min(good);p=[round(x,6) for x in p]
    moves.append(dict(type=tn,kind=key,slot=s.get('name',s.get('conn')),index=si,station=j,width=s.get('width'),old=q,new=p,new_neighbour_hops_um=ho,cycles_added=0))
    rr[j]=p
assert not lot_fail,lot_fail
# Map overlapped halo rectangles to actual canonical R25 clock-cell identities.
sites=json.load(gzip.open(I/'clock_mesh_sites_r25.json.gz','rt'))['sites'];lookup=collections.defaultdict(list)
for name,kind,x,y,part in sites:lookup[(part,round(x,3),round(y,3))].append((name,kind))
sys.path.insert(0,str(pathlib.Path(sys.argv[1])/'tools/die_plan'));import schema as S
SP=S.Plan(old);parts_by_type=collections.defaultdict(list)
for name,p in SP.parts.items():parts_by_type[p['type']].append(name)
for row in clock:
 r=row['rect_um'];body=[r[0]+.54,r[1]+.27,r[2]-.54,r[3]-.27];found=[]
 for part in parts_by_type[row['type']]:
  a=SP.to_die(part,(body[0],body[1]));b=SP.to_die(part,(body[2],body[3]));x,y=min(a[0],b[0]),min(a[1],b[1]);names=lookup.get((part,round(x,3),round(y,3)),[])
  found += [dict(part=part,name=n,kind=k,world_origin_um=[round(x,3),round(y,3)]) for n,k in names]
 assert found,('unmappedclock',row)
 row['canonical_cells']=found
# Published shared pre-build insertion model, used unchanged and labelled.
import master_plan as MP,kv_core_slice as KS
ex,ey=MP.snap(W/2),MP.snap(H/2);tree=MP.restructure_islands(W,H,200);lt,lf=MP.core_insertion(tree['leaf_reach_um']);tr=max(abs(q['centre_um'][0]-ex)+abs(q['centre_um'][1]-ey) for q in tree['islands']);tt=round(lt+tr*KS.TRUNK_PS_PER_UM,1);ff=round(lf+tr*KS.TRUNK_PS_PER_UM*MP.FF_RATIO,1);n=round((250-tt)/KS.BUF_STAGE_PS['TT']) if tt<230 else 0
clock_slice=dict(module=MOD,outline_um=[W,H],entry_um=[ex,ey],clock_pin_um=[ex+.024,ey],reset_pin_um=[ex+.408,ey],island_grid=tree['grid'],islands=tree['islands'],leaf_reach_um=tree['leaf_reach_um'],pred_TT_ps=round(tt+n*KS.BUF_STAGE_PS['TT'],1),pred_FF_ps=round(ff+n*KS.BUF_STAGE_PS['FF'],1),trunk_cells=n,trunk_master='BUFx4_ASAP7_75t_R',model='UNCHANGED published kv_core_slice/master_plan assumptions, MODEL UNCHECKED; no measured timing selected structure',build_status='NOT BUILT; CLOCK-KV must regenerate parent sites/clock wires first')
(D/'hm_pv_lot.json').write_text(json.dumps(P,indent=1)+'\n')
for name,data in [('pin_density.json',dens),('hard_core_delta.json',cores),('ft_station_delta.json',moves),('parent_clock_relocate.json',clock),('clock_slice_proposal.json',clock_slice),('base_unsited_ft.json',unsited)]:
 (O/name).write_text(json.dumps(data,indent=1)+'\n')
with gzip.open(O/'pin_delta.json.gz','wt') as z:json.dump(pin_delta,z)
print('PV_LOT_PROPOSAL',len(cores),'coredefs',len(moves),'FTmoves',len(clock),'parentclockrects',len(unsited),'baseunsited slots')
print('PIN_DENSITY',dens);print('CLOCK_SLICE',clock_slice)
