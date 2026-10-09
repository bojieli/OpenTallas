# CLOSURE-LOOP post-route VT-SWAP SETUP ECO (eco-sweep 2026-10-09; owner Vt policy 2026-10-07 21:10: RVT default, LVT on
# <= ~2 % of cells for SMALL TT misses).  NO re-route: ASAP7 R/L cells are footprint-identical (the LEFs differ only in the
# VT-implant OBS layer; tools/multivt/vt_swap_sta.py), so a master swap moves no pin, wire or DRC shape and the routed
# SPEF stays the parasitics of the design.
#
# Multi-mode session exactly as hold_eco.tcl rev 3 (scene ss = the setup sign-off: OT_SETUP_LIB=TT under option B, hold
# false-pathed; scene ff = the FF hold sign-off, setup false-pathed), routed SPEF on both scenes.  Then, per round:
#   1. every RVT standard cell on a TT setup path with slack < OT_TARGET -> its _L twin (launching register included),
#      never a cell frozen in step 2, never past OT_CAP_PCT % LVT of the standard cells (fillers/taps/decaps excluded);
#   2. FF hold guard: a swapped cell on an FF hold path under OT_HOLD_FLOOR goes back to RVT and is frozen.
# Stops when TT setup >= OT_TARGET, nothing new can be swapped, or the cap is reached.  Writes 6_final.odb/.v into
# OT_OUT; the sign-off (tools/w18/corner_sta.py, fresh session, VT libraries detected from the odb) judges the result.
# env: OT_DB, OT_SDC_SS, OT_SDC_FF, OT_SPEF, OT_OUT, OT_MACROS, OT_TARGET (10), OT_CAP_PCT (2.0), OT_ROUNDS (10),
#      OT_HOLD_FLOOR (2), OT_NPATHS (20000), OT_THREADS (8)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
proc envd {n d} { expr {[info exists ::env($n)] && $::env($n) ne "" ? $::env($n) : $d} }
proc ot_libc {c} {
  if {$c eq "ss" && [info exists ::env(OT_SETUP_LIB)] && $::env(OT_SETUP_LIB) ne ""} { return [string toupper $::env(OT_SETUP_LIB)] }
  return [string toupper $c]
}
proc ot_vt_libs {C} {
  set r {}
  foreach vt {RVT LVT} {
    lappend r asap7sc7p5t_AO_${vt}_${C}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_${vt}_${C}_nldm_220122.lib.gz \
      asap7sc7p5t_OA_${vt}_${C}_nldm_211120.lib.gz asap7sc7p5t_SEQ_${vt}_${C}_nldm_220123.lib \
      asap7sc7p5t_SIMPLE_${vt}_${C}_nldm_211120.lib.gz
  }
  return $r
}
set target [envd OT_TARGET 10]; set cap [envd OT_CAP_PCT 2.0]; set rounds [envd OT_ROUNDS 60]
set hfloor [envd OT_HOLD_FLOOR 2]; set npaths [envd OT_NPATHS 20000]
set_thread_count [envd OT_THREADS 8]
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach m [envd OT_MACROS ""] { read_lef $m/[file tail $m].lef }
foreach c {ss ff} {
  set C [ot_libc $c]; set L($c) {}
  foreach l [ot_vt_libs $C] { read_liberty $P/lib/NLDM/$l; lappend L($c) $P/lib/NLDM/$l }
  foreach m [envd OT_MACROS ""] { set ml $m/[file tail $m]_[string tolower $C].lib; read_liberty $ml; lappend L($c) $ml }
}
read_db $::env(OT_DB)
# the LVT LEF library AFTER read_db (the odb carries its own libraries; a LEF read before it is dropped -> ORD-2056)
read_lef -library $P/lef/asap7sc7p5t_28_L_1x_220121a.lef
read_sdc -mode ss $::env(OT_SDC_SS)
read_sdc -mode ff $::env(OT_SDC_FF)
define_scene ss -mode ss -liberty $L(ss)
define_scene ff -mode ff -liberty $L(ff)
foreach m {ss ff} f [list $::env(OT_SDC_SS) $::env(OT_SDC_FF)] {
  set envf $::env(OT_OUT)/env_$m.sdc
  set fi [open $f]; set fo [open $envf w]
  foreach l [split [read $fi] "\n"] { if {[regexp {^(set_load|set_driving_cell|set_input_transition)\M} $l]} { puts $fo $l } }
  close $fi; close $fo
  set_mode $m
  source $envf
}
source $P/setRC.tcl
foreach c {ss ff} { read_spef -corner $c $::env(OT_SPEF) }

