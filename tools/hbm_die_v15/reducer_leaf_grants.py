#!/usr/bin/env python3
"""Reserve four actual SU reducer leaves; complete qcore clock/fit stays OPEN.

The route is screened at 833.333 ps, matching its existing stricter signoff.
The architectural serial-900 MHz related-clock/calendar binding is unresolved.
This is an independent component grant, never a fictitious complete qcore view.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from leaf_grants_1103 import pins

ROOT=Path(__file__).resolve().parents[2]
SOURCE='rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static.sv'
PINFILE='results/arch/hbm_die_v15/reducer_leaf_pins_1319.json'
FACES=dict(N=[('clk',1),('rst_n',1)],W=[('cmd_valid',1),('cmd_op',3),('cmd_a',10),('cmd_b',10),
    ('cmd_dst',10),('operand_fp32',32),('cmd_tag',32)],E=[('scalar_valid',1),('scalar_tag',32),
    ('scalar_fp32',32),('scalar_bf16',16),('fault',1)])


def apply(c,source_ref):
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',source_ref+':'+SOURCE])
    assigned=pins(FACES,(216.0,151.2))
    io=dict(schema='opentallas.hbm_v15.reducer_assigned_pins.v1',top='ot_hbm_su_reduce_static',
        source_ref=source_ref,source_sha256=hashlib.sha256(raw).hexdigest(),outline_um=[216,151.2],pins=assigned,
        pin_ranges={p['name'].split('[')[0]:p['span_um'] for p in assigned},
        note='die-assigned local master-frame port windows; exact routed bit positions must be read back; external peers and qcore fit/phase are OPEN')
    blob=(json.dumps(io,indent=1)+'\n').encode()
    c['slots']=[s for s in c['slots'] if not s.get('su_reducer_child_grant_1319')]
    have={s['name']:s for s in c['slots']}
    for q in ('SW','SE','NW','NE'):
        parent='sucore_'+q; p=have[parent]
        assert 17.28+216<=p['outline']['w'] and 21.6+151.2<=p['outline']['h']
        c['slots'].append(dict(name=parent+'_reducer',cell='ot_hbm_su_reduce_static',source=SOURCE,
            source_sha256=io['source_sha256'],source_prerequisite=source_ref,params=dict(AW=10),kind='tile',
            parent=parent,instance_pending='whole SU qcore RTL hierarchy join OPEN; independent reducer component only',
            outline=dict(w=216.0,h=151.2),origin=dict(x=17.28,y=21.6,orient='R0'),pins=assigned,
            clock_entry=dict(pin='clk',face='N',layer='M5',offset=assigned[0]['offset']),
            clock_domain='su_reduce_local_qualification',clock_period_ps=833.333333,
            architectural_clock_binding=dict(intended_serial_period_ps=1111.111111,
                phase_and_static_calendar_qualified=False,
                note='component screened at stricter existing 833.333 ps signoff; this does not establish a serial-to-stream join'),
            io_budget=dict(in_delay_frac=.2,out_delay_frac=.2),pg_layer='M5',strap_layer='M6',
            signal_max_layer='M5',layer_cap='M5',layer_rule='tile',version=1,grant='diagnostic_component_child',
            assigned_pin_file=PINFILE,assigned_pin_file_sha256=hashlib.sha256(blob).hexdigest(),
            su_reducer_child_grant_1319=True,macros=[dict(cell='ot_sram_1r1w_128x256_m1_r2c2',count=2)],
            qualification_scope='independent actual reducer leaf only; complete qcore placement, RF capacity, related clocks and fixed-cycle parent integration OPEN'))
    c['su_reducer_child_grants_1319']=dict(count=4,source_ref=source_ref,
        outline_area_mm2=4*216*151.2/1e6,whole_su_or_die_qualified=False)
    return c,blob


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--source-ref',default='5223681bb');a=ap.parse_args()
    c,blob=apply(json.loads(a.contract.read_text()),a.source_ref)
    (ROOT/PINFILE).write_bytes(blob);a.out.write_text(json.dumps(c,indent=1)+'\n')
    print(json.dumps(c['su_reducer_child_grants_1319']))


if __name__=='__main__':main()
