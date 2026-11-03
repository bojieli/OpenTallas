"""PREP only: row/site quantization of the actual-graph zero-cycle LP."""
import sys,json,math,bisect,re,collections,csv
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];sys.path.insert(0,str(R/'tools/autopilot'))
import geom_rules as G
D=G.Design('/srv/opentallas-scratch/claude/codex-kv-ctl-place-2330/collector/geom.tsv',[str(O/'memory_tt.lib')],True)
p=json.load(open(O/(sys.argv[1] if len(sys.argv)>1 else 'joint_repack_keepout2.json')));assert p['success']
byname={c[6]:i for i,c in D.cells.items()};pins={x['name']:x for x in D.pins};macros=[c for c in D.cells.values() if c[0]=='M'];occupied=collections.defaultdict(list);poses={};fail=[];maxshift=0
RH=.27;SW=.054;X0=Y0=4.32;X1=Y1=367.2;radius=float(sys.argv[2]) if len(sys.argv)>2 else 4.5

def blocked_geometry(x,y,cw,ch):
 if x-cw/2<X0-1e-7 or x+cw/2>X1+1e-7 or y-ch/2<Y0-1e-7 or y+ch/2>Y1+1e-7:return True
 return any(x+cw/2>c[2] and x-cw/2<c[4] and y+ch/2>c[3] and y-ch/2<c[5] for c in macros) or (x+cw/2>181.4 and x-cw/2<190.44 and y+ch/2>181.4 and y-ch/2<190.44)
def reserve(name,x,y,cw,ch):
 row=round((y-ch/2-Y0)/RH);a=x-cw/2;b=x+cw/2
 ins=occupied[row];j=bisect.bisect_left(ins,(a,))
 assert not(j and ins[j-1][1]>a+1e-6) and not(j<len(ins) and ins[j][0]<b-1e-6),(name,'FF overlap')
 bisect.insort(ins,(a,b,name));poses[name]=(x,y)
def subtract(allowed,block):
 out=[]
 for a,b in allowed:
  left=a
  for c,d in sorted(block):
   if d<=left:continue
   if c>=b:break
   if c>left:out.append((left,min(b,c)))
   left=max(left,d)
  if left<b:out.append((left,b))
 return out
# Exact deterministic fixed tapcells from the reused floorplan checkpoint.
taps=[r for r in csv.DictReader(open('/srv/opentallas-scratch/claude/codex-kv-ctl-place-2330/collector/placed.csv')) if r['kind']=='tap']
for t in taps:
 tx,ty,tw,th=map(float,(t['x'],t['y'],t['w'],t['h']))
 assert abs(th-RH)<1e-5
 row=round((ty-Y0)/RH);bisect.insort(occupied[row],(tx,tx+tw,'TAP:'+t['name']))
points=p['points'];changed=[]
for q in points:
 c=D.cells[byname[q['name']]];cw,ch=c[4]-c[2],c[5]-c[3];x,y=q['new_xy'];ox,oy=q['old_xy'];assert abs(ch-RH)<1e-5,(q['name'],ch)
 if abs(x-ox)+abs(y-oy)<1e-5 and not blocked_geometry(ox,oy,cw,ch):reserve(q['name'],ox,oy,cw,ch)
 else:changed.append(q)
# Public anchors have the narrowest regions; preserve their placement first.
changed.sort(key=lambda q:(not bool(q['public_anchors']),-len(q['public_anchors']),q['name']))
for q in changed:
 c=D.cells[byname[q['name']]];cw,ch=c[4]-c[2],c[5]-c[3];tx,ty=q['new_xy'];pub=[pins[a['pin']] for a in q['public_anchors']];candidates=[]
 low=max(0,math.ceil((ty-radius-ch/2-Y0)/RH));high=math.floor((ty+radius-ch/2-Y0)/RH)
 for row in range(low,high+1):
  y=Y0+row*RH+ch/2;dy=abs(y-ty);left=max(X0+cw/2,tx-radius+dy);right=min(X1-cw/2,tx+radius-dy)
  for pin in pub:
   dx=150-abs(y-pin['y']);left=max(left,pin['x']-dx);right=min(right,pin['x']+dx)
  if left>right:continue
  blocks=[(a-cw/2-.00001,b+cw/2+.00001) for a,b,n in occupied[row]]
  for m in macros:
   if y+ch/2>m[3] and y-ch/2<m[5]:blocks.append((m[2]-cw/2-.00001,m[4]+cw/2+.00001))
  if y+ch/2>181.4 and y-ch/2<190.44:blocks.append((181.4-cw/2-.00001,190.44+cw/2+.00001))
  for a,b in subtract([(left,right)],blocks):
   k0=math.ceil((a-cw/2-X0)/SW-1e-8);k1=math.floor((b-cw/2-X0)/SW+1e-8)
   if k0>k1:continue
   k=max(k0,min(k1,round((tx-cw/2-X0)/SW)));x=X0+k*SW+cw/2
   if not blocked_geometry(x,y,cw,ch):candidates.append((abs(x-tx)+dy,x,y))
 if not candidates:fail.append(q['name']);continue
 shift,x,y=min(candidates);maxshift=max(maxshift,shift);reserve(q['name'],x,y,cw,ch)
report=dict(scope='PREP mathematical FF plan; existing logic/clock/reset connectivity, cycles, pins, macros and source unchanged; no P&R executed',LP=p.get('reach_target'),public_LP=p.get('public_target'),FFs=len(points),unchanged=len(points)-len(changed),relocated=len(changed),failed=len(fail),failed_names=fail,max_quantization_L1=maxshift,grid_um=[SW,RH])
if not fail:
 public_dist=collections.defaultdict(list)
 for q in points:
  name=q['name'];cid=byname[name];c=D.cells[cid];cw,ch=c[4]-c[2],c[5]-c[3];x,y=poses[name];D.cells[cid]=(c[0],c[1],x-cw/2,y-ch/2,x+cw/2,y+ch/2,c[6])
  for a in q['public_anchors']:
   pin=pins[a['pin']];public_dist[a['pin']].append(abs(x-pin['x'])+abs(y-pin['y']))
 report['R2R']=G.r2r_metrics(D);report['pin_data_max_all_captures']=max(max(v) for v in public_dist.values());report['pin_data_p90_nearest']=G.q([min(v) for v in public_dist.values()],.9);report['pin_data_distinct_over30']=sum(min(v)>30+1e-6 for v in public_dist.values());report['pose_count']=len(poses)
 data=[dict(name=q['name'],master=D.cells[byname[q['name']]][1],old_xy=q['old_xy'],center_xy=list(poses[q['name']]),ll_xy=[D.cells[byname[q['name']]][2],D.cells[byname[q['name']]][3]],outline_um=[D.cells[byname[q['name']]][4]-D.cells[byname[q['name']]][2],D.cells[byname[q['name']]][5]-D.cells[byname[q['name']]][3]]) for q in points]
 (O/'repack_legal_poses.json').write_text(json.dumps(data,indent=1)+'\n')
(O/'legalize_repack.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
