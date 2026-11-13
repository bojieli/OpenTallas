# Native partition run cap, measured on the actual synthesized top before
# TAP/filler insertion and before floorplan repair/placement. Macro masters are
# physical blocks, not standard cells. No library-helper stat is consulted.
# Default 400k. COORD 11-04 06:00 (2), OWNER targets-not-gates: a kit generated
# with gen.py phys --native-cell-cap N runs up to N, never above 517k, the largest
# closed run on record (0.53-1.31M all failed).
set ot_cap_limit 400000
if {[info exists ::ot_native_cell_limit]} {
 set ot_cap_limit [expr {min(int($::ot_native_cell_limit), 517000)}]
}
set ot_cap_std 0
set ot_cap_macros 0
foreach ot_cap_i [[ord::get_db_block] getInsts] {
 if {[[$ot_cap_i getMaster] isBlock]} { incr ot_cap_macros } else { incr ot_cap_std }
}
set ot_cap_receipt [open /work/native_cell_count.json w]
puts $ot_cap_receipt [format {{"schema":"opentallas.native_cell_count.v1","stage":"pre_floorplan","stdcells":%d,"macros":%d,"limit":%d}} $ot_cap_std $ot_cap_macros $ot_cap_limit]
close $ot_cap_receipt
puts "OT_NATIVE_CELL_CAP actual_std=$ot_cap_std macros=$ot_cap_macros limit=$ot_cap_limit"
if {$ot_cap_std > $ot_cap_limit} {
 error "OT_NATIVE_CELL_CAP actual standard cell count $ot_cap_std above $ot_cap_limit run cap"
}
if {$ot_cap_std > 400000} {
 puts "OT_NATIVE_CELL_CAP ADVISORY actual_std=$ot_cap_std above the 400000 target, within kit limit $ot_cap_limit"
}
# R-CAP (RULES-CAP-1, RULEBOOK 11-13): project the movable count after place resize from the synthesized top, before
# any floorplan repair runs.  Same model and constants as tools/die_plan/cap_estimate.py (test_cap_estimate.py keeps
# them equal): place = synth + pins + 0.395 * pins * hp/100 + 58.8 * macros * hp/100, hp = (W + H) / 2 in um.
# Above 400000 the run stops here with the split; a kit with a declared native limit (a capacity probe) only reports.
if {![catch {
  set ot_cap_blk [ord::get_db_block]
  set ot_cap_pins 0
  foreach ot_cap_b [$ot_cap_blk getBTerms] {
    if {[$ot_cap_b getSigType] in {POWER GROUND}} continue
    incr ot_cap_pins
  }
  set ot_cap_die [$ot_cap_blk getDieArea]
  set ot_cap_dbu [expr {double([[ord::get_db_tech] getDbUnitsPerMicron])}]
  set ot_cap_hp [expr {([$ot_cap_die dx] + [$ot_cap_die dy]) / $ot_cap_dbu / 200.0}]
} ot_cap_err]} {
  set ot_cap_proj [expr {int($ot_cap_std + $ot_cap_pins + round(0.395 * $ot_cap_pins * $ot_cap_hp + 58.8 * $ot_cap_macros * $ot_cap_hp))}]
  set ot_cap_parts 2
  while {$ot_cap_proj * 1.03 / $ot_cap_parts > 250000} { incr ot_cap_parts }
  catch {
    set ot_cap_receipt [open /work/cap_projection.json w]
    puts $ot_cap_receipt [format {{"schema":"opentallas.cap_projection.v1","stage":"pre_floorplan","synth":%d,"pins":%d,"macros":%d,"half_perimeter_100um":%.4f,"place":%d,"budget":400000}} $ot_cap_std $ot_cap_pins $ot_cap_macros $ot_cap_hp $ot_cap_proj]
    close $ot_cap_receipt
  }
  puts "OT_CELL_BUDGET stage=pre_floorplan synth=$ot_cap_std pins=$ot_cap_pins macros=$ot_cap_macros projected_place=$ot_cap_proj budget=400000 (+-25 %)"
  if {$ot_cap_proj > 400000} {
    set ot_cap_msg "OT_CELL_BUDGET projected movable cells after place resize $ot_cap_proj above the R-CAP place budget 400000: split into $ot_cap_parts parts of <= 250000 movable cells at lane-group boundaries with registered boundary buses, or harden logic into cores"
    if {[info exists ::ot_native_cell_limit]} {
      puts "$ot_cap_msg (declared native limit: capacity probe, not stopped)"
    } else {
      error $ot_cap_msg
    }
  }
}
unset -nocomplain ot_cap_std ot_cap_macros ot_cap_i ot_cap_receipt ot_cap_limit ot_cap_blk ot_cap_pins ot_cap_b ot_cap_die ot_cap_dbu ot_cap_hp ot_cap_err ot_cap_proj ot_cap_parts ot_cap_msg
