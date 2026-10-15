# Contact prerequisite only. The complete PDN must still pass check_power_grid.
# Actual ASAP7 tie PG pins are single M1 rectangles; reject any unsupported map.
proc ot_const_pg_check {} {
  set block [ord::get_db_block]
  set rails {}; set cells 0; set checked 0
  foreach name {VDD VSS} {
    set net [$block findNet $name]
    if {$net eq "NULL"} continue
    foreach sw [$net getSWires] {
      foreach shape [$sw getWires] {
        set layer [$shape getTechLayer]
        if {$layer eq "NULL" || [$layer getName] ne "M1"} continue
        set box [list [$shape xMin] [$shape yMin] [$shape xMax] [$shape yMax]]
        # Sparse y buckets avoid comparing every pin against every die rail.
        for {set bin [expr {int(floor(double([$shape yMin])/1000))}]} {$bin <= int(floor(double([$shape yMax])/1000))} {incr bin} {
          dict lappend rails "$name/$bin" $box
        }
      }
    }
  }
  foreach inst [$block getInsts] {
    if {[[$inst getMaster] getName] ni {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} continue
    incr cells
    foreach name {VDD VSS} {
      set it [$inst findITerm $name]
      if {$it eq "NULL" || [$it getNet] eq "NULL" || [[$it getNet] getName] ne $name} {
        error "OT_CONST: missing actual PG binding [$inst getName]/$name"
      }
      set shapes 0
      foreach mp [[$it getMTerm] getMPins] {
        foreach geometry [$mp getGeometry] {
          if {[[$geometry getTechLayer] getName] ne "M1"} { error "OT_CONST: unsupported tie PG pin layer" }
          incr shapes
        }
      }
      if {$shapes != 1} { error "OT_CONST: unsupported tie PG pin geometry" }
      set bb [$it getBBox]; set contact 0
      for {set bin [expr {int(floor(double([$bb yMin])/1000))}]} {$bin <= int(floor(double([$bb yMax])/1000)) && !$contact} {incr bin} {
        if {![dict exists $rails "$name/$bin"]} continue
        foreach box [dict get $rails "$name/$bin"] {
          lassign $box x0 y0 x1 y1
          if {[$bb xMin]<$x1 && [$bb xMax]>$x0 && [$bb yMin]<$y1 && [$bb yMax]>$y0} { set contact 1; break }
        }
      }
      if {!$contact} { error "OT_CONST: missing literal M1 rail contact [$inst getName]/$name; PG remains OPEN" }
      incr checked
    }
  }
  puts "OT_CONST PG_CONTACT cells=$cells pins=$checked; complete PDN connectivity still required"
}
ot_const_pg_check
