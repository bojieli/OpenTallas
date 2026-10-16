set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob -nocomplain /src/physical/asap7_memory_macros_v2/*/*.lef] {read_lef $l}
set base [lindex [glob /work/results/asap7/*/base] 0]
read_db $base/5_1_grt-failed.odb
set ::env(OT_LAYOUT_OUT) /out/actual_final.json
set ::env(OT_LAYOUT_CLOCKS) clk,clk_cap,clk_mem,clk_tgt
source /src/tools/ref_tile/layout_dump.tcl
exit
