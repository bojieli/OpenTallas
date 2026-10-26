# Clear only well-tap/endcap physical cells from newly reserved placement space.
# Same rule as physical/common_flow/macro_channel_block.tcl: a fixed physical-only
# cell under a hard keepout fails DPL's "placed in rows" check. Data/clock logic
# is never removed. The enclosing die/PHY owns physical cells in its reservation.
proc ot_clear_keepout_physical {block rects tag} {
  set removed 0
  foreach i [$block getInsts] {
    set m [$i getMaster]
    set type [$m getType]
    set name [$i getName]
    if {$type ne "CORE_WELLTAP" && ![string match "ENDCAP*" $type] &&
        ![string match "TAP_*" $name] && ![string match "PHY_EDGE_*" $name]} {continue}
    set b [$i getBBox]
    set x0 [$b xMin];set y0 [$b yMin];set x1 [$b xMax];set y1 [$b yMax]
    foreach r $rects {
      lassign $r a c d e
      if {$x0<$d && $x1>$a && $y0<$e && $y1>$c} {
        foreach mt [$m getMTerms] {
          set sig [$mt getSigType]
          if {$sig ne "POWER" && $sig ne "GROUND"} {
            error "keepout physical cell has non-PG pin: $name/[$mt getName] ($sig)"
          }
        }
        odb::dbInst_destroy $i
        incr removed
        break
      }
    }
  }
  puts "OT_KEEPOUT_PHYSICAL tag=$tag removed=$removed logical_cells_removed=0"
  return $removed
}
