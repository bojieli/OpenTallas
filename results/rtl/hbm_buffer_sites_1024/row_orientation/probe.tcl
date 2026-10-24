set PL /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PL/lef/asap7_tech_1x_201209.lef
read_lef $PL/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_def /work/probe.def
foreach i [[ord::get_db_block] getInsts] {set b [$i getBBox];puts "INST [$i getName] origin=[$i getOrigin] loc=[$i getLocation] box=[$b xMin],[$b yMin],[$b xMax],[$b yMax]"}
check_placement -verbose
