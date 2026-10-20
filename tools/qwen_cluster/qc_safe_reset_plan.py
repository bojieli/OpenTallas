#!/usr/bin/env python3
"""Price hard two-register reset relay payloads and equal-depth epochs.
Diagnostic mapped coordinates only, not a legal placement or a reset gate.
"""
import argparse,json,math,collections
from pathlib import Path
from qc_safe_graph import ROOT,extract

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--step',type=float,default=777.6);ap.add_argument('--out',required=True);a=ap.parse_args();g=extract();c=g['contract'];nodes=g['reset_nodes'];alias=g['aliases'];oldx=sorted(set(t['at'][0]for t in c['tiles']));cols=[172.8+i*a.step for i in range(4)];W=math.ceil((cols[-1]+457.92+172.8)/43.2-1e-8)*43.2;H=c['outline_um']['h'];knots=sorted([(0,0),(c['outline_um']['w'],W)]+[(x+d,y+d)for x,y in zip(oldx,cols)for d in [0,457.92]])
 def mx(x):
  for(oa,na),(ob,nb)in zip(knots,knots[1:]):
   if oa-1e-5<=x<=ob+1e-5:return na+(x-oa)*(nb-na)/(ob-oa)
  raise ValueError(x)
 def mp(p):return [mx(p[0]),p[1]]
 def res(n):
  while n in alias:n=alias[n]
  return n
 byq={q:n for n,v in nodes.items()for q in v['outputs']};roots={n:p for n,p in g['ports'].items()if n.startswith('rst_c')};pts={n:mp(v['at'])for n,v in nodes.items()};pts.update({n:mp(v['at'])for n,v in roots.items()})
 tiles=[(cols[int(t['inst'][4])],t['at'][1],cols[int(t['inst'][4])]+457.92,t['at'][1]+1166.4)for t in c['tiles']]
 rows=sorted(set(t['at'][1]for t in c['tiles']));chans=[rows[0]/2]+[(rows[i]+1166.4+rows[i+1])/2 for i in range(3)]+[(rows[-1]+1166.4+H)/2]
 cor=[cols[0]/2]+[(cols[i]+457.92+cols[i+1])/2 for i in range(3)]+[(cols[-1]+457.92+W)/2]
 def hits(p,q,b):
  x0,y0,x1,y1=b
  if abs(p[1]-q[1])<1e-8:return y0+1e-5<p[1]<y1-1e-5 and max(p[0],q[0])>x0+1e-5 and min(p[0],q[0])<x1-1e-5
  return x0+1e-5<p[0]<x1-1e-5 and max(p[1],q[1])>y0+1e-5 and min(p[1],q[1])<y1-1e-5
 def route(p,q):
  cand=[[p,(p[0],q[1]),q],[p,(q[0],p[1]),q]]
  cand += [[p,(p[0],y),(q[0],y),q]for y in chans]
  cand += [[p,(x,p[1]),(x,q[1]),q]for x in cor]
  cand += [[p,(p[0],y),(x,y),(x,q[1]),q]for y in chans for x in cor]
  cand += [[p,(x,p[1]),(x,y),(q[0],y),q]for y in chans for x in cor]
  ok=[P for P in cand if all(not hits(u,v,b)for u,v in zip(P,P[1:])for b in tiles)]
  if not ok:return None
  P=min(ok,key=lambda P:sum(abs(u[0]-v[0])+abs(u[1]-v[1])for u,v in zip(P,P[1:])))
  return P
 edges=[];unresolved=[]
 for n,v in nodes.items():
  d=res(v['inputs'][0]);src=byq.get(d,d)
  if src not in pts:unresolved.append((src,n));continue
  P=route(pts[src],pts[n])
  if P is None:unresolved.append((src,n,'route'));continue
  length=sum(abs(u[0]-v[0])+abs(u[1]-v[1])for u,v in zip(P,P[1:]));nh=max(1,math.ceil(length/315))
  edges.append(dict(src=src,dst=n,region=v['region'],route_um=round(length,3),polyline=P,hard_hops=nh,reset_edges=nh*2))
 assert not unresolved,unresolved[:10]
 old={n:0 for n in roots};new=dict(old)
 for _ in range(len(nodes)):
  oldlen=len(old)
  for e in edges:
   if e['dst']not in old and e['src']in old:old[e['dst']]=old[e['src']]+1;new[e['dst']]=new[e['src']]+e['reset_edges']
  if len(old)==oldlen:break
 assert len(old)==len(nodes)+len(roots),(len(old),len(nodes))
 def driver(net):return byq[res(net)]
 consumers=[]
 for n,v in g['nodes'].items():
  if v['bits']<=1:continue
  key='rst_n'if'xstn'in v['kind']else'rsi'if'land_'in v['kind']else None
  if key:
   src=driver(v['ports'][key]);consumers.append(dict(inst=n,kind=v['kind'],driver=src,old_pin_depth=old[src],mapped_new_pin_depth=new[src]))
 for col in range(4):
  for row in range(4):
   src=driver(f'trst_{col}_{row}');consumers.append(dict(inst=f'u_t_{col}_{row}',kind='A0',driver=src,old_pin_depth=old[src],mapped_new_pin_depth=new[src]))
 core=[v for v in consumers if v['kind']not in ['qfd_c_land_w','qfd_c_land_r']];core_depth=max(v['mapped_new_pin_depth']for v in core);assert set(v['old_pin_depth']for v in core)=={19}
 for v in core:v['pad_hops']=(core_depth-v['mapped_new_pin_depth'])//2;v['aligned_new_pin_depth']=core_depth
 lands=[]
 for L in c['landings']['list']:
  pair=[next(v for v in consumers if v['inst']==f'u_land_{L["name"]}_{h}')for h in ['w','r']];target=max(v['mapped_new_pin_depth']for v in pair)
  for v in pair:v['pad_hops']=(target-v['mapped_new_pin_depth'])//2;v['aligned_new_pin_depth']=target
  lands.append(dict(name=L['name'],source_pin_depth=target,receiver_pin_depth=target,local_child_reset_stages=2,G=target+2,R0=target+2,K=2,E=2))
 groups=collections.Counter((v['region'],tuple(v['at']))for v in nodes.values());group_hist=collections.Counter(groups.values());forward_hops=sum(e['hard_hops']for e in edges);padding=sum(v.get('pad_hops',0)for v in consumers)
 out=dict(schema='opentallas.cb16.safe_reset_plan.v1',source=g['source'],diagnostic_only=True,outline_um=dict(w=W,h=H),logical_reset_nodes=len(nodes),existing_groups_by_site=len(groups),group_master_width_hist=dict(group_hist),max_group_width=max(groups.values()),mapped_forward_hops=forward_hops,equal_depth_padding_hops=padding,total_two_stage_relay_hops=forward_hops+padding,added_reset_flops=2*(forward_hops+padding)-len(nodes),A0_xstn_reset_pin_depth=core_depth,old_A0_xstn_depth=19,latest_landing_epoch=max(l['G']for l in lands),landings=lands,consumers=consumers,edges=edges,release_ready=False,blockers=['mapped coordinates are not yet lattice legalized with actual data macros','315um is a route-segmentation target; legal endpoints and clock phases must be verified','co-located control-only padding chain needs explicit storage/hold review; grouping is not an automatic waiver','full fabric/epoch mutant bench and compiler reset-release update required before parent gate'])
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=1)+'\n');print('RESET_PLAN',forward_hops,'forward',padding,'pad hops; resetdepth',19,'->',core_depth,'latestlandingepoch',out['latest_landing_epoch'],'flop_delta',out['added_reset_flops'])
if __name__=='__main__':main()
