#!/usr/bin/env python3
"""Build source-pinned local DVM contact requests; no permission or qualification inferred."""
import copy,json,re,sys
from pathlib import Path
import dvm_m6_side_plan as P
from verify_static_slot_pins import ports

def build():
    root=Path(__file__).resolve().parents[2]; plan=P.generate();alias=plan['M6_aliases']['R0_origin_y_mod64_0']['contacts'];out=[]
    for base,typ in [('qfd_xs_leaf','leaf'),('qfd_xhead_e','head'),('qfd_xhead_w','head')]:
        s=json.loads((root/f'physical/ref_tile/{base}/spec.json').read_text());name=base+'_m6_138';kd=f'physical/ref_tile/{name}';h=138.24 if typ=='leaf' else 345.6
        s['name']=name;s['outline']={'w':64.8,'h':h,'exact':True};s.pop('pin_ranges',None)
        # Exact per-bit face maps supersede bundle face/ranges. Interior routing remains M5.
        s['pins']={k:[] for k in 'NSEW'}; assignments={}
        def put(n,layer,face,c):
            assert n not in assignments;assignments[n]={'layer':layer,'face':face,'center_um':c};s['pins'][face].append(n)
        for p in plan['NS_contacts']:
            for face,key in [('S','leaf_S'),('N','leaf_N')] if typ=='leaf' else [('N','head_N'),('S','head_S')]:put(p['names'][key],p['layer'],face,sum(p['rect_x_nm'])/2000)
        for p in alias:
            if typ=='leaf':
                for key,y in [('leaf_S',p['leaf_input_y_nm']/1000),('leaf_N',p['leaf_output_y_nm']/1000)]:put(p['names'][key],'M6',p['side'],y)
            else:
                for key,y in [('head_S',p['leaf_input_y_nm']/1000),('head_N',h-(138.24-p['leaf_output_y_nm']/1000))]:put(p['names'][key],'M6',p['side'],y)
        rtl=root/s['sources'][0];decl=ports(rtl,s['top']);expected={n if w==1 else f'{n}[{i}]' for n,w in decl.items() for i in range(w)}
        old=json.loads((root/f'physical/ref_tile/{base}/spec.json').read_text())['pins'];faces={n:f for f,ns in old.items() for n in ns}
        for face in ['W','E']:
            remaining=sorted(n for n in expected-assignments.keys() if faces[n.split('[')[0]]==face)
            # Keep every incident read/clock/reset/head-row port in the middle clear of both seam bands.
            layer='M6' if typ=='leaf' else 'M4'
            slots=[v/1000 for v in range(43216 if typ=='leaf' else 43212,round((h-43.2)*1000),128 if typ=='leaf' else 48)]
            assert len(slots)>=len(remaining)
            for i,n in enumerate(remaining):put(n,layer,face,slots[((2*i+1)*len(slots))//(2*len(remaining))])
        assert set(assignments)==expected,(name,sorted(expected-assignments.keys()))
        s['io_tcl']=kd+'/assigned_pins.tcl';s['route']['pin_h']='M6' if typ=='leaf' else 'M4 M6';s['route']['pin_v']='M3 M5';s['route'].pop('pin_balance',None)
        s['pin_source']='Exact source candidate. R0 origin-y phase0 and MX phase32 reuse one M6 frame at H138.24; actual exported outline and all parent tracks are unqualified.'
        s['slot_change_request']='Coordinator local-body candidate permission 2026-10-16: leaf64.8x138.24/head64.8x345.6 in r2h4 64.8x1473.12 envelope; parent M7/M9 tracks pending actualPG audit.'
        s['structural_change']='Move346 exact1170-bit chain contacts onto named M6 W/E PORT contacts, retain824 chain bits on N/S M3+M5. M5 interior/PG unchanged. Leaf read/reset/clock pins M6 support its coherent MX frame; nonflipped head read/head-row ports retain M4, because putting all2728E-side original head bits plus346seam bits on M6 would exceed two-track capacity. No workload/RTL/cycle change; placement/native/TT/FF/DRC remain unqualified.'
        s['job'].update(branch='codex/qwen-link-recovery-0253',tag='m6a',views_to=kd+'/views',record_to='results/rtl/ref_tile/'+name)
        d=root/kd;d.mkdir(parents=True,exist_ok=True)
        (d/'spec.json').write_text(json.dumps(s,indent=1)+'\n');(d/'contact_request.json').write_text(json.dumps({'master':s['top'],'outline':s['outline'],'qualified':False,'parent_track_grant':False,'ports':assignments},indent=1)+'\n')
        t=['source /src/physical/common_flow/assigned_pin_exact.tcl']
        for n,a in assignments.items():t.append(f"ot_assigned_pin_exact {{{n}}} {a['layer']} {a['face']} {a['center_um']:.6f}")
        (d/'assigned_pins.tcl').write_text('\n'.join(t)+'\n');out.append((name,len(expected),sum(a['layer']=='M6' for a in assignments.values())))
    return out
if __name__=='__main__':print(build())
