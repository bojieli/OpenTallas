# QC-CORES-2 btab_m0_r8 PRE_CTS: COORD RULING DRT-0255 (10-27 04:44) shared slice rule -- every centre-entry clock port is
# >= 0.048 x 0.48 on its M5 track (r7 pushdown placed 0.024 x 0.384).  Same centres (M5 x tracks 0.012 + k*0.048: ck 177.132,
# ft_ck_i 174.540, ft_ck_o 179.724 all on track); only the pin shape grows.  Then the unchanged r7 pre-CTS (pre_cts_m0.tcl).
foreach {p} {ck ft_ck_i ft_ck_o} {
  set bt [[ord::get_db_block] findBTerm $p]
  if {$bt eq "NULL"} { error "R8 clock port $p missing" }
  set bb [[lindex [$bt getBPins] 0] getBBox]
  set cx [expr {([$bb xMin] + [$bb xMax]) / 2000.0}]; set cy [expr {([$bb yMin] + [$bb yMax]) / 2000.0}]
  place_pin -pin_name $p -layer M5 -location [list $cx $cy] -pin_size {0.048 0.48}
  set bb [[lindex [$bt getBPins] 0] getBBox]
  set w [expr {([$bb xMax] - [$bb xMin]) / 1000.0}]; set h [expr {([$bb yMax] - [$bb yMin]) / 1000.0}]
  if {$w < 0.048 || $h < 0.48} { error "R8 clock port $p still $w x $h" }
  puts [format "R8_CLKPORT %s M5 centre (%.3f, %.3f) %.3f x %.3f (DRT-0255 rule >= 0.048 x 0.48)" $p $cx $cy $w $h]
}
source /work/pre_cts_m0.tcl
