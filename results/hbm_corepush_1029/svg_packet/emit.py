#!/usr/bin/env python3
"""Emit a density-safe SVG sm_packet proposal without changing any other bit."""
from pathlib import Path
import json, copy, hashlib, argparse
ap=argparse.ArgumentParser();ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
pf=a.plan/'cores/ot_hbm_svc_sm_group_rel_id__776.304x646.92__canon.json'
old=json.loads(pf.read_text());new=copy.deepcopy(old)
packet=sorted([q for q in new if q['name'].startswith('sm_packet[')],key=lambda q:int(q['name'].split('[')[1][:-1]))
assert len(packet)==1099 and all(q['layer']=='M5' and q['y']==.096 for q in packet)
other=[q for q in new if q['layer']=='M5' and q['y']<1 and not q['name'].startswith('sm_packet[')]
occ=[q['x'] for q in other]
# Compact band centred around old packet, four-track pitch; other pins are fixed.
x=.024+round((277.032-.024)/.048)*.048
for q in packet:
    while any(abs(x-z)<.096-1e-8 for z in occ):
        x+=.192
    q['x']=round(x,6)
    x+=.192
assert all(u==v for u,v in zip(old,new) if not u['name'].startswith('sm_packet['))
q=sorted([z['x'] for z in new if z['layer']=='M5' and z['y']<1]);best=0;j=0
for i,z in enumerate(q):
    while q[j]<z-10+1e-9:
        j+=1
    best=max(best,i-j+1)
assert best<=60
assert all(abs((q['x']-.024)/.048-round((q['x']-.024)/.048))<1e-7 for q in packet)
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'pins.json').write_text(json.dumps(new,indent=1)+'\n')
delta=[dict(name=u['name'],old_x_um=u['x'],new_x_um=v['x'],delta_x_um=round(v['x']-u['x'],6)) for u,v in zip(old,new) if u!=v]
d=json.loads((a.plan/'die_plan.json').read_text())
instances=[dict(type=t,inst=h['inst'],origin_um=h['origin_um'],orient=h.get('orient','R0'),outline_um=h['outline_um']) for t,v in d['partition_types'].items() for h in v.get('hard_cores',[]) if h['module']=='ot_hbm_svc_sm_group_rel_id']
report=dict(classification='CANDIDATE currentpin-onlyfix; noSIGNEDview/physicalbuild/adoption',source_pins_sha256=hashlib.sha256(pf.read_bytes()).hexdigest(),new_pins_sha256=hashlib.sha256((a.out/'pins.json').read_bytes()).hexdigest(),pins=len(new),changed=len(delta),unchanged=len(new)-len(delta),bus='sm_packet[1098:0]',old_span_um=[min(q['old_x_um'] for q in delta),max(q['old_x_um'] for q in delta)],new_span_um=[min(q['new_x_um'] for q in delta),max(q['new_x_um'] for q in delta)],South_M5_peak_10um=best/10,max_shift_um=max(abs(q['delta_x_um']) for q in delta),clock_reset_source_outline_cycles_changed=False,native_bitorder_preserved=True,instances=instances,before_PNR=['Planowner recomposes all actualsource packetendpoint/stationpaths attheseexactpins','Freshgeneration+actualsourcebind andphysicalview required; oldSIGNEDproof notinherited'],delta=delta)
(a.out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('instances','delta')}))
