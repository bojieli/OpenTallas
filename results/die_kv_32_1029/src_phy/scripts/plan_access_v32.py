#!/usr/bin/env python3
"""DIE-KV-32: plan_access_soft.py (DIE-KV-31 variant of Codex plan_access.py) + (1) per-failed-group blocker attribution,
(2) optional VIA78 landing on the nearest same-net die M8 PG stripe (--m8-landing fallback|first), off the M8 clock-leg reservations.
Original docstring: Construct power-first access from actual contacts; all dimensions are integer DBU.
No abstract obstruction is waived. A bridge rises inside its legal opening to M8,
then reaches an actual same-net M9 grid stripe. This is geometry, not IR closure.
"""
import argparse,json,collections,math,time
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--clock-seed',required=True,help='Actual fixed future clock lower-layer metal rectangles in um');p.add_argument('--limit',type=int,default=0);p.add_argument('--native-overlay');p.add_argument('--joint-clock-reserved',help='Clock access reservation rectangles [net,layer,x0,y0,x1,y1] in um; M8 shield clearance already included minus normal 40nm PG clearance');p.add_argument("--soft-block-layer",default="",help="DIE-KV-31 variant: BLOCK OBS on this layer (die_trial.band_share_obs capacity stripes) are NOT hard blockers; PG metal inside them is charged to the stripe capacity");p.add_argument("--y-reach",type=int,default=1400,help="DIE-KV-31 variant: M8 landing search half-range in DBU (original 1400)");p.add_argument("--m8-landing",default="off",choices=["off","fallback","first"],help="DIE-KV-32: VIA78 directly onto the nearest same-net M8 die PG stripe covering the stack x (no M8 bridge, no VIA89); fallback = only after every M9-bridge candidate failed");p.add_argument("--m9-select",default="x",choices=["x","cover"],help="DIE-KV-32: x = original (3 x-nearest same-net M9 segments, even when they are cuts of one column that miss the landing y); cover = 3 x-nearest segments that cover the landing y");p.add_argument("--m8-reach",type=int,default=4400,help="DIE-KV-32: max |stripe centre y - rail y| in DBU for the M8-stripe landing (M8 PG pitch 4320)");a=p.parse_args();src=Path(a.input);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
g=json.load(open(src/'geometry.json'));terms=json.load(open(src/'power_terms.json'))['terms'];ep=json.load(open(src/'endpoints.json'))['endpoints'];pg=json.load(open(src/'pg_rects.json'));tech=json.load(open(src/'probe_census.json'))['tech_vias_dbu'];D=g['dbu'];spacing={f'M{i}':v for i,v in enumerate([0,18,18,18,24,24,32,32,40,40]) if i}
if a.native_overlay:
 overlay=json.load(open(a.native_overlay))
 if overlay.get('schema')!='opentallas.native_pg_obstruction_overlay.v1':raise ValueError('Wrong actual native OBS overlay schema')
 old=collections.Counter(tuple(r) for r in overlay['old_native_supplies']);kept=[]
 for r in g['existing_supplies']:
  key=tuple(r)
  if old[key]:old[key]-=1
  else:kept.append(r)
 if any(old.values()):raise ValueError('Overlay old native PG census differs from exported source')
 g['existing_supplies']=kept+overlay['new_native_supplies'];g['obstructions']=overlay['obstructions'];g['source']=overlay['source']
 print('ACTUAL_NATIVE_OVERLAY',overlay['owned_supply_terms'],overlay['owned_pg_capacity_obstructions'],flush=True)
blocked=collections.defaultdict(list);btag=collections.defaultdict(list);cellnames={c['inst'] for c in g['cells']}
def otag(owner,ly,r):
 if owner=='BLOCK':
  if ly=='M8' and r[3]-r[1]==400:return 'clock_leg_M8'
  if ly=='M9' and r[2]-r[0]==400:return 'clock_leg_M9'
  if ly=='M7':return 'band_share_M7'
  return 'BLOCK_other_'+ly
 if 'VDDPHY' in owner:return 'VDDPHY_pg'
 return 'cell_obs' if owner in cellnames else 'macro_obs'