set blk [ord::get_db_block]; set db [ord::get_db]
proc ws {check scene} {
  set w 1e6
  foreach p [find_timing_paths -path_delay $check -scenes $scene -group_path_count 1] { set w [expr {min($w, [get_property $p slack])}] }
  return $w   ;# user time unit = ps (ASAP7 libs)
}
proc vt_counts {} {
  set c [dict create R 0 L 0 SL 0]
  foreach i [$::blk getInsts] {
    set m [[$i getMaster] getName]
    if {[regexp {^(FILLER|TAPCELL|DECAP)} $m]} continue
    if {[regexp {_ASAP7_75t_(R|L|SL)$} $m -> v]} { dict incr c $v }
  }
  return $c
}
proc lvt_pct {} { set c [vt_counts]; set t [expr {[dict get $c R] + [dict get $c L] + [dict get $c SL]}]
  return [expr {$t ? 100.0 * ([dict get $c L] + [dict get $c SL]) / $t : 0.0}] }
proc path_insts {check scene slack_max} {
  # text report (PathEnd point properties are not used: they crashed this build in vt_swap_sta.py)
  set f $::env(OT_OUT)/vt_paths.rpt
  report_checks -path_delay $check -scenes $scene -group_path_count $::npaths -endpoint_path_count 1 \
    -unique_paths_to_endpoint -slack_max $slack_max -format full > $f
  set fh [open $f r]; set txt [read $fh]; close $fh
  set r [dict create]
  foreach line [split $txt "\n"] {
    if {[regexp {\s(\S+)/[^/\s]+\s+\((\S+)_ASAP7_75t_(R|L|SL)\)\s*$} $line -> inst base vt]} { dict set r $inst [list $base $vt] }
  }
  return $r
}
proc set_vt {inst base to} {
  set i [$::blk findInst $inst]; if {$i eq "NULL" || $i eq ""} { return 0 }
  set nm [$::db findMaster "${base}_ASAP7_75t_$to"]; if {$nm eq "NULL" || $nm eq ""} { return 0 }
  $i swapMaster $nm   ;# odb swap: dbSta's swap-master callback re-times the instance (vt_swap_sta.py)
  return 1
}
set c0 [vt_counts]
set one_pct [expr {100.0 / max(1, [dict get $c0 R] + [dict get $c0 L] + [dict get $c0 SL])}]
set ::nlow [expr {[dict get $c0 L] + [dict get $c0 SL]}]   ;# incremental LVT/SLVT count (a full scan per swap is O(cells))
set tt0 [ws max ss]; set ff0 [ws min ff]
puts [format "OT_VTSWAP pre tt %.2f ff %.2f vt %s lvt_pct %.3f" $tt0 $ff0 $c0 [lvt_pct]]
set swapped [dict create]; set frozen [dict create]; set capped 0
for {set r 1} {$r <= $rounds} {incr r} {
  set tt [ws max ss]
  if {$tt >= $target} break
  # BAND: only the paths within OT_BAND ps of the current worst (worst first), so the fewest cells go LVT
  set band [expr {min($target, $tt + [envd OT_BAND 4])}]
  set n 0
  dict for {inst bv} [path_insts max ss $band] {
    lassign $bv base vt
    if {$vt ne "R" || [dict exists $frozen $inst] || [regexp {^(FILLER|TAPCELL|DECAP)} $base]} continue
    if {($::nlow + 1) * $::one_pct > $cap} { set capped 1; break }   ;# prospective: never past the cap
    if {[set_vt $inst $base L]} { dict set swapped $inst $base; incr n; incr ::nlow }
  }
  # FF hold guard: revert (and freeze) swapped cells on hold paths under the floor
  set nrev 0
  for {set g 0} {$g < 4 && [ws min ff] < $hfloor} {incr g} {
    set k 0
    dict for {inst bv} [path_insts min ff $hfloor] {
      if {[dict exists $swapped $inst]} { set_vt $inst [dict get $swapped $inst] R; dict unset swapped $inst; dict set frozen $inst 1; incr k; incr ::nlow -1 }
    }
    incr nrev $k
    if {!$k} break
  }
  puts [format "OT_VTSWAP round %d swapped %d reverted %d tt %.2f -> %.2f ff %.2f lvt_pct %.3f" $r $n $nrev $tt [ws max ss] [ws min ff] [lvt_pct]]
  if {$capped || $n == 0} break
}
set tt1 [ws max ss]; set ff1 [ws min ff]
puts [format "OT_VTSWAP post tt %.2f ff %.2f vt %s lvt_pct %.3f swapped %d frozen %d capped %d" $tt1 $ff1 [vt_counts] [lvt_pct] [dict size $swapped] [dict size $frozen] $capped]
set f [open $::env(OT_OUT)/vtswap_cells.txt w]; dict for {i b} $swapped { puts $f "$i ${b}_ASAP7_75t_L" }; close $f
write_db $::env(OT_OUT)/6_final.odb
write_verilog $::env(OT_OUT)/6_final.v
puts "OT_ECO done"
