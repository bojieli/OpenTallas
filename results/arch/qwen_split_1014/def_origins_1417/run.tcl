read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/relay.lef
read_verilog /work/top.v
link_design test
initialize_floorplan -die_area {0 0 500 500} -core_area {0 0 500 500} -site asap7sc7p5t
set b [ord::get_db_block]
set f [open /work/odb_positions.tsv w]
set k 0
foreach orient {R0 MX MY R180} {
 set i [$b findInst u$k]
 $i setOrient $orient
 $i setLocation [expr {100000+$k*50000}] 200000
 $i setPlacementStatus FIRM
 set bb [$i getBBox]
 puts $f "I	u$k	$orient	[$bb xMin]	[$bb yMin]	[$bb xMax]	[$bb yMax]"
 foreach it [$i getITerms] {
  set ib [$it getBBox]
  puts $f "P	u$k	[[$it getMTerm] getName]	[$ib xMin]	[$ib yMin]	[$ib xMax]	[$ib yMax]"
 }
 incr k
}
close $f
write_def /work/placed.def
puts OT_DEF_ORIGINS_EXPORTED
