foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz] {read_liberty $lib}
read_liberty /source/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
read_db /input/3_2_place_iop.odb
source /gate/src/physical/hbm_accel_die_views/coll/rtl_ps/capture_adjacent_place.tcl
write_db /gate/capture_placed.odb
