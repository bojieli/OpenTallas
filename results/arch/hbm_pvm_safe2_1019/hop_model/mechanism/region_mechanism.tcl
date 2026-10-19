foreach lib [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $lib}
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_tt.lib
read_db /work/1_synth_tie_split.odb
source /macro_regions.tcl
write_db /work/regions_only.odb
exit
