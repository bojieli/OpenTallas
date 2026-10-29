"""Explicit START-only relay sites outside actual hard-core halos.
Clock source paths remain actual measured nodes; proposed relay clock stubs must
be measured after source DB materialization. No clock-tree driver is relocated.
"""
import json,math
from pathlib import Path

def man(a,b):return sum(abs(x-y) for x,y in zip(a,b))
def propose(failed,meta,taps,site):
 out={};xy=meta['node_xy_um']
 for e in failed:
  a=xy[e['fork_node']];cap=taps[e['capture']];b=cap['xy_um']
  # Enumerate real halo corners of the obstructing core; choose two-stage path.
  # Every stage has an eight-FF conservative row envelope, not just a point.
  candidates=[]
  for f in site.forb:
   x0,y0,x1,y1,*_=f
   if not min(a[0],b[0])<x1 or not max(a[0],b[0])>x0:continue
   if not min(a[1],b[1])<y1 or not max(a[1],b[1])>y0:continue
   for edge,y in [('S',math.floor((y0-.81)/.27)*.27),('N',math.ceil((y1+.54)/.27)*.27)]:
    # Outside the core on the launch side, then across its short edge.
    q1x=max(a[0],x1+.54) if a[0]>=(x0+x1)/2 else min(a[0]-8.64,x0-9.18)
    qs=[[round(round(q1x/.054)*.054,6),round(y,6)],
        [round(round(((x0+x1)/2-4.32)/.054)*.054,6),round(y,6)]]
    rects=[[q[0],q[1],q[0]+8.64,q[1]+.27] for q in qs]
    if not all(site.legal((r[0],r[1])) and site.legal((r[2],r[3])) for r in rects):continue
    hops=[man(a,qs[0]),man(qs[0],qs[1]),man(qs[1],b)]
    if max(hops)>390:continue
    cost=sum(hops)
    candidates.append((cost,edge,qs,rects,hops,f))
  if not candidates:raise ValueError('no legal <=390 perimeter route: '+e['port'])
  _,edge,qs,rects,hops,f=min(candidates,key=lambda x:x[0])
  # Alias 0 takes the launch node's clock; alias 1 the capture driving node's
  # clock. These are explicit real source nets, not invented clock taps.
  aliases=[]
  for i,(path,q,r) in enumerate(zip([e['fork_node'],cap['tree_path']],qs,rects)):
   alias=f'st:{path}@qcperimeter{i}_{e["dst"]}'
   if alias in out:raise ValueError('duplicate alias '+alias)
   out[alias]=dict(region=alias,source_path=path,source_cell=meta['node_cell'][path],
     source_xy_um=xy[path],anchor_xy_um=q,conservative_rect_um=r,
     provisional_clock_stub_um=man(q,xy[path]),
     replaced_port=e['port'],perimeter=edge,barrier_rect_um=f[:4],path_hops_um=hops)
   aliases.append(alias)
  out[aliases[0]]['next']=aliases[1];out[aliases[1]]['next']=e['dst']
 return out
if __name__=='__main__':
 import sys
 R=Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251');sys.path.insert(0,str(R/'src407/tools/die_plan'))
 import schema as S,die_trial as D
 p=S.Plan(S.load('/srv/opentallas-scratch2/claude/codex-qc-1029/physical_event/plan_start_native_h800.json'))
 m=json.load(open('/srv/opentallas-scratch2/claude/codex-qc-start-provider-1029/actual26/proof/tap_arrivals_TT.json'))
 taps={t['port']:t for t in m['taps']};failed=[e for e in json.load(open(R/'start_edges.json'))['edges'] if not e['clean_ok']]
 o=propose(failed,m,taps,D.SiteMap(p));(R/'perimeter_geometry.json').write_text(json.dumps(o,indent=1))
 print(json.dumps(dict(stages=len(o),replaced_edges=len(failed),max_clock_stub_um=max(v['provisional_clock_stub_um'] for v in o.values()),max_hop_um=max(max(v['path_hops_um']) for v in o.values()))))
