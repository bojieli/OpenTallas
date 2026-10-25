# Place each pre-MIF data register beside its corresponding per-SRAM MIF register.
# No RTL/data wiring changes; the two existing pipeline stages keep their cycles.
uplevel #0 {
set id_blk [ord::get_db_block];set id_u [[ord::get_db_tech] getDbUnitsPerMicron]
proc id_name {i} {string map [list [format %c 92] ""] [$i getName]}
set id_map {}
foreach i [$id_blk getInsts] {dict set id_map [id_name $i] $i}
set id_n 0;set id_b 0
dict for {name src} $id_map {
  if {![regexp {^g_wr\[([01])\]\.g_r\.u_d/q\[([0-9]+)\]\$_DFF_P_$} $name -> bank bit]} continue
  set key [format {g_mw[%s].u_d/q[%s]$_DFF_P_} $bank $bit]
  if {![dict exists $id_map $key]} {error "IF_PAIR missing MIF register $key"}
  set dst [dict get $id_map $key];lassign [$dst getLocation] x y
  set x [expr {$x+int(round((($x/double($id_u))<129.6 ? -4.32 : 4.32)*$id_u))}]
  set core [$id_blk getCoreArea]
  if {$x<[$core xMin] || $x+[[$src getMaster] getWidth]>[$core xMax]} {error "IF_PAIR site outside core $name"}
  $src setPlacementStatus PLACED;$src setLocation $x $y
  foreach o [$src getITerms] {
    if {![$o isOutputSignal] || [$o getNet] eq "NULL"} continue
    foreach it [[$o getNet] getITerms] {
      if {![$it isInputSignal]} continue
      set b [$it getInst]
      if {![regexp {^(INV|BUF)} [[$b getMaster] getName]]} continue
      if {[string first [format {g_wr[%s].g_r.u_d/} $bank] [id_name $b]] != 0} continue
      $b setPlacementStatus PLACED;$b setLocation [expr {$x+int(round(0.54*$id_u))}] $y;incr id_b
    }
  }
  incr id_n
}
if {$id_n!=512} {error "IF_PAIR expected512 data register pairs, got$id_n"}
detailed_placement
check_placement -verbose
puts "IF_PAIR_PLACE PASS data_registers $id_n local_decode_cells $id_b data_changes0 added_cycles0"
}
