# Eight column macros: four on the west edge, four on the east edge; logic between.
set block [ord::get_db_block]
set W [expr {[[$block getDieArea] xMax]/1000.0}]
set n 0
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getName] ne "ot_sram_1r1w_64x512_m1_r2c2"} {continue}
  set nm [string map [list {\[} {[} {\]} {]}] [$inst getName]]
  if {![regexp {g_mem\[([0-9]+)\]\.u_col} $nm -> c]} {error "unexpected macro $nm"}
  set row [expr {$c % 4}]
  set y [expr {20.0 + $row*100.0}]
  if {$c < 4} {set x 20.0;set o R0} else {set x [expr {$W-20.0-171.288}];set o MY}
  place_macro -macro_name [$inst getName] -location [list $x $y] -orientation $o
  incr n
}
if {$n != 8} {error "expected 8 column macros, placed $n"}
