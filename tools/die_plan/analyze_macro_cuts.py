"""Necessary routing-cut census from every native placed net; no routing or zero-seam claim."""
import argparse,json,math,collections
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('native');ap.add_argument('out');a=ap.parse_args();d=json.load(open(a.native));mac=d['macros'];outline=d['outline_um'];eps=1e-6

def free_spans(intervals,lo,hi):
 merged=[]
 for x,y in sorted(intervals):
  x,y=max(lo,x),min(hi,y)
  if y<=x:continue
  if merged and x<=merged[-1][1]+eps:merged[-1][1]=max(y,merged[-1][1])
  else:merged.append([x,y])
 gaps=[];last=lo
 for x,y in merged:
  if x>last+eps:gaps.append([last,x])
  last=max(last,y)
 if last<hi-eps:gaps.append([last,hi])
 return gaps

bboxes=[]
for n in d['nets']:
 ps=n['endpoints']
 if ps:bboxes.append((n['net'], min(p['xy_um'][0] for p in ps),min(p['xy_um'][1] for p in ps),max(p['xy_um'][0] for p in ps),max(p['xy_um'][1] for p in ps)))
cuts=[]
for axis in [0,1]:
 values=sorted(set(round((m['rect_um'][axis]+m['rect_um'][axis+2])/2,6) for m in mac))
 for cut in values:
  blocked=[m['rect_um'] for m in mac if m['rect_um'][axis]+eps<cut<m['rect_um'][axis+2]-eps]
  lo,hi=outline[1-axis],outline[3-axis]
  spans=free_spans([(r[1-axis],r[3-axis]) for r in blocked],lo,hi)
  names=[n[0] for n in bboxes if n[axis+1]<cut-eps and n[axis+3]>cut+eps]
  if axis==0:
   layers=[dict(layer='M2',pitch_um=.036,share=.5,spans_um=spans),dict(layer='M4',pitch_um=.048,share=1.,spans_um=spans)]
  else:
   # SRAM OBS M1-M4. M5 stays available above macros, minus PG share.
   layers=[dict(layer='M3',pitch_um=.036,share=.5,spans_um=spans),dict(layer='M5',pitch_um=.048,share=.93,spans_um=[[lo,hi]])]
  cap=sum(math.floor((y-x)/l['pitch_um']+1e-9)*l['share'] for l in layers for x,y in l['spans_um'])
  use=len(names)/cap if cap else (0 if not names else math.inf)
  cuts.append(dict(direction='H' if axis==0 else 'V',axis='x' if axis==0 else 'y',cut_um=cut,demand_nets=len(names),capacity_tracks=cap,use=use,ok=use<=.6,layers=layers,net_names=names))

# Native macro pins must have one track of clear outward escape on their pin edge.
# This establishes immediate geometric escape only, not full detailed-router pin access.
mc={m['name']:m for m in mac};pins={}
for n in d['nets']:
 for p in n['endpoints']:
  if p.get('macro'):pins[(p['inst'],p['pin'])]=p
blocked=[];interior=[]
for key,p in pins.items():
 r=mc[p['inst']]['rect_um'];x,y=p['xy_um'];edge=min([('W',abs(x-r[0])),('E',abs(x-r[2])),('S',abs(y-r[1])),('N',abs(y-r[3]))],key=lambda z:z[1])
 if edge[1]>.5:interior.append(dict(inst=key[0],pin=key[1],xy_um=[x,y],edge_distance_um=edge[1]));continue
 dx,dy={'W':(-1,0),'E':(1,0),'S':(0,-1),'N':(0,1)}[edge[0]]
 px,py=({'W':r[0],'E':r[2]}.get(edge[0],x),{'S':r[1],'N':r[3]}.get(edge[0],y))
 qx,qy=px+dx*.048,py+dy*.048
 hits=[m['name'] for m in mac if m['name']!=key[0] and m['rect_um'][0]+eps<qx<m['rect_um'][2]-eps and m['rect_um'][1]+eps<qy<m['rect_um'][3]-eps]
 if qx<outline[0] or qx>outline[2] or qy<outline[1] or qy>outline[3]:hits.append('outside_core')
 if hits:blocked.append(dict(inst=key[0],pin=key[1],xy_um=[x,y],edge=edge[0],blocked_by=hits))
r=dict(schema='opentallas.macro_cut_demand.v1',native_source=a.native,odb=d['odb'],odb_sha256=d['odb_sha256'],native_nets=len(d['nets']),macro_count=len(mac),signal_layers=['M2','M3','M4','M5'],assumption='SRAM OBS M1-M4; M5 crosses macros; M2/M3 usable share0.5; M5 PG usable share0.93; track use limit0.6. Actual endpoint plane crossings, necessary capacity check only.',cuts=cuts,pin_escape=dict(native_macro_pins=len(pins),immediate_escape_ok=not blocked and not interior,blocked=blocked,non_edge_pins=interior,qualification='one track of outward geometric clearance; full router pin-access unqualified'),bad_cuts=[dict(direction=c['direction'],cut_um=c['cut_um'],use=c['use'],demand_nets=c['demand_nets'],capacity_tracks=c['capacity_tracks']) for c in cuts if not c['ok']],worst_use={dr:max([c['use'] for c in cuts if c['direction']==dr],default=0) for dr in ['H','V']},abutted_block_zero_crossings_claimed=False,routing_qualified=False)
Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:r[k] for k in ['macro_count','native_nets','worst_use','bad_cuts']}));print('PIN_ESCAPE',len(blocked),'blocked',len(interior),'nonedge')
