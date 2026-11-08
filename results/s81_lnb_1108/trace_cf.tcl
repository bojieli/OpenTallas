# S81-LNB-1 read-only probe: cf word bits -> final (non-repeater) sinks; cf D side -> the AO21 enable mux input nets
read_db $::env(ODB)
set blk [ord::get_db_block]
set dbu [$blk getDefUnits]
set fh [open $::env(OUT) w]
proc xy {it} { set b [$it getBBox]; global dbu; return [format "%.3f\t%.3f" [expr {([$b xMin]+[$b xMax])/2.0/$dbu}] [expr {([$b yMin]+[$b yMax])/2.0/$dbu}]] }
proc rep {m} { return [regexp {^(INV|BUF|HB)} $m] }
proc fwd {net depth} {
  # final sinks of a net through repeaters
  set out {}
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} continue
    set i [$it getInst]; set m [[$i getMaster] getName]
    if {[rep $m] && $depth < 8} {
      foreach o [$i getITerms] { if {[$o isOutputSignal] && [$o getNet] ne "NULL"} { lappend out {*}[fwd [$o getNet] [expr {$depth+1}]] } }
    } else { lappend out "[$i getName]|[[$it getMTerm] getName]|[xy $it]" }
  }
  return $out
}
proc drv {net} { foreach it [$net getITerms] { if {[$it isOutputSignal]} { return "[[$it getInst] getName]|[[$it getMTerm] getName]|[xy $it]" } }; return "PIN|PIN|0\t0" }
set done [dict create]
foreach inst [$blk getInsts] {
  set nm [$inst getName]
  if {![string match "*g_u_vp_cf*native_memory*" $nm]} continue
  foreach it [$inst getITerms] {
    set mt [[$it getMTerm] getName]
    if {[$it isOutputSignal]} {
      puts $fh "Q\t$nm\t[xy $it]\t[join [fwd [$it getNet] 0] { ;; }]"
    } elseif {$mt eq "D"} {
      # the enable mux feeding D: its input nets (data q1r, enable, feedback)
      set d [drv [$it getNet]]
      set mux [lindex [split $d |] 0]
      set mi [$blk findInst $mux]
      if {$mi eq "NULL"} continue
      foreach mit [$mi getITerms] {
        if {[$mit isOutputSignal] || [$mit getNet] eq "NULL"} continue
        set n [$mit getNet]; set nn [$n getName]
        if {[dict exists $done $nn]} continue
        dict set done $nn 1
        # trace the source back through repeaters
        set src [drv $n]; set hops 0
        while {$hops < 8} {
          set si [$blk findInst [lindex [split $src |] 0]]
          if {$si eq "NULL" || ![rep [[$si getMaster] getName]]} break
          set inn ""
          foreach x [$si getITerms] { if {![$x isOutputSignal] && [$x getNet] ne "NULL" && ![[$x getNet] isSpecial]} { set inn [$x getNet] } }
          if {$inn eq ""} break
          set src [drv $inn]; incr hops
          set n $inn
        }
        puts $fh "N\t$nn\t[[$mit getMTerm] getName]\t$src\t[join [fwd $n 0] { ;; }]"
      }
    }
  }
}
close $fh
