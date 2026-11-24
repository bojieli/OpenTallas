# Read-only forwarded-clock sender margin: min(data - fclk_out) per forwarded output, CPPR included. Nothing is written back.
# SINGLE CORNER ONLY. The kit SDC already makes fclk_out a generated clock of its source tap, so CPPR credits the shared tap.
# In a multi-corner (define_corners tc bc) context OpenSTA reports the bc launch against the tc generated-clock
# arrival with CPPR 0: kv3_io_ft_v1 ft3_o -107.8 instead of +80.6 ps (KIT-FWDCLK-SDC 11-23). A clock whose data launches from another
# tap keeps no credit: the tap window between two ports is a real check, not pessimism.
# columns: clk kind launch_tap source_tap m_ps data_ps fclk_ps credit_ps port
proc smp_require_single_corner {} {
  if {[info exists ::env(CORNERS)] && [string trim $::env(CORNERS)] ne ""} {
    error "sender_margin_probe: multi-corner context (CORNERS=$::env(CORNERS)): CPPR of generated clocks is lost; rerun with CORNERS="
  }
}
proc smp_classify {launch source} {
  if {$launch eq "" || $source eq ""} { return unknown }
  return [expr {$launch eq $source ? "same_tap" : "cross_tap"}]
}
# credit = reported slack - (data - clock); zero-external-delay check, so any remainder is CPPR
proc smp_credit {slack data clk} { return [expr {$slack - ($data - $clk)}] }
# generated clock name -> source tap, from the SDC text
proc smp_sources {txt} {
  set d [dict create]
  foreach l [split $txt "\n"] {
    if {[regexp {^\s*create_generated_clock\s} $l] && [regexp -- {-name\s+(\S+)} $l -> n] && [regexp -- {-source\s+\[get_ports\s+\{?([^\s\}\]]+)} $l -> s]} { dict set d $n $s }
  }
  return $d
}
proc smp_upport {net} {
  for {set n 0} {$n < 400 && $net ne "NULL" && $net ne ""} {incr n} {
    foreach b [$net getBTerms] { if {[$b getIoType] eq "INPUT"} { return [$b getName] } }
    set drv ""
    foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it } }
    if {$drv eq ""} { return "" }
    set ins {}
    foreach it [[$drv getInst] getITerms] { if {[$it isInputSignal]} { lappend ins $it } }
    if {[llength $ins] != 1} { return "" }
    set net [[lindex $ins 0] getNet]
  }
  return ""
}
# odb keeps bus-bit instance names escaped (q\[13\]$_DFF_P_), sta prints them plain
proc smp_odb_names {pn} { return [list $pn [string map [list {[} {\[} {]} {\]}] $pn]] }
proc smp_launch_tap {pathend} {
  foreach pin [[$pathend path] pins] {
    set pn [get_full_name $pin]
    if {[regexp {/CLK$} $pn]} {
      foreach name [smp_odb_names $pn] {
        set it [[ord::get_db_block] findITerm $name]
        if {$it ne "NULL"} { return [smp_upport [$it getNet]] }
      }
    }
  }
  return ""
}
proc smp_main {} {
  smp_require_single_corner
  source $::env(SCRIPTS_DIR)/load.tcl
  load_design $::env(VIS_ODB) $::env(VIS_SDC)
  estimate_parasitics -placement
  catch {set_propagated_clock [all_clocks]}
  set h [open $::env(RESULTS_DIR)/$::env(VIS_SDC)]; set src [smp_sources [read $h]]; close $h
  set jobs {}
  foreach c [all_clocks] {
    set n [get_name $c]; if {![string match fclk_out_* $n]} continue
    set b [string range $n 9 end]; set ps {}
    foreach pat [list $b "$b\[*\]" "cland_fstart_out_$b" "cland_fstart_out_$b\[*\]"] {
      foreach p [get_ports -quiet $pat] { if {[get_property $p direction] in {output out}} { lappend ps $p } }
    }
    if {![llength $ps]} { puts "SMP nodata $n"; continue }
    set_output_delay -min 0 -clock $c -add_delay $ps
    lappend jobs [list $n $ps]
  }
  set f [open $::env(SMP_OUT) w]
  puts $f "clk\tkind\tlaunch_tap\tsource_tap\tm_ps\tdata_ps\tfclk_ps\tcredit_ps\tport"
  foreach j $jobs {
    lassign $j n ps
    set w ""
    foreach pe [find_timing_paths -path_delay min -to $ps -group_path_count 4000 -unique_paths_to_endpoint] {
      set tn ""; catch {set tn [get_name [$pe target_clk]]}; if {$tn ne $n} continue
      if {$w eq "" || [$pe slack] < [$w slack]} { set w $pe }
    }
    if {$w eq ""} { puts "SMP nopath $n"; continue }
    set s [expr {[$w slack]*1e12}]; set d [expr {[$w data_arrival_time]*1e12}]; set k [expr {[$w target_clk_delay]*1e12}]
    set lt [smp_launch_tap $w]; set st ""; if {[dict exists $src $n]} { set st [dict get $src $n] }
    puts $f [format "%s\t%s\t%s\t%s\t%.1f\t%.1f\t%.1f\t%.1f\t%s" $n [smp_classify $lt $st] $lt $st $s $d $k [smp_credit $s $d $k] [get_full_name [$w pin]]]
  }
  close $f
  puts "SMP_DONE [llength $jobs]"
}
if {![info exists ::env(SMP_LIB_ONLY)]} { smp_main }
