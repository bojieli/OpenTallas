#!/usr/bin/env python3
"""Assign an honest standalone host ingress child; full host boundary stays OPEN."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from leaf_grants_1103 import pins

ROOT=Path(__file__).resolve().parents[2]
SOURCE='rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv'
PINFILE='results/arch/hbm_die_v15/host_ingress_pins_1319.json'
FACES=dict(N=[('clk',1),('rst_n',1),('block_ready',1),('program_active',1),('program_fault',1)],
 W=[('s_awvalid',1),('s_awready',1),('s_awaddr',12),('s_wvalid',1),('s_wready',1),('s_wdata',32),
    ('s_wstrb',4),('s_bvalid',1),('s_bready',1),('s_bresp',2),('s_arvalid',1),('s_arready',1),
    ('s_araddr',12),('s_rvalid',1),('s_rready',1),('s_rdata',32)],
 S=[('cfg_v',1),('cfg_target',8),('cfg_addr',12),('cfg_data',256),('desc_v',1),('desc_base',12),
    ('desc_limit',13),('desc_loops',16),('launch_v',1),('fault',1)])


def apply(c,ref):
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',ref+':'+SOURCE])
    assigned=pins(FACES,(216.0,216.0))
    io=dict(schema='opentallas.hbm_v15.host_ingress_pins.v1',top='ot_hbm_host_static_ingress',
        source_ref=ref,source_sha256=hashlib.sha256(raw).hexdigest(),outline_um=[216,216],pins=assigned,
        pin_ranges={p['name'].split('[')[0]:p['span_um'] for p in assigned},
        note='assigned component-local windows: host AXI west, programme south, clock/status north; full host packet/heterogeneous target/CDC joins OPEN')
    blob=(json.dumps(io,indent=1)+'\n').encode()
    c['slots']=[s for s in c['slots'] if s['name']!='host_cp_ingress']
    parent=next(s for s in c['slots'] if s['name']=='host_cp')
    assert 21.6+216<=parent['outline']['w'] and 21.6+216<=parent['outline']['h']
    c['slots'].append(dict(name='host_cp_ingress',cell='ot_hbm_host_static_ingress',source=SOURCE,
        source_sha256=io['source_sha256'],source_prerequisite=ref,params={},kind='tile',parent='host_cp',
        instance_pending='hostingress front component; host packet bridge and programme target adapters not yet joined',
        outline=dict(w=216.0,h=216.0),origin=dict(x=21.6,y=21.6,orient='R0'),pins=assigned,
        clock_entry=dict(pin='clk',face='N',layer='M5',offset=assigned[0]['offset']),
        clock_domain='stream',clock_period_ps=833.333333,
        io_budget=dict(in_delay_frac=.2,out_delay_frac=.2),pg_layer='M5',strap_layer='M6',
        signal_max_layer='M5',layer_cap='M5',layer_rule='tile',version=1,grant='diagnostic_component_child',
        assigned_pin_file=PINFILE,assigned_pin_file_sha256=hashlib.sha256(blob).hexdigest(),
        measured_std_um2=354.527280,
        supported_targets=[48],supported_target_scope='default target-mask VM calendar only; actual local full-row readiness validation required',
        qualification_scope='independent pin-registered ingress only; local readiness validator is separate hardware; host PHY/landing/packet bridge, heterogeneous target adapters, programme fanout and full host_cp binding remain OPEN'))
    c['host_ingress_child_grant_1319']=dict(source_ref=ref,area_mm2=216*216/1e6,
        whole_host_cp_or_die_qualified=False,local_readiness_validator_granted=False)
    return c,blob


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--source-ref',default='b69e85b0e');a=ap.parse_args()
    c,blob=apply(json.loads(a.contract.read_text()),a.source_ref)
    (ROOT/PINFILE).write_bytes(blob);a.out.write_text(json.dumps(c,indent=1)+'\n')
    print(json.dumps(c['host_ingress_child_grant_1319']))


if __name__=='__main__':main()
