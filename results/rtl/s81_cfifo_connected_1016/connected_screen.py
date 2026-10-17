from pathlib import Path
import gzip,json,hashlib,math,collections
R=Path(__file__).parent;P=Path('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz');j=json.load(gzip.open(P,'rt'));base={i['name']:dict(i) for i in j['insts']};cf={n:i for n,i in base.items() if i['master']=='dsfd_cfifo'};old=json.load(open(R.parent/'s81_cfifo_partition_1016/sizing.json'));W,H=old['proposal']['outline_um'];by=collections.defaultdict(list)
for b in j['buses']:
 for n,p in b[3]:by[n].append(b)
def corners(i):return [(i['x']+x*i['w'],i['y']+y*i['h']) for x in [0,1] for y in [0,1]]
def bounds(a,b):
 lo=max(a['x']-b['x']-b['w'],b['x']-a['x']-a['w'],0)+max(a['y']-b['y']-b['h'],b['y']-a['y']-a['h'],0)
 hi=max(abs(x-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b));return [round(lo,3),round(hi,3)]
def overlap(a,b):return min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+.001 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+.001
conflicts=[]
for q in old['overlaps']:
 n=q['other'];conflicts.append(dict(**q,instance=base[n],incident_buses=by[n]))
(R/'all10_conflicts.json').write_text(json.dumps(dict(scope=j['scope'],source=j['source_commit'],plan_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),conflicts=conflicts,final_pin_coordinates=False),indent=1)+'\n')
res=[]
for alt in ['A_south_aprons_rd_north','B_east_aprons_rd_south_plus1','C_east_horiz_final_preserve_upstream']:
 d={n:dict(v) for n,v in base.items()};moved=set();missing=[]
 for name,c in cf.items():
  r=int(name[2:]);a=d[name];a.update(w=W,h=H,y=c['y']+c['h']-H);moved.add(name)
  for lane in [0,1]:
   for stage in [1,2]:
    n=f'f_cx{r}'+('_x2' if lane else '')+f'_{stage}'
    if n not in d:missing.append(n);continue
    q=d[n]
    if alt.startswith('A'):
     q['y']=a['y']-32.4-lane*54-q['h']
    elif alt.startswith('C'):
     if stage==1:q['x']=a['x']+a['w']+82.08+38.88*lane
     else:
      q['x']=a['x']+a['w']+32.4;q['y']=a['y']+lane*54;q['w']=17.256;q['h']=32.376;q['orient']='MY';q['master']='PROPOSED_dsfd_stnh_'+('538x1' if lane else '566x1')+'_fn0'
    else:
     q['x']=a['x']+a['w']+32.4+(stage-1)*64.8;q['y']=a['y']+lane*54
    moved.add(n)
  if alt.startswith('A'):
   b=next(b for b in by[name] if b[3][0]==[name,'rd']);nn=b[3][1][0];q=d[nn]
   nxt=[z for z in by[nn] if z[3][0][0]==nn and z[1]=='lane'];right=bool(nxt and base[nxt[0][3][1][0]]['x']>a['x']+202)
   q['x']=a['x']+202+(32.4 if right else -32.4-q['w']);q['y']=a['y']+H+61.56;q['orient']='R0' if right else 'R180';moved.add(nn)

 if alt.startswith('C'):
  # Joint, source-connected station-pair placement. Coarse existing geometry only.
  firsts={f'f_cx{int(n[2:])}'+('_x2' if lane else '')+'_1' for n in cf for lane in [0,1]}
  occ=collections.defaultdict(set)
  def add_occ(n,a):
   for gx in range(math.floor(a['x']/200),math.floor((a['x']+a['w'])/200)+1):
    for gy in range(math.floor(a['y']/200),math.floor((a['y']+a['h'])/200)+1):occ[gx,gy].add(n)
  for n,a in d.items():
   if n not in firsts:add_occ(n,a)
  no_joint_home=[]
  for cn in sorted(cf,key=lambda n:int(n[2:])):
   rr=int(cn[2:]);names=[f'f_cx{rr}'+('_x2' if lane else '')+'_1' for lane in [0,1]];opts=[]
   for xx in range(1,13):
    for yy in range(-4,5):
     cand=[];score=0;ok=True
     for lane,n in enumerate(names):
      a=dict(d[n]);a['x']=d[cn]['x']+W+21.6*xx+38.88*lane;a['y']=base[n]['y']+21.6*yy
      if a['x']<0 or a['y']<0 or a['x']+a['w']>33000 or a['y']+a['h']>26000:ok=False;break
      near=set()
      for gx in range(math.floor(a['x']/200),math.floor((a['x']+a['w'])/200)+1):
       for gy in range(math.floor(a['y']/200),math.floor((a['y']+a['h'])/200)+1):near.update(occ[gx,gy])
      if any(overlap(a,d[z]) for z in near):ok=False;break
      for bus in by[n]:
       if bus[1]!='lane':continue
       peer=bus[3][0][0] if bus[3][0][0]!=n else bus[3][1][0]
       bb=bounds(a,d[peer])
       if bb[1]>430.56:ok=False;break
       score+=bb[1]
      if not ok:break
      score+=abs(a['x']-base[n]['x'])+abs(a['y']-base[n]['y']);cand.append(a)
     if ok and not overlap(cand[0],cand[1]):opts.append((score,cand))
   if opts:
    _,cand=min(opts,key=lambda z:z[0])
    for n,a in zip(names,cand):d[n]=a;add_occ(n,a)
   else:
    no_joint_home.append(cn)
    for n in names:add_occ(n,d[n])
 for n in ['f_KW3r_22','f_KW3r_25']:d[n]['y']-=54;moved.add(n)
 grid=collections.defaultdict(set)
 for n,a in d.items():
  for gx in range(math.floor(a['x']/200),math.floor((a['x']+a['w'])/200)+1):
   for gy in range(math.floor(a['y']/200),math.floor((a['y']+a['h'])/200)+1):grid[gx,gy].add(n)
 ov=set();outside=[]
 for n in moved:
  a=d[n]
  if a['x']<0 or a['y']<0 or a['x']+a['w']>33000 or a['y']+a['h']>26000:outside.append(n)
  near=set()
  for gx in range(math.floor(a['x']/200),math.floor((a['x']+a['w'])/200)+1):
   for gy in range(math.floor(a['y']/200),math.floor((a['y']+a['h'])/200)+1):near.update(grid[gx,gy])
  for nn in near:
   if nn!=n and overlap(a,d[nn]):ov.add(tuple(sorted([n,nn])))
 buses={b[0]:b for n in moved for b in by[n]};edges=[]
 for bid,b in buses.items():
  src=b[3][0]
  for dst in b[3][1:]:
   if src[0] not in moved and dst[0] not in moved:continue
   if src[0] not in d or dst[0] not in d:continue
   mm=dict(bus=bid,kind=b[1],bits=b[2],source=src,target=dst,before_rectangle_L1_bounds_um=bounds(base[src[0]],base[dst[0]]),after_rectangle_L1_bounds_um=bounds(d[src[0]],d[dst[0]]),actual_pin_reach_um=None,actual_cut_ratio=None,min_full_bus_corridor_width_at_60pct_um=round(b[2]/(.6*31.51),3))
   for key,(n,p) in [('source_pin_names',src),('target_pin_names',dst)]:
    t=j['pins'].get(d[n]['master']+'|'+p.split('[')[0]);mm[key]=dict(first=t[0],last=t[min(len(t),b[2])-1],count=b[2]) if t else dict(port=p,width=b[2],mapping='default bus names, no final coordinates')
   if src[0].startswith('cf') and src[1] in ['co','rf']:mm['scope']='OLD_CLOCK_DRIVER_REMOVED_NEEDS_ACTUAL_DIE_REBIND'
   elif alt.startswith('A') and src[0].startswith('cf') and src[1]=='rd':mm['scope']='RD_REHOMED_N_NO_FINAL_PIN_COORDS'
   else:mm['scope']='RECTANGLE_INTERVAL_ONLY_NOT_ACTUAL_PIN_PROOF'
   edges.append(mm)
 row=dict(name=alt,scope='UNQUALIFIED_FULL_FIRST_PASS_CONNECTED_GROUP_SCREEN',parent_count=len(cf),moved_instances=len(moved),missing_instances=missing,outline_um=[W,H],parent_area_delta_mm2=old['proposal']['parent_area_delta_vs_old_slot_mm2'],source_cycles_added=0,return_cycles_added=0 if alt.startswith('A') else 1,return_added_latency_ps=0 if alt.startswith('A') else 833.333,return_added_flops_per_parent=0 if alt.startswith('A') else 70,token_rate_loss='UNMEASURED_NOT_ACCEPTED',overlap_count=len(ov),overlaps=[list(p) for p in sorted(ov)],outside=outside,incident_buses=len(buses),incident_edges=len(edges),rectangle_lower_bound_over500=sum(e['after_rectangle_L1_bounds_um'][0]>500 for e in edges),rectangle_upper_bound_under500=sum(e['after_rectangle_L1_bounds_um'][1]<=500 for e in edges),actual_pin_reach_qualified_edges=0,actual_cut_qualified_edges=0,actual_clock_qualified_edges=0,station_reach_limit_um=430.56,data_lower_bounds_over430_56=sum(e['kind']=='lane' and e['after_rectangle_L1_bounds_um'][0]>430.56 for e in edges),proposed_new_master_ABI=alt.startswith('C'),joint_source_pair_unplaced=no_joint_home if alt.startswith('C') else [],edges=edges,homes={n:d[n] for n in sorted(moved)})
 (R/(alt+'.json.gz')).write_bytes(gzip.compress(json.dumps(row,separators=(',',':')).encode(),mtime=0));row['reach_by_kind']={kind:dict(edges=sum(e['kind']==kind for e in edges),rectangle_lower_bound_over500=sum(e['kind']==kind and e['after_rectangle_L1_bounds_um'][0]>500 for e in edges),rectangle_upper_bound_under500=sum(e['kind']==kind and e['after_rectangle_L1_bounds_um'][1]<=500 for e in edges)) for kind in sorted({e['kind'] for e in edges})}
 res.append({k:v for k,v in row.items() if k not in ['edges','homes','overlaps']})
print(json.dumps(res,indent=1));(R/'summary.json').write_text(json.dumps(dict(source_commit=j['source_commit'],generator_sha256=j['generator_sha256'],plan_sha256=hashlib.sha256(P.read_bytes()).hexdigest(),scope=j['scope'],alternatives=res,ranking='A rejected for collisions/outside. B is preferred as an unqualified zero-overlap footprint, but16 lane edges have >500um rectangle lower bounds; paired extra relay stages and final-pin/clock/cut proof remain required. A preserves return cycles; B pays explicit one-edge return pipeline and preserves S launch.',open=['Current final GEN/actual pins not emitted','Actual routed channels and cumulative cuts','Actual per-root phi-R/TT/FF/native80 spread','No fresh gate or physical grant']),indent=1)+'\n')
