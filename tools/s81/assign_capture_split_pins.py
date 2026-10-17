#!/usr/bin/env python3
"""Snap explicit R0 capture variant pin requests; actual export/PG/native gates stay owed."""
import argparse
import hashlib
import json
from pathlib import Path

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--geometry',required=True)
ap.add_argument('--out',required=True)
a=ap.parse_args();src=Path(a.geometry);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
d=json.loads(src.read_text());masters={}
for instance,row in d['children'].items():
    if not any('proposed' in p['status'] for p in row['pins'].values()):continue
    master=row['master'];signature=(row['outline_um'],{n:(p['layer'],p['local_xy_um'])for n,p in row['pins'].items()})
    if master in masters and masters[master]['signature']!=signature:
        raise ValueError('Same master has different literal pin maps: '+master)
    masters.setdefault(master,dict(signature=signature,instances=[],source=row));masters[master]['instances'].append(instance)
receipts={}
for master,rec in masters.items():
    row=rec['source'];w,h=row['outline_um'];pins={};occupied={};lines=['# Candidate-only explicit R0 variant pin assignment.', '# Actual exported contacts, PG access, all incident paths, native clocks and calendars require qualification.']
    for name,p in sorted(row['pins'].items()):
        x,y=p['local_xy_um'];layer=p['layer'];faces=[]
        if abs(x)<1e-6:faces.append('W')
        if abs(x-w)<1e-6:faces.append('E')
        if abs(y)<1e-6:faces.append('S')
        if abs(y-h)<1e-6:faces.append('N')
        if len(faces)!=1:raise ValueError((master,name,'not one literal boundary face',faces))
        face=faces[0];ns=face in 'NS'
        if (ns and layer not in ('M3','M5'))or(not ns and layer!='M4'):
            raise ValueError((master,name,'unsupported layer/face',layer,face))
        pitch=.036 if layer=='M3'else .048;off=.009 if layer=='M3'else .012
        old=x if ns else y
        requested=({'ckv[0]':2.412,'rsv[0]':4.812}.get(name,old) if master in ('dsfd_capt_x8_data_e','dsfd_capt_x8_data_w') else old)
        along=round((requested-off)/pitch)*pitch+off
        if not 0.2<along<(w if ns else h)-.2:raise ValueError((master,name,'pin endpoint margin'))
        key=(face,layer);others=occupied.setdefault(key,[])
        if any(abs(along-v)<2*pitch-1e-7 for v,n in others):
            raise ValueError((master,name,'same-layer 2-track access collision',[(n,v)for v,n in others if abs(along-v)<2*pitch-1e-7]))
        others.append((along,name));xy=[along,y]if ns else[x,along]
        size=([.018,.144]if layer=='M3'else[.024,.192])if ns else[.192,.024]
        lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{xy[0]:.6f} {xy[1]:.6f}}} -pin_size {{{size[0]:.3f} {size[1]:.3f}}} -force_to_die_boundary')
        pins[name]=dict(layer=layer,face=face,requested_xy_um=p['local_xy_um'],assigned_place_pin_location_um=xy,snap_along_delta_um=along-old,pin_size_um=size)
    f=out/(master+'.tcl');f.write_text('\n'.join(lines)+'\n')
    receipts[master]=dict(outline_um=[w,h],orient='R0',instances=rec['instances'],pins=pins,assigned_pin_file=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
packet=dict(schema='opentallas.s81.capture_split_assigned_pins.v1',scope='ASSIGNED_REQUEST_ONLY_NOT_ACTUAL_EXPORTED_PIN_PG_NATIVE_OR_PARENT_QUALIFICATION',geometry_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),masters=receipts,max_snap_delta_um=max(abs(p['snap_along_delta_um'])for m in receipts.values()for p in m['pins'].values()),actual_export_contact_audit='OPEN: place_pin coordinates are requests; consume actual emitted LEF rectangles',pg_gate='OPEN: source-current kit and actual routed pin access',clock_gate='OPEN: each actual source root and insertion/phi-minus-R',all_incident_gate='OPEN: rerun complete8442bit obstacle screen using actual exported pins')
(out/'assigned_pins.json').write_text(json.dumps(packet,indent=1)+'\n')
print(json.dumps(dict(masters=len(receipts),pins=sum(len(r['pins'])for r in receipts.values()),max_snap_delta_um=packet['max_snap_delta_um'])))
