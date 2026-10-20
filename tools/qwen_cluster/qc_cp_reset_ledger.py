#!/usr/bin/env python3
"""Diagnostic last-mile reset ledger for separately placed physical landing halves.
Reset relay points are inherited mapped sites; no reset placement/route qualification.
"""
import argparse,json,math,hashlib
from pathlib import Path
from qc_safe_graph import extract,ROOT
p=argparse.ArgumentParser();p.add_argument('witness');p.add_argument('--reset-plan',required=True);p.add_argument('--pin-plan',required=True);p.add_argument('--mut-offset',action='store_true');p.add_argument('--out',required=True);a=p.parse_args();raw=Path(a.witness).read_bytes();d=json.loads(raw);reset=json.loads(Path(a.reset_plan).read_text());pinplan=json.loads(Path(a.pin_plan).read_text());g=extract();assert d['outline_um']==reset['outline_um'];placed={v['inst']:v for v in d['placement']};reset_points={e['dst']:e['polyline'][-1]for e in reset['edges']};assets={}
for master,v in pinplan['native_pin_assets'].items():
 asset=(ROOT/v['path']).read_bytes();assert hashlib.sha256(asset).hexdigest()==v['sha256'];assets[master]=json.loads(asset)['pins']
cols=[172.8+i*777.6 for i in range(4)];H=d['outline_um']['h'];W=d['outline_um']['w'];tiles=[(cols[int(t['inst'][4])],t['at'][1],cols[int(t['inst'][4])]+457.92,t['at'][1]+1166.4)for t in g['contract']['tiles']];rows=sorted(set(t['at'][1]for t in g['contract']['tiles']));ys=[rows[0]/2]+[(rows[i]+1166.4+rows[i+1])/2 for i in range(3)]+[(rows[-1]+1166.4+H)/2];xs=[cols[0]/2]+[(cols[i]+457.92+cols[i+1])/2 for i in range(3)]+[(cols[-1]+457.92+W)/2]
def hits(p,q,b):
 x0,y0,x1,y1=b
 if abs(p[1]-q[1])<1e-8:return y0+1e-5<p[1]<y1-1e-5 and max(p[0],q[0])>x0+1e-5 and min(p[0],q[0])<x1-1e-5
 return x0+1e-5<p[0]<x1-1e-5 and max(p[1],q[1])>y0+1e-5 and min(p[1],q[1])<y1-1e-5

def route(p,q):
 cand=[[p,(p[0],q[1]),q],[p,(q[0],p[1]),q]]+[[p,(p[0],y),(q[0],y),q]for y in ys]+[[p,(x,p[1]),(x,q[1]),q]for x in xs]+[[p,(p[0],y),(x,y),(x,q[1]),q]for y in ys for x in xs]+[[p,(x,p[1]),(x,y),(q[0],y),q]for x in xs for y in ys]
 ok=[v for v in cand if all(not hits(p,q,b)for p,q in zip(v,v[1:])for b in tiles)];assert ok,(p,q)
 return min(ok,key=lambda v:sum(abs(p[0]-q[0])+abs(p[1]-q[1])for p,q in zip(v,v[1:])))
cons=[]
for old in reset['consumers']:
 kind=old['kind'];n=old['inst'];parts=[0,1]if kind.startswith('qfd_c_land_')else[None]
 for part in parts:
  physical=n+f'_p{part}'if part is not None else n;v=dict(inst=physical,logical=n,kind=kind,part=part,driver=old['driver'],graph_pin_depth=old['mapped_new_pin_depth'],lastmile_relays=0)
  if kind=='A0':v.update(lastmile_qualified=False,unqualified_reason='NO selected A0 reset pin/native reset face contract',lastmile_route_um=None,reset_face_stages=None)
  else:
   if part is not None:
    width=int(g['nodes'][n]['ports']['W'])//2;master=f'qfd_c_land_{kind[-1]}{width}_narrow';port='rsi'
   else:master=kind+'_safe';port='rst_n'
   pin=assets[master][port];assert len(pin['centers_um'])==1;target=[x+y for x,y in zip(placed[physical]['at'],pin['centers_um'][0])];P=route(reset_points[old['driver']],target);length=sum(abs(p[0]-q[0])+abs(p[1]-q[1])for p,q in zip(P,P[1:]));extra=max(0,math.ceil(length/315-1e-10)-1)
   v.update(native_master=master,native_reset_pin=port,native_pin_position_um=target,lastmile_qualified=False,lastmile_scope='A0-obstacle route only; data-child obstructions/relay locations/clock phases NOT legalized',lastmile_route_um=length,lastmile_polyline=P,lastmile_relays=extra,reset_face_stages=2)
  v['pre_alignment_pin_edge']=v['graph_pin_depth']+2*v['lastmile_relays'];cons.append(v)
