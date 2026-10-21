read_db /gate/3_place.odb
set block [ord::get_db_block]
set u [$block getDbUnitsPerMicron]
set out [open /out/actual_placement.tsv w]
puts $out "root\troot_x_um\troot_y_um\tdirect_iterms\tstd_cells\thard_cells\tmin_x_um\tmin_y_um\tmax_x_um\tmax_y_um\tcentroid_x_um\tcentroid_y_um"
foreach port {clk clk_c clk_ce clk_w0 clk_w1 clk_w2 clk_w3 clk_x0 clk_x1 clk_x2 clk_x3 clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_e0 clk_e1 clk_e2 clk_e3} {
 set bt [$block findBTerm $port]
 if {$bt eq "NULL"} {error "missing original root $port"}
 set net [$bt getNet]
 set px 0; set py 0; set got 0
 foreach bp [$bt getBPins] {foreach b [$bp getBoxes] {if {!$got} {set px [expr {([$b xMin]+[$b xMax])/2.0/$u}];set py [expr {([$b yMin]+[$b yMax])/2.0/$u}];set got 1}}}
 set lo_x 1e30; set lo_y 1e30;set hi_x -1e30;set hi_y -1e30;set sx 0;set sy 0;set ns 0;set nh 0
 foreach it [$net getITerms] {
  if {![$it isInputSignal]} continue
  set inst [$it getInst];set master [$inst getMaster]
  if {[$master isBlock]} {incr nh;continue}
  set bb [$inst getBBox]
  set x [expr {([$bb xMin]+[$bb xMax])/2.0/$u}];set y [expr {([$bb yMin]+[$bb yMax])/2.0/$u}]
  set lo_x [expr {min($lo_x,$x)}];set lo_y [expr {min($lo_y,$y)}];set hi_x [expr {max($hi_x,$x)}];set hi_y [expr {max($hi_y,$y)}]
  set sx [expr {$sx+$x}];set sy [expr {$sy+$y}];incr ns
 }
 set cx [expr {$ns?$sx/$ns:0}];set cy [expr {$ns?$sy/$ns:0}]
 puts $out [join [list $port $px $py [llength [$net getITerms]] $ns $nh $lo_x $lo_y $hi_x $hi_y $cx $cy] "\t"]
}
close $out
puts "E2_CLOCK_MODEL DONE: /out/actual_placement.tsv"

set pins [open /out/actual_clock_sinks.tsv w]
puts $pins "root\tinstance\tmaster\tpin\tx_um\ty_um\tis_macro"
foreach root {clk clk_c clk_ce clk_w0 clk_w1 clk_w2 clk_w3 clk_x0 clk_x1 clk_x2 clk_x3 clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_e0 clk_e1 clk_e2 clk_e3} {
 set bt [$block findBTerm $root]
 foreach it [[$bt getNet] getITerms] {
  if {![$it isInputSignal]} continue
  set inst [$it getInst];set master [$inst getMaster];set b [$it getBBox]
  puts $pins [join [list $root [$inst getName] [$master getName] [[$it getMTerm] getName] [expr {([$b xMin]+[$b xMax])/2.0/$u}] [expr {([$b yMin]+[$b yMax])/2.0/$u}] [$master isBlock]] "\t"]
 }
}
close $pins
set macros [open /out/actual_macros.tsv w]
puts $macros "instance\tmaster\tx0_um\ty0_um\tx1_um\ty1_um"
foreach inst [$block getInsts] {
 if {![[$inst getMaster] isBlock]} continue
 set b [$inst getBBox]
 puts $macros [join [list [$inst getName] [[$inst getMaster] getName] [expr {[$b xMin]/double($u)}] [expr {[$b yMin]/double($u)}] [expr {[$b xMax]/double($u)}] [expr {[$b yMax]/double($u)}]] "\t"]
}
close $macros
puts "E2_CLOCK_MODEL ALL_DONE read-only original3_place geometry; no clockqualification"
