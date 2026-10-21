set plat /OpenROAD-flow-scripts/flow/platforms/asap7
set ::env(PLATFORM) asap7
set ::env(PLATFORM_DIR) $plat
set ::env(OT_HOLD_MM) 0
foreach l [glob $plat/lib/NLDM/*RVT_@CORNER_UPPER@*] {read_liberty $l}
foreach l [glob $plat/lib/NLDM/*_LVT_@CORNER_UPPER@_* $plat/lib/NLDM/*_SLVT_@CORNER_UPPER@_*] {if {![string match *FAKE* $l]} {read_liberty $l}}
@MACRO_LIB_READS@
read_db @DATABASE@
read_sdc /input/3_place.sdc
source $plat/setRC.tcl
set_propagated_clock [all_clocks]
source /src/tools/orfs_hold_mm.tcl

proc model_hard_entries {} {
  set b [ord::get_db_block];set out {}
  foreach {family count} {l 8 w 8 x 4} {
    for {set i 0} {$i<$count} {incr i} {
      set name [format {ck_%s[%d]} $family $i];set bt [$b findBTerm $name]
      if {$bt eq "NULL"} {error "MODEL missing exact hard clock entry $name"}
      set net [$bt getNet];set sinks {}
      foreach it [$net getITerms] {
        if {![$it isInputSignal]} continue
        if {![[[$it getInst] getMaster] isBlock]} {error "MODEL hard entry changed to standard cell $name"}
        lappend sinks [list [[$it getInst] getName] [[$it getMTerm] getName]]
      }
      if {[llength $sinks]!=1} {error "MODEL hard entry $name is not one-port/one-child"}
      lappend out [list $name [$net getName] $sinks]
    }
  }
  return $out
}
set original_hard [model_hard_entries]
proc model_measure {stage rc} {
  if {$rc eq "platform"} {source $::env(PLATFORM_DIR)/setRC.tcl} else {ot_rc_cal_apply spine}
  estimate_parasitics -placement
  sta::find_timing_paths -path_delay max -group_path_count 1
  foreach root {clk_w0 clk_w1 clk_w2 clk_w3} {
    set selected {}
    foreach c [all_clocks] {foreach src [get_property $c sources] {
      if {[get_full_name $src] eq $root} {lappend selected $c}
    }}
    if {[llength $selected]!=1} {error "MODEL ambiguous actual clock owner $root"}
    set c [lindex $selected 0];set pins [all_registers -clock [get_full_name $c] -clock_pins]
    set expected [expr {$root eq "clk_w3" ? 1052 : 1035}]
    if {[llength $pins]!=$expected} {error "MODEL $root ALL$expected realpins required got[llength $pins]"}
    set f [open /out/@CASE@_@CORNER@_${stage}_${rc}_${root}.tsv w]
    puts $f "clock\tpin\tarrival_max_rise_ps"
    set lo 1e30;set hi -1e30
    foreach p $pins {
      set v [get_property $p arrival_max_rise]
      if {![string is double -strict $v]} {error "MODEL invalid clock arrival [get_full_name $p] $v"}
      set lo [expr {min($lo,$v)}];set hi [expr {max($hi,$v)}]
      puts $f [join [list [get_full_name $c] [get_full_name $p] $v] "\t"]
    }
    close $f
    if {$hi<=0 || $hi<=$lo} {error "MODEL clock graph not propagated"}
    puts "E2_WRITE_MODEL case=@CASE@ corner=@CORNER@ stage=$stage rc=$rc source=$root ALL_pins=[llength $pins] min_ps=$lo max_ps=$hi spread_ps=[expr {$hi-$lo}]"
  }
}
if {@BUILD@} {
  set ::env(ADDITIONAL_LIBS) {@ALL_MACRO_LIBS@}
  set ::env(OT_SPINE_BIN) 60
  set ::env(OT_SPINE_LEAF_N) 8
  set ::env(OT_SPINE_SEG) 150
  set ::env(OT_SPINE_SYM) 1
  set ::env(OT_SPINE_CTS_REST) 0
  # Diagnostic exact prefix only; production's original23root contract remains unchanged.
  set ::env(OT_SPINE_PORTS) clk,clk_c,clk_ce,clk_w0,clk_w1,clk_w2,clk_w3
  source /src/physical/common_flow/clock_spine_child_ins.tcl
  if {"@CASE@" eq "candidate"} {source /src/tools/hbm_hc_clock_1021/e2_write_perimeter_spine.tcl} else {source /src/tools/hbm_hc_clock_1021/e2_perimeter_spine.tcl}
  if {![ot_clock_spines]} {error "MODEL prefix was not built"}
  if {![info exists ::ot_e2_perimeter_applied]} {error "MODEL qualifiedw1 topology absent"}
  if {"@CASE@" eq "candidate" && (![info exists ::ot_e2_write_applied] || [lsort [dict keys $::ot_e2_write_applied]] ne {clk_w2 clk_w3})} {error "MODEL remaining2writeroots notboth modeled"}
  model_measure before_repair platform
  model_measure before_repair calibrated
  source $plat/setRC.tcl
  estimate_parasitics -placement
  set before [llength [[ord::get_db_block] getInsts]]
  est::check_parasitics
  set maxwire [rsz::check_max_wire_length 0 true]
  foreach port {clk clk_c clk_ce clk_w0 clk_w1 clk_w2 clk_w3} {
    set net [[[ord::get_db_block] findBTerm $port] getNet]
    rsz::repair_net_cmd [sta::db_net_to_sta $net] $maxwire 0 0
  }
  ot_pg_standard_bind prefix_model_selected_repair
  set after [llength [[ord::get_db_block] getInsts]]
  puts "E2_PREFIX_REPAIR case=@CASE@ before_cells=$before after_cells=$after"
  model_measure after_repair platform
  model_measure after_repair calibrated
  source $plat/setRC.tcl
  if {$original_hard ne [model_hard_entries]} {error "MODEL changed one of20 exact hard clock entries"}
  write_db /out/@CASE@.odb
  puts "E2_PREFIX_BUILD_DONE case=@CASE@ unchanged_hard_entries=20"
} else {
  # Same TT-built physical clock tree, newly loaded real FF Liberty.
  model_measure after_repair platform
  model_measure after_repair calibrated
  if {$original_hard ne [model_hard_entries]} {error "MODEL changed20 hard entries at FF reload"}
}
