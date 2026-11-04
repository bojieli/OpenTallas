# PG-CORECONN-3 probe step 2: die-PDN mini-run = the plan's die_pdn_tcl (M8/M9 grid + {parts} macro grid M7 -> M8) over
# one instance of the step-1 tile abstract; counts M7->M8 vias landing on each published macro strap.
set PL /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PL/lef/asap7_tech_1x_201209.lef
read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /p/out/tile_pg3.lef
read_verilog /p/die_mini.v
link_design dpdie
initialize_floorplan -die_area {0 0 1442.88 1226.88} -core_area {0 0 1442.88 1226.88} -site asap7sc7p5t
set b [ord::get_db_block]
set t [$b findInst u_t]
$t setOrient R0; $t setLocation 0 0; $t setPlacementStatus FIRM
source /p/die_pdn.tcl
pdngen
source /p/macro_straps.tcl
array set hit {}; array set nstrap {}; set tot 0; set m78 0; set wrong 0
foreach s $straps { lassign $s k net a bb c d; incr nstrap($k); set hit($k) 0 }
foreach net {VDD VSS} {
  foreach sw [[$b findNet $net] getSWires] { foreach v [$sw getWires] {
    if {![$v isVia]} continue
    set tv [$v getTechVia]; if {$tv eq "NULL" || $tv eq ""} { set tv [$v getBlockVia] }
    if {[[$tv getBottomLayer] getName] ne "M7"} continue
    incr m78
    set x [expr {([$v xMin]+[$v xMax])/2}]; set y [expr {([$v yMin]+[$v yMax])/2}]
    foreach s $straps { lassign $s k sn a bb c d
      if {$x > $a && $x < $c && $y > $bb && $y < $d} { incr tot; incr hit($k); if {$sn ne $net} { incr wrong } ; break }
    }
  } }
}
foreach k [lsort [array names hit]] { puts "OT_PROBE die M7-M8 vias on $k straps: $hit($k) (straps $nstrap($k))" }
puts "OT_PROBE die M7-M8 vias total $m78, on published macro straps $tot, net mismatch $wrong"
