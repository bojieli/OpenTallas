# Opt-in POST_PDN placement hook for the complete NC8/PIO2 SM_v element.
# Relocates existing response capture, result launch, and bulk-copy count cells.
# No timing exceptions, clock changes, new state, or changed handshake/arithmetic.
# The current sm_r2 clock tree still needs a separately admitted correction.
namespace eval ot_smv_boundary {
  variable block [ord::get_db_block]
  variable dbu [$block getDbUnitsPerMicron]
  variable groups
  array set groups {response {} result {} credit {}}
  proc norm {name} {string map {"\\" ""} $name}
  proc um {v} {variable dbu; expr {$v / double($dbu)}}
  proc region {name x0 y0 x1 y1 cells} {
    variable block; variable dbu
    if {$x0 >= $x1 || $y0 >= $y1} {error "SM_v: no macro-free $name corridor"}
    set area 0.0
    foreach inst $cells {
      set m [$inst getMaster]
      set area [expr {$area + double([$m getWidth])*[$m getHeight]/($dbu*$dbu)}]
      if {[$inst getRegion] ne "NULL"} {error "SM_v: overlapping cell ownership [$inst getName]"}
    }
    # Reservation includes cells only; CTS/repair/routing still require validation.
    if {$area > 0.45 * ($x1-$x0)*($y1-$y0)} {error "SM_v: $name region exceeds 45% cell screen"}
    set r [odb::dbRegion_create $block "smv_$name"]
    odb::dbBox_create $r [expr {int(ceil($x0*$dbu))}] [expr {int(ceil($y0*$dbu))}] \
                       [expr {int(floor($x1*$dbu))}] [expr {int(floor($y1*$dbu))}]
    foreach inst $cells {$r addInst $inst}
    puts "SMV_REGION $name cells [llength $cells] existing_cell_um2 $area box_um $x0 $y0 $x1 $y1"
  }
  set die [$block getDieArea]; set core [$block getCoreArea]
  set dx [um [$die xMax]]; set dy [um [$die yMax]]
  if {abs($dx-2202.768) > 0.1 || abs($dy-2072.790) > 0.1} {
    error "SM_v: requires actual complete sm_r2 geometry, not an undersized element"
  }
  set min_macro_y $dy; set max_macro_x 0.0; set macros 0
  set low_ring_top -1; set high_ring_bottom $dy
  foreach inst [$block getInsts] {
    set n [norm [$inst getName]]; set m [$inst getMaster]
    if {[$m isBlock]} {
      incr macros
      set b [$inst getBBox]
      set min_macro_y [expr {min($min_macro_y,[um [$b yMin]])}]
      set max_macro_x [expr {max($max_macro_x,[um [$b xMax]])}]
      if {[regexp {g_grp\[([01])\].*u_ring} $n -> group]} {
        if {$group == 0} {set low_ring_top [expr {max($low_ring_top,[um [$b yMax]])}]}
        if {$group == 1} {set high_ring_bottom [expr {min($high_ring_bottom,[um [$b yMin]])}]}
      }
      continue
    }
    if {![string match DFF* [$m getName]]} {continue}
    if {[regexp {^g_new\.u_pr[vd]\.g_s\[0\]\.g_[nr]\.u/q(\[|\$)} $n]} {
      lappend groups(response) $inst
    } elseif {[regexp {^g_new\.u_pr[vd]_o\.g_s\[1\]\.g_[nr]\.u/q(\[|\$)} $n]} {
      lappend groups(result) $inst
    } elseif {[regexp {^g_new\.u_bc\.g_lookahead\.(g_sram\.oq_n\[|u_free_c/q\[)} $n]} {
      lappend groups(credit) $inst
    }
  }
  if {$macros != 202 || [llength $groups(response)] != 1099 || \
      [llength $groups(result)] != 270 || [llength $groups(credit)] != 8} {
    error "SM_v: source instance census differs: macros=$macros response=[llength $groups(response)] result=[llength $groups(result)] credit=[llength $groups(credit)]"
  }
  region response [expr {$dx*.25}] [expr {[um [$core yMin]]+1}] \
                  [expr {$dx*.75}] [expr {$min_macro_y-4}] $groups(response)
  region result [expr {$max_macro_x+4}] [expr {$dy*.25}] \
                [expr {[um [$core xMax]]-1}] [expr {$dy*.75}] $groups(result)
  if {$low_ring_top < 0 || $high_ring_bottom == $dy} {error "SM_v: actual ring groups absent"}
  region credit [expr {$dx/2-80}] [expr {$low_ring_top+2}] \
                [expr {$dx/2+80}] [expr {$high_ring_bottom-2}] $groups(credit)
}
