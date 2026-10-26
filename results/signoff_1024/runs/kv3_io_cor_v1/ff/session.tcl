
proc so {k args} { puts "SO $k [join $args { }]" }
proc so_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f [sta::time_sta_ui $t]] }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_FF_*] { read_liberty $l }
foreach l [glob -nocomplain /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }

read_db /base/6_final.odb
read_spef /base/6_final.spef
read_sdc /sdc/golden.sdc
set_propagated_clock [all_clocks]
so CORNER FF
so PARASITICS spef
so DESIGN [current_design]
so CELLS [llength [get_cells *]]
# ---- ports (for sdc_lint context) and IO virtual clock ----
set so_ck_ports {}
foreach c [all_clocks] { foreach s [get_property $c sources] { if {[llength [get_ports -quiet [get_full_name $s]]]} { lappend so_ck_ports [get_full_name $s] } } }
set so_ck_ports [lsort -unique $so_ck_ports]
so CLOCK_PORTS {*}$so_ck_ports
set so_din {}
foreach p [all_inputs] { if {[get_full_name $p] ni $so_ck_ports} { lappend so_din $p } }
so INPUTS {*}[lsort -unique [lmap p $so_din {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
so OUTPUTS {*}[lsort -unique [lmap p [all_outputs] {regsub {\[[0-9]+\]$} [get_full_name $p] {}}]]
set so_vclk {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend so_vclk $c } }
so CLOCKS {*}[lmap c [all_clocks] {get_full_name $c}]
so VCLKS {*}[lmap c $so_vclk {get_full_name $c}]
foreach c [all_clocks] { so PERIOD [get_full_name $c] [get_property $c period] }
# ---- timing with the block's own SDC ----
proc so_timing {tag} {
  so ${tag}_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
  so ${tag}_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
  so ${tag}_TNS_MAX [so_ps [sta::total_negative_slack_cmd max]]
  so ${tag}_TNS_MIN [so_ps [sta::total_negative_slack_cmd min]]
  so ${tag}_NVIOL_MAX [sta::endpoint_violation_count max]
  so ${tag}_NVIOL_MIN [sta::endpoint_violation_count min]
}
so_timing SDC
puts "SO_PATH_BEGIN SDC_MAX"
report_checks -path_delay max -format full_clock_expanded -digits 2 -fields {slew cap fanout}
puts "SO_PATH_END"
# ---- standard boundary-hold overlay (4b7b2b3e64 kit standard) ----
if {[llength $so_vclk] == 1} {
  if {[llength $so_din]} { set_input_delay -min [expr {-40}] -clock [lindex $so_vclk 0] $so_din }
  if {[llength [all_outputs]]} { set_output_delay -min 0 -clock [lindex $so_vclk 0] [all_outputs] }
  so OVERLAY applied [get_full_name [lindex $so_vclk 0]] in_min -40 out_min 0
} else {
  so OVERLAY skipped vclks [llength $so_vclk]
}
so_timing STD
puts "SO_PATH_BEGIN STD_MIN"
report_checks -path_delay min -format full_clock_expanded -digits 2
puts "SO_PATH_END"
# ---- DRV ----
so SLEW_VIOL [sta::max_slew_violation_count]
so CAP_VIOL [sta::max_capacitance_violation_count]
set so_fo_max 0; set so_fo_n 0; set so_fo_worst ""
foreach n [get_nets -hierarchical *] {
  set k [llength [get_pins -quiet -of_objects $n -filter "direction==input"]]
  if {$k > $so_fo_max} { set so_fo_max $k; set so_fo_worst [get_full_name $n] }
  if {$k > 64} { incr so_fo_n }
}
so FANOUT_MAX $so_fo_max $so_fo_worst
so FANOUT_VIOL $so_fo_n
puts "SO_PATH_BEGIN DRV"
report_check_types -max_slew -max_capacitance -violators -max_count 10
puts "SO_PATH_END"
# ---- constraint coverage ----
puts "SO_PATH_BEGIN CHECK_SETUP"
check_setup -verbose -unconstrained_endpoints -no_clock -loops -generated_clocks -multiple_clock
puts "SO_PATH_END"
# ---- OCV sensitivity (information only) ----
set_timing_derate -late 1.05
set_timing_derate -early 0.95
so OCV5_WNS_MAX [so_ps [sta::worst_slack_cmd max]]
so OCV5_WNS_MIN [so_ps [sta::worst_slack_cmd min]]
unset_timing_derate
# ---- clock: active-edge arrival at register clock pins, pin flops ----
# Actual OpenSTA clock ancestry and physical propagated-clock measurements.
# OpenSTA's Clock wrapper has no master accessor. Its canonical SDC exporter
# resolves inferred masters; evaluate only its generated-clock declarations in
# an isolated safe interpreter, never replay constraints in the live session.
proc ot_cf_record {args} {
  set ni [lsearch -exact $args -name]; set mi [lsearch -exact $args -master_clock]
  set si [lsearch -exact $args -source]
  if {$ni < 0 || $mi < 0 || $si < 0} {error "OT_CLOCK_FAMILY: canonical generated clock lacks resolved name/master/source"}
  set name [lindex $args [expr {$ni+1}]]
  set master [lindex $args [expr {$mi+1}]]; set source [lindex $args [expr {$si+1}]]
  if {[llength $master] != 1 || [llength $source] != 1 || [dict exists $::ot_cf_master $name]} {
    error "OT_CLOCK_FAMILY: ambiguous generated clock $name"
  }
  set parent [get_full_name $master]
  if {[sta::object_type $source] eq "Port"} {set source [sta::get_port_pin $source]}
  set owners {}; foreach c [get_property $source clocks] {lappend owners [get_full_name $c]}
  if {[lsort -unique $owners] ne [list $parent]} {
    error "OT_CLOCK_FAMILY: generated source of $name has owners $owners, expected $parent"
  }
  dict set ::ot_cf_master $name $parent
}
proc ot_cf_refresh {} {
  set ::ot_cf_master {}; set ::ot_cf_active_cache {}; set generated {}
  foreach c [all_clocks] {if {[$c is_generated]} {lappend generated [get_full_name $c]}}
  if {![llength $generated]} {return}
  sta::update_generated_clks
  # Iterating paths alone does not initialize generated source insertion.
  # A native timing search fills the complete root-to-bank physical arrivals.
  find_timing_paths -group_path_count 1
  set fd [file tempfile path ot-clock-family-]; close $fd
  set ip [interp create -safe]
  try {
    write_sdc $path
    foreach cmd {get_ports get_pins get_clocks} {interp alias $ip $cmd {} $cmd}
    interp alias $ip create_generated_clock {} ot_cf_record
    set fd [open $path r]; set text [read $fd]; close $fd
    set command {}
    foreach line [split $text \n] {
      append command $line \n
      if {![info complete $command]} continue
      if {[regexp {^\s*create_generated_clock\s} $command]} {interp eval $ip $command}
      set command {}
    }
    if {[string trim $command] ne ""} {error "OT_CLOCK_FAMILY: incomplete canonical SDC"}
    if {[lsort [dict keys $::ot_cf_master]] ne [lsort $generated]} {error "OT_CLOCK_FAMILY: incomplete generated-clock ancestry"}
    foreach c $generated {ot_cf_root $c}
  } finally {interp delete $ip; file delete -force $path}
}
proc ot_cf_root {name} {
  set seen {}
  while {[dict exists $::ot_cf_master $name]} {
    if {$name in $seen} {error "OT_CLOCK_FAMILY: ancestry cycle $name"}
    lappend seen $name; set name [dict get $::ot_cf_master $name]
  }
  set c [get_clocks -quiet $name]
  if {[llength $c] != 1 || [$c is_generated]} {error "OT_CLOCK_FAMILY: unresolved root $name"}
  return $name
}
proc ot_cf_pins {root} {
  set name [get_full_name $root]
  if {[ot_cf_root $name] ne $name} {error "OT_CLOCK_FAMILY: requested root $name is generated"}
  # Ordinary roots retain the existing all_registers ownership query. In
  # pre-CTS ideal sessions get_property(pin, clocks) can be empty on check-only
  # macro entries; all_registers -clock still proves actual graph membership.
  if {![dict size $::ot_cf_master]} {
    set pins [all_registers -clock_pins -clock $root]; set owners {}
    foreach p $pins {dict set owners [get_full_name $p] $root}
    return [list $pins $owners]
  }
  set pins {}; set owners {}
  foreach c [all_clocks] {
    if {[ot_cf_root [get_full_name $c]] ne $name} continue
    foreach p [all_registers -clock_pins -clock $c] {
      set pn [get_full_name $p]
      set actual {}; foreach owner [get_property $p clocks] {lappend actual [get_full_name $owner]}
      if {[llength [lsort -unique $actual]] != 1} {
        error "OT_CLOCK_FAMILY: ambiguous clock sink $pn ($actual)"
      }
      if {[ot_cf_root [lindex $actual 0]] ne $name} {error "OT_CLOCK_FAMILY: foreign sink $pn"}
      if {[lindex $actual 0] ne [get_full_name $c]} continue
      if {[dict exists $owners $pn]} {error "OT_CLOCK_FAMILY: duplicate sink $pn"}
      dict set owners $pn $c; lappend pins $p
    }
  }
  return [list $pins $owners]
}
proc ot_cf_active {p} {
  set cell [get_cells -of_objects $p]
  set key [list [get_property $cell ref_name] [get_property $p lib_pin_name]]
  if {[dict exists $::ot_cf_active_cache $key]} {return [dict get $::ot_cf_active_cache $key]}
  sta::redirect_string_begin
  set failed [catch {report_edges -from $p} message]
  set report [sta::redirect_string_end]; set on 0; set edges {}
  if {$failed} {error "OT_CLOCK_FAMILY: active-edge query failed [get_full_name $p]: $message"}
  foreach line [split $report \n] {
    if {[regexp {^\S} $line]} {set on [regexp {(Clk|En) to Q} $line]; continue}
    if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
  }
  if {![llength $edges] && [llength [info commands ord::get_db]]} {
    # Check-only hard entries (notably SRAM write clocks) have no clock-to-Q
    # arc. Only an actual physical BLOCK with unique loaded Liberty clock
    # timing-check edges is supported; missing soft-register arcs still fail.
    set master [[ord::get_db] findMaster [get_property $cell ref_name]]
    if {$master ne "NULL" && [$master isBlock]} {
      set on 0
      foreach line [split $report \n] {
        if {[regexp {^\S} $line]} {set on [regexp { (setup|hold|recovery|removal)$} $line]; continue}
        if {$on && [regexp {^\s+([\^v])\s+->} $line -> edge] && $edge ni $edges} {lappend edges $edge}
      }
    }
  }
  if {[llength $edges] != 1} {error "OT_CLOCK_FAMILY: missing unique active clock edge [get_full_name $p] ($edges)"}
  set active [expr {[lindex $edges 0] eq "^" ? "rise" : "fall"}]
  dict set ::ot_cf_active_cache $key $active
  return $active
}
proc ot_cf_wire {pin clock {scene {}}} {
  if {$scene eq ""} {set scene [get_property [sta::cmd_scene] name]}
  set cn [get_full_name $clock]; set waveform {}
  foreach time [$clock waveform] {lappend waveform [sta::time_sta_ui $time]}
  if {[llength $waveform] != 2} {error "OT_CLOCK_FAMILY: invalid waveform $cn"}
  foreach time $waveform {if {![string is double -strict $time] || [regexp -nocase {inf|nan} $time]} {error "OT_CLOCK_FAMILY: nonfinite waveform $cn"}}
  set transition [ot_cf_active $pin]; set marker [expr {$transition eq "rise" ? "^max" : "vmax"}]
  set values {}
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    set paths [$vertex path_iterator $transition max]
    while {[$paths has_next]} {
      set path [$paths next]; set tag [$path tag]; set edge [lindex $tag 4]
      if {[lindex $tag 1] ne $scene || [lindex $tag 2] ne $marker || [lindex $tag 3] ne $cn || $edge ni {^ v} || [string first "(clock prop)" $tag] < 0} continue
      set arrival [sta::time_sta_ui [$path arrival]]
      if {![string is double -strict $arrival] || [regexp -nocase {inf|nan} $arrival]} {$paths finish; error "OT_CLOCK_FAMILY: nonfinite clock arrival [get_full_name $pin]"}
      lappend values [expr {$arrival-[lindex $waveform [expr {$edge eq "^" ? 0 : 1}]]}]
    }
    $paths finish
  }
  if {[llength $values] != 1} {error "OT_CLOCK_FAMILY: missing unique physical clock arrival [get_full_name $pin] clock=$cn scene=$scene"}
  return [lindex $values 0]
}

set so_regs {}
foreach p [all_registers -clock_pins] { dict set so_regs [regsub {/[^/]+$} [get_full_name $p] {}] $p }
set so_bnd {}
set so_data {}
set so_async {}
foreach p [all_registers -async_pins] { dict set so_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] { set n [get_full_name $p]; if {![dict exists $so_async $n]} { dict set so_data $n 1 } }
if {[llength $so_din]} {
  foreach p [get_fanout -from $so_din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $so_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
if {[llength [all_outputs]]} {
  foreach p [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $so_regs $i]} { dict set so_bnd $i 1 }
  }
}
foreach c [all_clocks] { if {[llength [get_property $c sources]]} { set_clock_latency -source 0 $c } }
set so_ck_err 0
set so_cf [llength [info commands ot_cf_wire]]
if {$so_cf} { catch {ot_cf_refresh} }
dict for {i p} $so_regs {
  set cl [get_property $p clocks]
  if {[llength $cl] != 1} { incr so_ck_err; continue }
  set a ""
  if {$so_cf} { catch {set a [ot_cf_wire $p [lindex $cl 0]]} }
  if {$a eq ""} {
    catch {set a [sta::time_sta_ui [get_property $p arrival_max_rise]]}
  }
  if {$a eq "" || ![string is double -strict $a]} { incr so_ck_err; continue }
  puts "SO_CK [expr {[dict exists $so_bnd $i] ? 1 : 0}] [format %.2f $a] [get_full_name [lindex $cl 0]]"
}
so CK_ERRORS $so_ck_err
so DONE 1
exit
