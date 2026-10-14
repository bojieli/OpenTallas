#!/usr/bin/env python3
"""Build actual-ETM, all-entry STA probe (zero-wire calibration, not route signoff).

Usage: probe_clock_entries.py SPEC --root PATH --out DIR
Run each out/probe_<corner>.tcl with OpenSTA/OpenROAD through ot-run. Probe checks
all source associations and numerical phi compensation. An actual rr4 pair gives
setup AND hold paths; this pair is required by the current Qwen region fixture.
"""
import argparse
import json
from pathlib import Path
import clock_entry_constraints as C


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('spec', type=Path)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(); s = json.loads(a.spec.read_text()); a.out.mkdir(parents=True, exist_ok=True)
    children = []
    for child in s['children']:
        for _ in range(child.get('count', 1)):
            children.append(child)
    ports = [f'c{i}' for i in range(len(s['clock_ports']))]
    test = dict(s, clock_ports=ports, clock_port=ports[0])
    v = ['module probe(input ' + ','.join(ports) + ');', 'wire [511:0] hop;']
    n = 0
    for i, child in enumerate(children):
        view = a.root / child['view']; rec = json.loads((view/'insertion.json').read_text())
        pins = list(rec.get('clock_measurements', {})) or [rec.get('lib_clock_pin') or 'clk']
        con = [f'.{p}({ports[n+j]})' for j,p in enumerate(pins)]; n += len(pins)
        if i == 0 and view.name == 'ot_qfd_vm_rr4_t': con.append('.t1(hop)')
        if i == 1 and view.name == 'ot_qfd_vm_rr4_t': con.append(".bx({1536'b0,hop})")
        v.append(f'{view.name} u{i}(' + ','.join(con) + ');')
    v.append('endmodule'); (a.out/'probe.v').write_text('\n'.join(v)+'\n')
    body = C.generate(test, a.root)
    for corner in C.CORNERS:
        libs = sorted({str(a.root/c['view']/(Path(c['view']).name+f'_{corner}.lib')) for c in children})
        script = '\n'.join('read_liberty {'+p+'}' for p in libs)+'\n'
        script += 'read_verilog {'+str(a.out/'probe.v')+'}\nlink_design probe\n'
        script += C.clocks(test,833.333) + 'set_propagated_clock [get_clocks ot_entry_*]\n'
        script += 'set_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\n'
        script += f'set ::ot_ce_corner {corner}\n'
        script += '''foreach kind {max min} {
  set path [find_timing_paths -from [get_pins u0/t1*] -to [get_pins u1/bx*] -path_delay $kind -group_path_count 1]
  if {![llength $path]} { error "PROBE missing uncompensated ETM $kind path" }
  dict set before $kind [get_property [lindex $path 0] slack]
}
''' + body
        script += r'''
sta::worst_slack_cmd max
foreach cell [get_cells -hierarchical *] {
  set m [get_property $cell ref_name]
  foreach pin [get_pins -of_objects $cell] {
    set key "$m/[get_property $pin lib_pin_name]"
    if {![dict exists $::ot_ce_refs $key]} continue
    set arrival [get_property $pin arrival_max_rise]
    set mean [lindex [dict get $::ot_ce_refs $key $::ot_ce_corner] 1]
    lappend actual [expr {$arrival + $mean}]
  }
}
set sorted [lsort -real $actual]
if {[llength $actual] != [llength $::ot_ce_ports] || abs([lindex $sorted end]-[lindex $sorted 0]) > 0.01} {
  error "PROBE compensation/coverage failed"
}
foreach kind {max min} {
  set paths [find_timing_paths -from [get_pins u0/t1*] -to [get_pins u1/bx*] -path_delay $kind -group_path_count 1]
  if {![llength $paths]} { error "PROBE missing actual ETM $kind path" }
  set slack [get_property [lindex $paths 0] slack]
  # u0/u1 use the same actual rr4 view, so insertion cancels. Source balancing
  # reserves exactly90ps setup and50ps hold die skew.
  set expected [expr {[dict get $before $kind] - ($kind eq "max" ? 90.0 : 50.0)}]
  if {abs($slack-$expected) > 0.02} { error "PROBE $kind numerical slack mismatch $slack vs $expected" }
  puts "PROBE_PATH $kind $slack expected=$expected"
}
puts "PROBE_PASS $::ot_ce_corner [llength $actual] actual child clock pins, phi spread <0.01ps; setup and hold paths checked"
exit
'''
        (a.out/f'probe_{corner}.tcl').write_text(script)
    print(a.out)


if __name__ == '__main__': main()
