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
    # ETM calibration must see one external source per clock. All entries remain synchronous:
    # equal periods and phases, every cross-clock path timed, no async groups or false paths.
    clocks = {port: ('core_clk' if port == 'ck_core' else 'entry_' + port) for port in PORTS}
    constraint = ['# Independent synchronous source clocks; preserve the current route/signoff period.',
        'set ot_pc_period [get_property [get_clocks core_clk] period]',
        'delete_clock [get_clocks core_clk]']
    for port, cname in clocks.items():
        constraint.append(f'create_clock -name {cname} -period $ot_pc_period [get_ports {port}]')
    constraint += ['set_propagated_clock [all_clocks]',
        'set_clock_uncertainty -setup 60 [all_clocks]', 'set_clock_uncertainty -hold 25 [all_clocks]',
        'set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]',
        'set_output_delay 166.667 -clock core_clk [all_outputs]',
        'set ::ot_wc_clocks [dict create ' + ' '.join(port+' '+cname for port,cname in clocks.items()) + ']']
    generated = (ROOT/ref).read_text()
    generated = generated.replace('foreach src [get_property [get_clocks core_clk] sources] { set_clock_latency -source 0.0 -clock [get_clocks core_clk] $src }',
        'dict for {entry cname} $::ot_wc_clocks { set_clock_latency -source 0.0 -clock [get_clocks $cname] [get_ports $entry] }')
    generated = generated.replace('set_clock_latency -source $lat -clock [get_clocks core_clk] $tp',
        'set_clock_latency -source $lat -clock [get_clocks [dict get $::ot_wc_clocks $tn]] $tp')
    (ROOT/ref).write_text('\n'.join(constraint) + '\n' + generated)
    print(path)
