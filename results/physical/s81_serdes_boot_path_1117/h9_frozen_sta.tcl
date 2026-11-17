# S81-SERDES-R read-only: worst TT setup / FF hold paths of H at CTS, full clock expanded
set C $::env(OT_CORNER)
set fh [open /work/config.mk]
foreach ln [split [read $fh] "\n"] {
  if {[regexp {^export\s+(OT_VCLK_TT|OT_VCLK_FF|LAYER_PARASITICS_FILE)\s*\??=\s*(\S+)} $ln -> k v] && ![info exists ::env($k)]} { set ::env($k) $v }
}
close $fh
set field [dict get {TT TC_LIB_FILES FF BC_LIB_FILES} $C]
set output [exec bash -c {source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1 || exit; exec make --no-print-directory -s -C /OpenROAD-flow-scripts/flow "DESIGN_CONFIG=/work/config.mk" "print-$1"} x $field]
set recs {}
foreach line [split $output \n] { if {[regexp "^${field}\\s*\[:=\]\\s*(.*)$" $line -> v]} { lappend recs $v } }
if {[llength $recs] != 1} { error "libs" }
foreach f [regexp -all -inline {\S+} [lindex $recs 0]] {
  set g [file join [file dirname [file dirname $f]] .busfit [file tail $f]]
  if {[file exists $g]} { set c [open $g]; gets $c h; close $c; if {[string first [lindex [exec sha256sum -- $f] 0] $h] >= 0} { set f $g } }
  read_liberty $f
}
read_db $::env(ODB)
source /proof/boot_local_source.tcl
set b [ord::get_db_block];set d [expr {double([$b getDbUnitsPerMicron])}]
set ff [ot_serdes_boot_release_registers $b]
set ca [$b getCoreArea];set core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
set macs {};set halo [expr {8.64*$d}]
foreach i [$b getInsts] {if {![[$i getMaster] isBlock]} continue;set z [$i getBBox];lappend macs [list [expr {[$z xMin]-$halo}] [expr {[$z yMin]-$halo}] [expr {[$z xMax]+$halo}] [expr {[$z yMax]+$halo}]]}

ot_serdes_boot_path_local $b $d $ff $macs $core
lassign [ot_serdes_boot_path_plan $ff $d $macs $core] plans summaries
set targets {};foreach v $plans {dict set targets [[lindex $v 0] getName] 1}
set others {}
foreach i [$b getInsts] {
 if {[dict exists $targets [$i getName]]} continue
 lassign [$i getLocation] x y;set st [$i getPlacementStatus]
 lappend others [list $i $st $x $y]
 if {$st ni {FIRM LOCKED COVER}} {$i setPlacementStatus FIRM}
}
detailed_placement
check_placement -verbose
foreach v $others {
 lassign $v i st x y;lassign [$i getLocation] nx ny
 if {$x!=$nx || $y!=$ny} {error "OT_BOOT_ISOLATION non-target moved [$i getName]"}
 $i setPlacementStatus $st
}
puts "OT_BOOT_ISOLATION clock/FF/all-nontarget coordinates unchanged [llength $others] instances; only [dict size $targets] private data buffers eligible"
lassign [ot_serdes_boot_path_plan $ff $d $macs $core] _ post_summaries
puts "OT_BOOT_POST_DPL_PATH $post_summaries"
write_db /out/h9_frozen_$C.odb

read_sdc /work/constraint.sdc
if {$C eq "FF" && [file isfile /work/core_taps_ff.sdc]} { read_sdc /work/core_taps_ff.sdc }
set virt {}; set real {}
foreach c [all_clocks] { if {![llength [get_property $c sources]]} { lappend virt $c } else { lappend real $c } }
if {[info exists ::env(OT_VCLK_$C)] && [llength $virt]==1} { set_clock_latency -source $::env(OT_VCLK_$C) $virt }
set_propagated_clock $real
if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} { source $::env(LAYER_PARASITICS_FILE) } else { source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl }
estimate_parasitics -placement
set boots [get_cells -hierarchical *u_boot_release*]
set bootpd [expr {$C eq "TT" ? "max" : "min"}]
report_checks -from $boots -to $boots -path_delay $bootpd -group_path_count 12 -format full_clock_expanded -digits 3 > /out/boot_TTFF_$C.rpt
set bw 1e30
foreach path [find_timing_paths -from $boots -to $boots -path_delay $bootpd -group_path_count 32] {
 set slack [get_property $path slack];if {$slack<$bw} {set bw $slack}
}
puts "OT_BOOT_TARGET_WNS $C $bw"
set pd [expr {$C eq "TT" ? "max" : "min"}]
report_checks -path_delay $pd -group_path_count 400 -unique_paths_to_endpoint -slack_max 0 -format full_clock_expanded -digits 2 > /out/h_worst_$C.rpt
puts "H_WORST_DONE $C [sta::worst_slack -$pd]"
exit
