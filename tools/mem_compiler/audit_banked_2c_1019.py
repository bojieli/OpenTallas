#!/usr/bin/env python3
"""Census actual native LEF contacts, not logical connected bits or halo width."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[2]
records=[]
for depth in (32,128,256):
    name=f'ot_sram_1r1w2c_{depth}x64_m1'
    d=ROOT/'physical/asap7_memory_macros_v2'/name
    lef=d/f'{name}.lef'
    text=lef.read_text()
    w,h=map(float,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',text).groups())
    faces={'W':[],'E':[]}
    for match in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',text,re.M|re.S):
        pin,body=match.groups()
        if 'USE POWER' in body or 'USE GROUND' in body:continue
        rects=re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body)
        assert len(rects)==1,(pin,rects)
        x0,y0,x1,y1=map(float,rects[0])
        face='W' if x0==0 else 'E' if abs(x1-w)<1e-6 else None
        assert face,(pin,rects)
        faces[face].append((pin,y0,y1))
    fs={}
    for face,pins in faces.items():
        span=max(p[2] for p in pins)-min(p[1] for p in pins)
        fs[face]={'contacts':len(pins),'full_face_um':h,
                  'contacts_per_full_face_um':len(pins)/h,
                  'active_span_um':span,'contacts_per_active_span_um':len(pins)/span,
                  'minimum_center_pitch_um':min(b[1]-a[1] for a,b in zip(pins,pins[1:]))}
        assert len(pins)/h<=6
    # The same source compiler emits Liberty freshly for each new bank shape.
    # Check distinct clock references; this is not transistor characterization.
    clock_checks={}
    for corner in ('tt','ff','ss'):
        lib=(d/f'{name}_{corner}.lib').read_text()
        assert 'related_pin : "rclk"' in lib and 'related_pin : "wclk"' in lib
        clock_checks[corner]={'rclk_arcs':lib.count('related_pin : "rclk"'),
                              'wclk_arcs':lib.count('related_pin : "wclk"')}
    records.append({'master':name,'faces':fs,'clock_arc_census':clock_checks,
                    'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()},
                    'external_escape_pg_via_drc':'OPEN: full-face density is necessary, not a routing proof',
                    'internal_layout':'not supplied by project analytical compiler'})
out=ROOT/'results/arch/sram_pin_access_1019/native_audit.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'masters':records},indent=2)+'\n')
print('NATIVE_CONTACT_AUDIT PASS three native families; external escape remains OPEN')