grid_keys={(ly,*[round(v*D) for v in r]) for n,ly,*r in pg if ly in ['M8','M9']}
owned_grid_obs=0
soft=[]
for owner,ly,*r in g['obstructions']:
 if owner=='BLOCK' and ly==a.soft_block_layer:soft.append(r);continue
 if owner=='BLOCK' and (ly,*r) in grid_keys:owned_grid_obs+=1
 else:blocked[ly].append(r);btag[ly].append(otag(owner,ly,r))
print('exact_owned_grid_obstructions',owned_grid_obs,flush=True)
for i0,_,ly,*r in g['signal_shapes']:blocked[ly].append(r);btag[ly].append('cell_signal_pin' if i0 in cellnames else 'macro_signal_pin')
for e in ep.values():blocked[e['layer']].append([round(v*D) for v in e['rect_um']]);btag[e['layer']].append('endpoint')
for n,ly,*r in json.load(open(a.clock_seed)):blocked[ly].append([round(v*D) for v in r]);btag[ly].append('clock_seed')
if a.joint_clock_reserved:
 for n,ly,*r in json.load(open(a.joint_clock_reserved)):blocked[ly].append([round(v*D) for v in r]);btag[ly].append('joint_clock')
trees={ly:STRtree([box(*r) for r in rr]) for ly,rr in blocked.items()}
supply=collections.defaultdict(list);stag=collections.defaultdict(list)
for n,ly,*r in g['existing_supplies']:supply[n,ly].append(r);stag[n,ly].append('opp_native_supply')
for n,ly,*r in pg:supply[n,ly].append([round(v*D) for v in r]);stag[n,ly].append('opp_grid_'+ly)
for t in terms:
 for ly,*r in t['shapes_dbu']:supply[t['pin'],ly].append(r);stag[t['pin'],ly].append('opp_cell_rail')
suptrees={k:STRtree([box(*r) for r in rr]) for k,rr in supply.items()}
# Rail grouping only uses exact same-y, overlapping or abutting native metal.
rows=collections.defaultdict(list)
for t in terms:
 assert len(t['shapes_dbu'])==1
 ly,x0,y0,x1,y1=t['shapes_dbu'][0];assert ly=='M1' and t['orient']=='R0'
 rows[t['pin'],y0,y1].append((x0,x1,t['inst']))
groups=[]
for (n,y0,y1),rr in rows.items():
 rr.sort();cur=None
 for x0,x1,inst in rr:
  if cur and x0<=cur[1]:cur[1]=max(cur[1],x1);cur[2].append(inst)
  else:
   if cur:groups.append((n,cur[0],y0,cur[1],y1,cur[2]))
   cur=[x0,x1,[inst]]
 if cur:groups.append((n,cur[0],y0,cur[1],y1,cur[2]))
groups.sort(key=lambda q:(q[2],q[1],q[0]));print('groups',len(groups),flush=True)
m8s={n:[tuple(round(v*D) for v in r) for nn,ly,*r in pg if nn==n and ly=='M8'] for n in ['VDD','VSS']};m8t={n:STRtree([box(*r) for r in m8s[n]]) for n in m8s}
stripes={n:sorted([tuple(round(v*D) for v in r) for nn,ly,*r in pg if nn==n and ly=='M9']) for n in ['VDD','VSS']}
# Opposite proposed conductors are indexed in fine bins. No large die-wide bins.
new=collections.defaultdict(lambda:collections.defaultdict(list));B=4000
reasons=collections.Counter(); examples={}

