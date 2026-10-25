# Isolated FF hold repair. Run in a NEW OpenROAD process, never in the legacy
# two-scene OT_HOLD_MM session. TT setup is checked separately after this step.
# Required env: PLIBS (FF only), ODB, SDC, RCFILE, OUT_DIR.
# Optional: FF_SDC, OT_REPAIR_MODE (placement; GRT requires a routed incremental wrapper), OT_HOLD_FF_MARGIN (0..5).
foreach key {PLIBS ODB SDC RCFILE OUT_DIR} {
  if {![info exists ::env($key)] || $::env($key) eq ""} { error "repair_ff: $key missing" }
}
if {[file exists $::env(OUT_DIR)/repair_ff.tsv]} {
  error "repair_ff: output verdict already exists; use a fresh OUT_DIR"
}
if {![llength $::env(PLIBS)]} { error "repair_ff: no FF libraries" }
foreach lib $::env(PLIBS) {
  if {![file exists $lib] || ![regexp -nocase {(^|[_/])ff([_/.-]|$)} [file tail $lib]]} {
    error "repair_ff: require an explicit existing FF library: $lib"
  }
}
set ff_margin [expr {[info exists ::env(OT_HOLD_FF_MARGIN)] ? $::env(OT_HOLD_FF_MARGIN) : 0}]
if {![string is double -strict $ff_margin] || $ff_margin < 0 || $ff_margin > 5} {
  error "repair_ff: hold margin must be 0..5 ps"
}
set ff_mode [expr {[info exists ::env(OT_REPAIR_MODE)] ? $::env(OT_REPAIR_MODE) : "placement"}]
if {$ff_mode ne "placement"} {
  error "repair_ff: only placement repair is qualified; GRT requires incremental routing of inserted cells before its final FF check"
}
foreach lib $::env(PLIBS) { read_liberty $lib }
read_db $::env(ODB)
read_sdc $::env(SDC)
if {![info exists ::env(FF_SDC)] || ![file exists $::env(FF_SDC)]} {
  error "repair_ff: explicit FF_SDC boundary reference required"
}
read_sdc $::env(FF_SDC)
foreach clk [all_clocks] {
  if {[llength [get_property $clk sources]]} { set_propagated_clock $clk }
}
source $::env(RCFILE)
estimate_parasitics -$ff_mode
set ff_pre_w [sta::time_sta_ui [sta::worst_slack_cmd min]]
set ff_pre_n [sta::endpoint_violation_count min]
puts [format "OT_REPAIR_FF before basis %s wns_ps %.4f endpoints %d margin %.1f" $ff_mode $ff_pre_w $ff_pre_n $ff_margin]
# Same structural stop as hold_gate.tcl; only true negative endpoints count.
if {$ff_pre_w < -100 || $ff_pre_n > 2000} {
  error "repair_ff: structural FF failure; revise plan/RTL/boundary before repair"
}
# Legalization can move a newly inserted hold cell after repair_timing reports
# success. Repair and legalize again while the actual final-placement metric
# improves; preserve a stalled checkpoint rather than claiming closure.
set ff_prev_w $ff_pre_w
set ff_prev_n $ff_pre_n
set ff_pass 0
while {1} {
  incr ff_pass
  repair_timing -hold -hold_margin $ff_margin -setup_margin 0
  estimate_parasitics -$ff_mode
  detailed_placement
  check_placement -verbose
  estimate_parasitics -$ff_mode
  set ff_post_w [sta::time_sta_ui [sta::worst_slack_cmd min]]
  set ff_post_n [sta::endpoint_violation_count min]
  puts [format "OT_REPAIR_FF legalized pass %d wns_ps %.4f endpoints %d" $ff_pass $ff_post_w $ff_post_n]
  if {$ff_post_n == 0 && $ff_post_w >= 0} { break }
  if {$ff_post_n >= $ff_prev_n && $ff_post_w <= $ff_prev_w + 1e-6} {
    puts "OT_REPAIR_FF stalled after legalization; retaining failed checkpoint"
    break
  }
  set ff_prev_w $ff_post_w
  set ff_prev_n $ff_post_n
}
file mkdir $::env(OUT_DIR)
write_db $::env(OUT_DIR)/repair_ff.odb
write_sdc $::env(OUT_DIR)/repair_ff.sdc
set ff_f [open $::env(OUT_DIR)/repair_ff.tsv w]
puts $ff_f "basis\t$ff_mode\nbefore_wns_ps\t$ff_pre_w\nbefore_endpoints\t$ff_pre_n\nafter_wns_ps\t$ff_post_w\nafter_endpoints\t$ff_post_n\nsetup_gate\tNOT_RUN_TT_REQUIRED"
close $ff_f
puts [format "OT_REPAIR_FF after wns_ps %.4f endpoints %d; TT setup/signoff required" $ff_post_w $ff_post_n]
if {$ff_post_n > 0 || $ff_post_w < 0} { error "repair_ff: FF hold remains negative; checkpoint retained" }
puts "OT_REPAIR_FF PASS (FF hold only; TT setup/signoff required)"
