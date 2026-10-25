# ELEM-HBM (gen_core_kit_hbm.py, from KVG3-CORES corners.tcl): re-time the routed core at one corner (RCX SPEF of
# 6_final) + R4 face-flop CK spread over the pin registers + ETM.
# env: OT_CORNER (tt|ff|ss) OT_LIBS OT_LEFS RES OT_MOD OT_OUT OT_PER (ps)
foreach l $::env(OT_LEFS) { read_lef $l }
foreach l $::env(OT_LIBS) { read_liberty $l }
read_db $::env(RES)/6_final.odb
read_sdc $::env(RES)/6_final.sdc
set_propagated_clock [get_clocks clk]
source /work/clock_family.tcl
if {[file exists $::env(RES)/6_final.spef]} { read_spef $::env(RES)/6_final.spef; set par spef } else { estimate_parasitics -placement; set par placement }
set_propagated_clock [get_clocks clk]
set c $::env(OT_CORNER)
proc nviol {kind} {
  set n 0
  foreach p [find_timing_paths -path_delay $kind -group_path_count 100000 -endpoint_path_count 1 -slack_max 0] { incr n }
  return $n
}
set ws [worst_slack -max]
set wh [worst_slack -min]
set tns [total_negative_slack -max]
set thns [total_negative_slack -min]
set nv [nviol max]
set nh [nviol min]
# R4 face-flop spread: rise CK arrival at every register within 2 buffers of a signal port (face_flops.tcl list)
proc ot_ck {pin} { ot_cf_refresh; return [ot_cf_wire $pin [get_clocks clk]] }
set arr {}
set ffl $::env(RES)/ot_face_flops.txt
if {[file exists $ffl]} {
  set fh [open $ffl r]
  foreach ln [split [read $fh] "\n"] {
    set n [lindex $ln 0]; if {$n eq ""} continue
    foreach cp {CLK CK clk} { set q [get_pins -quiet $n/$cp]; if {$q ne ""} break }
    if {$q eq ""} continue
    set a [ot_ck $q]; if {$a ne ""} { lappend arr $a }
  }
  close $fh
}
set arr [lsort -real $arr]
if {[llength $arr]} { set lo [lindex $arr 0]; set hi [lindex $arr end]; set sp [expr {$hi - $lo}] } else { set lo 0; set hi 0; set sp -1 }
set fh [open $::env(OT_OUT)/sta_$c.json w]
puts $fh "{\"corner\": \"$c\", \"parasitics\": \"$par\", \"setup_ws_ps\": $ws, \"setup_tns_ps\": $tns, \"setup_viol_endpoints\": $nv, \"hold_ws_ps\": $wh, \"hold_tns_ps\": $thns, \"hold_viol_endpoints\": $nh, \"face_flops\": [llength $arr], \"ck_lo_ps\": $lo, \"ck_hi_ps\": $hi, \"ck_spread_ps\": $sp}"
close $fh
report_checks -path_delay max -group_path_count 5 -format full_clock_expanded > $::env(OT_OUT)/sta_${c}_max.rpt
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > $::env(OT_OUT)/sta_${c}_min.rpt
puts "OT_CORNER $c setup_ws $ws tns $tns nviol $nv hold_ws $wh nviol $nh spread $sp n [llength $arr] ($par)"
set_clock_latency -source 0 [all_clocks]
write_timing_model -library_name $::env(OT_MOD)_$c $::env(OT_OUT)/$::env(OT_MOD)_$c.lib
puts "OT_ETM_DONE $c"
exit
