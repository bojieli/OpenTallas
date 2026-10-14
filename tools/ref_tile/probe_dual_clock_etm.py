#!/usr/bin/env python3
"""Prepare an actual routed dual-clock ETM accounting probe, not physical closure.

Run generated run.sh with ot-run inside openroad/orfs:asap7lock. The fixture
must supply dsfd_wfc_vmx_{tt,ff,ss}.lib plus both insertion_*_clk.json records.
--tool-root permits testing a reviewed clock API worktree before it is merged.
"""
import argparse
import importlib.util
import hashlib
import json
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixture', required=True, type=Path)
    p.add_argument('--tool-root', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--unmapped-input-mutant', action='store_true', help='Add an actual top data input absent from domain lists; API must reject it')
    p.add_argument('--zero-source-mutant', action='store_true', help='Erase source compensation after application; numerical oracle must reject it')
    p.add_argument('--setup-only-diagnostic', action='store_true', help='Explicitly unqualified diagnostic when actual ETM hold arcs are absent')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    view = args.out / 'dsfd_wfc_vmx'
    view.mkdir(exist_ok=True)
    measured = {}
    for pin, name in [('ck[0]', 'core'), ('ckv[0]', 'ser')]:
        measured[pin] = json.loads((args.fixture / f'insertion_{name}_clk.json').read_text())
        measured[pin]['lib_clock_pin'] = pin
    (view / 'insertion.json').write_text(json.dumps({'clock_measurements': measured}, indent=2))
    for corner in ('tt', 'ff', 'ss'):
        shutil.copyfile(args.fixture / f'dsfd_wfc_vmx_{corner}.lib', view / f'dsfd_wfc_vmx_{corner}.lib')
    shutil.copyfile(args.fixture / 'dsfd_wfc_vmx.lef', view / 'dsfd_wfc_vmx.lef')
    provenance = {'scope': 'default VMX actual closed ETM accounting fixture only; not priced die qualification', 'source': str(args.fixture), 'sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in args.fixture.iterdir() if f.is_file() and f.suffix in ('.lib', '.json', '.lef')}}
    (args.out / 'provenance.json').write_text(json.dumps(provenance, indent=2))
    spec = {'clock': 'entries', 'clock_port': 'ac', 'clock_ports': ['ac', 'av', 'bc', 'bv'],
            'children': [{'view': 'dsfd_wfc_vmx', 'count': 2}],
            'clock_entry_domains': {
                'core': {'ratio': [1, 1], 'ports': ['ac', 'bc'], 'inputs': [], 'outputs': []},
                'serial': {'ratio': [4, 3], 'ports': ['av', 'bv'], 'inputs': [], 'outputs': []}}}
    modpath = args.tool_root / 'tools/ref_tile/clock_entry_constraints.py'
    import sys
    sys.path.insert(0, str(modpath.parent))
    module_spec = importlib.util.spec_from_file_location('clock_entry_constraints', modpath)
    api = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(api)
    (args.out / 'spec.json').write_text(json.dumps(spec, indent=2))
    (args.out / 'probe.v').write_text('''module probe(input ac,av,bc,bv);
wire [53:0] ab;
wire [52:0] ba;
dsfd_wfc_vmx a(.ck(ac), .ckv(av), .t_cd(ab), .f_cs(ba));
dsfd_wfc_vmx b(.ck(bc), .ckv(bv), .f_kd(ab), .t_ks(ba));
endmodule
''')
    if args.unmapped_input_mutant:
        net = args.out / 'probe.v'
        net.write_text(net.read_text().replace('input ac,av,bc,bv', 'input ac,av,bc,bv,unmapped'))
    constraints = api.generate(spec, args.out)
    if args.zero_source_mutant:
        constraints += '\nforeach c [get_clocks ot_entry_*] {set_clock_latency -source 0 $c}\n'
    for corner in ('tt', 'ff', 'ss'):
        rc = measured['ck[0]'][corner]['boundary']['mean']
        rv = measured['ckv[0]'][corner]['boundary']['mean']
        text = f'''read_liberty /probe/dsfd_wfc_vmx/dsfd_wfc_vmx_{corner}.lib
read_verilog /probe/probe.v
link_design probe
{api.clocks(spec, 833.333)}
set ::ot_ce_corner {corner}
proc sample {{}} {{
  set result {{}}
  foreach {{tag from to}} {{cs a/t_cd* b/f_kd* sc b/t_ks* a/f_cs*}} {{
    foreach kind {{max min}} {{
      set ps [find_timing_paths -from [get_pins $from] -to [get_pins $to] -path_delay $kind -group_path_count 1]
      if {{![llength $ps]}} {{error "missing $tag $kind actual ETM path"}}
      dict set result $tag $kind [get_property [lindex $ps 0] slack]
    }}
  }}
  return $result
}}
set_propagated_clock [get_clocks ot_entry_*]
set before [sample]
{constraints}
set after [sample]
foreach {{tag delta}} {{cs {rc-rv} sc {rv-rc}}} {{
  foreach kind {{max min}} {{
    set old [dict get $before $tag $kind]
    set now [dict get $after $tag $kind]
    # No uncertainty in baseline; composed setup150/hold100 on same-level
    # clocks. Source compensation shifts setup by Rlaunch-Rcapture and hold
    # by its negative. The ETM launch/check arcs stay exactly as exported.
    set expected [expr {{$old + ($kind eq "max" ? $delta-150 : -$delta-100)}}]
    if {{abs($now-$expected)>0.03}} {{error "slack mismatch $tag $kind $now vs $expected"}}
    puts "DUAL_PATH {corner} $tag $kind before=$old after=$now expected=$expected"
  }}
}}
foreach {{pin ref}} {{a/ck[0] {rc} b/ck[0] {rc} a/ckv[0] {rv} b/ckv[0] {rv}}} {{
  set arrival [get_property [get_pins $pin] arrival_max_rise]
  set phase [expr {{$arrival+$ref}}]
  if {{![info exists phi]}} {{set phi $phase}}
  if {{abs($phase-$phi)>0.01}} {{error "per-pin phi-R mismatch $pin"}}
  puts "DUAL_REF {corner} $pin arrival=$arrival R=$ref phi=$phase"
}}
report_checks -path_delay max -format full_clock_expanded -group_path_count 4
report_checks -path_delay min -format full_clock_expanded -group_path_count 4
puts "DUAL_PASS {corner} actual ETM both directions max/min; zero-wire API accounting only"
exit
'''
        if args.setup_only_diagnostic:
            text = text.replace('foreach kind {max min}', 'foreach kind {max}')
            text = text.replace('actual ETM both directions max/min', 'UNQUALIFIED actual ETM setup-only diagnostic; missing hold arcs')
        (args.out / f'probe_{corner}.tcl').write_text(text)
    (args.out / 'run.sh').write_text('''#!/bin/bash
set -euo pipefail
for corner in tt ff ss; do
 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta -exit /probe/probe_${corner}.tcl > /probe/probe_${corner}.log 2>&1
 grep -q "DUAL_PASS $corner" /probe/probe_${corner}.log
done
''')
    print(args.out)


if __name__ == '__main__':
    main()
