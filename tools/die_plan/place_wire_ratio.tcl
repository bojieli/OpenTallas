# POST-PLACE built-wire check for zero-logic register-to-register paths (CLOSURE-STRATEGY lever 7, HOLD-FLOW-R 11-17), all dies.
# A path that is only buffers and inverters between two registers has no reason to detour: its built length (sum of the Manhattan hops
# pin to pin along the placed cells) over the Manhattan distance of its two registers should be near 1 (S81 t47 classes read 1.03-1.88).
# QC cb read 6.2 and failed setup by hundreds of ps.  Violation = length > OT_PLACE_WIRE_MIN_UM (400) AND length / direct > OT_PLACE_WIRE_RATIO_MAX (3).
# Sourced after global placement (end of gp_noconverge_gate.tcl, the PRE_RESIZE hook every kit carries; QC core_input_chain.tcl sources it too).
# OT_PLACE_WIRE_RATIO = report (default: print + write place_wire_ratio.tsv, never stops the flow) | fail (marker FAIL_PLACE_WIRE_RATIO +
# Tcl error, make stops before resize) | 0 (off).  The first zero-logic hop count per path is capped by OT_PLACE_WIRE_MAX_STAGES (64).
# pwr_eval {paths min_um ratio_max} : paths = list of {name direct_um length_um}; -> {violations worst-first}
proc pwr_eval {paths min_um ratio_max} {
  set bad {}
  foreach p $paths {
    lassign $p name direct len
    set ratio [expr {$direct > 0.0 ? double($len) / $direct : 1e9}]
    if {$len > $min_um && $ratio > $ratio_max} { lappend bad [list $name $direct $len $ratio] }
  }
  return [lsort -real -decreasing -index 3 $bad]
}
proc pwr_env {k d} { return [expr {[info exists ::env($k)] && $::env($k) ne "" ? $::env($k) : $d}] }
proc pwr_reg {master} { return [regexp {^(DFF|DHL|DLL|SDF|ASYNC_DFF)} $master] }
proc pwr_buf {master} { return [regexp {^(BUF|INV|HB[0-9]|CKINV|CKBUF)} $master] }
proc pwr_pt {it dbu} {
  set r [$it getAvgXY]
  if {[lindex $r 0]} { return [list [expr {[lindex $r 1] / $dbu}] [expr {[lindex $r 2] / $dbu}]] }
  set b [[$it getInst] getBBox]
  return [list [expr {([$b xMin] + [$b xMax]) / 2.0 / $dbu}] [expr {([$b yMin] + [$b yMax]) / 2.0 / $dbu}]]
}
proc pwr_paths {} {
  set blk [ord::get_db_block]; set dbu [expr {double([$blk getDbUnitsPerMicron])}]
  set maxs [pwr_env OT_PLACE_WIRE_MAX_STAGES 64]
  set out {}
  foreach inst [$blk getInsts] {
    set m [[$inst getMaster] getName]
    if {![pwr_reg $m]} continue
    foreach ot [$inst getITerms] {
      if {![$ot isOutputSignal]} continue
      set n [$ot getNet]; if {$n eq "NULL"} continue
      # depth-first over buffer / inverter cells; every register D reached closes one path
      set stack [list [list $n [pwr_pt $ot $dbu] 0.0 0]]
      while {[llength $stack]} {
        lassign [lindex $stack end] net from len depth
        set stack [lrange $stack 0 end-1]
        foreach it [$net getITerms] {
          if {![$it isInputSignal]} continue
          set i2 [$it getInst]; if {$i2 eq $inst && $depth == 0} continue
          set m2 [[$i2 getMaster] getName]
          set p [pwr_pt $it $dbu]
          set l2 [expr {$len + abs([lindex $p 0] - [lindex $from 0]) + abs([lindex $p 1] - [lindex $from 1])}]
          if {[pwr_reg $m2]} {
            set src [pwr_pt $ot $dbu]
            set direct [expr {abs([lindex $p 0] - [lindex $src 0]) + abs([lindex $p 1] - [lindex $src 1])}]
            lappend out [list "[$inst getName]/[[$ot getMTerm] getName]->[$i2 getName]/[[$it getMTerm] getName]" $direct $l2]
          } elseif {[pwr_buf $m2] && $depth < $maxs} {
            foreach o2 [$i2 getITerms] {
              if {[$o2 isOutputSignal] && [$o2 getNet] ne "NULL"} { lappend stack [list [$o2 getNet] [pwr_pt $o2 $dbu] $l2 [expr {$depth + 1}]] }
            }
          }
        }
      }
    }
  }
  return $out
}
proc pwr_run {} {
  set mode [string tolower [pwr_env OT_PLACE_WIRE_RATIO report]]
  if {$mode in {0 off}} { puts "PLACE-WIRE-RATIO off (OT_PLACE_WIRE_RATIO=$mode)"; return }
  if {$mode ni {report fail}} { puts "PLACE-WIRE-RATIO unknown mode $mode: report only"; set mode report }
  set min [pwr_env OT_PLACE_WIRE_MIN_UM 400.0]; set rmax [pwr_env OT_PLACE_WIRE_RATIO_MAX 3.0]
  set paths [pwr_paths]
  set bad [pwr_eval $paths $min $rmax]
  set rdir [pwr_env REPORTS_DIR [pwr_env LOG_DIR .]]
  catch {
    set fh [open [file join $rdir place_wire_ratio.tsv] w]
    puts $fh "path\tdirect_um\tlength_um\tratio"
    foreach b $bad { puts $fh [format "%s\t%.1f\t%.1f\t%.2f" {*}$b] }
    close $fh
  }
  set worst [expr {[llength $bad] ? [format %.2f [lindex [lindex $bad 0] 3]] : "-"}]
  puts "OT_PLACE_WIRE_RATIO mode $mode paths [llength $paths] violations [llength $bad] worst_ratio $worst (length > $min um and ratio > $rmax)"
  foreach b [lrange $bad 0 9] { puts [format "OT_PLACE_WIRE_RATIO_PATH %s direct %.1f um built %.1f um ratio %.2f" {*}$b] }
  if {[llength $bad] && $mode eq "fail"} {
    catch { set fh [open [file join [pwr_env OT_KIT_DIR /work] FAIL_PLACE_WIRE_RATIO] w]; puts $fh "[llength $bad] zero-logic reg-to-reg paths with built wire > ${rmax}x direct and > $min um, worst $worst"; close $fh }
    error "PLACE-WIRE-RATIO: [llength $bad] zero-logic register paths with built wire > ${rmax}x the direct distance and > $min um (worst $worst); see place_wire_ratio.tsv"
  }
}
pwr_run
