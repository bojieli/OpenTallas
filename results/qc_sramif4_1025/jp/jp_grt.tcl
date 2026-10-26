# PATH-QC-SRAMIF4 joint TT/FF finishing pads on the fullhalf PROG 5_1_grt (copy-out; kit mounted read-only).
# Adopts Codex 5d3ea4fbd joint selector result {P0 1 R0W 1 R2E 1 S1 1}; PAD master from env (BUFx4 = Codex, BUFx16f = finer step).
# No data/FF movement; pads only on the tap input nets; then full GRT with the kit profile and MCMM tap windows.
define_corners TT FF
foreach C {TT FF} {
 foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] {read_liberty -corner $C $f}
 foreach f [glob /work/macros/*_[string tolower $C].lib] {read_liberty -corner $C $f}
}
set B $::env(PHASE_NICK)
read_db /work/run/results/asap7/$B/base/5_1_grt.odb
read_sdc /work/constraint.sdc
source /pk/shallow_clock.tcl
source /pk/local_clock_depth.tcl
set b [ord::get_db_block]
set ::ot_dtsh::blk $b
set PAD $::env(JP_PAD)
set ::ot_dtsh::master [[ord::get_db] findMaster $PAD]
if {$::ot_dtsh::master eq "NULL"} {error "no master $PAD"}
ot_dtsh::capture
set u [$b getDbUnitsPerMicron]
set added {}
foreach who [split $::env(JP_TAPS) ,] {
 set tap [$b findInst ot_ms_${who}_tap]
 if {$tap eq "NULL"} {error "missing tap $who"}
 set ip [lindex [ot_dtsh::sigpins $tap INPUT] 0]
 set source [$ip getNet]
 lassign [$tap getLocation] x y
 lassign [ot_local_depth::site_near $x $y [expr {10*$u}] $::ot_dtsh::master] xx yy orient
 set pi [odb::dbInst_create $b $::ot_dtsh::master ot_ms_jp_$who]
 $pi setOrient $orient;$pi setLocation $xx $yy;$pi setPlacementStatus FIRM
 ot_dtsh::pg $pi
 set next [odb::dbNet_create $b ot_ms_jp_${who}_n];$next setSigType CLOCK
 set sd [$source isDoNotTouch];set td [$tap isDoNotTouch]
 if {$sd} {$source setDoNotTouch false};if {$td} {$tap setDoNotTouch false}
 [lindex [ot_dtsh::sigpins $pi INPUT] 0] connect $source
 [lindex [ot_dtsh::sigpins $pi OUTPUT] 0] connect $next
 $ip disconnect;$ip connect $next
 if {$sd} {$source setDoNotTouch true};if {$td} {$tap setDoNotTouch true}
 $pi setDoNotTouch true;$next setDoNotTouch true
 lappend added "$who@[expr {$xx/double($u)}],[expr {$yy/double($u)}]"
}
dict for {name state} $::ot_dtsh::original {
 set i [$b findInst $name]
 if {[list [ot_dtsh::box $i] [$i getOrient] [[$i getMaster] getName]] ne $state} {error "projection moved original $name"}
}
dict for {key expected} $::ot_dtsh::ff_data {
 lassign $key n p
 set net [[[$b findInst $n] findITerm $p] getNet]
 set got [expr {$net eq "NULL" || $net eq "" ? "" : [$net getName]}]
 if {$got ne $expected} {error "projection changed FF data/control $n/$p"}
}
puts "JP_GEOM_AUDIT_PASS pad $PAD added $added cells[dict size $::ot_dtsh::original] FFdata[dict size $::ot_dtsh::ff_data]"
set ::env(OT_RC_CAL) 0.8,0.9
source /work/cf/rc_cal.tcl
set_routing_layers -signal M2-M5 -clock M4-M5
set_global_routing_layer_adjustment M2-M5 0.0
set_placement_padding -global -left 0 -right 0
pin_access
global_route -congestion_iterations 30 -congestion_report_file /out/congestion.rpt -allow_congestion
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
source /work/cf/mscts_core.tcl
ot_ms_pinmap
set ok [ot_ms_report grt]
puts "JP_WINDOW_RESULT $ok"
puts "JP_DIAG setup [sta::time_sta_ui [sta::worst_slack_cmd max]] slew [sta::max_slew_violation_count] cap [sta::max_capacitance_violation_count]"
write_db /out/jp_grt.odb
exit
