# geom_dump.tcl (AUTO-GEOM 2026-10-25): compact geometry + connectivity dump of a placed / CTS checkpoint for
# tools/autopilot/geom_rules.py.  Read-only: `read_db <3_place.odb|4_cts.odb>` first, then source this file.
# env: OT_GEOM_OUT (output path).  One record per line, tab separated, coordinates in um:
#   D  x0 y0 x1 y1                                   die area
#   C  id kind master x0 y0 x1 y1 name               instance (dbInst id); kind S seq | B buf/inv | K clock cell |
#                                                    L other logic | M hard macro / hardened child; fillers, tap cells
#                                                    and decaps are skipped
#   P  k name io sig layer cx cy                     top pin (first box of the first BPin)
#   N  sig drv sink...                               signal/clock net: drv / sink = i<id> (cell pin), i<id>c (clock pin
#                                                    of a seq/macro), p<k> (top pin), '-' (no driver); PG nets skipped
set gd_b [ord::get_db_block]
set gd_u [expr {double([$gd_b getDbUnitsPerMicron])}]
proc gd_f {v} { return [format %.4f [expr {$v / $::gd_u}]] }
set gd_o [open $::env(OT_GEOM_OUT) w]
set d [$gd_b getDieArea]
puts $gd_o "D\t[gd_f [$d xMin]]\t[gd_f [$d yMin]]\t[gd_f [$d xMax]]\t[gd_f [$d yMax]]"
array set gd_skip {}
foreach i [$gd_b getInsts] {
  set m [$i getMaster]; set mn [$m getName]
  if {[$m isBlock]} { set k M } elseif {[regexp {^(TAPCELL|FILLER|FILL|DECAP)} $mn]} { set gd_skip([$i getId]) 1; continue
  } elseif {[regexp {^(ICG|CKINV|CKBUF|CLKBUF)} $mn]} { set k K
  } elseif {[regexp {^(DFF|DHL|DLL|SDF|ASYNC)} $mn]} { set k S
  } elseif {[regexp {^(BUF|INV|HB)} $mn]} { set k B } else { set k L }
  set bb [$i getBBox]
  puts $gd_o "C\t[$i getId]\t$k\t$mn\t[gd_f [$bb xMin]]\t[gd_f [$bb yMin]]\t[gd_f [$bb xMax]]\t[gd_f [$bb yMax]]\t[$i getName]"
}
set k 0
array set gd_pk {}
foreach bt [$gd_b getBTerms] {
  set bps [$bt getBPins]
  set cx 0; set cy 0; set ln "-"
  if {[llength $bps]} {
    set bx [lindex [[lindex $bps 0] getBoxes] 0]
    if {$bx ne ""} {
      set cx [gd_f [expr {([$bx xMin] + [$bx xMax]) / 2.0}]]; set cy [gd_f [expr {([$bx yMin] + [$bx yMax]) / 2.0}]]
      if {[$bx getTechLayer] ne "NULL"} { set ln [[$bx getTechLayer] getName] }
    }
  }
  set gd_pk([$bt getName]) $k
  puts $gd_o "P\t$k\t[$bt getName]\t[$bt getIoType]\t[$bt getSigType]\t$ln\t$cx\t$cy"
  incr k
}
foreach n [$gd_b getNets] {
  set sg [$n getSigType]
  if {$sg eq "POWER" || $sg eq "GROUND"} { continue }
  set drv "-"; set sk {}
  foreach it [$n getITerms] {
    set i [$it getInst]; set id [$i getId]
    if {[info exists gd_skip($id)]} { continue }
    if {[$it isOutputSignal]} { if {$drv eq "-"} { set drv "i$id" }; continue }
    set mt [$it getMTerm]
    if {[$mt getSigType] eq "CLOCK" || [regexp {^(CLK|CK|GCLK)$} [$mt getName]]} { lappend sk "i${id}c" } else { lappend sk "i$id" }
  }
  foreach bt [$n getBTerms] {
    set pk $gd_pk([$bt getName])
    if {[$bt getIoType] eq "INPUT" && $drv eq "-"} { set drv "p$pk" } else { lappend sk "p$pk" }
  }
  if {[llength $sk] == 0} { continue }
  puts $gd_o "N\t$sg\t$drv\t[join $sk \t]"
}
close $gd_o
puts "OT_GEOM_DUMP $::env(OT_GEOM_OUT)"
