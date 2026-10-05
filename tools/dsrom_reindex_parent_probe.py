#!/usr/bin/env python3
"""Read-only SS/FF inspection of the actual routed production control/list.

Reports the real ready cones, macro loads/capture/check ports and mutable-state
register inventory. The raw timing reports must be assessed against 166.666ps;
successful execution alone is not a ready-budget or parent qualification PASS.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACRO = 'ot_sram_1r1w_512x128_m4_r2c2'
TCL = r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_TAG_*.lib*]] {read_liberty $f}
read_liberty /src/physical/asap7_memory_macros/MACRO/MACRO_CORNER.lib
read_db /route/6_final.odb
read_sdc /route/6_final.sdc
read_spef /route/6_final.spef
set_propagated_clock [all_clocks]
report_units
report_clock_properties
set macros [get_cells -hierarchical *u_macro]
if {[llength $macros]!=16} {error "Expected sixteen actual list SRAM macros"}
puts "PARENT_MACROS [llength $macros]"
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set area 0.0
foreach inst [$block getInsts] {
    set m [$inst getMaster]
    if {![$m isBlock]} {set area [expr {$area+double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]}
}
puts "PARENT_STANDARD_CELL_AREA_UM2 $area CAP_UM2 37452.2"
set endpoints [all_registers -data_pins]
set core {}
foreach pin $endpoints {
    if {[regexp {u_control[./]u_c[./]} [get_full_name $pin]]} {lappend core $pin}
}
if {![llength $core]} {error "Missing actual core register endpoints"}
puts "PARENT_CORE_ENDPOINTS [llength $core]"
foreach pattern {*c_req_rdy* *drain_ready*} {
    set nets [get_nets -hierarchical -quiet $pattern]
    if {![llength $nets]} {error "Missing actual ready net $pattern"}
    puts "PARENT_READY_GROUP $pattern BUDGET_PS 166.666"
    set through {}
    foreach net $nets {
        report_net -digits 6 [get_full_name $net]
        foreach pin [get_pins -of_objects $net] {
            if {[get_property $pin direction]=="output"} {lappend through $pin}
        }
    }
    if {![llength $through]} {error "Ready source is not an actual internal driver"}
    foreach delay {max min} {
        puts "PARENT_READY_PATH $pattern $delay"
        report_checks -from [all_registers -output_pins] -through $through -to $core \
            -path_delay $delay -group_path_count 8 -format full_clock_expanded \
            -fields {slew capacitance input_pin net fanout} -digits 6
    }
}
set mq [get_pins -hierarchical *u_macro/rd_out*]
set ma [get_pins -hierarchical *u_macro/r_addr_in*]
set mw [get_pins -hierarchical *u_macro/w*_in*]
set mc [get_pins -hierarchical *u_macro/clk]
set repair [get_pins -hierarchical *u_macro/*r_en*]
puts "PARENT_MACRO_PORTS Q [llength $mq] ADDR [llength $ma] WRITE [llength $mw] CLK [llength $mc] REPAIR [llength $repair]"
if {[llength $mq]!=2048 || [llength $mc]!=16} {error "Missing real macro ports"}
foreach pin [concat $mq $mc $repair] {
    foreach net [get_nets -of_objects $pin] {
        puts "PARENT_MACRO_NET [get_full_name $pin]"
        report_net -digits 6 [get_full_name $net]
    }
}
foreach {name pins direction} [list read $mq from address $ma to write $mw to] {
    foreach delay {max min} {
        puts "PARENT_MACRO_PATH $name $delay"
        report_checks -$direction $pins -path_delay $delay -group_path_count 16 \
            -format full_clock_expanded -fields {slew capacitance input_pin net fanout} -digits 6
    }
}
# List every surviving protection-state register's output net. This inventory
# exposes lost/aliased rails; counting names alone is not an integrity proof.
foreach pin [all_registers -output_pins] {
    foreach net [get_nets -of_objects $pin] {
        set name [get_full_name $net]
        if {[regexp {u_list|g_req|u_command|u_drain|pending_.*check|metadata_check|cntc} $name]} {
            puts "PARENT_STATE_REGISTER [get_full_name $pin] NET $name"
        }
    }
}
foreach kind {max_slew max_capacitance max_fanout min_period min_pulse_width} {
    puts "PARENT_CHECK $kind"
    report_check_types -$kind -violators -digits 6 -no_line_splits
}
puts "PARENT_PROBE_DONE"
'''


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--route-base', type=Path, required=True)
    p.add_argument('--route-source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    base, out = a.route_base.resolve(), a.out.resolve()
    route_source = json.loads(a.route_source.read_text())
    for name, expected in route_source['sha256'].items():
        if name.endswith('.sv') or name.endswith('_bb.v') or name in ('tools/run_abi3_physical.py', 'tools/orfs_allcorner_spef.py'):
            if sha(ROOT / name) != expected:
                raise SystemExit('Routed source mismatch: ' + name)
    artifacts = {f'6_final.{ext}': base / f'6_final.{ext}' for ext in ('odb', 'sdc', 'spef', 'v')}
    for f in artifacts.values():
        if not f.is_file():
            raise SystemExit('Missing routed artifact: ' + str(f))
    sdc = artifacts['6_final.sdc'].read_text()
    for expression in (r'-period\s+833\.333', r'-setup\s+60(?:\.0*)?\b', r'-hold\s+25(?:\.0*)?\b'):
        if not re.search(expression, sdc):
            raise SystemExit('Clock/uncertainty mismatch')
    if re.search(r'set_false_path\s+-(from|to)\s+\[(all_inputs|all_outputs)', sdc):
        raise SystemExit('Blanket IO falsepath is not production parent evidence')
    hashes = {n: sha(f) for n, f in artifacts.items()}
    out.mkdir(parents=True, exist_ok=False)
    pins = ['tools/dsrom_reindex_parent_probe.py', 'tools/run_abi3_physical.py', 'tools/orfs_allcorner_spef.py']
    rec = dict(artifacts_sha256=hashes, route_source_sha256=sha(a.route_source),
               route_commit=route_source['commit'], tools_sha256={f: sha(ROOT / f) for f in pins},
               scope='Actual production control/list/request/drain-header component; key-data store outside scope',
               ready_budget_ps=166.666, standard_cell_cap_um2=37452.2,
               qualification=False, corners={})
    for corner in ('ss', 'ff'):
        (out / f'{corner}.tcl').write_text(TCL.replace('TAG', corner.upper()).replace('MACRO/', MACRO + '/').replace('MACRO_CORNER', MACRO + '_' + corner))
        cmd = ['docker', 'run', '--rm', '-e', 'OMP_NUM_THREADS=16',
               '-v', f'{ROOT}:/src:ro', '-v', f'{base}:/route:ro', '-v', f'{out}:/probe',
               'openroad/orfs:latest', 'bash', '-lc',
               f'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /probe/{corner}.tcl']
        run = subprocess.run(cmd, capture_output=True, text=True)
        log = out / f'{corner}.log'
        log.write_text(run.stdout + run.stderr)
        rec['corners'][corner] = dict(exit=run.returncode, log_sha256=sha(log),
            macro_lib_sha256=sha(ROOT / 'physical/asap7_memory_macros' / MACRO / f'{MACRO}_{corner}.lib'),
            complete=run.returncode == 0 and 'PARENT_PROBE_DONE' in log.read_text() and '[ERROR' not in log.read_text())
        (out / 'record.json').write_text(json.dumps(rec, indent=2) + '\n')
    rec['artifacts_unchanged'] = hashes == {n: sha(f) for n, f in artifacts.items()}
    (out / 'record.json').write_text(json.dumps(rec, indent=2) + '\n')
    if not rec['artifacts_unchanged'] or not all(c['complete'] for c in rec['corners'].values()):
        raise SystemExit('Incomplete probe; preserve raw reports')


if __name__ == '__main__':
    main()
