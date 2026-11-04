"""Optional selected-histogram parent observer, inside an existing STD session.

Native data slack is collected before pair measurement zeroes uncertainty. This
observer does not qualify expansion or grant additional CPPR credit.
"""
import re

MASTER = 'ot_s81ph_native_sel_hist_bank'


def targets_tcl(instances):
    if not instances or len(set(instances)) != len(instances):
        raise ValueError('Explicit unique parent histogram instances required')
    if any(not value or any(c in value for c in '{}\n\r\t*?') for value in instances):
        raise ValueError('Parent boundary instances must be exact literal names')
    return '[list ' + ' '.join('{' + value + '}' for value in instances) + ']'


def std_tcl(instances, limit, corner):
    targets = targets_tcl(instances)
    if corner not in ('tt', 'ff') or not isinstance(limit, int) or limit < 0:
        raise ValueError('Invalid parent STD observer corner/query budget')
    if limit == 0:
        return ''
    return (r'''
# Selected actual histogram interfaces only. Existing original STD constraints
# are still active: this runs BEFORE ot_ps_zero_unc and never sets constraints.
set ::pb_targets @TARGETS@
set ::pb_limit @LIMIT@
set ::pb_master @MASTER@
set ::ot_ps_method tag
proc pb_exact {name} {
  return "^[regsub -all {[][(){}.*+?^$|\\]} $name {\\&}]$"
}
proc pb_pin {name} {
  set pins [get_pins -hierarchical -quiet -regexp [pb_exact $name]]
  if {[llength $pins] != 1 || [get_full_name [lindex $pins 0]] ne $name} {
    error "missing/nonunique exact parent data pin $name"
  }
  return [lindex $pins 0]
}
proc pb_selected {name} {
  foreach target $::pb_targets {if {[string first "$target/" $name] == 0} {return 1}}
  return 0
}
proc pb_clock_arrival {pin clock which pin_edge source} {
  set clocks [get_clocks -quiet $clock]
  if {[llength $clocks] != 1} {error "missing actual path clock"}
  set clk [lindex $clocks 0]
  lassign $source source_pin source_edge source_insertion
  set roots [get_property $clk sources]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set iterator [$vertex path_iterator $pin_edge $which]
    while {[$iterator has_next]} {
      set path [$iterator next]; set tag [$path tag]
      if {[lindex $tag 3] ne $clock || [lindex $tag 4] ne [expr {$source_edge eq "rise" ? "^" : "v"}] || [string first "(clock prop)" $tag] < 0} continue
      if {[info exists ::env(OT_PS_CORNER)] && [lindex $tag 1] ne $::env(OT_PS_CORNER)} continue
      set at [lsearch -all -exact $tag clk_src]
      if {[llength $at] == 1} {
        if {[lindex $tag [expr {[lindex $at 0]+1}]] ne $source_pin} continue
      } elseif {[llength $roots] != 1 || [get_full_name [lindex $roots 0]] ne $source_pin} {
        $iterator finish
        error "clock-pin arrival lacks an unambiguous actual source tag"
      }
      set phase [lindex [$clk waveform] [expr {$source_edge eq "rise" ? 0 : 1}]]
      set value [expr {([$path arrival]-$phase)*1e12}]
      if {[lsearch -real $values $value] < 0} {lappend values $value}
    }
    $iterator finish
  }
  if {[llength $values] != 1} {error "missing/nonunique source-specific clock-pin arrival"}
  return [lindex $values 0]
}
proc pb_path {sp dp delay} {
  set source [pb_pin $sp]; set capture [pb_pin $dp]
  set lr [ot_ps_clock_role $source clkq]
  set cr [ot_ps_clock_role $capture [expr {$delay eq "max" ? "setup" : "hold"}]]
  if {[llength $lr] != 2 || [llength $cr] != 2} {error "unresolved real sequential clock role"}
  lassign $lr lp le; lassign $cr cp ce
  set lpin [get_full_name $lp]; set cpin [get_full_name $cp]
  set lclks [lmap clk [get_property $lp clocks] {get_full_name $clk}]
  set cclks [lmap clk [get_property $cp clocks] {get_full_name $clk}]
  set paths [find_timing_paths -from $source -to $capture -path_delay $delay -group_path_count 1 -endpoint_path_count 1]
  if {![llength $paths]} {return [list NO_PATH]}
  set pe [lindex $paths 0]
  if {![$pe is_check] || [$pe is_latch_check]} {return [list UNSUPPORTED_CHECK]}
  # Copy ALL PathEnd values/tags before source arrival queries invalidate them.
  set actual_sp [get_full_name [get_property $pe startpoint]]
  set actual_dp [get_full_name [get_property $pe endpoint]]
  set role [$pe check_role]
  set slack [get_property $pe slack]
  set launch_tag [[$pe path] tag]
  set target_path [$pe target_clk_path]
  if {$target_path eq "NULL" || $target_path eq ""} {error "missing actual capture clock path"}
  set capture_tag [$target_path tag]
  set lc [lindex $launch_tag 3]; set cc [lindex $capture_tag 3]
  unset paths pe target_path
  if {$actual_sp ne $sp || $actual_dp ne $dp || $role ne [expr {$delay eq "max" ? "setup" : "hold"}]} {
    error "actual parent data path/check identity mismatch"
  }
  if {$lc ni $lclks || $cc ni $cclks} {error "actual path clock is not owned by its sequential clock pin"}
  if {![string is double -strict $slack] || [regexp -nocase {inf|nan} $slack]} {error "nonfinite native STD slack"}
  set launch_source [ot_ps_source_from_tag $launch_tag $lc $delay]
  set capture_source [ot_ps_source_from_tag $capture_tag $cc [expr {$delay eq "max" ? "min" : "max"}]]
  set launch_arrival [pb_clock_arrival $lp $lc $delay $le $launch_source]
  set capture_arrival [pb_clock_arrival $cp $cc [expr {$delay eq "max" ? "min" : "max"}] $ce $capture_source]
  return [concat [list EXACT_STD_PATH $actual_sp $actual_dp $role $slack $lpin $lc $le] $launch_source [list $cpin $cc $ce] $capture_source [list $launch_arrival $capture_arrival]]
}
set pb_relations {}
foreach target $::pb_targets {
  set cells [get_cells -hierarchical -quiet -regexp [pb_exact $target]]
  if {[llength $cells] != 1 || [get_full_name [lindex $cells 0]] ne $target || [get_property [lindex $cells 0] ref_name] ne $::pb_master} {
    error "selected actual histogram instance/master mismatch: $target"
  }
  foreach pin [get_pins -of_objects $cells] {
    set dir [get_property $pin direction]
    if {$dir eq "input" && [llength [ot_ps_clock_role $pin setup]] && [llength [ot_ps_clock_role $pin hold]]} {
      foreach source [get_fanin -to $pin -flat -startpoints_only] {
        if {[llength [ot_ps_clock_role $source clkq]] != 2} continue
        set sp [get_full_name $source]; set dp [get_full_name $pin]
        dict set pb_relations [list $sp $dp] [list $sp $dp]
      }
    } elseif {$dir eq "output" && [llength [ot_ps_clock_role $pin clkq]]} {
      foreach capture [get_fanout -from $pin -flat -endpoints_only] {
        if {[llength [ot_ps_clock_role $capture setup]] != 2 || [llength [ot_ps_clock_role $capture hold]] != 2} continue
        set sp [get_full_name $pin]; set dp [get_full_name $capture]
        dict set pb_relations [list $sp $dp] [list $sp $dp]
      }
    }
  }
}
set pb_out [open /out/parent_boundary_std_@CORNER@.tsv w]
puts $pb_out [join {launch_data_pin capture_data_pin delay status actual_startpoint actual_endpoint check_role native_std_slack_ps launch_clock_pin launch_clock launch_pin_edge launch_source_pin launch_source_edge launch_source_insertion_ps capture_clock_pin capture_clock capture_pin_edge capture_source_pin capture_source_edge capture_source_insertion_ps launch_clock_pin_arrival_ps capture_clock_pin_arrival_ps} \t]
set pb_queries 0; set pb_errors 0; set pb_missing 0; set pb_limited 0
set pb_cppr [sta::crpr_enabled]
dict for {key row} $pb_relations {
  lassign $row sp dp
  foreach delay {max min} {
    if {$pb_queries >= $::pb_limit} {
      set result [list LIMIT]; incr pb_limited
    } else {
      incr pb_queries
      if {[catch {set result [pb_path $sp $dp $delay]} reason]} {
        set result [list ERROR]; incr pb_errors
        puts "PARENT_BOUNDARY_PATH_ERROR $sp $dp $delay [string map [list \n { } \t { }] $reason]"
      } elseif {[lindex $result 0] ne "EXACT_STD_PATH"} {incr pb_missing}
    }
    # Fixed-width rows; absent evidence remains empty, never an inferred slack.
    while {[llength $result] < 19} {lappend result ""}
    puts $pb_out [join [concat [list $sp $dp $delay] $result] \t]
  }
}
close $pb_out
set pb_meta [open /out/parent_boundary_std_@CORNER@_counts.tsv w]
puts $pb_meta "phase\tORIGINAL_STD_BEFORE_ZERO_UNCERTAINTY"
puts $pb_meta "relations\t[dict size $pb_relations]"
puts $pb_meta "queries\t$pb_queries"
puts $pb_meta "errors\t$pb_errors"
puts $pb_meta "missing_paths\t$pb_missing"
puts $pb_meta "limited_paths\t$pb_limited"
puts $pb_meta "native_engine_cppr_enabled\t$pb_cppr"
puts $pb_meta "additional_clock_or_cppr_credit\tNONE"
close $pb_meta
puts "PARENT_BOUNDARY_STD @CORNER@ COMPLETE"
'''.replace('@TARGETS@', targets).replace('@LIMIT@', str(limit))
        .replace('@MASTER@', '{' + MASTER + '}').replace('@CORNER@', corner))
