# QC-RP1 10-25 F6 (cqb COORD GEOM VERDICT): macro interface registers sit next to the macro pins they drive.
# PRE_GLOBAL_PLACE, after face_flops.tcl.  For every macro data/addr input pin (OT_MIF_PINS, default wd_in w_addr_in)
# driven flop -> (<= 2 buffers/inverters) -> pin:
#  * a flop whose chain reaches pins of ONE macro is placed FIRM (with its chain cells) in a column just outside the
#    macro halo on the pin's edge, on the pin's row;
#  * a flop whose chain fans out to several macros (u_twca: one register for both banks) is cloned per extra macro
#    (same master, same D and clock net; its own inverter/buffer chain) -- logically identical register duplication,
#    +0 cycles -- and every copy is anchored at its own macro.
# Anchored cells are appended to RESULTS_DIR/ot_face_flops.txt, so face_flops_release.tcl releases them before DPL.
uplevel #0 {
set ma_blk [ord::get_db_block]
set ma_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ma_rows [$ma_blk getRows]
set ma_rh [[[lindex $ma_rows 0] getSite] getHeight]
set ma_sw [[[lindex $ma_rows 0] getSite] getWidth]
set ma_orient {}
foreach r $ma_rows { dict set ma_orient [lindex [$r getOrigin] 1] [$r getOrient] }
set ma_core [$ma_blk getCoreArea]
set ma_pins [expr {[info exists ::env(OT_MIF_PINS)] ? $::env(OT_MIF_PINS) : "wd_in w_addr_in"}]
set ma_halo [expr {round(4.32 * $ma_dbu) + 2 * $ma_sw}]
proc ma_isff {i} { string match "*DFF*" [[$i getMaster] getName] }
proc ma_isbuf {i} { set m [[$i getMaster] getName]; expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]} }
proc ma_out {i} { foreach it [$i getITerms] { if {[$it getSigType] eq "SIGNAL" && [[$it getMTerm] getIoType] eq "OUTPUT"} { return $it } }; return "" }
proc ma_in {i} { foreach it [$i getITerms] { if {[$it getSigType] eq "SIGNAL" && [[$it getMTerm] getIoType] eq "INPUT"} { return $it } }; return "" }
# chain from a macro input pin back to its flop: list {flop buf...} (flop first) or "" if logic in between
proc ma_chain {it} {
  set net [$it getNet]; set chain {}
  for {set d 0} {$d < 3} {incr d} {
    if {$net eq "NULL"} { return "" }
    set drv ""
    foreach x [$net getITerms] { if {[[$x getMTerm] getIoType] eq "OUTPUT"} { set drv [$x getInst] } }
    if {$drv eq ""} { return "" }
    if {[ma_isff $drv]} { return [linsert $chain 0 $drv] }
    if {![ma_isbuf $drv]} { return "" }
    set chain [linsert $chain 0 $drv]
    set net [[ma_in $drv] getNet]
  }
  return ""
}
# macro instances reached by a net (through buffers/inverters, depth 3)
proc ma_macros_of {net d} {
  set r {}
  foreach x [$net getITerms] {
    if {[[$x getMTerm] getIoType] ne "INPUT"} continue
    set i [$x getInst]
    if {[[$i getMaster] isBlock]} { lappend r [$i getName] } elseif {$d < 3 && [ma_isbuf $i]} { set o [ma_out $i]; if {$o ne "" && [$o getNet] ne "NULL"} { set r [concat $r [ma_macros_of [$o getNet] [expr {$d+1}]]] } }
  }
  return [lsort -unique $r]
}
set ma_ncl 0
# clone flop+chain for the pin iterms of macro $m on the chain's last net; returns new chain
proc ma_clone {chain m pinits} {
  global ma_blk ma_ncl
  incr ma_ncl
  set prev ""; set new {}
  foreach i $chain {
    set c [odb::dbInst_create $ma_blk [$i getMaster] "[$i getName]_mif$ma_ncl"]
    set onet [odb::dbNet_create $ma_blk "mif_net${ma_ncl}_[llength $new]"]
    foreach it [$i getITerms] {
      set mt [$it getMTerm]
      if {[$mt getSigType] in {POWER GROUND}} continue
      set ct [$c findITerm [$mt getName]]
      if {[$mt getIoType] eq "INPUT"} {
        if {$prev ne "" && ![ma_isff $i]} { $ct connect $prev } elseif {[$it getNet] ne "NULL"} { $ct connect [$it getNet] }
      } elseif {[$mt getIoType] eq "OUTPUT" && [$it getNet] ne "NULL"} { $ct connect $onet }
    }
    if {[$i isDoNotTouch]} { $c setDoNotTouch 1 }
    set prev $onet; lappend new $c
  }
  foreach it $pinits { $it disconnect; $it connect $prev }
  return $new
}
# place a chain at (x edge column, pin row); column k steps away from the macro
set ma_used {}
set ma_out [open $::env(RESULTS_DIR)/ot_face_flops.txt a]
proc ma_place {chain px py side} {
  global ma_rh ma_sw ma_used ma_orient ma_core ma_out ma_halo
  set row [expr {[$ma_core yMin] + int(round(double($py - [$ma_core yMin]) / $ma_rh - 0.5)) * $ma_rh}]
  set w 0; foreach i $chain { set w [expr {$w + [[$i getMaster] getWidth] + $ma_sw}] }
  set k 0
  while {[dict exists $ma_used "$side,$row,$k"]} { incr k }
  dict set ma_used "$side,$row,$k" 1
  if {$side eq "W"} { set x [expr {$px - $ma_halo - ($k + 1) * $w}] } else { set x [expr {$px + $ma_halo + $k * $w}] }
  set x [expr {($x / $ma_sw) * $ma_sw}]
  set o R0; if {[dict exists $ma_orient $row]} { set o [dict get $ma_orient $row] }
  foreach i $chain {
    $i setOrient $o; $i setLocation $x $row; $i setPlacementStatus FIRM
    set x [expr {$x + [[$i getMaster] getWidth] + $ma_sw}]
    puts $ma_out "[$i getName]\tmif"
  }
}
set ma_n 0; set ma_seen {}
foreach m [$ma_blk getInsts] {
  if {![[$m getMaster] isBlock]} continue
  set mb [$m getBBox]
  foreach it [$m getITerms] {
    set pn [[$it getMTerm] getName]
    if {[regsub {\[[0-9]+\]$} $pn {}] ni $ma_pins} continue
    if {[$it getNet] eq "NULL"} continue
    set chain [ma_chain $it]
    if {$chain eq ""} { puts "OT_MIF skip [$m getName]/$pn (logic between register and pin)"; continue }
    set pb [$it getBBox]
    set px [expr {([$pb xMin] + [$pb xMax]) / 2}]; set py [expr {([$pb yMin] + [$pb yMax]) / 2}]
    set side [expr {$px - [$mb xMin] < [$mb xMax] - $px ? "W" : "E"}]
    set edge [expr {$side eq "W" ? [$mb xMin] : [$mb xMax]}]
    set f [lindex $chain 0]
    if {[dict exists $ma_seen [$f getName]]} {
      # this register is already anchored at another macro: this macro's pin moves onto a clone chain
      set chain [ma_clone $chain [$m getName] [list $it]]
    } else { dict set ma_seen [$f getName] [$m getName] }
    ma_place $chain $edge $py $side
    incr ma_n
  }
}
close $ma_out
puts "OT_MIF anchored $ma_n macro interface chains ($ma_ncl clones)"
}
