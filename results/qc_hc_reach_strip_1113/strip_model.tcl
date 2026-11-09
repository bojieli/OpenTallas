read_db /in/run/results/asap7/dp_slw_hc0__cl1bc59e1c/base/3_place.odb
set b [ord::get_db_block];set du [$b getDbUnitsPerMicron]
set f [open /out/hc0w_north_strip_model.tsv w]
set ff 0;set cells 0;set maxw 0;set maxh 0
foreach i [$b getInsts] {
 set nm [$i getName]
 if {[string match "u_bound.u_cland_rsf_i/*" $nm]} {
  incr cells
  set m [$i getMaster]
  if {[string match "DFF*" [$m getName]]} {incr ff;set maxw [expr {max($maxw,[$m getWidth]/double($du))}];set maxh [expr {max($maxh,[$m getHeight]/double($du))}]}
 }
 set bb [$i getBBox];set x [expr {([$bb xMin]+[$bb xMax])/2.0/$du}];set y [expr {([$bb yMin]+[$bb yMax])/2.0/$du}]
 if {$x<514.3 || $x>544.3 || $y<1314.3 || $y>1324.3} continue
 puts $f [join [list [$i getName] [[$i getMaster] getName] $x $y [$i getPlacementStatus]] "\t"]
}
close $f
puts "RSF_MODEL cells=$cells flops=$ff max_master_width_um=$maxw max_master_height_um=$maxh"
