# Companion to assumed_access.py v1. No historical abstract may use this grid.
proc ot_assumed_phy_pg_grids {} {
  set block [ord::get_db_block]; set dbu [$block getDbUnitsPerMicron]; set n 0
  foreach inst [$block getInsts] {
    set master [$inst getMaster]; set name [$master getName]
    if {![regexp {^(OT_PDN_BBOX_)?ot_q(fd_serdes_112g_x12|fd_ucie_x64|kvd_ucie_x64)_phy} $name]} continue
    # A planning PHY with real M7/M8 PG access stays on its existing grid.
    # Only the actual M4-only interface needs this revised access contract.
    set m4nets 0
    foreach net {VDD VSS} {
      set term [$master findMTerm $net]; set ls {}
      if {$term ne "NULL"} {foreach mp [$term getMPins] {foreach box [$mp getGeometry] {
        lappend ls [[$box getTechLayer] getName]
      }}}
      if {[lsort -unique $ls] eq "M4"} {incr m4nets}
    }
    if {!$m4nets} {continue}
    if {$m4nets != 2} {error "OT_ASSUMED_PHY_PG: asymmetric M4 power profile $name"}
    set width [expr {[$master getWidth]/double($dbu)}]
    set left [expr {floor(($width-2.0)/0.048+1e-7)*0.048}]
    set orient [$inst getOrient]
    if {$orient in {R0 MX}} {set offset [expr {$left+.06}]} elseif {$orient in {MY R180}} {
      set offset [expr {$width-$left-1.068}]
    } else {error "OT_ASSUMED_PHY_PG: unsupported orientation $orient"}
    # The exact two access windows must be free of M5 OBS. Never silently carve
    # ODB geometry here; caller must load a source-pinned v1 candidate LEF.
    foreach obs [$master getObstructions] {
      if {[[$obs getTechLayer] getName] ne "M5"} continue
      foreach c [list [expr {$left+.06}] [expr {$left+1.068}]] {
        if {[$obs xMin] < ($c+.20-1e-7)*$dbu && [$obs xMax] > ($c-.20+1e-7)*$dbu} {
          error "OT_ASSUMED_PHY_PG: $name has blocked declared M5 PG access; historical LEF forbidden"
        }
      }
    }
    set grid ot_assumed_phy_$n
    define_pdn_grid -macro -instances [list "^[$inst getName]$"] -voltage_domains CORE -name $grid -halo {0 0 0 0} -grid_over_boundary -starts_with POWER
    add_pdn_stripe -grid $grid -layer M5 -width .12 -pitch 2.016 -spacing .888 -offset $offset -number_of_straps 1 -starts_with POWER
    add_pdn_connect -grid $grid -layers {M4 M5}
    add_pdn_connect -grid $grid -layers {M5 M8}
    puts "OT_ASSUMED_PHY_PG instance=[$inst getName] orient=$orient offset=$offset reserved_M5_columns=2"
    incr n
  }
  if {!$n} {error "OT_ASSUMED_PHY_PG: no modeled PHY found"}
}
