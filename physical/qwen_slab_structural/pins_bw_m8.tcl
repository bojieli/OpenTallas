# Die seam fix (owner 2026-10-06): the slab port group's block-word / tree-word ports (bw_*, tw_*) on M8 at the
# array-facing (left) face, spread uniformly over the whole face, so die block words arrive horizontally on M8 over
# the tile array and land without dropping through a narrow M6/M7 strip.  Every other port keeps the IO placer
# (IO_PLACER_H / _V) and its --pin-region.  Sourced as PRE_IO_PLACEMENT: place_pins leaves these placed pins alone.
set blk [ord::get_db_block]
set names {}
foreach bt [$blk getBTerms] { set n [$bt getName]; if {[regexp {^(bw_|tw_)} $n]} { lappend names $n } }
proc ot_key {n} { if {[regexp {\[(\d+)\]} $n -> i]} { return [format %06d $i] } { return 999999 } }
set names [lsort -command {apply {{a b} {
  set c [string compare [ot_key $a] [ot_key $b]]; if {$c != 0} { return $c }; return [string compare $a $b] }}} $names]
set die [$blk getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set y0 [expr {[$die yMin] / double($dbu) + 2.16}]
set y1 [expr {[$die yMax] / double($dbu) - 2.16}]
set n [llength $names]
set p 0.08
set step [expr {max($p, floor(($y1 - $y0) / $n / $p) * $p)}]
set ys [expr {$y0 + (($y1 - $y0) - $step * ($n - 1)) / 2.0}]
set i 0
foreach nm $names {
  set y [expr {$ys + $i * $step}]
  place_pin -pin_name $nm -layer M8 -location [list 0.2 $y] -pin_size {0.4 0.04} -force_to_die_boundary
  incr i
}
puts "OT_PINS_BW_M8 pins=$n step_um=$step y=[format %.3f $ys]..[format %.3f [expr {$ys + $step * ($n - 1)}]]"
