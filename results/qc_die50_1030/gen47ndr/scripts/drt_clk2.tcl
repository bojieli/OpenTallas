# DIE-QC-50/gen47ndr stage 2 v2 (+ obsfix.tcl street-cross M1-M3 OBS fix, + RCX in-session): DETAILED ROUTE of the 48,297 clock nets only (CLK2W2S NDR, guides = the full-die NDR GRT
# guides of stage 1, so clock topology respects the signal congestion; signal nets stay GRT-only and are absent here).
# PG stripes are kept as full-span obstructions; macros (abstracts) and clock cells as placed.
set O $::env(OUT)
read_db $::env(RUN)/grt_TT/clk_grt.odb
source $::env(RUN)/obsfix.tcl
set b [ord::get_db_block]
puts "DRT_IN nets [llength [$b getNets]] gcell [expr {[$b getGCellGrid] ne "NULL"}]"
set ng 0; foreach n [$b getNets] { incr ng [llength [$n getGuides]] }
puts "DRT_IN guides $ng"
set_routing_layers -signal M1-M9 -clock M1-M9
detailed_route -output_drc $O/drc.rpt -output_maze $O/maze.log \
  -droute_end_iter $::env(ITERS) -verbose 1
puts DRT_DONE
write_db $O/clk_drt.odb
puts DRT_DB_DONE
set ot_tech [ord::get_db_tech]
[$ot_tech findLayer M1] setResistance 0.563166
[$ot_tech findLayer M2] setResistance 0.534825
[$ot_tech findLayer M3] setResistance 0.563166
[$ot_tech findLayer M4] setResistance 0.432876
[$ot_tech findLayer M5] setResistance 0.455842
[$ot_tech findLayer M6] setResistance 0.380144
[$ot_tech findLayer M7] setResistance 0.400304
[$ot_tech findLayer M8] setResistance 0.337862
[$ot_tech findLayer M9] setResistance 0.355786
extract_parasitics -ext_model_file $::env(RUN)/rcx_ndr008.rules -lef_res
write_spef $O/clk_rcx.spef
puts RCX_DONE