def binrect(r):
 x0,y0,x1,y1=r
 for x in range(x0//B,x1//B+1):
  for y in range(y0//B,y1//B+1):yield x,y

def hit(r,s):return r[0]<s[2] and s[0]<r[2] and r[1]<s[3] and s[1]<r[3]
def blk(n,ly,r):
 """None if clear, else the owner tag of the first blocker found (same order/semantics as the original clear())."""
 sp=spacing[ly];q=[r[0]-sp,r[1]-sp,r[2]+sp,r[3]+sp]
 if q[0]<0 or q[1]<0 or q[2]>g['die_dbu'][2] or q[3]>g['die_dbu'][3]:return 'die_edge'
 b=box(*q)
 if ly in trees:
  for j in trees[ly].query(b):
   if hit(q,trees[ly].geometries[j].bounds):
    reasons['obstacle_'+ly]+=1
    if ly not in examples:examples[ly]=dict(candidate=r,blocking=list(trees[ly].geometries[trees[ly].query(b)[0]].bounds))
    return btag[ly][j]
 opp='VSS' if n=='VDD' else 'VDD'
 if (opp,ly) in suptrees:
  for j in suptrees[opp,ly].query(b):
   if hit(q,suptrees[opp,ly].geometries[j].bounds):return stag[opp,ly][j]
 if any(hit(q,s) for k in binrect(q) for s in new[opp,ly].get(k,[])):return 'opp_new_access'
 return None
def clear(n,ly,r):return blk(n,ly,r) is None

def stack(x,y):
 sh=[('M1',x-9,y-11,x+9,y+11),('M2',x-25,y-9,x+25,y+9),('M3',x-9,y-25,x+9,y+25),('M4',x-48,y-12,x+48,y+12),('M5',x-12,y-48,x+12,y+48),('M6',x-40,y-16,x+40,y+16),('M7',x-16,y-40,x+16,y+40)]
 return sh
shapes=[];vias=[];paths=[];failed=[];landing=collections.Counter()
for gi,(n,x0,y0,x1,y1,members) in enumerate(groups):
 if a.limit and gi>=a.limit:break
 # Land outward by 2nm so VIA12's 22nm M1 box does not consume the native 18nm A/Y spacing.
 y=(y0+y1)//2+(2 if n=='VDD' else -2);par=0 if n=='VDD' else 1
 xs=range(math.ceil((x0+50-32-64*par)/128),math.floor((x1-50-32-64*par)/128)+1)
 xs=sorted((32+64*par+128*k for k in xs),key=lambda x:abs(x-(x0+x1)/2))
 ys=sorted((40+80*par+160*k for k in range(math.floor((y-a.y_reach-40-80*par)/160),math.ceil((y+a.y_reach-40-80*par)/160)+1)),key=lambda yy:abs(yy-y))
 found=None;tally=collections.defaultdict(collections.Counter);okx=[]
 for x in xs:
  ss=stack(x,y);t=None
  for ly,*r in ss:
   t=blk(n,ly,list(r))
   if t:tally['stack'][ly+':'+t]+=1;break
  if not t:okx.append((x,ss))
 def try_m9(x,ss):
  # Original: nearest actual same-net M9 stripe via an M8 bridge; retain its full via89 enclosure.
  dst=sorted(stripes[n],key=lambda r:max(r[0]+20-x,0,x-r[2]+20))
  for yy in ys:
   stem=('M7',x-16,min(y-40,yy-40),x+16,max(y+40,yy+40))
   land=('M8',x-96,yy-20,x+96,yy+20) # 7680 DBU^2 >= actual M8 minimum AREA7520
   t=blk(n,stem[0],list(stem[1:]))
   if t:tally['stem']['M7:'+t]+=1;continue
   t=blk(n,land[0],list(land[1:]))
   if t:tally['land']['M8:'+t]+=1;continue
   for sx0,sy0,sx1,sy1 in ([r for r in dst if r[1]+20<=yy<=r[3]-20][:3] if a.m9_select=='cover' else dst[:3]):
    if not sy0+20<=yy<=sy1-20:tally['m9_yrange']['M9_stripe_y_range']+=1;continue
    xx=max(sx0+20,min(x,sx1-20))
    bridge=('M8',min(x,xx)-40,yy-20,max(x,xx)+40,yy+20)
    end=('M9',xx-20,yy-20,xx+20,yy+20)
    t=blk(n,'M8',list(bridge[1:]))
    if t:tally['bridge']['M8:'+t]+=1;continue
    t=blk(n,'M9',list(end[1:]))
    if t:tally['m9end']['M9:'+t]+=1;continue
    return ss+[stem,land,bridge,end],x,yy,xx,'M9_bridge'
  return None
 def try_m8s(x,ss):
  # DIE-KV-32: VIA78 straight onto the nearest same-net die M8 PG stripe that covers x (real grid metal, which the die plan
  # already keeps off the M8 clock legs); the M7 stem is the only new routing, no M8 bridge and no VIA89.
  cs=[m8s[n][j] for j in m8t[n].query(box(x-96,y-a.m8_reach,x+96,y+a.m8_reach))]
  cs=sorted((R for R in cs if R[0]<=x-96 and x+96<=R[2] and abs((R[1]+R[3])//2-y)<=a.m8_reach),key=lambda R:abs((R[1]+R[3])//2-y))
  if not cs:tally['m8s_none']['no_same_net_M8_stripe_covering_x']+=1;return None
  for R in cs:
   yc=(R[1]+R[3])//2
   stem=('M7',x-16,min(y-40,yc-40),x+16,max(y+40,yc+40));land=('M8',x-96,yc-20,x+96,yc+20)
   t=blk(n,stem[0],list(stem[1:]))
   if t:tally['m8s_stem']['M7:'+t]+=1;continue
   t=blk(n,land[0],list(land[1:]))
   if t:tally['m8s_land']['M8:'+t]+=1;continue
   return ss+[stem,land],x,yc,None,'M8_stripe'
  return None
 order={'off':[try_m9],'fallback':[try_m9,try_m8s],'first':[try_m8s,try_m9]}[a.m8_landing]
 for fn in order:
  for x,ss in okx:
   found=fn(x,ss)
   if found:break
  if found:break
 if not found:
  rk=['stack','stem','land','m9_yrange','bridge','m9end'];deep=[k for k in rk if tally[k]];m9c=(deep[-1],tally[deep[-1]].most_common(1)[0][0]) if deep else ('no_stack_site','rail_too_short')
  m8c=None
  for k in ['m8s_land','m8s_stem','m8s_none']:
   if tally[k]:m8c=(k,tally[k].most_common(1)[0][0]);break
  failed.append(dict(net=n,rail=[x0,y0,x1,y1],members=members,cause_m9=m9c,cause_m8s=m8c,tally={k:dict(v.most_common(4)) for k,v in tally.items()}))
 else:
  ss,x,yy,xx,how=found;landing[how]+=1
  for ly,*r in ss:
   shapes.append([n,ly,*r])
   for k in binrect(r):new[n,ly][k].append(r)
  vv=[(f'VIA{i}{i+1}',x,y) for i in range(1,7)]+[('VIA78',x,yy)]+([('VIA89',xx,yy)] if xx is not None else [])
  for vn,vx,vy in vv:
   vias.append([n,vn,vx,vy])
   for ly,ax,ay,bx,by in tech[vn]:
    if not ly.startswith('M'):continue
    r=[vx+ax,vy+ay,vx+bx,vy+by];shapes.append([n,ly,*r])
    for k in binrect(r):new[n,ly][k].append(r)
  paths.append(dict(net=n,members=members,rail=[x0,y0,x1,y1],stack=[x,y],m8=[x,yy,xx if xx is not None else x,yy],landing=how))
 if gi%1000==0:print(gi,'ok',len(paths),'fail',len(failed),flush=True)

# DIE-KV-32: attribution of every failed group, bucketed by distance of the rail to the nearest M8 clock-leg reservation (DIE-KV-31 why_m8 buckets).
ck=[r for r,t in zip(blocked.get('M8',[]),btag.get('M8',[])) if t=='clock_leg_M8'];ckt=STRtree([box(*r) for r in ck]) if ck else None
att=collections.defaultdict(lambda:collections.defaultdict(collections.Counter))
for q in failed:
 x0,y0,x1,y1=q['rail'];cy=(y0+y1)//2;bk='no_clock_M8_reserve_within_10.8um'
 for R in (1400,5400,10800):
  if ckt is not None and len(ckt.query(box(x0,cy-R,x1,cy+R))):bk=f'clock_M8_reserve_within_{R/1000}um';break
 q['clock_bucket']=bk;att[bk]['m9_path:'+q['cause_m9'][0]][q['cause_m9'][1]]+=1
 if q['cause_m8s']:att[bk]['m8_stripe:'+q['cause_m8s'][0]][q['cause_m8s'][1]]+=1
att_out=dict(clock_leg_M8_reservations=len(ck),attribution={bk:{st:dict(c.most_common()) for st,c in v.items()} for bk,v in att.items()},attribution_bucket_counts={bk:sum(1 for q in failed if q['clock_bucket']==bk) for bk in att})
json.dump(dict(source=g['source'],paths=paths,vias_dbu=vias,failed=failed,dbu=D,tech_vias_dbu=tech),open(out/'access_plan.json','w'),separators=(',',':'))
json.dump([[n,ly,*[v/D for v in r]] for n,ly,*r in shapes],open(out/'reserved_access.json','w'),separators=(',',':'))
s=dict(groups=len(groups),attempted=len(paths)+len(failed),connected_groups=len(paths),connected_contacts=sum(len(q['members']) for q in paths),failed_groups=len(failed),routing_rectangles=len(shapes),vias=len(vias),verdict='GEOMETRY_CANDIDATE' if not failed else 'INCOMPLETE_NO_MATERIALIZATION')
s.update(att_out);s['m8_landing_mode']=a.m8_landing;s['m8_reach_dbu']=a.m8_reach;s['m9_select']=a.m9_select;s['landing']=dict(landing);s['owned_grid_obstructions']=owned_grid_obs;s['rejections']=dict(reasons);s['obstacle_examples']=examples

# DIE-KV-31: charge PG metal on the soft layer against each band-share stripe, per 10.8-um gcell segment.
if soft:
 G=10800;pitch={'M7':64,'M6':64,'M5':48,'M4':48}.get(a.soft_block_layer,64);st=STRtree([box(*r) for r in soft]);use=collections.defaultdict(set)
 for n,ly,*r in shapes:
  if ly!=a.soft_block_layer:continue
  for j in st.query(box(*r)):
   R=soft[j]
   if not hit(r,R):continue
   vert=(R[3]-R[1])>(R[2]-R[0])
   tr0,tr1=((r[0]//pitch,(r[2]-1)//pitch) if vert else (r[1]//pitch,(r[3]-1)//pitch))
   g0,g1=((max(r[1],R[1])//G,(min(r[3],R[3])-1)//G) if vert else (max(r[0],R[0])//G,(min(r[2],R[2])-1)//G))
   for gg in range(g0,g1+1):
    for t in range(tr0,tr1+1):use[j,gg].add(t)
 rows=[]
 for (j,gg),tt in use.items():
  R=soft[j];vert=(R[3]-R[1])>(R[2]-R[0]);cap=((R[2]-R[0]) if vert else (R[3]-R[1]))//pitch
  rows.append([int(j),int(gg),len(tt),int(cap),round(len(tt)/max(int(cap),1),4)])
 rows.sort(key=lambda q:-q[4])
 s['soft_charge']=dict(layer=a.soft_block_layer,soft_stripes=len(soft),charged_stripe_gcells=len(rows),max_use=rows[0][4] if rows else 0,over_0p6=sum(q[4]>0.6 for q in rows),tracks_used=sum(q[2] for q in rows),top=rows[:10],note='use = distinct PG tracks on the stripe within one 10.8-um gcell / stripe tracks')
json.dump(s,open(out/'summary.json','w'),indent=2);print(s,flush=True)
