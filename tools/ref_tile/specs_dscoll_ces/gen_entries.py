#!/usr/bin/env python3
"""Preserve CLOSED CES leaves; expose one independent clock entry per child."""
import json
import copy
from pathlib import Path
from gen_specs import cluster_spec, ROOT, HERE
PORTS = ['ck_x1','ck_x2','ck_x3','ck_core','ck_l0','ck_l1','ck_l2','ck_l3','ck_o','ck_pt']
for zero in [True, False]:
    s = copy.deepcopy(cluster_spec(zero))
    s['name'] = 'dscoll_ces' + ('0' if zero else 'n') + '_pc'
    s['top'] = 'dsfd_coll_ces' + ('0' if zero else 'n') + '_pc'
    s['clock'] = 'entries'
    s['clock_port'] = PORTS[0]
    s['clock_ports'] = PORTS
    s['pins']['N'].remove('ck')
    positions = {
        'ck_x1': ('W', 108.0), 'ck_x2': ('W', 211.68), 'ck_x3': ('N', 34.04),
        'ck_core': ('N', 220.38 if zero else 168.92),
        'ck_l0': ('N',132.92), 'ck_l1':('N',202.04), 'ck_l2':('N',271.16), 'ck_l3':('N',340.28),
        'ck_o': ('S',337.0), 'ck_pt':('E',237.56 if zero else 203.0)}
    for port,(face,along) in positions.items():
        s['pins'][face].append(port)
        s['pin_ranges'][port] = [round(along-.144,3), round(along+.144,3)]
    s['structural_change'] += '; remove the shared parent clock spine: ten face entries each drive one hard-child clock pin, die delivers phi-R_i at each entry'
    s['job']['tag'] = 'pc1'
    s['job']['purpose'] = 'Independent compensated clock entries; CLOSED leaves and all pipeline stages preserved'
    s['job']['views_to'] = f"physical/ref_tile/{s['name']}/views"
    s['job']['record_to'] = f"results/rtl/ref_tile/{s['name']}"
    s['job']['extra_paths'].append('physical/common_flow/clock_entries.tcl')
    # Execute the actual independent-clock hierarchy in the production composition gate.
    for b in s['job']['benches']:
        if 'cmd' in b and 'run_coll_bench.sh' in b['cmd']:
            b['cmd'] += ' +define+OT_S81PH_COLL_CES_ENTRIES'
    s['reroute_reason'] = {'kind':'rtl_change','why':'ten distinct clock ports replace the shared clock spine; child RTL unchanged'}
    path=HERE/(s['name']+'.json')
    ref='physical/redesign_ds/coll_split/'+s['name']+'_child_ioref.sdc'
    s['sdc_extra']=[ref];s['boundary_tcl']=[ref]
    path.write_text(json.dumps(s,indent=1)+'\n')
    import subprocess,sys
    subprocess.run([sys.executable,str(ROOT/'tools/ref_tile/wires_only_ioref.py'),str(path),str(ROOT/ref)],check=True)
    print(path)
