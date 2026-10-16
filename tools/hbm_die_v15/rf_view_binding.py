#!/usr/bin/env python3
"""Bind RF footprint witness to actual source-pinned standard48 ETMs and pins.

Serial900MHz is the production domain. Stream1.2GHz is sensitivity only.
Qcore boundary views absent => complete RF timing stays fail closed.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as PA


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan');ap.add_argument('--ref',default='b55c8b228')
    a=ap.parse_args();d=Path(a.plan)
    alloc=json.loads((d/'rf_centre_allocation.json').read_text())
    views={}
    for flow in ['WE','EW','SN','NS']:
        master='hbfd_rly_48_'+flow
        base=f'physical/ref_tile/hbfd_rly_48_{flow.lower()}/views/{master}/'
        files={n:subprocess.check_output(['git','-C',str(ROOT),'show',a.ref+':'+base+n])
               for n in [master+'.lef',master+'_tt.lib',master+'_ff.lib','insertion.json']}
        ins=json.loads(files['insertion.json'])
        timings={}
        for corner in ['tt','ff']:
            with tempfile.NamedTemporaryFile(suffix='.lib') as f:
                f.write(files[master+'_'+corner+'.lib']);f.flush()
                lib=PA.parse_lib(f.name);refs=PA.clock_refs(lib,ins,corner)
                timings[corner]=dict(refs=refs,pins=PA.pin_metrics(lib,refs))
        lef=files[master+'.lef'].decode();pins={}
        for match in re.finditer(r'\bPIN\s+(\S+)\s+(.*?)\bEND\s+\1\b',lef,re.S):
            m=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',match[2])
            if m:
                x0,y0,x1,y1=map(float,m.groups());pins[match[1]]=[(x0+x1)/2,(y0+y1)/2]
        views[master]=dict(view=base,source_ref=a.ref,sha256={n:hashlib.sha256(b).hexdigest() for n,b in files.items()},
                           lef_pins=pins,timing=timings)
    # Timing-safe conservative envelope: centre polyline plus both endpoint
    # offsets bounded by2*21.6um. Actual source/sink per-bit routing is still open.
    wire_bound=alloc['max_allocated_hop_um']+43.2
    checks=[]
    for ma,va in views.items():
        for mb,vb in views.items():
            tt=[];hold=[]
            for bit in range(41):
                op=va['timing']['tt']['pins'][f'o[{bit}]']['out']
                ip=vb['timing']['tt']['pins'][f'i[{bit}]']['inp']
                pair=op+ip+.76*wire_bound
                tt.append(dict(bit=bit,o_ps=op,s_ps=ip,wire_bound_um=wire_bound,
                               serial_slack_ps=1111.1-60-90-pair,stream_sensitivity_slack_ps=833.3-60-90-pair))
                launch=va['timing']['ff']['pins'][f'o[{bit}]']['lmin']
                capture=vb['timing']['ff']['pins'][f'i[{bit}]']['hold']
                hold.append(dict(bit=bit,launch_min_ps=launch,hold_ps=capture,
                                 zero_wire_margin_ps=launch-capture,clock_uncertainty_skew_margin_ps=launch-capture-25-90))
            checks.append(dict(source=ma,sink=mb,worst_serial=min(tt,key=lambda x:x['serial_slack_ps']),
                               worst_stream_sensitivity=min(tt,key=lambda x:x['stream_sensitivity_slack_ps']),
                               worst_ff_hold=min(hold,key=lambda x:x['clock_uncertainty_skew_margin_ps'])))
    out=dict(schema='opentallas.hbm.rf_view_binding.v1',qualification='FAIL_CLOSED_QCORE_BOUNDARY_VIEWS_OPEN',
             production_domain='serial',period_ps=1111.1,setup_budget_ps=961.1,wire_ps_per_um=.76,
             centre_hop_max_um=alloc['max_allocated_hop_um'],conservative_pin_wire_bound_um=wire_bound,
             views=views,pair_checks=checks,
             relay_pair_serial_setup_pass=all(x['worst_serial']['serial_slack_ps']>=0 for x in checks),
             relay_pair_zero_wire_ff_hold_pass=all(x['worst_ff_hold']['clock_uncertainty_skew_margin_ps']>=0 for x in checks),
             open=['actual per-stage master FLOW binding and orientation',
                   'actual source-bound qcore red_rf_v/red_tag[7:0]/red_x launch arcs and N/S pins',
                   'actual qcore rf_wv/rf_wa/rf_wd capture arcs,64 RF clock roots and boundary insertion',
                   'per-bit routed lengths and actual die clock phase/spread',
                   'complete current graph cuts including824new incident edges', 'die GRT/STA/DRC0'])
    (d/'rf_view_binding.json').write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:out[k] for k in ['qualification','production_domain','setup_budget_ps','conservative_pin_wire_bound_um','relay_pair_serial_setup_pass','relay_pair_zero_wire_ff_hold_pass']}))
    print('worst serial slack ps',min(x['worst_serial']['serial_slack_ps'] for x in checks))
    print('worst FF zero-wire hold margin after25+90ps',min(x['worst_ff_hold']['clock_uncertainty_skew_margin_ps'] for x in checks))


if __name__=='__main__':main()