by={v['inst']:v for v in cons};lands=[]
for idx,L in enumerate(g['contract']['landings']['list']):
 members=[by[f'u_land_{L["name"]}_{h}_p{part}']for h in ['w','r']for part in [0,1]];target=max(v['pre_alignment_pin_edge']for v in members)
 for v in members:
  v['alignment_pad_hops']=(target-v['pre_alignment_pin_edge'])//2;v['release_pin_edge']=target+(1 if a.mut_offset and idx==0 and v['inst'].endswith('_r_p0')else 0);v['local_reset_state_edge']=v['release_pin_edge']+2;v['first_active_edge']=v['local_reset_state_edge']+1
 epochs={v['inst'].rsplit('_',2)[-2]+'_'+str(v['part']):v['local_reset_state_edge']for v in members};lands.append(dict(landing=L['name'],epochs=epochs,effective_E_per_part=[2+members[2+i]['local_reset_state_edge']-members[i]['local_reset_state_edge']for i in [0,1]],equal_all_four_epochs=len(set(epochs.values()))==1))
core=[v for v in cons if v['kind']in ['A0','qfd_c_xstn','qfd_c_xstnw']];core_target=max(v['pre_alignment_pin_edge']for v in core)
for v in core:
 v['alignment_pad_hops']=(core_target-v['pre_alignment_pin_edge'])//2;v['release_pin_edge']=core_target;v['local_reset_state_edge']=None if v['reset_face_stages']is None else core_target+v['reset_face_stages']
lastmile=sum(v['lastmile_relays']for v in cons);padding=sum(v['alignment_pad_hops']for v in cons);latest=max(v['local_reset_state_edge']for v in cons if v['local_reset_state_edge']is not None);ok=all(v['equal_all_four_epochs']and v['effective_E_per_part']==[2,2]for v in lands)
out=dict(schema='opentallas.cb16.cp_reset_ledger.v1',diagnostic_only=True,release_ready=False,witness_sha256=hashlib.sha256(raw).hexdigest(),reset_plan_sha256=hashlib.sha256(Path(a.reset_plan).read_bytes()).hexdigest(),physical_consumers=len(cons),unqualified_A0_consumers=sum(v['kind']=='A0'for v in cons),all_four_epoch_pass=ok,landing_groups=lands,consumers=cons,mapped_forward_hops=reset['mapped_forward_hops'],new_lastmile_relays=lastmile,independent_branch_padding_hops=padding,serial_reset_flops=2*(reset['mapped_forward_hops']+lastmile+padding),old_logical_model_reset_flops=2*reset['total_two_stage_relay_hops'],known_consumer_latest_reset_state_edge=latest,known_consumer_boot_guard_lower_bound=latest+4+74,core_pin_alignment_lower_bound=core_target,boot_guard_scope='For this explicit serial reset construction only; A0 unknowns remain. Not a universal route/schedule minimum.',blockers=['No selected A0 reset pin/native face contract; cannot certify complete reset epoch or boot bound','Mapped old reset relay sites not legalized alongside CP data macros','Last-mile routes avoid A0 only; data-child obstructions/actual <=315 segments and reset package pin loads unqualified','Independent branch padding is explicit serial model cost, not selected minimum hardware','No parent clock phases/reserve/absolute-age proof; full parent MUT8/compiler replay required for any adopted composition'])
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print('CP_RESET_LEDGER',ok,len(cons),'consumers','resetFF',out['serial_reset_flops'],'latestKnown',latest,'bootLowerBound',latest+78);raise SystemExit(not ok)
