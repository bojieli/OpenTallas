import pickle,json,re,math
from pathlib import Path
B=Path(__file__).parent
D=pickle.load(open(B/'ACTUAL_PRE_MODEL.pkl','rb'))
C=Path('/srv/opentallas-scratch/claude/mu-die-qw/dv2f21g5r6b/out/case')
sizes={};cur=None
for l in (C/'elements.lef').open():
 q=re.match(r'MACRO (\S+)',l)
 if q:cur=q[1]
 q=re.match(r'\s*SIZE ([\d.]+) BY ([\d.]+)',l)
 if q:sizes[cur]=tuple(map(float,q.groups()))
masters={}
for l in (C/'die.v').open():
 q=re.match(r'\s*(\w+)\s+(\w+)\s*\(',l)
 if q and q[1] in sizes:masters[q[2]]=q[1]
frames={}
for l in (C/'place.tcl').open():
 q=re.search(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)',l)
 if q:
  n,x,y,o=q.groups();w,h=sizes[masters[n]]
  if o in ('R90','R270','MXR90','MYR90'):w,h=h,w
  frames[n]=(float(x),float(y),w,h)
for i in D['insts']:
 if i['name'].startswith('flt_root_'):frames[i['name']]=(i['x'],i['y'],i['w'],i['h'])
by={i['name']:i for i in D['insts']};R=D['fault']['roots'];E={e['bid']:e for e in D['fault']['edges']};bus={b[0]:b for b in D['buses']}
fin=json.load(open(B/'CAPTURE_MODEL.json'))['leaves'][0]['native_input_xy']
def point(ep):
 i=by[ep[0]];p=ep[1]
 off=(21.504,10.812) if p=='o' else fin[int(p[1:])]
 return (i['x']+off[0],i['y']+off[1])
def collision(r,fs):
 x,y,w,h=r
 return [n for n,(a,b,c,d) in fs if x<a+c-.0001 and a<x+w-.0001 and y<b+d-.0001 and b<y+h-.0001]
def sweep(P0,P1,w,h):
 # Sufficient reach bound for every point on frame, stronger than any actual scalar face pin.
 radius=405-(w+h)/2-.1
 near=[(n,r) for n,r in frames.items() if r[0]<max(P0[0],P1[0])+405 and r[0]+r[2]>min(P0[0],P1[0])-405 and r[1]<max(P0[1],P1[1])+405 and r[1]+r[3]>min(P0[1],P1[1])-405]
 ys=range(math.ceil((max(P0[1],P1[1])-radius-h/2)/2.16),math.floor((min(P0[1],P1[1])+radius-h/2)/2.16)+1)
 count=0
 for yi in sorted(ys,key=lambda q:abs(q*2.16+h/2-(P0[1]+P1[1])/2)):
  y=round(yi*2.16,3);lo=-1e9;hi=1e9
  for px,py in [P0,P1]:
   rr=radius-abs(y+h/2-py);lo=max(lo,px-rr-w/2);hi=min(hi,px+rr-w/2)
  if lo>hi:continue
  blocked=sorted((a-w,a+c) for n,(a,b,c,d) in near if y<b+d-.0001 and b<y+h-.0001)
  cursor=lo;gaps=[]
  for a,b in blocked:
   if b<cursor:continue
   if a>hi:break
   if a>=cursor:gaps.append((cursor,min(a,hi)))
   cursor=max(cursor,b)
  if cursor<=hi:gaps.append((cursor,hi))
  for a,b in gaps:
   x=math.ceil((a+1e-6)/.432)*.432
   if x>b-1e-6:continue
   r=(round(x,3),y,w,h)
   if collision(r,near):continue
   count+=1
   return dict(frame=r,all_frame_point_reach_bound=max(abs(x+w/2-p[0])+abs(y+h/2-p[1])+(w+h)/2 for p in [P0,P1]),overlap=[],nearby_frames=len(near))
 return None
out=dict(scope='actual candidate PRE roots; baseline r6b actual data/reset frames plus candidate roots, conservative reference only; no final GEN or reset/clock/native claim',frame_count=len(frames),edges=[])
for bid in ['flt_t_d2d_rom_g5','flt_t_d2d_rom_g4']:
 if bid not in E:out['edges'].append(dict(bid=bid,absent=True));continue
 eps=bus[bid][3];P0,P1=map(point,eps);edge=dict(bid=bid,tree=E[bid],eps=eps,P0=P0,P1=P1,actual_direct_um=sum(abs(a-b) for a,b in zip(P0,P1)))
 edge['generic65x30']=sweep(P0,P1,64.8,30.24)
 edge['fault21x21']=sweep(P0,P1,21.6,21.6)
 out['edges'].append(edge)
print(json.dumps(out,indent=2));(B/'ROOT_MODEL.json').write_text(json.dumps(out,indent=2))
