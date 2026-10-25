# PATH-QC-PROGVMR read-only pair/clock probe (session setup = kit hold_grt_s6.tcl; never writes the DB).
# env: OT_PROBE_ODB, OT_PROBE_LIB (macro ff lib), OT_PROBE_TAG, OT_PROBE_FROM (glob of launch cells for the pair table, optional)
set R $::env(RESULTS_DIR)
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_FF_nldm_*.lib*]] { read_liberty $f }
read_liberty /work/macros/$::env(OT_PROBE_LIB)
read_db $R/$::env(OT_PROBE_ODB)
read_sdc /work/constraint.sdc
set ::env(OT_VCLK_CORNER) ff
source /work/cf/main/vclk_corner.tcl
source /work/cf/rc_cal.tcl
set_global_routing_layer_adjustment M2-M5 0.25
set_routing_layers -clock M4-M5
set_routing_layers -signal M2-M5
if {[info exists ::env(OT_PROBE_GUIDE)]} { read_guides $R/$::env(OT_PROBE_GUIDE); puts "PROBE parasitics from $::env(OT_PROBE_GUIDE)" } else { pin_access; global_route -congestion_iterations 30 }
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
source /work/cf/mscts_core.tcl
if {[info exists ::env(OT_MSCTS_CORR)]} { ot_ms_assign_corr ff }
ot_ms_report probe_ff
ot_ms_pinmap
set T $::env(OT_PROBE_TAG)
set O /work/progvmr; file mkdir $O
set blk [ord::get_db_block]; set dbu [$blk getDefUnits]
proc k {n} { return [string map {\\ {}} $n] }
proc inst_of {pinname} { set n [k $pinname]; if {[string first / $n] < 0} {return ""}; return [regsub {/[^/]+$} $n {}] }
proc fi {iname} { global blk; set i [$blk findInst $iname]; if {$i eq "NULL"} { regsub -all {([][])} $iname {\\\1} e; set i [$blk findInst $e] }; return $i }
proc loc {iname} { global blk dbu; if {$iname eq ""} {return "port port"}; set i [fi $iname]; if {$i eq "NULL"} {return "? ?"}; set b [$i getBBox]; return [format "%.2f %.2f" [expr {([$b xMin]+[$b xMax])/2.0/$dbu}] [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]] }
proc ck {iname} { if {$iname eq ""} {return -}; foreach c {CLK clk} { set a [ot_ms_arr "$iname/$c" min]; if {$a ne ""} {return [format %.1f $a]} }; return - }
proc leaf {iname} { global blk; if {$iname eq ""} {return -}; set i [fi $iname]; if {$i eq "NULL"} {return ?}
  foreach c {CLK clk} { set it [$i findITerm $c]; if {$it eq "NULL" || $it eq ""} continue; set n [$it getNet]; if {$n eq "NULL"} {return ?}
    foreach x [$n getITerms] { if {[$x isOutputSignal]} { return [[$x getInst] getName] } } }; return ? }
proc dist {a b} { if {![string is double -strict [lindex $a 0]] || ![string is double -strict [lindex $b 0]]} {return -}; return [format %.1f [expr {abs([lindex $a 0]-[lindex $b 0])+abs([lindex $a 1]-[lindex $b 1])}]] }
# PathEnd objects are invalidated by any later STA query (pin arrivals), so collect names + slack first, then annotate.
proc collect {ps} { set out {}; foreach p $ps { lappend out [list [get_property $p slack] [get_full_name [get_property $p startpoint]] [get_full_name [get_property $p endpoint]]] }; return $out }
proc rows {f lst} {
  foreach r $lst { lassign $r sl sn en
    set si [inst_of $sn]; set ei [inst_of $en]; set a [loc $si]; set b [loc $ei]
    puts $f "[format %.2f $sl]\t[k $sn]\t[k $en]\t$a\t$b\t[dist $a $b]\t[ck $si]\t[ck $ei]\t[leaf $si]\t[leaf $ei]"; flush $f }
}
set hdr "slack\tstart\tend\tstart_xy\tend_xy\tdist_um\tlaunch_ck_ff\tcapture_ck_ff\tlaunch_leaf\tcapture_leaf"
set f [open $O/${T}_fail_eps.tsv w]; puts $f $hdr; flush $f
set lst [collect [find_timing_paths -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0.0]]
rows $f $lst
close $f; puts "PROBE fail_eps done"
if {[info exists ::env(OT_PROBE_FROM)]} {
  set f [open $O/${T}_pairs.tsv w]; puts $f $hdr; flush $f
  set lst {}
  foreach c [get_cells -quiet $::env(OT_PROBE_FROM)] {
    if {[get_pins -quiet [get_full_name $c]/CLK] eq ""} continue
    lappend lst {*}[collect [find_timing_paths -path_delay min -from [get_pins [get_full_name $c]/CLK] -to [all_registers -data_pins] -endpoint_path_count 2 -group_path_count 2]]
  }
  rows $f $lst
  close $f; puts "PROBE pairs done"
}
set f [open $O/${T}_leaf_ck.tsv w]; puts $f "leaf\tleaf_xy\tn\tck_ff_mean\tck_ff_min\tck_ff_max"
foreach i [$blk getInsts] {
  set nm [$i getName]; if {![string match clkbuf_leaf_* $nm]} continue
  set o ""; foreach it [$i getITerms] { if {[$it isOutputSignal]} { set o [$it getNet] } }
  if {$o eq "" || $o eq "NULL"} continue
  set v {}; foreach x [$o getITerms] { if {[$x isInputSignal]} { set ii [[$x getInst] getName]; set a [ck $ii]; if {$a ne "-"} { lappend v $a } } }
  if {![llength $v]} continue
  set s 0.0; foreach a $v { set s [expr {$s+$a}] }; set v [lsort -real $v]
  puts $f "$nm\t[loc $nm]\t[llength $v]\t[format %.1f [expr {$s/[llength $v]}]]\t[lindex $v 0]\t[lindex $v end]"
}
close $f; puts "PROBE_DONE"
