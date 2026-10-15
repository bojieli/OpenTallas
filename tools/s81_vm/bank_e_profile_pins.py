#!/usr/bin/env python3
"""E-input pin profile of dsfd_vm_static_bank128 (module dsfd_vm_static_bank128_E).
Mirrors only the signal faces of the die-assigned standard bank plan: every W-face M4 request pin moves to the
E face and every E-face M4 return/commit pin to the W face at the SAME y track (M4 horizontal, on-track), the
N-face M3 ck/rst_n keep their exact coordinates (a MY instance flip would put them and the M5 PG half a track
off).  Outline, layers, PG, signal cap and pin order are unchanged; zero cycles."""
import json,hashlib,pathlib
R=pathlib.Path(__file__).resolve().parents[2]
src=R/'physical/s81_die_pins/v20_vm_static_standard/dsfd_vm_static_bank128.json'
out=R/'physical/s81_die_pins/v20_vm_static_bank_e';out.mkdir(parents=True,exist_ok=True)
P=json.loads(src.read_text());w,h=P['outline_um']
swap={'W':'E','E':'W'}
for n,p in P['ports'].items():
    p['per_bit']=[[swap.get(f,f),ly,c,d] for f,ly,c,d in p['per_bit']]
P.update(master='dsfd_vm_static_bank128_E',case='v20_static_vm_bank_e',
         rule='E M4 requests, W M4 registered return/commit (signal-face mirror of v20 standard); N M3 root/reset unchanged',
         derived_from={'path':str(src.relative_to(R)),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()},
         source='tools/s81_vm/bank_e_profile_pins.py')
(out/'dsfd_vm_static_bank128_E.json').write_text(json.dumps(P,indent=1)+'\n')
L=['# dsfd_vm_static_bank128_E: signal-face mirror of v20 standard bank pins (tools/s81_vm/bank_e_profile_pins.py)\n']
for n,p in P['ports'].items():
    for i,(f,ly,c,d) in enumerate(p['per_bit']):
        nm=n if p['bits']==1 else f'{n}[{i}]'
        x=.042 if f=='W' else round(w-.042,3) if f=='E' else c
        y=.042 if f=='S' else round(h-.042,3) if f=='N' else c
        L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary\n')
(out/'dsfd_vm_static_bank128_E.tcl').write_text(''.join(L))
print(len(L)-1,'pins')
