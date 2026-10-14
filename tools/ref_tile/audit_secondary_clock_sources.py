#!/usr/bin/env python3
"""Prepare read-only actual clock/data arrival diagnostics from frozen signoff Tcl.

All normal IO, input transitions, waveforms and physical inputs remain unchanged
in the primary comparison. A separately labelled zero-data-transition diagnostic
is never a signoff recommendation or clock slew policy.
"""
import argparse
import hashlib
import json
from pathlib import Path

BODY = r'''
proc snapshot {label} {
  puts "SOURCE_AUDIT_BEGIN $label"
  report_clock_properties [all_clocks]
  puts "SOURCE_AUDIT_SLACK $label setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
  foreach name {ck ckd} {
    set port [get_ports -quiet $name]
    if {![llength $port]} continue
    puts "SOURCE_AUDIT_PORT $label $name"
    report_arrival -digits 6 $port
    report_slews -digits 6 $port
  }
  set summary [dict create]
  dict set summary source_slew [get_property [get_ports ckd] slew_max_rise]
  foreach clk {core_clk ckd} {
    set values {}; set mins {}
    foreach pin [all_registers -clock $clk -clock_pins] {
      set a [get_property $pin arrival_max_rise]
      set b [get_property $pin arrival_min_rise]
      if {[string is double -strict $a]} {lappend values $a}
      if {[string is double -strict $b]} {lappend mins $b}
    }
    if {[llength $values]} {
      set sum 0; foreach a $values {set sum [expr {$sum+$a}]}
      set sorted [lsort -real $values]
      dict set summary $clk [expr {$sum/[llength $values]}]
      puts "SOURCE_AUDIT_METRIC $label $clk n=[llength $values] mean=[expr {$sum/[llength $values]}] min=[lindex $sorted 0] max=[lindex $sorted end]"
    }
  }
  set ref [get_pins {u_port.u_cq.o_d[189]$_DFF_P_/CLK}]
  puts "SOURCE_AUDIT_REFERENCE $label [get_full_name $ref]"
  report_arrival -digits 6 $ref
  report_slews -digits 6 $ref
  write_sdc /audit/constraints_LABEL.sdc
  puts "SOURCE_AUDIT_END $label"
  return $summary
}
set raw [snapshot actual_signoff]
# Preserve every source transition, clock waveform and normal IO constraint.
foreach clk [all_clocks] {
 foreach source [get_property $clk sources] {
  set name [get_full_name $source]
  if {![llength [get_ports -quiet $name]]} continue
  foreach ref [all_clocks] {
   unset_input_delay -clock $ref [get_ports $name]
   unset_input_delay -clock $ref -clock_fall [get_ports $name]
  }
  unset_input_delay [get_ports $name]
 }
}
read_sdc /src/physical/ref_tile/qfd_coll_xfifo_native/signoff.sdc
set clean [snapshot data_delays_cleared_same_slew]
if {abs([dict get $raw ckd]-[dict get $clean ckd]-EXPECTED_DELTA)>0.02} {error "clock-source DATA delay contamination mismatch"}
if {abs([dict get $raw core_clk]-[dict get $clean core_clk])>0.01} {error "primary clock physical arrival changed"}
if {abs([dict get $raw source_slew]-[dict get $clean source_slew])>0.01 || abs([dict get $clean source_slew]-150)>0.01} {error "source slew was changed while clearing clock-source data delays"}
# Calibration only: demonstrate whether set_input_transition affects clock
# versus data tags. This is never the primary correction or die slew policy.
set_input_transition 0 [get_ports ckd]
snapshot diagnostic_zero_data_transition
puts "SOURCE_AUDIT_PASS CORNER preserved physical clock/data comparison"
exit
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scripts', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--signoff-sdc', help='Diagnostic copied signoff path in the container; replaces only frozen signoff read')
    p.add_argument('--expected-data-delta', type=float, default=166.667)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    records = {}
    for corner, name in [('tt', 'native_signoff_probe.tcl'), ('ff', 'native_signoff_probe_ff.tcl'), ('ss', 'native_signoff_probe_ss.tcl')]:
        src = a.scripts / name
        text = src.read_text()
        prefix = text.split('puts "NATIVE_SIGNOFF_CONTEXT', 1)[0]
        if prefix == text or 'read_sdc /src/physical/ref_tile/qfd_coll_xfifo_native/signoff.sdc' not in prefix:
            raise ValueError(f'{src}: frozen executed signoff prefix missing')
        body = BODY.replace('CORNER', corner).replace('EXPECTED_DELTA', str(a.expected_data_delta))
        if a.signoff_sdc:
            original = '/src/physical/ref_tile/qfd_coll_xfifo_native/signoff.sdc'
            prefix = prefix.replace(original, a.signoff_sdc)
            body = body.replace(original, a.signoff_sdc)
        # Keep a distinct complete constraint snapshot for every state.
        body = body.replace('write_sdc /audit/constraints_LABEL.sdc', 'write_sdc "/audit/constraints_' + corner + '_${label}.sdc"')
        (a.out / f'audit_{corner}.tcl').write_text(prefix + body)
        records[corner] = {'executed_source_tcl': str(src), 'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'signoff_replacement': a.signoff_sdc, 'expected_data_delta': a.expected_data_delta, 'audit_sha256': hashlib.sha256((prefix+body).encode()).hexdigest()}
    (a.out/'audit_scripts_provenance.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
