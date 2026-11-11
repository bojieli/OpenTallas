# GENERATED-COPY of tools/die_plan/cell_census.tcl (VSN6-B 11-11, S7 class fix from HBM vsN6 form3).
# native_cell_cap.tcl checks only the synthesized netlist (pre_floorplan: vsN6 151k).  Place/CTS and GRT repair_design
# (max-wire 80: +66,306 buffers) then grew the run with no count at all, and the final 440,169 leaf instances read as a
# 400k cap break although 196,595 of them were TAPCELL/endcap (non-tap 243,574).  ot_cell_census STAGE recounts the
# block wherever a hook calls it: NON-TAP standard cells (what the 400k run cap judges) apart from tap/endcap/filler
# cells and macros.  Before GRT it also estimates the max-wire repair buffers from the placed pins
# (per signal net max(0, ceil(HPWL / OT_MAXWIRE_UM) - 1); unplaced nets are skipped and counted) and projects the
# final non-tap count.  One loud line per stage against the cap (OT_CELL_CENSUS_CAP, default 400000):
#   OT_CELL_CENSUS stage=... nontap=... projected_nontap=... cap=...: OK (n% of cap) | WARN NEAR_CAP | WARN OVER_CAP
# ADVISORY (OWNER 11-03 targets-not-gates): it never stops a run, but it never passes silently.
# Receipt: one JSON line per call in cell_census.jsonl next to this file.
set ::ot_cc_dir [file dirname [file normalize [info script]]]
proc ot_cell_census {stage {estimate auto}} {
  set cap 400000
  if {[info exists ::env(OT_CELL_CENSUS_CAP)] && [string is integer -strict $::env(OT_CELL_CENSUS_CAP)]} { set cap $::env(OT_CELL_CENSUS_CAP) }
  set blk [ord::get_db_block]
  set tap 0; set std 0; set mac 0
  foreach i [$blk getInsts] {
    set m [$i getMaster]
    if {[$m isBlock]} { incr mac; continue }
    if {[regexp {^(TAPCELL|ENDCAP|FILLER|FILL|DECAP)} [$m getName]]} { incr tap; continue }
    incr std
  }
  set mw 0
  if {[info exists ::env(OT_MAXWIRE_UM)] && [string is double -strict $::env(OT_MAXWIRE_UM)] && $::env(OT_MAXWIRE_UM) > 0} {
    set mw $::env(OT_MAXWIRE_UM)
  }
  if {$estimate eq "auto"} { set estimate [expr {$stage ni {grt route final}}] }
  set est 0; set nm 0; set nu 0
  if {$estimate && $mw > 0} {
    set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
    foreach n [$blk getNets] {
      if {[$n getSigType] in {POWER GROUND CLOCK RESET}} continue
      set xs {}; set ys {}; set ok 1
      foreach it [$n getITerms] {
        set inst [$it getInst]
        if {[$inst getPlacementStatus] in {NONE UNPLACED}} { set ok 0; break }
        lassign [$inst getLocation] x y
        lappend xs $x; lappend ys $y
      }
      if {!$ok} { incr nu; continue }
      foreach bt [$n getBTerms] {
        set bb [$bt getBBox]
        lappend xs [$bb xMin]; lappend ys [$bb yMin]
      }
      if {[llength $xs] < 2} continue
      incr nm
      set xs [lsort -integer $xs]; set ys [lsort -integer $ys]
      set hp [expr {double([lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]) / $dbu}]
      set k [expr {int(ceil($hp / $mw)) - 1}]
      if {$k > 0} { incr est $k }
    }
  }
  set proj [expr {$std + $est}]
  set pct [expr {100.0 * $proj / $cap}]
  if {$std > $cap || $proj > $cap} {
    set v "WARN OVER_CAP"
  } elseif {$proj >= 0.9 * $cap} {
    set v "WARN NEAR_CAP"
  } else {
    set v "OK"
  }
  set note [expr {$estimate && $mw > 0 ? "maxwire_est=+$est (OT_MAXWIRE_UM $mw, nets measured $nm, unplaced $nu)" : "recount (no estimate)"}]
  puts [format "OT_CELL_CENSUS stage=%s nontap=%d tap_endcap=%d macros=%d %s projected_nontap=%d cap=%d: %s (%.1f%% of cap; ADVISORY, run cap judged on non-tap)" \
        $stage $std $tap $mac $note $proj $cap $v $pct]
  if {![catch {open [file join $::ot_cc_dir cell_census.jsonl] a} fh]} {
    puts $fh [format {{"schema":"opentallas.cell_census.v1","stage":"%s","nontap":%d,"tap_endcap":%d,"macros":%d,"maxwire_um":%s,"maxwire_est":%d,"nets_measured":%d,"nets_unplaced":%d,"projected_nontap":%d,"cap":%d,"verdict":"%s"}} \
              $stage $std $tap $mac $mw $est $nm $nu $proj $cap $v]
    close $fh
  }
  return [list $std $proj $v]
}
