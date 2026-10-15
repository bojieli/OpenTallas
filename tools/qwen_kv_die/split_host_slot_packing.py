#!/usr/bin/env python3
"""Provisional host-static/station sites inside old PC frames, using closed PC outline."""
import gzip,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'results/arch/qwen_split_feasibility_1013'
source=OUT/'host_requests_snapshot.json'
request=json.loads(source.read_text());req={r['master']:r for r in request['children']}
lef=ROOT/'physical/ref_tile/qkd_ctrl_pc/views/qkd_ctrl_pc/qkd_ctrl_pc.lef'
w,h=map(float,re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',lef.read_text()).groups())
base=json.load(gzip.open(OUT/'system_96_ectl_bindings.json.gz','rt'))
rects=[];slots=[]
for old in base['positions']:
 if old['m']!='qkd_ctrl_pc':rects.append(old);continue
 pc=dict(old);pc.update(w=w,h=h,view='physical/ref_tile/qkd_ctrl_pc/views/qkd_ctrl_pc',status='CLOSED_OUTLINE_ONLY_HOST_OBSERVER_VARIANT_UNCLOSED');rects.append(pc)
 children=[]
 for master,dx,dy in [('qkd_host_static_pc',0.,194.4),('qkd_host_ingest_station',151.2,194.4)]:
  r=req[master];rw,rh=r['outline_request_um'];p=dict(n=old['n']+'_'+master,m=master,x=old['x']+dx,y=old['y']+dy,w=rw,h=rh,status='REQUEST_ONLY_NOT_HARD_VIEW',source=r['source'],source_sha256=r['sha256']);rects.append(p);children.append(p)
 outside=[p['n'] for p in [pc]+children if p['x']<old['x'] or p['y']<old['y'] or p['x']+p['w']>old['x']+old['w']+1e-6 or p['y']+p['h']>old['y']+old['h']+1e-6]
 slots.append(dict(old=old,children=[p['n'] for p in children],outside=outside))
overlap=[]
for j,p in enumerate(rects):
 for q in rects[j+1:]:
  if p['x']<q['x']+q['w']-1e-6 and q['x']<p['x']+p['w']-1e-6 and p['y']<q['y']+q['h']-1e-6 and q['y']<p['y']+p['h']-1e-6:overlap.append([p['n'],q['n']])
result=dict(status='PROVISIONAL_HOST_SITES_IN_RELEASED_PC_FRAME_NOT_PHYSICAL_PROOF',source_request_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),closed_pc_lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),
 pc_sites=len(slots),new_static_sites=len(slots),new_station_sites=len(slots),overlaps=overlap,slot_outside_count=sum(len(s['outside']) for s in slots),combined_envelope_um=[246.24,367.2],positions=rects,slot_checks=slots,
 missing=['Static PC/station outlines are unverified requests, not synthesized fit/CTS or routed views.',
 'Closed PC outline is a lower-bound proxy; new host-observer variant must close and keep the outline.',
 'Actual orientation/pin plans, registered buses, PG phases and all new root clocks require binding.',
 'Per-PC credit/ACK semantics and full saturated native transport benchmark remain required.'])
json.dump(result,gzip.open(OUT/'system_host_sites.json.gz','wt'))
print(json.dumps({k:v for k,v in result.items() if k not in ('positions','slot_checks','missing')},indent=2))
