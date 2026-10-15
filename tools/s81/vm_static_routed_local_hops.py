#!/usr/bin/env python3
"""Per-bit local-hop construction check using actual routed dual-root ETMs.
This diagnostic retains the unchanged old188 bank/relay microcluster coordinates.
It is not extracted die STA and never authorizes rerouting a CLOSED source.
"""
import json,collections,sys,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 import argparse
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--relay-kit',default='native_option',help='relay kit suffix whose CLOSED views are composed (native_option | native_cb)')
 ap.add_argument('--out',default='results/physical/s81_vm_static_ownership_1015/routed_local_hops.json')
 ap.add_argument('--left-bank-profile',choices=['standard','E'],default='standard',help='E: every bank LEFT of its quarter uses dsfd_vm_static_bank128_E (signal-face mirror pins, v20_vm_static_bank_e)')
 ap.add_argument('--bank-e-views',default='physical/ref_tile/dsfd_vm_static_bank128_e_m4_v20/views/dsfd_vm_static_bank128_E',help='routed E-profile views; when absent the standard bank ETM is used and the result is labelled PREDICTED')
 a=ap.parse_args()
 sys.path.insert(0,str(R/"tools/hier_contract"));import pinreg_audit as P
 viewdirs={"dsfd_vm_static_bank128":R/"physical/ref_tile/dsfd_vm_static_bank128_m4_v20/views/dsfd_vm_static_bank128",**{f"dsfd_vm_static_relay128_b{n}":R/f"physical/ref_tile/dsfd_vm_static_relay128_b{n}_{a.relay_kit}/views/dsfd_vm_static_relay128_b{n}" for n in [4,8]}}
 predicted=False
 if a.left_bank_profile=='E':
  ev=R/a.bank_e_views
  if not (ev/'insertion.json').exists():ev=viewdirs['dsfd_vm_static_bank128'];predicted=True
  viewdirs['dsfd_vm_static_bank128_E']=ev
 metrics={};provenance={}
 for master,d in viewdirs.items():
  ins=json.loads((d/"insertion.json").read_text());metrics[master]={};provenance[master]={}
  for corner in ["tt","ff"]:
   path=next(d.glob(f"*_{corner}.lib"));lib=P.parse_lib(path);refs=P.clock_refs(lib,ins,corner);metrics[master][corner]=P.pin_metrics(lib,refs);provenance[master][corner]={"lib":str(path.relative_to(R)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"refs":refs}
 layout=json.loads((R/'physical/s81_die_pins/v20_vm_static_small_groups/layout_option.json').read_text());nodes={n['name']:n for n in layout['nodes']}
 pins={'dsfd_vm_static_bank128':json.loads((R/'physical/s81_die_pins/v20_vm_static_standard/dsfd_vm_static_bank128.json').read_text())}
 if a.left_bank_profile=='E':
  pins['dsfd_vm_static_bank128_E']=json.loads((R/'physical/s81_die_pins/v20_vm_static_bank_e/dsfd_vm_static_bank128_E.json').read_text())
  for nm,nd in list(nodes.items()):
   if nd['master']=='dsfd_vm_static_bank128':
    qn=nm.split('_bank')[0]+f"_quarter{int(nm.split('_bank')[1])//4}"
    if nd['xy_um'][0]+nd['outline_um'][0]<=nodes[qn]['xy_um'][0]:nodes[nm]=dict(nd,master='dsfd_vm_static_bank128_E')
 for n in [4,8,16]:
  k=f'dsfd_vm_static_relay128_b{n}';pins[k]=json.loads((R/f'physical/s81_die_pins/v20_vm_static_transport_options/{k}.json').read_text())
 def loc(inst,port,bit):
  n=nodes[inst];f,ly,c,depth=pins[n['master']]['ports'][port]['per_bit'][bit];x,y=n['xy_um'];w,h=n['outline_um'];return (x+depth/2 if f=='W' else x+w-depth/2 if f=='E' else x+c,y+depth/2 if f=='S' else y+h-depth/2 if f=='N' else y+c)
 stats={};worst=[];timing_worst=[];missing=[]
 def connect(kind,a,ap,ai,b,bp,bi):
  x,y=loc(a,ap,ai);xx,yy=loc(b,bp,bi);l=abs(x-xx)+abs(y-yy);s=stats.setdefault(kind,dict(bits=0,over500=0,max_um=0));s['bits']+=1;s['over500']+=l>500+1e-6;s['max_um']=max(s['max_um'],l)
  if l>500:worst.append(dict(source=f'{a}.{ap}[{ai}]',target=f'{b}.{bp}[{bi}]',manhattan_um=round(l,3)))
  an=f'{ap}[{ai}]' if pins[nodes[a]['master']]['ports'][ap]['bits']>1 else ap
  bn=f'{bp}[{bi}]' if pins[nodes[b]['master']]['ports'][bp]['bits']>1 else bp
  # Actual exported per-pin arcs and clock-domain-specific boundary references.
  at=metrics[nodes[a]['master']]['tt'].get(an);bt=metrics[nodes[b]['master']]['tt'].get(bn)
  af=metrics[nodes[a]['master']]['ff'].get(an);bf=metrics[nodes[b]['master']]['ff'].get(bn)
  if at is None or bt is None or at['out'] is None or bt['inp'] is None:
   missing.append(dict(source=f'{a}.{an}',target=f'{b}.{bn}'));return
  slack=833.333-60-90-(at['out']+.76*l+bt['inp'])
  hold=af['lmin']-bf['hold']-100 if af and bf and af['lmin'] is not None and bf['hold'] is not None else None
  s['setup_fail_bits']=s.get('setup_fail_bits',0)+(slack<0);s['min_setup_slack_ps']=min(s.get('min_setup_slack_ps',1e9),slack)
  s['max_launch_residual_ps']=max(s.get('max_launch_residual_ps',0),at['out']);s['max_capture_residual_ps']=max(s.get('max_capture_residual_ps',0),bt['inp'])
  s['launch_over220_bits']=s.get('launch_over220_bits',0)+(at['out']>220);s['capture_over190_bits']=s.get('capture_over190_bits',0)+(bt['inp']>190)
  if hold is not None:s['min_hold_reserve_no_wire_credit_ps']=min(s.get('min_hold_reserve_no_wire_credit_ps',1e9),hold)
  if slack<0:timing_worst.append(dict(source=f'{a}.{an}',target=f'{b}.{bn}',um=round(l,3),launch_ps=round(at['out'],3),capture_ps=round(bt['inp'],3),setup_slack_ps=round(slack,3),source_clock=at['clk'],target_clock=bt['clk']))

 req={'rv':1,'ra':9,'rt':8,'wv':1,'wa':9,'wd':128,'wm':4,'wt':8};rsp={'sv':('o_rv',1),'sd':('o_rd',128),'st':('o_rt',8),'cv':('o_commit',1),'ct':('o_ct',8),'ca':('o_ca',9),'cm':('o_cm',4)}
 for s in range(4):
  for b in range(32):
   q=b//4;k=b%4;bank=f'vm_s{s}_bank{b}';quarter=f'vm_s{s}_quarter{q}'
   for p,w in req.items():
    for bit in range(w):connect('quarter_to_bank_request',quarter,'o_'+p,k*w+bit,bank,'i_'+p,bit)
   for p,(bp,w) in rsp.items():
    for bit in range(w):connect('bank_to_quarter_response',bank,bp,bit,quarter,'i_'+p,k*w+bit)
  for q in range(8):
   quarter=f'vm_s{s}_quarter{q}';bridge=f'vm_s{s}_bridge{q//2}';off=4*(q%2)
   for p,w in req.items():
    for k in range(4):
     for bit in range(w):connect('bridge_to_quarter_request',bridge,'o_'+p,(off+k)*w+bit,quarter,'i_'+p,k*w+bit)
   for p,(_,w) in rsp.items():
    for k in range(4):
     for bit in range(w):connect('quarter_to_bridge_response',quarter,'o_'+p,k*w+bit,bridge,'i_'+p,(off+k)*w+bit)
 for v in stats.values():
  for k,x in v.items():
   if isinstance(x,float):v[k]=round(x,3)
 d=dict(schema='opentallas.s81.actual-routed-local-hop-diagnostic.v1',tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),status='REJECT_NATIVE_ADOPTION' if timing_worst or missing or worst else 'LOCAL_SETUP_PASS_GLOBAL_AND_EXTRACTED_DIE_OPEN',scope='83712 bank-quarter-bridge endpoint bits in old188 local template; proposed328 retains these microcluster relative pins; real clock-domain-specific TT/FF exported arcs, phase compensated per measured boundary R. Linear .76ps/um TT wire is a construction model, not extracted die STA.',rule=dict(T_ps=833.333,setup_unc_ps=60,skew_ps=90,wire_ps_per_um=.76,hold_reserve_ps=100,hold_wire_credit_ps=0),left_bank_profile=a.left_bank_profile,bank_e_timing='PREDICTED: standard bank routed ETM with E-profile pin geometry (same RTL leaf, mirrored faces)' if predicted else ('routed E-profile views' if a.left_bank_profile=='E' else None),left_e_banks=sum(n['master']=='dsfd_vm_static_bank128_E' for n in nodes.values()),stats=stats,missing_arcs=missing[:100],missing_arc_count=len(missing),over500=worst[:100],worst_setup=sorted(timing_worst,key=lambda e:e['setup_slack_ps'])[:100],view_provenance=provenance,limits=['CLOSED leaf route stands; this diagnostic is no reroute authorization','Classify actual launch residual vs export-source reference before native structural repair','No global cap/CDC/FSR/return/writeedge geometry, no load/slew sweep or extracted die timing','FF reserve uses no minimum wire credit; no FF wire estimate invented'])
 out=R/a.out;out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(status=d['status'],stats=stats,missing=len(missing))))
if __name__=='__main__':main()
