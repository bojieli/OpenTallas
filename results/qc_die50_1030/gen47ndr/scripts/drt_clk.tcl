# DIE-QC-50/gen47ndr stage 2: DETAILED ROUTE of the 48,297 clock nets only (CLK2W2S NDR, guides = the full-die NDR GRT
# guides of stage 1, so clock topology respects the signal congestion; signal nets stay GRT-only and are absent here).
# PG stripes are kept as full-span obstructions; macros (abstracts) and clock cells as placed.
set O $::env(OUT)
read_db $::env(RUN)/grt_TT/clk_grt.odb
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
