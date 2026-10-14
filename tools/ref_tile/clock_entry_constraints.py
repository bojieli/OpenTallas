"""Fail-closed clock delivery for wires-only parents, using bound routed child pins.

An ETM already contains clock insertion in its launch/check arcs. Source latency
compensates that reference once; it must never be added back to the ETM arcs.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
import child_lint

CORNERS = ('tt', 'ff', 'ss')


def clocks(spec, period):
    if spec.get('clock') != 'entries':
        return f"create_clock -name core_clk -period {period} [get_ports {spec['clock_port']}]\n"
    lines = [f"create_clock -name core_clk -period {period}"]
    for i, port in enumerate(spec['clock_ports']):
        lines.append(f"create_clock -name ot_entry_{i} -period {period} [get_ports {{{port}}}]")
    return '\n'.join(lines) + '\n'


def generate(spec, root):
    if spec.get('clock') != 'entries':
        return ''
    refs, counts = {}, {}
    for child in spec['children']:
        view = Path(root) / child['view']
        master = view.name
        counts[master] = counts.get(master, 0) + int(child.get('count', 1))
        if master in refs:
            continue
        record = json.loads((view / 'insertion.json').read_text())
        pins = record.get('clock_measurements')
        if not pins:
            pin = record.get('lib_clock_pin')
            if not pin:
                # Legacy exports have one routed root named ck and one actual
                # Liberty clock pin named clk. Only a unique pin can bind it.
                clocks = child_lint.clock_insertion((view / f'{master}_tt.lib').read_text())
                if len(clocks) != 1 or not record.get('clock'):
                    raise ValueError(f'{view}: ambiguous routed clock pin association')
                pin = next(iter(clocks))
            pins = {pin: record}
        refs[master] = {}
        for pin, measured in pins.items():
            refs[master][pin] = {}
            for corner in CORNERS:
                lib = view / f'{master}_{corner}.lib'
                if not lib.is_file():
                    raise ValueError(f'{lib}: missing bound child ETM')
                clocks = child_lint.clock_insertion(lib.read_text())
                if pin not in clocks or set(clocks) != set(pins):
                    raise ValueError(f'{lib}: routed/Liberty clock pin association mismatch')
                data = measured.get(corner, {})
                b = data.get('boundary', {})
                values = [float(b[k]) for k in ('min', 'mean', 'max')]
                if not b.get('n') or data.get('errors') or not all(math.isfinite(x) for x in values):
                    raise ValueError(f'{view}/{pin}/{corner}: missing real routed boundary reference')
                if not values[0] <= values[1] <= values[2]:
                    raise ValueError(f'{view}/{pin}/{corner}: inconsistent boundary reference')
                refs[master][pin][corner] = values
    expected = sum(counts[m] * len(refs[m]) for m in refs)
    if expected != len(spec['clock_ports']):
        raise ValueError(f'entries: {expected} bound child clock pins, {len(spec["clock_ports"])} source ports')
    rows = []
    for master, pins in refs.items():
        for pin, corners in pins.items():
            row = ' '.join(f'{c} {{{" ".join(map(str, corners[c]))}}}' for c in CORNERS)
            rows.append(f'{{{master}/{pin}}} {{{row}}}')
    return ('# AUTO clock entries: bound insertion.json boundary refs; no ETM arc modification.\n'
            'set ::ot_ce_refs [dict create ' + ' '.join(rows) + ']\n'
            'set ::ot_ce_counts [dict create ' + ' '.join(f'{{{m}}} {n}' for m, n in counts.items()) + ']\n'
            'set ::ot_ce_ports {' + ' '.join('{' + p + '}' for p in spec['clock_ports']) + '}\n' + BODY)


BODY = r'''
proc ot_ce_corner {} {
  if {[info exists ::ot_ioref_scene] && $::ot_ioref_scene eq "BC"} { return ff }
  if {[info exists ::ot_ce_corner]} { return $::ot_ce_corner }
  foreach key {OT_MM_SETUP_CORNER CORNER} {
    if {[info exists ::env($key)]} {
      switch -nocase -- $::env($key) { TC - tt {return tt} BC - ff {return ff} WC - ss {return ss} }
    }
  }
  error "OT_ENTRIES: actual library corner is unknown (set ot_ce_corner tt/ff/ss)"
}
proc ot_ce_apply {} {
  set corner [ot_ce_corner]
  set clk [get_clocks core_clk]
  if {[llength $clk] != 1} { error "OT_ENTRIES: core_clk missing" }
  set sources {}; set names {}
  foreach c [get_clocks ot_entry_*] {
    foreach p [get_property $c sources] { lappend sources $p; lappend names [get_full_name $p] }
  }
  if {[lsort $names] ne [lsort $::ot_ce_ports]} { error "OT_ENTRIES: source clock coverage differs from spec" }
  foreach c [get_clocks ot_entry_*] { set_clock_latency -source 0 $c }
  sta::worst_slack_cmd max
  set rows {}; set seen {}; set counts {}
  foreach cell [get_cells -quiet -hierarchical *] {
    set master [get_property $cell ref_name]
    if {![dict exists $::ot_ce_counts $master]} continue
    dict incr counts $master
    foreach pin [get_pins -quiet -of_objects $cell] {
      set key "$master/[get_property $pin lib_pin_name]"
      if {![dict exists $::ot_ce_refs $key]} continue
      set ports [get_ports -quiet -of_objects [get_nets -quiet -of_objects $pin]]
      if {[llength $ports] != 1} { error "OT_ENTRIES: [get_full_name $pin] lacks one direct top clock port" }
      set port [lindex $ports 0]; set name [get_full_name $port]
      if {$name ni $::ot_ce_ports || [dict exists $seen $name]} { error "OT_ENTRIES: duplicate or undeclared source $name" }
      dict set seen $name 1
      set wire [get_property $pin arrival_max_rise]
      if {![string is double -strict $wire]} { error "OT_ENTRIES: missing entry wire clock arrival on [get_full_name $pin]" }
      lassign [dict get $::ot_ce_refs $key $corner] lo mean hi
      set clock [get_clocks ot_entry_[lsearch -exact $::ot_ce_ports $name]]
      if {[llength $clock] != 1} { error "OT_ENTRIES: $name has no unique related clock" }
      set ttmean [lindex [dict get $::ot_ce_refs $key tt] 1]
      lappend rows [list $port $pin $wire $lo $mean $hi $clock $ttmean]
    }
  }
  dict for {m n} $::ot_ce_counts {
    if {![dict exists $counts $m] || [dict get $counts $m] != $n} { error "OT_ENTRIES: bound child count mismatch $m" }
  }
  if {[dict size $seen] != [llength $::ot_ce_ports]} { error "OT_ENTRIES: incomplete actual child/source coverage" }
  set ref 0
  foreach row $rows { lassign $row p pin wire lo mean hi; set ref [expr {max($ref, $wire + $mean)}] }
  set low {}; set high {}; set lowclocks {}; set highclocks {}
  foreach row $rows {
    lassign $row p pin wire lo mean hi clock ttmean
    if {$ttmean > 300} { lappend highclocks $clock } else { lappend lowclocks $clock }
    set latency [expr {$ref - $wire - $mean}]
    set_clock_latency -source $latency $clock
    lappend low [expr {$ref + $lo - $mean}]; lappend high [expr {$ref + $hi - $mean}]
    puts "OT_ENTRIES COMP $corner [get_full_name $p] -> [get_full_name $pin] wire=$wire R=$mean latency=$latency phi=$ref"
  }
  # Every entry is synchronous and related. Reserve die skew on internal hops;
  # no asynchronous groups, false paths or ETM insertion add-back.
  set_clock_uncertainty -setup 150 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  set_clock_uncertainty -hold 75 -from [get_clocks ot_entry_*] -to [get_clocks ot_entry_*]
  if {[llength $lowclocks] && [llength $highclocks]} {
    set_clock_uncertainty -setup 210 -from $lowclocks -to $highclocks
    set_clock_uncertainty -setup 210 -from $highclocks -to $lowclocks
  }
  # Preserve measured boundary spread: balancing the mean does not erase the
  # earliest/latest physical boundary arrivals or change ETM setup/hold arcs.
  set lmin [lindex [lsort -real $low] 0]; set lmax [lindex [lsort -real $high] end]
  unset_input_delay [all_inputs]; unset_output_delay [all_outputs]
  set sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]
  set hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  set_input_delay [expr {166.667+$lmax+$sk}] -max -clock $clk [all_inputs -no_clocks]
  set hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
  set_input_delay [expr {$lmin-$hki}] -min -clock $clk [all_inputs -no_clocks]
  set_output_delay [expr {166.667-$lmax+$sk}] -max -clock $clk [all_outputs]
  set_output_delay [expr {-$lmin-$hk}] -min -clock $clk [all_outputs]
  if {[info exists ::env(OT_IO_INTER)] && $::env(OT_IO_INTER) ne ""} {
    foreach pattern [split $::env(OT_IO_INTER) ","] {
      set_input_delay [expr {166.667+$lmax+150}] -max -clock $clk [get_ports -quiet $pattern -filter "direction == input"]
      set_output_delay [expr {166.667-$lmax+150}] -max -clock $clk [get_ports -quiet $pattern -filter "direction == output"]
    }
  }
  puts "OT_ENTRIES COMP DONE $corner [llength $rows] entries phi=$ref boundary=$lmin..$lmax"
}
ot_ce_apply
'''
