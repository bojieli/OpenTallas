# Native partition run cap, measured on the actual synthesized top before
# TAP/filler insertion and before floorplan repair/placement. Macro masters are
# physical blocks, not standard cells. No library-helper stat is consulted.
# Default 400k. COORD 11-04 06:00 (2), OWNER targets-not-gates: a kit generated
# with gen.py phys --native-cell-cap N runs up to N, never above 517k, the largest
# closed run on record (0.53-1.31M all failed).
# WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 D): the ONE limit is die_plan/cell_cap.py SPLIT_CELLS (test_cell_cap_everywhere keeps this number equal).  A kit
# over it stops here, whatever launched it, unless a ruling id waives it: env OT_CELL_WAIVER=rNNN or the first line of /work/CELL_WAIVER.
set ot_cap_split 400000
set ot_cap_waiver ""
if {[info exists ::env(OT_CELL_WAIVER)] && [regexp {^r[0-9]{3,4}$} [string trim $::env(OT_CELL_WAIVER)]]} {
 set ot_cap_waiver [string trim $::env(OT_CELL_WAIVER)]
} elseif {[file exists /work/CELL_WAIVER]} {
 set ot_cap_wf [open /work/CELL_WAIVER r]; set ot_cap_wl [string trim [gets $ot_cap_wf]]; close $ot_cap_wf
 if {[regexp {^r[0-9]{3,4}$} $ot_cap_wl]} { set ot_cap_waiver $ot_cap_wl }
}
set ot_cap_limit $ot_cap_split
if {[info exists ::ot_native_cell_limit] && $ot_cap_waiver ne ""} {
 set ot_cap_limit [expr {int($::ot_native_cell_limit)}]
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
# KV-HUBPV-1118 11-18 (COORD FABLE-FLOW-1750 G, OWNER 11-14 remove cell caps): the in-kit stop was DELETED here (FLOW-OPS-0900 11-21: CELL-CAP below REPORTS at floorplan; stop only with OT_CELL_CAP_STOP=1).  Six KV types (hub_C 709k, pv_v3 432k ...) died here
# with r576 at the place stage although the wave already lets them through; the count is only reported (the receipt above keeps the number).
if {$ot_cap_std > $ot_cap_split} {
 puts "OT_NATIVE_CELL_CAP info: actual standard cell count $ot_cap_std above $ot_cap_split (cell cap removed, not stopped)"
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
      puts "$ot_cap_msg (info: R-CAP removed, LIMIT-BIND-1 11-14, not stopped)"
    }
  }
}
# CELL-CAP (FLOW-OPS-0900 11-21, FABLE-FLOW-0745 class a; owner rule "OpenROAD closes <= ~400k cells per run, largest closed 517k: split oversized types").
# COORD ruling 11-21 (r703, all safety stops removed): a REPORT by default, never a stop.  Over = the measured synthesized standard cells above 400000, or the
# projected movable count above 517000 (no run above it ever closed; the projection is +-25 %).  A declared native limit (capacity probe) is over only above
# its own limit.  The report writes /work/CELL_CAP_REPORT.json and one "OT_CELL_CAP REPORT" line; the wave posts it once per die|type to the owning lane and
# the die plan lane (kit_wave.cell_cap_report_step).  Opt-in stop: env OT_CELL_CAP_STOP=1 (die_gen_env / item_env) errors here at floorplan.
set ot_cap_stop_on 0
if {[info exists ::env(OT_CELL_CAP_STOP)] && [string trim $::env(OT_CELL_CAP_STOP)] eq "1"} { set ot_cap_stop_on 1 }
set ot_cap_over ""
if {[info exists ::ot_native_cell_limit]} {
  if {$ot_cap_std > int($::ot_native_cell_limit)} { set ot_cap_over "actual standard cells $ot_cap_std above the declared native limit [expr {int($::ot_native_cell_limit)}]" }
} elseif {$ot_cap_std > $ot_cap_split} {
  set ot_cap_over "actual standard cells $ot_cap_std above the $ot_cap_split run cap"
} elseif {[info exists ot_cap_proj] && $ot_cap_proj > 517000} {
  set ot_cap_over "projected movable cells $ot_cap_proj above 517000 (largest closed run; synthesized $ot_cap_std)"
}
if {$ot_cap_over ne ""} {
  catch {
    set ot_cap_sf [open /work/CELL_CAP_REPORT.json w]
    puts $ot_cap_sf [format {{"schema":"opentallas.cell_cap_report.v1","stage":"floorplan","stdcells":%d,"stop":%d,"why":"%s"}} $ot_cap_std $ot_cap_stop_on $ot_cap_over]
    close $ot_cap_sf
  }
  puts "OT_CELL_CAP REPORT stage=floorplan: $ot_cap_over: the type must be split (registered boundaries) or logic hardened into cores"
  if {$ot_cap_stop_on} {
    puts "OT_CELL_CAP STOP stage=floorplan: $ot_cap_over (OT_CELL_CAP_STOP=1)"
    error "OT_CELL_CAP STOP stage=floorplan: $ot_cap_over"
  }
}
unset -nocomplain ot_cap_over ot_cap_stop_on ot_cap_sf
unset -nocomplain ot_cap_std ot_cap_macros ot_cap_i ot_cap_receipt ot_cap_limit ot_cap_blk ot_cap_pins ot_cap_b ot_cap_die ot_cap_dbu ot_cap_hp ot_cap_err ot_cap_proj ot_cap_parts ot_cap_msg
