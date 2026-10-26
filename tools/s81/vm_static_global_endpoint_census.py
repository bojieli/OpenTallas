#!/usr/bin/env python3
"""Source-owned necessary pin-capacity bound; no physical view is invented."""
import json, sys, hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools'))
import die_port_bind as D

def census():
    rows=[]
    for top,params,box in [('dsfd_vm_static_suhc_fsr',{},[345.6,51.84]),('dsfd_vm_static_scatter',{},[345.6,103.68]),('dsfd_vm_static_return',{'NROW':32},[345.6,207.36])]:
        p=R/'rtl/dsrom_sys/s81_ph/vm'/(top+'.sv')
        m=D.parse_modules(p.read_text(),str(p))[0];env=m.env(params)
        ports={n:dict(direction=d,width=m.width(n,env)) for n,(d,_) in m.ports.items()}
        count=sum(v['width'] for v in ports.values())
        capacity=sum(int(x/.096)*2 for x in box)
        rows.append(dict(master=top,params=params,source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ports=ports,port_bits=count,provisional_outline_um=box,native_pitch_um=.096,optimistic_all_face_capacity=capacity,necessary_perimeter_um=round(count*.096,3),perimeter_um=round(2*sum(box),3),capacity_possible=count<=capacity,status='NEEDS_ACTUAL_FACE_PINS_AND_GLOBAL_REGISTERED_HOPS' if count<=capacity else 'REJECT_PROVISIONAL_BOX_EVEN_BEFORE_CLOCK_PG_KEEPOUT'))
    return dict(schema='opentallas.s81.vm-global-endpoint-census.v1',status='ACTUAL_SOURCE_NECESSARY_BOUND_ONLY',scope='All ports counted at native pitch, even optimistic full perimeter; no route, timing, face reach or adoption claim',endpoints=rows,next=['Structurally split or enlarge scatter with actual pin registers and uniform compiler ages','Assign actual FSR/return faces; route uniform registered global fanout to all four bridge groups','Place cap/CDC/53writer, native clock roots and power channels before canonical geometry adoption'])
if __name__=='__main__':
    d=census();out=R/'results/physical/s81_vm_static_ownership_1015/global_endpoint_census.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['master','port_bits','optimistic_all_face_capacity','status']} for r in d['endpoints']]))
