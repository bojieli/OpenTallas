#!/usr/bin/env python3
"""Exact R0 candidate signal-bit Manhattan screening, not routed timing.
Uses closed bank assignment and actual relay local pin options. No clock/PG,
no unknown FSR/return pins are invented. Failing candidate stays unadopted.
"""
import json,collections,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 layout=json.loads((R/('physical/s81_die_pins/v20_vm_static_small_groups/layout_option.json' if '--small' in sys.argv else 'physical/s81_die_pins/v20_vm_static_local_groups/layout_option.json')).read_text());nodes={n['name']:n for n in layout['nodes']}
 pins={'dsfd_vm_static_bank128':json.loads((R/'physical/s81_die_pins/v20_vm_static_standard/dsfd_vm_static_bank128.json').read_text())}
 for n in [4,8,16]:
  k=f'dsfd_vm_static_relay128_b{n}';pins[k]=json.loads((R/f'physical/s81_die_pins/v20_vm_static_transport_options/{k}.json').read_text())
 def loc(inst,port,bit):
  n=nodes[inst];f,ly,c,depth=pins[n['master']]['ports'][port]['per_bit'][bit];x,y=n['xy_um'];w,h=n['outline_um'];return (x+depth/2 if f=='W' else x+w-depth/2 if f=='E' else x+c,y+depth/2 if f=='S' else y+h-depth/2 if f=='N' else y+c)
 stats={};worst=[]
 def connect(kind,a,ap,ai,b,bp,bi):
  x,y=loc(a,ap,ai);xx,yy=loc(b,bp,bi);l=abs(x-xx)+abs(y-yy);s=stats.setdefault(kind,dict(bits=0,over500=0,max_um=0));s['bits']+=1;s['over500']+=l>500+1e-6;s['max_um']=max(s['max_um'],l)
  if l>500:worst.append(dict(source=f'{a}.{ap}[{ai}]',target=f'{b}.{bp}[{bi}]',manhattan_um=round(l,3)))
 req={'rv':1,'ra':9,'rt':8,'wv':1,'wa':9,'wd':128,'wm':4,'wt':8};rsp={'sv':('o_rv',1),'sd':('o_rd',128),'st':('o_rt',8),'cv':('o_commit',1),'ct':('o_ct',8),'ca':('o_ca',9),'cm':('o_cm',4)}
 for s in range(4):
  for b in range(32):
   q=b//(4 if '--small' in sys.argv else 8);k=b%(4 if '--small' in sys.argv else 8);bank=f'vm_s{s}_bank{b}';quarter=f'vm_s{s}_quarter{q}'
   for p,w in req.items():
    for bit in range(w):connect('quarter_to_bank_request',quarter,'o_'+p,k*w+bit,bank,'i_'+p,bit)
   for p,(bp,w) in rsp.items():
    for bit in range(w):connect('bank_to_quarter_response',bank,bp,bit,quarter,'i_'+p,k*w+bit)
  for q in range(8 if '--small' in sys.argv else 4):
   quarter=f'vm_s{s}_quarter{q}';bridge=f'vm_s{s}_bridge{q//2}';off=(4 if '--small' in sys.argv else 8)*(q%2)
   for p,w in req.items():
    for k in range(4 if '--small' in sys.argv else 8):
     for bit in range(w):connect('bridge_to_quarter_request',bridge,'o_'+p,(off+k)*w+bit,quarter,'i_'+p,k*w+bit)
   for p,(_,w) in rsp.items():
    for k in range(4 if '--small' in sys.argv else 8):
     for bit in range(w):connect('quarter_to_bridge_response',quarter,'o_'+p,k*w+bit,bridge,'i_'+p,(off+k)*w+bit)
 for v in stats.values():v['max_um']=round(v['max_um'],3)
 d=dict(status='REJECT_FOR_NATIVE_ADOPTION' if worst else 'NEEDS_CLOCK_TIMING_AND_MISSING_ENDPOINT_PROOF',scope='exact assigned R0 bank/relay bit geometry only; clock/PG and unknown endpoint pins excluded',stats=stats,worst=sorted(worst,key=lambda e:-e['manhattan_um'])[:100],requirements=['change actual relay face assignment/grouping/orientation or add explicit pin-registered stages and recompile ages','actual quarter/bridge native CTS and boundary phi-R timing','FSR/scatter/return/53writer/capture actual pins/cuts before wholeVM claim'])
 out=R/('results/physical/s81_vm_static_ownership_1015/small_group_pin_reach.json' if '--small' in sys.argv else 'results/physical/s81_vm_static_ownership_1015/local_group_pin_reach.json');out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({'status':d['status'],'stats':stats}))
if __name__=='__main__':main()
