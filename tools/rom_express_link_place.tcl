# ORFS POST_PDN hook for rtl/rom/ot_rom_express_link.sv (pass it with
# tools/run_abi3_physical.py --step-tcl POST_PDN=tools/rom_express_link_place.tcl).
#
# Fixes the link's register columns at their distance along a long, thin die,
# so the routed wire between two columns really spans that distance:
#
#   column 0            launch_data[*], launch_valid      west core edge
#   column 1+s          chain_data[s*W +: W], chain_valid[s]
#   column STAGES+1     out_data[*], out_valid, out_err   east core edge
#
# Columns are evenly spaced between the core edges (2 um in), snapped to the
# placement site and nudged east past any tap cell.  Bit b of every column sits
# in the same row, so each bit's wire runs straight east-west.  Without this a
# timing-driven placer is free to put the launch register next to the capture
# register and leave the long wire on the (untimed) pin side.  Everything else
# -- repeaters, clock tree, boundary logic -- is placed by the flow as usual.

set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set core [$block getCoreArea]

set rows {}
foreach row [$block getRows] {
  lappend rows [list [lindex [$row getOrigin] 1] $row]
}
set rows [lsort -integer -index 0 $rows]

# Tap cells per row y, as {x0 x1} intervals.
set taps [dict create]
foreach inst [$block getInsts] {
  if {[string match "TAPCELL*" [[$inst getMaster] getName]]} {
    set box [$inst getBBox]
    dict lappend taps [$box yMin] [list [$box xMin] [$box xMax]]
  }
}

set width 0
set stages 0
set placements {}
foreach inst [$block getInsts] {
  if {![string match "*DFF*" [[$inst getMaster] getName]]} { continue }
  set name [string map {"\\" ""} [$inst getName]]
  if {[regexp {^launch_data\[(\d+)\]} $name -> b]} {
    lappend placements [list $inst launch $b]
    set width [expr {max($width, $b + 1)}]
  } elseif {[regexp {^launch_valid} $name]} {
    lappend placements [list $inst launch valid]
  } elseif {[regexp {^chain_data\[(\d+)\]} $name -> k]} {
    lappend placements [list $inst chain_data $k]
  } elseif {[regexp {^chain_valid\[(\d+)\]} $name -> k]} {
    lappend placements [list $inst chain_valid $k]
    set stages [expr {max($stages, $k + 1)}]
  } elseif {[regexp {^chain_valid\$} $name]} {
    lappend placements [list $inst chain_valid 0]
    set stages [expr {max($stages, 1)}]
  } elseif {[regexp {^out_data\[(\d+)\]} $name -> b]} {
    lappend placements [list $inst out $b]
  } elseif {[regexp {^out_valid} $name]} {
    lappend placements [list $inst out valid]
  } elseif {[regexp {^out_err} $name]} {
    lappend placements [list $inst out err]
  }
}
if {$width == 0} { error "rom_express_link_place: no launch_data registers found" }

set ncol [expr {$stages + 2}]
set nbits [expr {$width + 2}]
if {$nbits > [llength $rows]} { error "rom_express_link_place: $nbits bit rows need more than [llength $rows] rows" }
set row0 [expr {([llength $rows] - $nbits) / 2}]
set x_left [expr {[$core xMin] + 2 * $dbu}]
set x_right [expr {[$core xMax] - 4 * $dbu}]

set columns {}
foreach p $placements {
  lassign $p inst kind idx
  switch $kind {
    launch      { set col 0 }
    out         { set col [expr {$ncol - 1}] }
    chain_data  { set col [expr {1 + $idx / $width}]; set idx [expr {$idx % $width}] }
    chain_valid { set col [expr {1 + $idx}]; set idx valid }
  }
  if {$idx eq "valid"} { set bit $width } elseif {$idx eq "err"} { set bit [expr {$width + 1}] } else { set bit $idx }
  lassign [lindex $rows [expr {$row0 + $bit}]] y row
  set site [$row getSite]
  set sw [$site getWidth]
  set ox [lindex [$row getOrigin] 0]
  set x [expr {$x_left + round(double($col) * ($x_right - $x_left) / ($ncol - 1))}]
  set x [expr {$ox + (($x - $ox) / $sw) * $sw}]
  set w [[$inst getMaster] getWidth]
  set moved 1
  while {$moved} {
    set moved 0
    if {[dict exists $taps $y]} {
      foreach iv [dict get $taps $y] {
        lassign $iv t0 t1
        if {$x < $t1 && $x + $w > $t0} { set x [expr {$x + $sw}]; set moved 1 }
      }
    }
  }
  $inst setOrient [$row getOrient]
  $inst setLocation $x $y
  $inst setPlacementStatus FIRM
  dict lappend columns $col [expr {double($x) / $dbu}]
}

puts "rom_express_link_place: W=$width STAGES=$stages columns=$ncol"
foreach col [lsort -integer [dict keys $columns]] {
  set xs [dict get $columns $col]
  puts [format "rom_express_link_place: column %d x %.3f..%.3f um (%d registers)" \
    $col [tcl::mathfunc::min {*}$xs] [tcl::mathfunc::max {*}$xs] [llength $xs]]
}
