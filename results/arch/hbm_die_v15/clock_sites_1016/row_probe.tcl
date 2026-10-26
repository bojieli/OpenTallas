read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_verilog /work/test.v
link_design test
initialize_floorplan -die_area {0 0 100 100} -core_area {0 0 100 100} -site asap7sc7p5t
set block [ord::get_db_block]
set n 0
foreach row [$block getRows] {
 puts "ROW [$row getName] [$row getOrigin] [$row getOrient] [$row getSpacing]"
 incr n
 if {$n >= 8} {break}
}
