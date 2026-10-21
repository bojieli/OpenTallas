read_db /gate/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_hc_bankq_rw8_static_asap7_ref_gate/base/3_place.odb
set block [ord::get_db_block]
set u [$block getDbUnitsPerMicron]
set out [open /out/actual_placement.tsv w]
puts $out "root\troot_x_um\troot_y_um\tdirect_iterms\tstd_cells\thard_cells\tmin_x_um\tmin_y_um\tmax_x_um\tmax_y_um\tcentroid_x_um\tcentroid_y_um"
foreach port {clk clk_c clk_o clk_w0 clk_w1 clk_w2 clk_w3 clk_x0 clk_x1 clk_x2 clk_x3 clk_d0 clk_d1 clk_d2 clk_d3 clk_h0 clk_h1 clk_h2 clk_h3 clk_f clk_e0 clk_e1 clk_e2 clk_e3 clk_i0 clk_i1 clk_i2 clk_i3 clk_q0 clk_q1 clk_q2 clk_q3} {
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
puts "CB_CLOCK_MODEL DONE: /out/actual_placement.tsv"
